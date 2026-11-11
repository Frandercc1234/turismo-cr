"""Dashboard de llegadas internacionales a Costa Rica (datos ICT).

Uso:
    streamlit run app.py
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import streamlit as st

from src import consultas as q
from src import graficos as g
from src import indicadores as ind
from src.estilo import MESES_CORTOS, fmt

DB = Path(__file__).parent / "data" / "processed" / "turismo.duckdb"
NOMBRE_VIA = {"todas": "Todas las vías", "aerea": "Aérea", "terrestre": "Terrestre",
              "sjo": "Aeropuerto Juan Santamaría", "lir": "Aeropuerto de Liberia (LIR)",
              "maritima": "Marítima"}  # fmt: skip

MES_LARGO = {3: "marzo", 4: "abril"}

st.set_page_config(page_title="Turismo CR", layout="wide")


@st.cache_resource
def conexion():
    return duckdb.connect(str(DB), read_only=True)


def mes_anio(fecha) -> str:
    return f"{MESES_CORTOS[fecha.month - 1]} {fecha.year}"


def grafica(fig):
    st.plotly_chart(fig, theme=None, width="stretch", config={"displayModeBar": False})


def metrica(col, etiqueta: str, valor: str, variacion, referencia: str):
    """Métrica con variación contra una referencia; 'sin base' si no hay con qué comparar."""
    hay = variacion is not None and variacion == variacion
    col.metric(
        etiqueta, valor, border=True, delta_color="normal" if hay else "off",
        delta_arrow="auto" if hay else "off",
        delta=f"{fmt(variacion, 'pct')} {referencia}" if hay else "sin base 2019",
    )  # fmt: skip


if not DB.exists():
    st.error("No existe data/processed/turismo.duckdb. Corré `python -m src.cargar` primero.")
    st.stop()

con = conexion()
op = q.opciones(con)

# ---------- Filtros ----------
DEFAULTS = {"via": "lir" if "lir" in op["vias"] else op["vias"][0],
            "rango": (max(2019, op["anios"][0]), op["anios"][-1]), "regiones": [], "paises": []}  # fmt: skip
for k, v in DEFAULTS.items():
    st.session_state.setdefault(k, v)


def restablecer():
    for k, v in DEFAULTS.items():
        st.session_state[k] = v


st.title("Llegadas a Costa Rica")
st.caption(f"Fuente: ICT · Datos hasta {mes_anio(op['actualizado'])}")

n_extra = len(st.session_state.regiones) + len(st.session_state.paises)
c_via, c_rango, c_mas = st.columns([2, 3, 1.3], vertical_alignment="bottom")
c_via.selectbox("Vía de ingreso", op["vias"], key="via", format_func=lambda v: NOMBRE_VIA.get(v, v))
if len(op["anios"]) > 1:
    c_rango.slider("Años", op["anios"][0], op["anios"][-1], key="rango")
with c_mas.popover(f"Más filtros ({n_extra})" if n_extra else "Más filtros", width="stretch"):
    st.multiselect("Región", sorted(op["paises"]["region"].unique()), key="regiones", placeholder="Todas")
    disponibles = op["paises"]
    if st.session_state.regiones:
        disponibles = disponibles[disponibles["region"].isin(st.session_state.regiones)]
    st.multiselect("País", disponibles["pais"], key="paises", placeholder="Todos")
    st.button("Restablecer filtros", on_click=restablecer, width="stretch")

desde, hasta = st.session_state.rango
filtros = dict(via=st.session_state.via, desde=desde, hasta=hasta,
               regiones=st.session_state.regiones, paises=st.session_state.paises)  # fmt: skip
con_detalle = bool(filtros["regiones"] or filtros["paises"])
via = NOMBRE_VIA.get(filtros["via"], filtros["via"])

serie = q.serie_mensual(con, **filtros)
if serie.empty:
    st.info("No hay datos para esta combinación de filtros. Probá ampliar el rango o quitar países.")
    st.stop()

# ---------- P1: recuperación ----------
with st.container(border=True):
    st.subheader("1. ¿El mercado ya se recuperó?")
    st.caption(f"{via}, contra el mismo mes de 2019.")
    ult = serie.dropna(subset=["llegadas"]).iloc[-1]
    anio = ult["fecha"].year
    acum = ind.acumulado_vs_2019(serie, anio)
    pais = None
    if filtros["via"] != "todas" and not con_detalle:
        sp = q.serie_mensual(con, **{**filtros, "via": "todas"})
        pais = ind.acumulado_vs_2019(sp, anio)
    cols = st.columns(3 if pais else 2)
    metrica(cols[0], mes_anio(ult["fecha"]), fmt(ult["llegadas"]), ult["vs_2019"], "vs mismo mes 2019")
    total, variacion, n = acum
    metrica(cols[1], f"Año {anio}" if n == 12 else f"{anio} ({n} meses)", fmt(total), variacion, "vs 2019")
    if pais:
        metrica(cols[2], "Todo el país (todas las vías)", fmt(pais[0]), pais[1], "vs 2019")
    if ult["fecha"].month in (3, 4) and ind.mes_semana_santa(anio) != ind.mes_semana_santa(2019):
        mar_abr = ind.marzo_abril_vs_2019(serie, anio)
        if mar_abr is not None:  # Semana Santa cambió de mes: marzo o abril solos no son comparables
            st.caption(
                f"Semana Santa fue en {MES_LARGO[ind.mes_semana_santa(2019)]} en 2019 y en "
                f"{MES_LARGO[ind.mes_semana_santa(anio)]} en {anio}. Marzo y abril juntos: {fmt(mar_abr, 'pct')} vs 2019."
            )
    if serie["llegadas_2019"].isna().all() and con_detalle:
        st.info("Detalle por país desde 2024: no hay base 2019 para comparar.")
    grafica(g.fig_recuperacion(serie))

# ---------- P2: países ----------
with st.container(border=True):
    st.subheader(f"2. ¿Qué países aportan más en {hasta}?")
    rk = q.ranking_paises(con, **filtros)
    if rk.empty:
        st.info("Sin datos de países para este filtro. El detalle por país existe desde 2024.")
    elif len(rk) == 1 or len(filtros["paises"]) == 1:
        f = rk.iloc[0]
        metrica(
            st.columns(2)[0],
            f"{f['pais']} · {hasta}",
            fmt(f["llegadas"]),
            f["crecimiento"],
            f"vs {hasta - 1}",
        )
    else:
        lider, crece = rk.iloc[0], q.mas_crece(rk)
        cols = st.columns(2)
        cols[0].metric("Más llegadas", lider["pais"], f"{fmt(lider['llegadas'])} llegadas",
                       delta_color="off", delta_arrow="off", border=True)  # fmt: skip
        if crece is not None:
            cols[1].metric(
                "Mayor crecimiento", crece["pais"], f"{fmt(crece['crecimiento'], 'pct')} vs {hasta - 1}",
                border=True,
                help=f"Entre los {len(rk)} países con más llegadas. Cuentan solo los que en {hasta - 1} "
                f"tenían al menos {fmt(q.MIN_PARTICIPACION, 'part')} de las llegadas de la vía.",
            )  # fmt: skip
        idiomas = q.idiomas_principales(con, **filtros)
        if not idiomas.empty:
            st.markdown(
                "Idiomas: "
                + " · ".join(f"{i.idioma} {fmt(i.participacion, 'part')}" for i in idiomas.itertuples())
            )
        grafica(g.fig_ranking(rk))
        st.caption(
            f"Los {len(rk)} países con más llegadas, ordenados por crecimiento: mismos meses de {hasta} contra "
            f"{hasta - 1}. Bajo cada país: variación · llegadas de {hasta}. Sin las filas agregadas «Otros»."
        )

# ---------- P3: estacionalidad ----------
with st.container(border=True):
    st.subheader("3. ¿Qué meses concentran la demanda?")
    conc, perfil = ind.concentracion_temporada(serie), ind.perfil_mensual(serie)
    if conc is None:
        st.info("Hace falta al menos un año completo en el rango (sin 2020 ni 2021) para medir la temporada.")
    else:
        pico, valle = perfil.idxmax(), perfil.idxmin()
        cols = st.columns(3)
        cols[0].metric("Temporada alta (dic-abr)", fmt(conc, "part"), "de las llegadas del año",
                       delta_color="off", delta_arrow="off", border=True)  # fmt: skip
        cols[1].metric("Mes pico", MESES_CORTOS[pico - 1], f"{fmt(perfil[pico] / perfil[valle], 'dec')} veces el mes más bajo",
                       delta_color="off", delta_arrow="off", border=True)  # fmt: skip
        cols[2].metric("Mes más bajo", MESES_CORTOS[valle - 1], border=True)
        st.caption("Calculado con los años completos del rango, sin 2020 ni 2021 (pandemia).")
    mc = q.mapa_calor(con, **filtros)
    if mc.empty:
        st.info("Sin datos de países para el mapa de calor.")
    else:
        grafica(g.fig_estacionalidad(mc))
        st.caption("Cada fila suma 100%: qué parte de las llegadas de ese país cae en cada mes. "
                   "Más oscuro, más peso. La línea marca la temporada alta.")  # fmt: skip

# ---------- Descarga y metodología ----------
datos = q.datos_filtrados(con, **filtros)
st.download_button("Descargar CSV de los datos filtrados", datos.to_csv(index=False).encode("utf-8"),
                   file_name="llegadas_filtradas.csv", mime="text/csv")  # fmt: skip

with st.expander("Metodología y limitaciones"):
    st.markdown("""
- **Fuente:** Instituto Costarricense de Turismo (ICT), con datos de la Dirección General de Migración y Extranjería. Detalle de archivos y fechas de descarga en `data/raw/archivos.csv`.
- **Llegadas:** turistas internacionales que pernoctan, por país de residencia.
- **Vías:** "Todas" ya incluye aérea y terrestre; no se suman entre sí. El aeropuerto de Liberia (LIR) es la medida de Guanacaste.
- **Detalle por país:** solo 2024 y 2025. Con filtro de región o país no hay base 2019.
- **Mayor crecimiento:** solo entre los 10 países con más llegadas cuyas llegadas del año previo sean al menos 0,5% del total de la vía ese año. Así un salto de 50 a 100 llegadas no gana a uno de 10.000 a 11.000.
- **Idiomas:** idioma asignado por país de residencia; es una aproximación (ej. Canadá cuenta como inglés). El porcentaje es sobre todas las llegadas con los filtros activos; los agregados «Otros» cuentan en el total y no se listan.
- **Semana Santa:** cambia de mes (2024 en marzo, 2025 en abril) y distorsiona las comparaciones de marzo y abril. En la línea temporal se marca con un rombo.
- **Filas «Otros»:** son agregados de región, no un país; se excluyen del ranking y del mapa de calor.
- **Temporada alta:** diciembre a abril (estación seca).
- **Meses sin dato:** se dejan vacíos, no como cero.
- **2020-2021:** cierre de fronteras por pandemia. No se usan para medir la temporada.
""")
