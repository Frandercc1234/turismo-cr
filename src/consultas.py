"""SQL parametrizado que usa la app.

Importante: cada consulta filtra por UNA vía. "todas" ya incluye aérea y terrestre,
así que sumar varias vías duplica las cifras.
"""

from __future__ import annotations

import duckdb
import pandas as pd

JOINS = """
FROM fact_llegadas f
JOIN dim_pais p USING (pais_id)
JOIN dim_fecha d USING (fecha)
"""


def _base(via, desde, hasta, regiones=(), paises=()) -> tuple[str, dict]:
    """FROM + WHERE con solo los filtros activos (evita pasar listas vacías a DuckDB)."""
    where = ["f.via = $via", "d.anio BETWEEN $desde AND $hasta"]
    params = {"via": via, "desde": desde, "hasta": hasta}
    if regiones:
        where.append("list_contains($regiones, p.region)")
        params["regiones"] = list(regiones)
    if paises:
        where.append("list_contains($paises, p.pais)")
        params["paises"] = list(paises)
    return JOINS + "WHERE " + " AND ".join(where), params


def opciones(con: duckdb.DuckDBPyConnection) -> dict:
    return {
        "vias": [r[0] for r in con.execute("SELECT DISTINCT via FROM fact_llegadas ORDER BY 1").fetchall()],
        "anios": [r[0] for r in con.execute("SELECT DISTINCT anio FROM dim_fecha ORDER BY 1").fetchall()],
        "paises": con.execute("SELECT pais, region FROM dim_pais ORDER BY region, pais").df(),
        "actualizado": con.execute("SELECT max(fecha) FROM fact_llegadas").fetchone()[0],
    }


def serie_mensual(con, **filtros) -> pd.DataFrame:
    """P1: llegadas por mes y comparación contra el mismo mes de 2019.

    Sin filtro de país o región usa la serie publicada por el ICT (2019 en adelante).
    Con filtro usa fact_llegadas, que solo cubre los años con detalle por país.
    La base 2019 se toma siempre completa, aunque el rango filtrado no la incluya.
    """
    if filtros.get("regiones") or filtros.get("paises"):
        base_sql, p = _base(**filtros)
        sql = f"""SELECT d.fecha, d.mes, d.semana_santa, sum(f.llegadas) AS llegadas
        {base_sql} GROUP BY ALL ORDER BY 1"""
    else:
        p = {k: filtros[k] for k in ("via", "desde", "hasta")}
        sql = """
        SELECT d.fecha, d.mes, d.semana_santa, s.llegadas
        FROM serie_publicada s JOIN dim_fecha d USING (fecha)
        WHERE s.via = $via AND d.anio BETWEEN $desde AND $hasta
        ORDER BY 1
        """
    serie = con.execute(sql, p).df()
    base = con.execute(sql, {**p, "desde": 2019, "hasta": 2019}).df()[["mes", "llegadas"]]
    serie = serie.merge(base.rename(columns={"llegadas": "llegadas_2019"}), on="mes", how="left")
    serie["vs_2019"] = serie["llegadas"] / serie["llegadas_2019"] - 1
    return serie


def variacion_interanual(con, **filtros) -> pd.DataFrame:
    """Variación contra el mismo mes del año anterior, por país.

    Usa una fecha explícita (fecha - 12 meses) en lugar de LAG(12) para no
    comparar contra el mes equivocado cuando falta un mes.
    """
    base_sql, p = _base(**{**filtros, "desde": filtros["desde"] - 1})  # incluye el año previo
    sql = f"""
    WITH mensual AS (
      SELECT p.pais, p.region, d.fecha, sum(f.llegadas) AS total {base_sql} GROUP BY ALL
    )
    SELECT a.pais, a.region, a.fecha, a.total, b.total AS total_anio_previo,
           a.total / NULLIF(b.total, 0) - 1 AS variacion_interanual
    FROM mensual a
    LEFT JOIN mensual b ON b.pais = a.pais AND b.fecha = a.fecha - INTERVAL 12 MONTH
    ORDER BY a.pais, a.fecha
    """
    df = con.execute(sql, p).df()
    return df[df["fecha"].dt.year >= filtros["desde"]].reset_index(drop=True)


MIN_PARTICIPACION = 0.005


def ranking_paises(
    con, top: int = 10, min_participacion: float = MIN_PARTICIPACION, **filtros
) -> pd.DataFrame:
    """P2: países con más llegadas en el último año del rango y su crecimiento
    frente al año anterior, comparando solo los meses que ambos años tienen.
    Excluye las filas agregadas "Otros <región>", que no son un país.

    `califica` marca a los países cuyas llegadas del año previo son al menos
    `min_participacion` del total de la vía en ese año (sin filtro de región ni país):
    así un salto de 50 a 100 llegadas no cuenta como "mayor crecimiento".
    """
    hasta = filtros["hasta"]
    base_sql, p = _base(**{**filtros, "desde": hasta - 1})
    total_sql, _ = _base(via=filtros["via"], desde=hasta - 1, hasta=hasta)
    sql = f"""
    WITH m AS (
      SELECT p.pais, p.region, d.anio, d.mes, sum(f.llegadas) AS llegadas
      {base_sql} AND p.pais NOT LIKE 'Otros %' GROUP BY ALL
    ),
    meses_comunes AS (
      SELECT mes FROM m GROUP BY mes HAVING count(DISTINCT anio) = 2
    ),
    total_previo AS (
      SELECT sum(f.llegadas) AS total {total_sql} AND d.anio = {hasta - 1}
        AND (d.mes IN (SELECT mes FROM meses_comunes) OR NOT EXISTS (SELECT 1 FROM meses_comunes))
    )
    SELECT pais, region,
           sum(llegadas) FILTER (WHERE anio = {hasta}) AS llegadas,
           sum(llegadas) FILTER (WHERE anio = {hasta - 1}) AS llegadas_previo,
           sum(llegadas) FILTER (WHERE anio = {hasta}) /
             NULLIF(sum(llegadas) FILTER (WHERE anio = {hasta - 1}), 0) - 1 AS crecimiento,
           COALESCE(sum(llegadas) FILTER (WHERE anio = {hasta - 1})
             >= {float(min_participacion)} * (SELECT total FROM total_previo), false) AS califica
    FROM m
    WHERE mes IN (SELECT mes FROM meses_comunes) OR NOT EXISTS (SELECT 1 FROM meses_comunes)
    GROUP BY ALL
    ORDER BY llegadas DESC NULLS LAST
    LIMIT {int(top)}
    """
    return con.execute(sql, p).df()


def idiomas_principales(con, top: int = 3, **filtros) -> pd.DataFrame:
    """P2: idiomas de atención con más llegadas en el último año del rango, como parte del
    total de llegadas con los filtros activos. 'Varios' (los agregados "Otros ...") cuenta
    en el total pero no se lista."""
    base_sql, p = _base(**{**filtros, "desde": filtros["hasta"]})
    sql = f"""
    WITH t AS (SELECT p.idioma, sum(f.llegadas) AS llegadas {base_sql} GROUP BY ALL)
    SELECT idioma, llegadas, llegadas / (SELECT sum(llegadas) FROM t) AS participacion
    FROM t WHERE idioma <> 'Varios'
    ORDER BY llegadas DESC LIMIT {int(top)}
    """
    return con.execute(sql, p).df()


def mas_crece(rk: pd.DataFrame) -> pd.Series | None:
    """Fila del ranking con mayor crecimiento entre los países que califican."""
    elegibles = rk[rk["califica"]].dropna(subset=["crecimiento"])
    return None if elegibles.empty else elegibles.loc[elegibles["crecimiento"].idxmax()]


def mapa_calor(con, top: int = 12, **filtros) -> pd.DataFrame:
    """P3: participación de cada mes en el año, por país (promedio del rango).
    Excluye las filas agregadas "Otros <región>", que no son un país."""
    base_sql, p = _base(**filtros)
    sql = f"""
    WITH m AS (
      SELECT p.pais, d.anio, d.mes, sum(f.llegadas) AS llegadas
      {base_sql} AND p.pais NOT LIKE 'Otros %' GROUP BY ALL
    ),
    principales AS (
      SELECT pais FROM m GROUP BY pais ORDER BY sum(llegadas) DESC LIMIT {int(top)}
    )
    SELECT pais, mes, sum(llegadas) AS llegadas,
           sum(llegadas) / sum(sum(llegadas)) OVER (PARTITION BY pais) AS participacion
    FROM m WHERE pais IN (SELECT pais FROM principales)
    GROUP BY pais, mes ORDER BY pais, mes
    """
    return con.execute(sql, p).df()


def datos_filtrados(con, **filtros) -> pd.DataFrame:
    base_sql, p = _base(**filtros)
    return con.execute(
        f"SELECT d.fecha, p.pais, p.region, f.via, f.llegadas {base_sql} ORDER BY 1, 2", p
    ).df()


def totales_vs_publicados(con) -> pd.DataFrame:
    """Para pruebas: suma de países vs total publicado, en los meses con detalle por país."""
    return con.execute("""
        SELECT s.fecha, s.via, s.llegadas AS total_publicado, sum(f.llegadas) AS suma
        FROM serie_publicada s
        JOIN fact_llegadas f USING (fecha, via)
        GROUP BY ALL ORDER BY 1, 2
    """).df()
