"""Genera las capturas del README en docs/img/.

Uso:
    python scripts/capturas.py                 # contra la app local
    BASE_URL=https://... python scripts/capturas.py   # contra producción
"""

import re

from _comun import JS_CONTENEDOR, RAIZ, abrir, servidor
from playwright.sync_api import sync_playwright

SALIDA = RAIZ / "docs" / "img"


def seccion(app, patron: str):
    """Contenedor de la pregunta cuyo título empieza con `patron` (por ejemplo '2.')."""
    titulo = app.get_by_role("heading", name=re.compile(rf"^{re.escape(patron)}"))
    return titulo.evaluate_handle(JS_CONTENEDOR).as_element()


def main() -> None:
    SALIDA.mkdir(parents=True, exist_ok=True)
    with servidor() as url, sync_playwright() as p:
        navegador = p.chromium.launch()

        escritorio = navegador.new_page(viewport={"width": 1280, "height": 800})
        app = abrir(escritorio, url)
        escritorio.screenshot(path=SALIDA / "app.png")
        for patron, nombre in [("2.", "ranking.png"), ("3.", "estacionalidad.png")]:
            elemento = seccion(app, patron)
            elemento.scroll_into_view_if_needed()
            escritorio.wait_for_timeout(1000)
            elemento.screenshot(path=SALIDA / nombre)

        movil = navegador.new_page(viewport={"width": 375, "height": 812})
        abrir(movil, url)
        movil.screenshot(path=SALIDA / "app-movil.png")

        navegador.close()
    for nombre in ["app.png", "app-movil.png", "ranking.png", "estacionalidad.png"]:
        print(f"{nombre}: {(SALIDA / nombre).stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
