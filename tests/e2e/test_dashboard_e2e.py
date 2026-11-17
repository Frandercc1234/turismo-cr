"""Pruebas en navegador (Playwright). Se corren con `pytest -m e2e`.

Contra producción (BASE_URL) Streamlit Cloud mete la app en un iframe; el fixture `app`
devuelve el iframe en ese caso y la página en local.
"""

import os
import time

import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.e2e

TITULO = "Llegadas a Costa Rica"
CSV_ENCABEZADO = "fecha,pais,region,via,llegadas"
IFRAME = 'iframe[title="streamlitApp"]'
PANTALLAS = {"escritorio": {"width": 1280, "height": 800}, "movil": {"width": 375, "height": 812}}


@pytest.fixture(params=list(PANTALLAS))
def pantalla(request) -> str:
    return request.param


@pytest.fixture
def pagina(browser, url_app, pantalla) -> Page:
    contexto = browser.new_context(viewport=PANTALLAS[pantalla], accept_downloads=True)
    page = contexto.new_page()
    page.errores_consola = []

    def registrar(mensaje):
        # Streamlit Cloud (no la app) pide estas URL y recibe 403/404 si no hay sesión de usuario
        ruido = ("heapanalytics.com", "/api/v1/app/event", "/api/v2/user/")
        if mensaje.type == "error" and not any(r in mensaje.location.get("url", "") for r in ruido):
            page.errores_consola.append(mensaje.text)

    page.on("console", registrar)
    page.on("pageerror", lambda e: page.errores_consola.append(str(e)))
    yield page
    contexto.close()


@pytest.fixture
def app(pagina):
    """Donde están los elementos de la app: la página (local) o el iframe de Streamlit Cloud."""
    return pagina.frame_locator(IFRAME) if "streamlit.app" in os.environ.get("BASE_URL", "") else pagina


def abrir(page: Page, app, url: str) -> None:
    page.goto(url)
    expect(app.get_by_role("heading", name=TITULO)).to_be_visible(timeout=20_000)
    expect(app.locator(".js-plotly-plot")).to_have_count(3, timeout=30_000)


def test_carga_en_menos_de_20_segundos(pagina, app, url_app):
    inicio = time.time()
    pagina.goto(url_app)
    expect(app.get_by_role("heading", name=TITULO)).to_be_visible(timeout=20_000)
    assert time.time() - inicio < 20


def test_sin_errores_de_streamlit_ni_de_consola(pagina, app, url_app):
    abrir(pagina, app, url_app)
    assert app.locator('[data-testid="stException"]').count() == 0
    assert pagina.errores_consola == []


def test_se_dibujan_las_tres_graficas(pagina, app, url_app):
    abrir(pagina, app, url_app)
    expect(app.locator(".js-plotly-plot")).to_have_count(3)


def test_descarga_csv(pagina, app, url_app):
    abrir(pagina, app, url_app)
    with pagina.expect_download() as descarga:
        app.get_by_role("button", name="Descargar CSV de los datos filtrados").click()
    archivo = descarga.value
    assert archivo.suggested_filename == "llegadas_filtradas.csv"
    with open(archivo.path(), encoding="utf-8") as f:
        assert f.readline().strip() == CSV_ENCABEZADO


def test_cambiar_la_via_actualiza_la_pregunta_1(pagina, app, url_app):
    abrir(pagina, app, url_app)
    expect(app.get_by_text("Aeropuerto de Liberia (LIR), contra el mismo mes de 2019.")).to_be_visible()
    app.get_by_label("Vía de ingreso").click()
    app.get_by_role("option", name="Todas las vías").click()
    expect(app.get_by_text("Todas las vías, contra el mismo mes de 2019.")).to_be_visible(timeout=20_000)
    assert app.locator('[data-testid="stException"]').count() == 0


def test_ningun_texto_se_recorta_con_puntos_suspensivos_en_movil(pagina, app, url_app, pantalla):
    if pantalla != "movil":
        pytest.skip("Solo aplica a móvil")
    abrir(pagina, app, url_app)
    recortados = app.locator("body").evaluate(
        """() => [...document.querySelectorAll('body *')]
            .filter(e => getComputedStyle(e).textOverflow === 'ellipsis' && e.scrollWidth > e.clientWidth)
            .map(e => e.innerText.trim().slice(0, 40))"""
    )
    assert recortados == [], f"textos recortados a 375 px: {recortados}"


def test_sin_scroll_horizontal_en_movil(pagina, app, url_app, pantalla):
    if pantalla != "movil":
        pytest.skip("Solo aplica a móvil")
    abrir(pagina, app, url_app)
    ancho = app.locator("body").evaluate("() => [document.documentElement.scrollWidth, window.innerWidth]")
    assert ancho[0] <= ancho[1], f"scrollWidth {ancho[0]} > innerWidth {ancho[1]}"
