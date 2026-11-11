"""Dashboard de llegadas internacionales a Costa Rica (datos ICT).

Uso:
    streamlit run app.py
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import plotly.express as px
import streamlit as st

from src import consultas as q

DB = Path(__file__).parent / "data" / "processed" / "turismo.duckdb"
MESES_CORTOS = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Set", "Oct", "Nov", "Dic"]
NOMBRE_VIA = {"todas": "Todas las vías", "aerea": "Aérea", "terrestre": "Terrestre",
              "sjo": "Aeropuerto Juan Santamaría", "lir": "Aeropuerto de Liberia (LIR)"}  # fmt: skip

st.set_page_config(page_title="Turismo CR", layout="wide")


@st.cache_resource
def conexion():
    return duckdb.connect(str(DB), read_only=True)


def mes_anio(fecha) -> str:
    return f"{MESES_CORTOS[fecha.month - 1]} {fecha.year}"


def pct(x: float | None) -> str:
    return "sin dato" if x is None or x != x else f"{x:+.1%}"


if not DB.exists():
    st.error("No existe data/processed/turismo.duckdb. Corré `python -m src.cargar` primero.")
    st.stop()

con = conexion()
op = q.opciones(con)

# ---------- Filtros ----------
DEFAULTS = {"via": "todas" if "todas" in op["vias"] else op["vias"][0],
            "rango": (max(2019, op["anios"][0]), op["anios"][-1]), "regiones": [], "paises": []}  # fmt: skip
for k, v in DEFAULTS.items():
    st.session_state.setdefault(k, v)


def restablecer():
    for k, v in DEFAULTS.items():
        st.session_state[k] = v


with st.sidebar:
    st.header("Filtros")
    st.selectbox("Vía de ingreso", op["vias"], key="via", format_func=lambda v: NOMBRE_VIA.get(v, v))
    if len(op["anios"]) > 1:
        st.slider("Años", op["anios"][0], op["anios"][-1], key="rango")
    st.multiselect("Región", sorted(op["paises"]["region"].unique()), key="regiones")
    disponibles = op["paises"]
    if st.session_state.regiones:
        disponibles = disponibles[disponibles["region"].isin(st.session_state.regiones)]
    st.multiselect("País", disponibles["pais"], key="paises")
    st.button("Restablecer filtros", on_click=restablecer, use_container_width=True)

desde, hasta = st.session_state.rango
filtros = dict(via=st.session_state.via, desde=desde, hasta=hasta,
               regiones=st.session_state.regiones, paises=st.session_state.paises)  # fmt: skip

st.title("Llegadas internacionales a Costa Rica")
st.caption(f"Fuente: ICT · Datos hasta {mes_anio(op['actualizado'])} · {NOMBRE_VIA.get(filtros['via'])}")

serie = q.serie_mensual(con, **filtros)
if serie.empty:
    st.info("No hay datos para esta combinación de filtros. Probá ampliar el rango o quitar países.")
    st.stop()

# ---------- P1: recuperación ----------
st.subheader("1. ¿El mercado ya se recuperó?")
ult = serie.dropna(subset=["llegadas"]).iloc[-1]
if ult["llegadas_2019"] == ult["llegadas_2019"]:  # hay base 2019
    st.markdown(
        f"**{mes_anio(ult['fecha'])}: {int(ult['llegadas']):,} llegadas, "
        f"{pct(ult['vs_2019'])} frente al mismo mes de 2019.**"
    )
else:
    st.markdown(
        f"**{mes_anio(ult['fecha'])}: {int(ult['llegadas']):,} llegadas.** Sin base 2019 para comparar."
    )
fig = px.line(serie, x="fecha", y=["llegadas", "llegadas_2019"], markers=True,
              labels={"value": "Llegadas", "fecha": "", "variable": ""})  # fmt: skip
fig.for_each_trace(
    lambda t: t.update(name={"llegadas": "Llegadas", "llegadas_2019": "Mismo mes 2019"}[t.name])
)
fig.update_traces(selector=dict(name="Mismo mes 2019"), line_dash="dot")
fig.add_vrect(x0="2020-03-01", x1="2021-10-31", fillcolor="gray", opacity=0.1, line_width=0,
              annotation_text="Pandemia", annotation_position="top left")  # fmt: skip
fig.update_layout(legend=dict(orientation="h", y=1.1), margin=dict(t=30, b=0))
st.plotly_chart(fig, use_container_width=True)

# ---------- P2: países ----------
st.subheader(f"2. ¿Qué países aportan más en {hasta}?")
rk = q.ranking_paises(con, **filtros)
if rk.empty:
    st.info("Sin datos de países para este filtro.")
else:
    lider = rk.iloc[0]
    crece = rk.dropna(subset=["crecimiento"]).sort_values("crecimiento", ascending=False)
    frase = f"**{lider['pais']} lidera con {int(lider['llegadas']):,} llegadas.**"
    if not crece.empty:
        frase += f" Entre los principales, el que más crece es **{crece.iloc[0]['pais']} ({pct(crece.iloc[0]['crecimiento'])})** frente a {hasta - 1}."
    st.markdown(frase)
    rk["texto"] = rk["crecimiento"].map(pct)
    fig = px.bar(rk.sort_values("llegadas"), x="llegadas", y="pais", orientation="h", text="texto",
                 color="region", labels={"llegadas": "Llegadas", "pais": "", "region": "Región"})  # fmt: skip
    fig.update_layout(margin=dict(t=10, b=0), height=max(350, 28 * len(rk)))
    st.plotly_chart(fig, use_container_width=True)
    st.caption(f"Crecimiento = mismos meses de {hasta} vs {hasta - 1}.")

# ---------- P3: estacionalidad ----------
st.subheader("3. ¿Qué meses concentran la demanda?")
mc = q.mapa_calor(con, **filtros)
if mc.empty:
    st.info("Sin datos para el mapa de calor.")
else:
    pico = mc.loc[mc.groupby("pais")["participacion"].idxmax()]
    top_mes = pico["mes"].mode().iloc[0]
    st.markdown(
        f"**{MESES_CORTOS[top_mes - 1]} es el mes pico para {(pico['mes'] == top_mes).sum()} de {len(pico)} mercados.**"
    )
    tabla = mc.pivot(index="pais", columns="mes", values="participacion").reindex(columns=range(1, 13))
    tabla.columns = MESES_CORTOS
    fig = px.imshow(tabla, color_continuous_scale="Blues", aspect="auto", text_auto=".0%",
                    labels={"color": "% del año", "x": "", "y": ""})  # fmt: skip
    fig.update_layout(margin=dict(t=10, b=0))
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Cada fila suma 100%: qué parte de las llegadas de ese país cae en cada mes.")

# ---------- Descarga y metodología ----------
datos = q.datos_filtrados(con, **filtros)
st.download_button("Descargar CSV de los datos filtrados", datos.to_csv(index=False).encode("utf-8"),
                   file_name="llegadas_filtradas.csv", mime="text/csv")  # fmt: skip

with st.expander("Metodología y limitaciones"):
    st.markdown("""
- **Fuente:** Instituto Costarricense de Turismo (ICT), con datos de la Dirección General de Migración y Extranjería. Detalle de archivos y fechas de descarga en `data/raw/archivos.csv`.
- **Llegadas:** turistas internacionales que pernoctan, por país de residencia.
- **Vías:** "Todas" ya incluye aérea y terrestre; no se suman entre sí.
- **Temporada alta:** diciembre a abril (estación seca).
- **Meses sin dato:** se dejan vacíos, no como cero.
- **2020-2021:** cierre de fronteras por pandemia. Las variaciones de esos años no reflejan demanda normal.
""")
