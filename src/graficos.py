"""Las tres gráficas del dashboard (Plotly), construidas con la paleta de estilo.py."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from src.estilo import (
    COLOR_REFERENCIA,
    COLOR_SERIE,
    ESCALA_SECUENCIAL,
    GRILLA,
    MESES_CORTOS,
    PLANTILLA,
    SUPERFICIE,
    TINTA_2,
    TINTA_TENUE,
    color_variacion,
    fmt,
)

PANDEMIA = ("2020-03-01", "2021-10-31")


def _ticks_fecha(fechas: pd.Series) -> tuple[list, list[str]]:
    """Ticks en español: solo años si el rango pasa de 2 años; si no, 'Ene 2024' cada 3 o 6 meses."""
    meses = pd.DatetimeIndex(fechas.dropna().unique()).sort_values()
    if len(meses) > 24:
        anios = sorted(set(meses.year))
        valores = [pd.Timestamp(a, 1, 1) for a in anios[:: 1 if len(anios) <= 8 else 2]]
        return valores, [str(v.year) for v in valores]
    valores = list(meses[:: 3 if len(meses) <= 12 else 6])
    return valores, [f"{MESES_CORTOS[v.month - 1]} {v.year}" for v in valores]


def fig_recuperacion(serie: pd.DataFrame) -> go.Figure:
    """P1: llegadas por mes contra el mismo mes de 2019 (si hay base)."""
    hay_base = bool(serie["llegadas_2019"].notna().any())
    fig = go.Figure()
    if hay_base:
        fig.add_scatter(
            x=serie["fecha"], y=serie["llegadas_2019"], name="Mismo mes 2019", mode="lines",
            line=dict(color=COLOR_REFERENCIA, width=2, dash="dot"),
            customdata=[fmt(v) for v in serie["llegadas_2019"]],
            hovertemplate="%{fullData.name}: %{customdata}<extra></extra>",
        )  # fmt: skip
    fig.add_scatter(
        x=serie["fecha"], y=serie["llegadas"], name="Llegadas", mode="lines",
        line=dict(color=COLOR_SERIE, width=2),
        customdata=[fmt(v) for v in serie["llegadas"]],
        hovertemplate="%{fullData.name}: %{customdata}<extra></extra>",
    )  # fmt: skip
    santa = serie[serie["semana_santa"] & serie["llegadas"].notna()]
    if not santa.empty:  # el ICT avisa que Semana Santa cambia de mes y distorsiona marzo y abril
        fig.add_scatter(
            x=santa["fecha"], y=santa["llegadas"], name="Semana Santa", mode="markers",
            marker=dict(symbol="diamond", size=8, color=TINTA_2, line=dict(width=2, color=SUPERFICIE)),
            hovertemplate="Semana Santa<extra></extra>",
        )  # fmt: skip
    ult = serie.dropna(subset=["llegadas"]).iloc[-1]
    fig.add_scatter(
        x=[ult["fecha"]], y=[ult["llegadas"]], mode="markers", showlegend=False, hoverinfo="skip",
        marker=dict(size=9, color=COLOR_SERIE, line=dict(width=2, color=SUPERFICIE)),
    )  # fmt: skip
    en_pandemia = serie["fecha"].between(*PANDEMIA) & serie["llegadas"].notna()
    if en_pandemia.any():
        fig.add_vrect(
            x0=PANDEMIA[0], x1=PANDEMIA[1], fillcolor=GRILLA, opacity=0.5, line_width=0, layer="below",
            annotation_text="Pandemia", annotation_position="top left",
            annotation_font=dict(size=12, color=TINTA_TENUE),
        )  # fmt: skip
    valores, textos = _ticks_fecha(serie["fecha"])
    fig.update_layout(
        template=PLANTILLA, height=360, hovermode="x unified", showlegend=hay_base or not santa.empty,
        yaxis=dict(tickformat=",.0f", rangemode="tozero", automargin=True),
    )  # fmt: skip
    fig.update_xaxes(tickmode="array", tickvals=valores, ticktext=textos, tickangle=0, hoverformat="%m/%Y")
    return fig


def fig_ranking(rk: pd.DataFrame) -> go.Figure:
    """P2: crecimiento del último año contra el anterior, por país. Verde sube, rojo baja."""
    d = rk.dropna(subset=["crecimiento"]).sort_values("crecimiento", ascending=False)
    # La etiqueta va bajo el nombre del país: en pantallas angostas una etiqueta al final de la barra se recorta.
    nombres = [
        f"{p}<br><span style='color:{TINTA_TENUE}'>{fmt(c, 'pct')} · {fmt(n)}</span>"
        for p, c, n in zip(d["pais"], d["crecimiento"], d["llegadas"], strict=True)
    ]
    fig = go.Figure(
        go.Bar(
            x=d["crecimiento"], y=d["pais"], orientation="h",
            marker_color=[color_variacion(c) for c in d["crecimiento"]],
            customdata=[
                f"Variación: {fmt(c, 'pct')}<br>Llegadas: {fmt(n)}<br>Año anterior: {fmt(p)}"
                for c, n, p in zip(d["crecimiento"], d["llegadas"], d["llegadas_previo"], strict=True)
            ],
            hovertemplate="<b>%{y}</b><br>%{customdata}<extra></extra>",
        )
    )  # fmt: skip
    menor, mayor = min(d["crecimiento"].min(), 0), max(d["crecimiento"].max(), 0)
    holgura = 0.04 * ((mayor - menor) or 0.01)
    fig.add_vline(x=0, line_width=1.5, line_color=TINTA_2)
    fig.update_layout(
        template=PLANTILLA, bargap=0.35, height=max(240, 46 * len(d) + 30), margin=dict(r=0, t=8),
        yaxis=dict(
            autorange="reversed", showgrid=False, linecolor=SUPERFICIE, automargin=True,
            tickmode="array", tickvals=list(d["pais"]), ticktext=nombres,
            tickfont=dict(color=TINTA_2, size=12),
        ),
    )  # fmt: skip
    fig.update_xaxes(visible=False, range=[menor - holgura, mayor + holgura])
    return fig


def fig_estacionalidad(mc: pd.DataFrame) -> go.Figure:
    """P3: participación de cada mes en el año, por país (filas ordenadas por mes pico)."""
    pico = mc.loc[mc.groupby("pais")["participacion"].idxmax()].set_index("pais")["mes"]
    volumen = mc.groupby("pais")["llegadas"].sum()
    orden = sorted(pico.index, key=lambda p: (pico[p], -volumen[p]))
    tabla = mc.pivot(index="pais", columns="mes", values="participacion")
    tabla = tabla.reindex(index=orden, columns=range(1, 13))
    tabla.columns = MESES_CORTOS
    fig = go.Figure(
        go.Heatmap(
            z=tabla.to_numpy(), x=list(tabla.columns), y=list(tabla.index), zmin=0,
            colorscale=ESCALA_SECUENCIAL, showscale=False, xgap=2, ygap=2,
            customdata=tabla.map(lambda v: fmt(v, "part")).to_numpy(),
            hovertemplate="%{y} · %{x}: %{customdata} del año<extra></extra>",
        )
    )  # fmt: skip
    for x0, x1 in ((-0.5, 3.5), (10.5, 11.5)):  # temporada alta: ene-abr y dic
        fig.add_shape(
            type="line", xref="x", yref="paper", x0=x0, x1=x1, y0=1.02, y1=1.02,
            line=dict(color=TINTA_TENUE, width=2),
        )  # fmt: skip
    fig.add_annotation(
        x=1.5, xref="x", y=1.03, yref="paper", yanchor="bottom", showarrow=False,
        text="Temporada alta", font=dict(size=12, color=TINTA_TENUE),
    )  # fmt: skip
    fig.update_layout(
        template=PLANTILLA, height=max(180, 32 * len(orden) + 70), margin=dict(t=40),
        xaxis=dict(automargin=True),
        yaxis=dict(autorange="reversed", showgrid=False, automargin=True),
    )  # fmt: skip
    return fig
