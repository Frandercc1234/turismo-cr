"""Cada año con detalle por país cuadra con su fila TOTAL y con la serie publicada del ICT."""

import duckdb
import pandas as pd
import pytest

from src.cargar import DB, RAW
from src.limpieza import extraer_cuadro_pdf, leer_cuadro, validar

pytestmark = pytest.mark.skipif(not DB.exists(), reason="Falta data/processed/turismo.duckdb")

MANIFIESTO = pd.read_csv(RAW / "archivos.csv")
PAISES = MANIFIESTO[MANIFIESTO["tipo"] == "paises"]
ANIOS = sorted(int(a) for a in PAISES["anio"].unique())
VIAS_ESPERADAS = {"todas", "aerea", "sjo", "lir", "terrestre"}


@pytest.fixture(scope="module")
def con():
    return duckdb.connect(str(DB), read_only=True)


def test_hay_detalle_por_pais_de_2019_a_2025():
    assert ANIOS == list(range(2019, 2026))


@pytest.mark.parametrize("anio", ANIOS)
def test_total_por_pais_cuadra_con_su_fila_total_y_con_la_serie_publicada(anio, con):
    cuadros = PAISES[PAISES["anio"] == anio]
    assert VIAS_ESPERADAS <= set(cuadros["via"])
    for f in cuadros.itertuples():
        grilla = extraer_cuadro_pdf(RAW / f.archivo, int(f.pagina), int(f.cuadro), int(f.paginas))
        datos, totales = leer_cuadro(grilla, anio=anio, via=f.via)
        validar(datos, totales)  # la suma de países de cada mes es igual a la fila TOTAL del cuadro
        publicada = con.execute(
            "SELECT fecha, llegadas FROM serie_publicada WHERE via = ? AND year(fecha) = ?", [f.via, anio]
        ).df()
        con_total = totales.dropna(subset=["total_publicado"])
        cruce = con_total.merge(publicada, on="fecha", how="left")
        assert cruce["llegadas"].notna().all(), f"{f.via} {anio}: meses sin serie publicada"
        assert (cruce["total_publicado"] == cruce["llegadas"]).all(), (
            f"{f.via} {anio}: TOTAL distinto de la serie"
        )


@pytest.mark.parametrize("anio", ANIOS)
def test_suma_de_paises_en_la_base_es_igual_a_la_serie_publicada(anio, con):
    df = con.execute(
        """
        SELECT s.via, s.fecha, s.llegadas AS total, sum(f.llegadas) AS suma
        FROM serie_publicada s JOIN fact_llegadas f USING (fecha, via)
        WHERE year(s.fecha) = ?
        GROUP BY ALL
        """,
        [anio],
    ).df()
    assert not df.empty
    assert (df["total"] == df["suma"]).all(), df[df["total"] != df["suma"]]


def _anual(con, **filtros):
    from src.consultas import serie_mensual

    serie = serie_mensual(con, via="lir", desde=2019, hasta=2025, **filtros)
    return serie.groupby(serie["fecha"].dt.year)["llegadas"].sum(), serie


def test_recuperacion_de_estados_unidos_y_canada_en_lir_contra_2019(con):
    from src.indicadores import acumulado_vs_2019

    esperado = {"Estados Unidos": (695_273, 57.8, 2022), "Canadá": (173_618, 55.4, 2023)}
    for pais, (llegadas, variacion, supera_en) in esperado.items():
        por_anio, serie = _anual(con, regiones=[], paises=[pais])
        total, var, meses = acumulado_vs_2019(serie, 2025)
        assert (int(total), round(var * 100, 1), meses) == (llegadas, variacion, 12)
        primero = por_anio[(por_anio.index > 2019) & (por_anio > por_anio[2019])].index.min()
        assert primero == supera_en
    lir, _ = _anual(con, regiones=[], paises=[])
    norte, _ = _anual(con, regiones=[], paises=["Estados Unidos", "Canadá"])
    assert round(norte[2019] / lir[2019] * 100, 1) == 92.1
    assert round(norte[2025] / lir[2025] * 100, 1) == 96.0


def test_pais_nuevo_de_los_anuarios_tiene_idioma(con):
    idioma = con.execute("SELECT idioma FROM dim_pais WHERE pais LIKE 'Rep. Dem. Pop. Corea%'").fetchall()
    assert idioma == [("coreano",)]
