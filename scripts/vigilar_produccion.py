"""Abre la app publicada, la despierta si está dormida y falla si no carga o muestra una excepción.

Uso:
    BASE_URL=https://... python scripts/vigilar_produccion.py

Sale con código 1 y guarda una captura en capturas-produccion/ si algo falla.
"""

import os
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

IFRAME = 'iframe[title="streamlitApp"]'
TITULO = "Llegadas a Costa Rica"
BOTON_DESPERTAR = "Yes, get this app back up!"
ESPERA_S = 180
CAPTURAS = Path(__file__).resolve().parents[1] / "capturas-produccion"
ERRORES_CONOCIDOS = (
    "No se pudo abrir la base de datos",
    "no tiene llegadas cargadas",
    "No existe data/processed",
)


def fallar(page, motivo: str) -> None:
    CAPTURAS.mkdir(exist_ok=True)
    page.screenshot(path=CAPTURAS / "falla.png")
    print(f"FALLA: {motivo}")
    sys.exit(1)


def main() -> None:
    url = os.environ.get("BASE_URL", "").rstrip("/")
    if not url:
        sys.exit("Falta BASE_URL")
    with sync_playwright() as p:
        navegador = p.chromium.launch()
        page = navegador.new_page(viewport={"width": 1280, "height": 800})
        page.goto(url, wait_until="domcontentloaded")
        app = page.frame_locator(IFRAME) if "streamlit.app" in url else page
        inicio = time.time()
        despertada = False
        while time.time() - inicio < ESPERA_S:
            boton = page.get_by_role("button", name=BOTON_DESPERTAR)
            if boton.count() and not despertada:
                print("La app estaba dormida: pulsando el botón para despertarla")
                boton.click()
                despertada = True
            if app.get_by_role("heading", name=TITULO).is_visible():
                break
            time.sleep(2)
        else:
            fallar(page, f"No apareció «{TITULO}» en {ESPERA_S} s")
        print(
            f"«{TITULO}» visible a los {time.time() - inicio:.0f} s" + (" (despertada)" if despertada else "")
        )

        try:
            app.locator(".js-plotly-plot").nth(2).wait_for(timeout=60_000)
        except Exception:  # noqa: BLE001
            fallar(page, "No se dibujaron las 3 gráficas")
        excepciones = app.locator('[data-testid="stException"]').count()
        if excepciones:
            fallar(page, f"{excepciones} excepción(es) de Streamlit en la página")
        texto = app.locator("body").inner_text()
        for error in ERRORES_CONOCIDOS:
            if error in texto:
                fallar(page, f"La app muestra un error: {error}")
        print("OK: la app carga, dibuja las 3 gráficas y no muestra errores")
        navegador.close()


if __name__ == "__main__":
    main()
