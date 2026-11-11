"""Crea data/processed/turismo.duckdb a partir de los archivos listados en data/raw/archivos.csv.

Uso:
    python -m src.cargar
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from src.limpieza import clave_pais, extraer_cuadro_pdf, leer_cuadro, leer_serie, nombre_preferido, validar

RAIZ = Path(__file__).resolve().parents[1]
RAW = RAIZ / "data" / "raw"
DB = RAIZ / "data" / "processed" / "turismo.duckdb"

NOMBRES_MES = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio",
    "Agosto", "Setiembre", "Octubre", "Noviembre", "Diciembre",
]  # fmt: skip

ESQUEMA = """
CREATE TABLE dim_fecha (
  fecha DATE PRIMARY KEY, anio INT, mes INT, nombre_mes VARCHAR, temporada VARCHAR
);
CREATE TABLE dim_pais (
  pais_id INT PRIMARY KEY, pais VARCHAR UNIQUE, region VARCHAR NOT NULL
);
CREATE TABLE fact_llegadas (
  fecha DATE REFERENCES dim_fecha, pais_id INT REFERENCES dim_pais,
  via VARCHAR, llegadas INT CHECK (llegadas >= 0),
  PRIMARY KEY (fecha, pais_id, via)
);
-- Totales mensuales tal como los publica el ICT (cuadros 11-14 y filas TOTAL).
-- Sirven para la serie 2019+ sin desglose por país y para validar fact_llegadas.
CREATE TABLE serie_publicada (
  fecha DATE REFERENCES dim_fecha, via VARCHAR, llegadas INT CHECK (llegadas >= 0),
  PRIMARY KEY (fecha, via)
);
"""


def temporada(mes: int) -> str:
    """Temporada alta = estación seca (diciembre a abril)."""
    return "Alta" if mes in (12, 1, 2, 3, 4) else "Baja"


def unificar_paises(datos: pd.DataFrame) -> pd.DataFrame:
    """'PANAMA' (cuadro 1) y 'Panamá' (cuadro 7) quedan como un solo país."""
    clave = datos["pais"].map(clave_pais)
    nombres = datos.groupby(clave)["pais"].agg(lambda s: nombre_preferido(list(s.unique())))
    return datos.assign(pais=clave.map(nombres))


def unir_series(series: list[pd.DataFrame]) -> pd.DataFrame:
    """Une las series publicadas y falla si dos cuadros dan cifras distintas para el mismo mes."""
    todo = pd.concat(series, ignore_index=True).dropna()
    conflictos = todo.groupby(["fecha", "via"])["llegadas"].nunique()
    if (conflictos > 1).any():
        raise ValueError(f"Cuadros del ICT con totales distintos:\n{conflictos[conflictos > 1]}")
    return todo.drop_duplicates(["fecha", "via"]).sort_values(["via", "fecha"]).reset_index(drop=True)


def leer_todo() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Lee data/raw/archivos.csv. Devuelve (datos por país, serie publicada)."""
    manifiesto = pd.read_csv(RAW / "archivos.csv")
    datos, series = [], []
    for f in manifiesto.itertuples():
        grilla = extraer_cuadro_pdf(RAW / f.archivo, pagina=int(f.pagina), cuadro=int(f.cuadro))
        if f.tipo == "paises":
            d, t = leer_cuadro(grilla, anio=int(f.anio), via=f.via)
            validar(d, t)
            datos.append(d)
            series.append(t.rename(columns={"total_publicado": "llegadas"}).assign(via=f.via))
        elif f.tipo == "serie":
            series.append(leer_serie(grilla, via=f.via))
        else:
            raise ValueError(f"tipo desconocido en archivos.csv: {f.tipo}")
    return unificar_paises(pd.concat(datos, ignore_index=True)), unir_series(series)


def construir(datos: pd.DataFrame, serie: pd.DataFrame, ruta: Path | str = DB):
    """Crea la base desde cero. Devuelve la conexión abierta."""
    if ruta != ":memory:":
        ruta = Path(ruta)
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.unlink(missing_ok=True)
    con = duckdb.connect(str(ruta))
    con.execute(ESQUEMA)

    todas = pd.concat([datos["fecha"], serie["fecha"]]).drop_duplicates().sort_values()
    fechas = pd.DataFrame({"fecha": pd.to_datetime(todas.values)})
    fechas["anio"] = fechas["fecha"].dt.year
    fechas["mes"] = fechas["fecha"].dt.month
    fechas["nombre_mes"] = fechas["mes"].map(lambda m: NOMBRES_MES[m - 1])
    fechas["temporada"] = fechas["mes"].map(temporada)

    paises = datos[["pais", "region"]].drop_duplicates("pais").sort_values("pais")
    paises.insert(0, "pais_id", range(1, len(paises) + 1))

    # DuckDB lee `fechas`, `paises`, `hechos` y `serie` por nombre de variable
    hechos = datos.merge(paises[["pais", "pais_id"]], on="pais")[  # noqa: F841
        ["fecha", "pais_id", "via", "llegadas"]
    ]

    con.execute("INSERT INTO dim_fecha SELECT * FROM fechas")
    con.execute("INSERT INTO dim_pais SELECT * FROM paises")
    con.execute("INSERT INTO fact_llegadas SELECT * FROM hechos")
    con.execute("INSERT INTO serie_publicada SELECT fecha, via, llegadas FROM serie")
    return con


if __name__ == "__main__":
    datos, serie = leer_todo()
    con = construir(datos, serie)
    n = con.execute("SELECT count(*) FROM fact_llegadas").fetchone()[0]
    m = con.execute("SELECT count(*) FROM serie_publicada").fetchone()[0]
    print(f"OK: {n:,} filas por país y {m:,} meses de serie publicada -> {DB}")
