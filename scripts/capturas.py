"""Genera las capturas del README en docs/img/ (o en la carpeta que se indique).

Uso:
    python scripts/capturas.py                      # contra la app local, en docs/img/
    python scripts/capturas.py docs/img/antes       # en otra carpeta
    BASE_URL=https://... python scripts/capturas.py   # contra producción
"""

import re
import sys
from pathlib import Path

from _comun import JS_CONTENEDOR, RAIZ, abrir, servidor
from playwright.sync_api import sync_playwright

SECCIONES = [("2.", "ranking"), ("3.", "estacionalidad")]


def seccion(app, patron: str):
    """Contenedor de la pregunta cuyo título empieza con `patron` (por ejemplo '2.')."""
    titulo = app.get_by_role("heading", name=re.compile(rf"^{re.escape(patron)}"))
    return titulo.evaluate_handle(JS_CONTENEDOR).as_element()


def secciones(pagina, app, salida: Path, sufijo: str) -> None:
    ventana = pagina.viewport_size
    for patron, nombre in SECCIONES:
        elemento = seccion(app, patron)
        # la ventana tiene que ser más alta que la sección; si no, Streamlit no dibuja lo que queda fuera
        pagina.set_viewport_size({"width": ventana["width"], "height": 2600})
        pagina.wait_for_timeout(800)
        elemento.scroll_into_view_if_needed()
        pagina.wait_for_timeout(1000)
        elemento.screenshot(path=salida / f"{nombre}{sufijo}.png")
    pagina.set_viewport_size(ventana)


def main() -> None:
    salida = RAIZ / (sys.argv[1] if len(sys.argv) > 1 else "docs/img")
    salida.mkdir(parents=True, exist_ok=True)
    with servidor() as url, sync_playwright() as p:
        navegador = p.chromium.launch()

        escritorio = navegador.new_page(viewport={"width": 1280, "height": 800})
        app = abrir(escritorio, url)
        escritorio.screenshot(path=salida / "app.png")
        secciones(escritorio, app, salida, "")

        movil = navegador.new_page(viewport={"width": 375, "height": 812})
        app_movil = abrir(movil, url)
        movil.screenshot(path=salida / "app-movil.png")
        secciones(movil, app_movil, salida, "-movil")

        navegador.close()
    for archivo in sorted(salida.glob("*.png")):
        print(f"{archivo.name}: {archivo.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
