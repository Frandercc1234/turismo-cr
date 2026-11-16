"""Utilidades de capturas.py y video.py: levantar la app local o usar BASE_URL."""

import os
import subprocess
import sys
import time
import urllib.request
from contextlib import contextmanager
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
IFRAME = 'iframe[title="streamlitApp"]'
PUERTO = 8598

# Primer ancestro con borde redondeado: el contenedor de cada pregunta
JS_CONTENEDOR = """(h) => {
  let e = h;
  while (e && e !== document.body) {
    const s = getComputedStyle(e);
    if (parseFloat(s.borderTopWidth) > 0 && parseFloat(s.borderTopLeftRadius) > 0) return e;
    e = e.parentElement;
  }
  return null;
}"""


@contextmanager
def servidor():
    """Devuelve la URL de la app: BASE_URL si existe, o una app local recién levantada."""
    externa = os.environ.get("BASE_URL")
    if externa:
        yield externa.rstrip("/")
        return
    url = f"http://localhost:{PUERTO}"
    comando = [sys.executable, "-m", "streamlit", "run", "app.py", "--server.headless", "true"]
    proceso = subprocess.Popen(
        [*comando, "--server.port", str(PUERTO)],
        cwd=RAIZ,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        limite = time.time() + 90
        while True:
            try:
                with urllib.request.urlopen(f"{url}/_stcore/health", timeout=2):
                    break
            except OSError:
                if time.time() > limite:
                    raise RuntimeError("La app no respondió en 90 s") from None
                time.sleep(0.5)
        yield url
    finally:
        proceso.terminate()
        try:
            proceso.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proceso.kill()


def raiz_app(page):
    """La página en local; el iframe `streamlitApp` en Streamlit Cloud."""
    return page.frame_locator(IFRAME) if os.environ.get("BASE_URL") else page


def abrir(page, url):
    """Abre la app y espera a que estén las 3 gráficas dibujadas."""
    app = raiz_app(page)
    page.goto(url)
    app.get_by_role("heading", name="Llegadas a Costa Rica").wait_for(timeout=30_000)
    app.locator(".js-plotly-plot").nth(2).wait_for(timeout=30_000)
    page.wait_for_timeout(1500)
    return app
