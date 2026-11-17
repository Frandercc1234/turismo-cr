"""Paleta, formato numérico y plantilla Plotly del dashboard.

Única fuente de colores y de formato. Reglas de color: un solo azul para la serie
principal, una escala azul para la intensidad (mapa de calor), gris para referencias,
y verde/rojo solo para variaciones (siempre con flecha o signo, nunca solo color).
"""

from __future__ import annotations

import plotly.graph_objects as go

MESES_CORTOS = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Set", "Oct", "Nov", "Dic"]

SUPERFICIE = "#fcfcfb"
FONDO_SECUNDARIO = "#f3f2ee"  # secondaryBackgroundColor del tema (selectores, métricas)
TINTA = "#0b0b0b"
TINTA_2 = "#52514e"
TINTA_TENUE = "#6e6c66"  # texto secundario: 5,1:1 sobre SUPERFICIE y 4,7:1 sobre FONDO_SECUNDARIO
GRILLA = "#e1e0d9"
EJE = "#c3c2b7"
FUENTE = '"Source Sans Pro", "Source Sans 3", system-ui, sans-serif'  # lectura (cuerpo del tema)
FUENTE_TITULO = '"Fraunces", Georgia, "Times New Roman", serif'  # títulos y cifras (headingFont del tema)

# Un solo color propio (verde azulado, el del Pacífico) para la serie, el tema y la escala secuencial.
COLOR_SERIE = "#00818d"  # 4,5:1 sobre SUPERFICIE; es el paso 5 de SECUENCIAL
COLOR_REFERENCIA = (
    "#898781"  # solo marca (línea del mismo mes 2019): 3:1 basta, y sigue más claro que la serie
)
VERDE = "#527a00"  # sube: marca de las barras y texto de las variaciones (greenColor del tema)
ROJO = "#c93636"  # baja (redColor del tema): 4,6:1 incluso sobre FONDO_SECUNDARIO
COLOR_VARIACION = {"sube": VERDE, "baja": ROJO, "sin_dato": COLOR_REFERENCIA}  # marcas (barras)
# 7 pasos del mismo matiz (OKLCH 205), de claro a oscuro con la luminancia estrictamente decreciente
SECUENCIAL = ["#daf4f7", "#b0e2e8", "#7bc9d2", "#45acb7", COLOR_SERIE, "#00626a", "#03464c"]
ESCALA_SECUENCIAL = [[i / (len(SECUENCIAL) - 1), c] for i, c in enumerate(SECUENCIAL)]


def _luminancia(color: str) -> float:
    canales = [int(color[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    r, g, b = (c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in canales)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contraste(a: str, b: str) -> float:
    """Razón de contraste WCAG entre dos colores '#rrggbb' (4,5 es el mínimo AA para texto, 3 para marcas)."""
    claro, oscuro = sorted((_luminancia(a), _luminancia(b)), reverse=True)
    return (claro + 0.05) / (oscuro + 0.05)


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
            title=dict(font=dict(family=FUENTE_TITULO, size=16, color=TINTA)),
            hoverlabel=dict(
                bgcolor=SUPERFICIE, bordercolor=EJE, font=dict(family=FUENTE_TITULO, size=13, color=TINTA)
            ),
        )
    )


PLANTILLA = _plantilla()
