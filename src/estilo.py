"""Paleta, formato numérico y plantilla Plotly del dashboard.

Única fuente de colores y de formato. Reglas de color: un solo azul para la serie
principal, una escala azul para la intensidad (mapa de calor), gris para referencias,
y verde/rojo solo para variaciones (siempre con flecha o signo, nunca solo color).
"""

from __future__ import annotations

import plotly.graph_objects as go

MESES_CORTOS = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Set", "Oct", "Nov", "Dic"]

SUPERFICIE = "#fcfcfb"
TINTA = "#0b0b0b"
TINTA_2 = "#52514e"
TINTA_TENUE = "#898781"
GRILLA = "#e1e0d9"
EJE = "#c3c2b7"
FUENTE = '"Source Sans Pro", "Source Sans 3", system-ui, sans-serif'

COLOR_SERIE = "#2a78d6"  # serie principal de la línea de tiempo
COLOR_REFERENCIA = TINTA_TENUE  # comparación (mismo mes 2019)
COLOR_VARIACION = {"sube": "#0ca30c", "baja": "#d03b3b", "sin_dato": TINTA_TENUE}  # marcas (barras)
SECUENCIAL = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
ESCALA_SECUENCIAL = [[i / (len(SECUENCIAL) - 1), c] for i, c in enumerate(SECUENCIAL)]


def fmt(x, tipo: str = "n") -> str:
    """Formato español para toda cifra visible (frases, métricas y tooltips).

    n: 2.943.991 · corto: 1,63 M · pct: +6,2% · part: 56,6% · dec: 5,3
    """
    if x is None or x != x:
        return "sin dato"
    if tipo == "pct":
        s = f"{x * 100:+.1f}%"
    elif tipo == "part":
        s = f"{x * 100:.1f}%"
    elif tipo == "dec":
        s = f"{x:.1f}"
    elif tipo == "corto":
        s = f"{x / 1e6:.2f} M" if abs(x) >= 1e6 else f"{x:,.0f}"
    else:
        s = f"{x:,.0f}"
    return s.replace(",", "\0").replace(".", ",").replace("\0", ".")


def color_variacion(x) -> str:
    if x is None or x != x:
        return COLOR_VARIACION["sin_dato"]
    return COLOR_VARIACION["sube" if x >= 0 else "baja"]


def _plantilla() -> go.layout.Template:
    eje = dict(ticks="", linecolor=EJE, tickfont=dict(color=TINTA_TENUE, size=12), title_text="")
    return go.layout.Template(
        layout=dict(
            font=dict(family=FUENTE, size=13, color=TINTA_2),
            paper_bgcolor=SUPERFICIE,
            plot_bgcolor=SUPERFICIE,
            colorway=[COLOR_SERIE],
            separators=",.",
            margin=dict(l=0, r=0, t=24, b=0),
            legend=dict(
                orientation="h",
                x=0,
                y=-0.1,
                yanchor="top",
                title_text="",
                font=dict(size=12, color=TINTA_2),
            ),  # fmt: skip
            xaxis=dict(showgrid=False, **eje),
            yaxis=dict(gridcolor=GRILLA, gridwidth=1, zeroline=False, **eje),
            hoverlabel=dict(
                bgcolor=SUPERFICIE, bordercolor=EJE, font=dict(family=FUENTE, size=13, color=TINTA)
            ),
        )
    )


PLANTILLA = _plantilla()
