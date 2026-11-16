"""Fixtures de las pruebas en navegador.

Sin BASE_URL levanta la app en el puerto 8599. Con BASE_URL (por ejemplo la URL de producción)
no levanta nada y prueba contra esa dirección.
"""

import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
PUERTO = 8599


def _esperar(url: str, segundos: int = 90) -> None:
    limite = time.time() + segundos
    while time.time() < limite:
        try:
            with urllib.request.urlopen(f"{url}/_stcore/health", timeout=2) as r:
                if r.status == 200:
                    return
        except OSError:
            time.sleep(0.5)
    raise RuntimeError(f"La app no respondió en {segundos} s: {url}")


@pytest.fixture(scope="session")
def url_app():
    externa = os.environ.get("BASE_URL")
    if externa:
        yield externa.rstrip("/")
        return
    url = f"http://localhost:{PUERTO}"
    proceso = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            "app.py",
            "--server.headless",
            "true",
            "--server.port",
            str(PUERTO),
        ],
        cwd=RAIZ,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        _esperar(url)
        yield url
    finally:
        proceso.terminate()
        try:
            proceso.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proceso.kill()
