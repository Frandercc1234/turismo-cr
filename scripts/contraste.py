"""Imprime el contraste WCAG de los colores de src/estilo.py y falla si alguno no llega al mínimo.

Texto: 4,5:1 sobre la superficie y sobre el fondo secundario. Marcas (líneas, barras): 3:1 sobre la superficie.

Uso:
    python scripts/contraste.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import estilo as e  # noqa: E402

TEXTO = {"TINTA": e.TINTA, "TINTA_2": e.TINTA_2, "TINTA_TENUE": e.TINTA_TENUE}
MARCAS = {
    "COLOR_SERIE": e.COLOR_SERIE,
    "COLOR_REFERENCIA": e.COLOR_REFERENCIA,
    "variación: sube": e.COLOR_VARIACION["sube"],
    "variación: baja": e.COLOR_VARIACION["baja"],
}


def revisar() -> list[str]:
    fallas = []
    print(f"{'texto':<20}{'sobre superficie':>18}{'sobre secundario':>18}")
    for nombre, color in TEXTO.items():
        a, b = e.contraste(color, e.SUPERFICIE), e.contraste(color, e.FONDO_SECUNDARIO)
        print(f"{nombre:<20}{a:>16.2f}:1{b:>16.2f}:1")
        if min(a, b) < 4.5:
            fallas.append(f"{nombre} {min(a, b):.2f}:1 (mínimo 4,5)")
    print(f"\n{'marca':<20}{'sobre superficie':>18}")
    for nombre, color in MARCAS.items():
        a = e.contraste(color, e.SUPERFICIE)
        print(f"{nombre:<20}{a:>16.2f}:1")
        if a < 3:
            fallas.append(f"{nombre} {a:.2f}:1 (mínimo 3)")
    return fallas


if __name__ == "__main__":
    problemas = revisar()
    if problemas:
        sys.exit("FALLA: " + "; ".join(problemas))
    print("\nOK: todo cumple AA")
