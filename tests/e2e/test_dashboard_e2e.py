"""Pruebas en navegador (Playwright). Se corren con `pytest -m e2e`."""

import time

import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.e2e

TITULO = "Llegadas a Costa Rica"
CSV_ENCABEZADO = "fecha,pais,region,via,llegadas"
PANTALLAS = {"escritorio": {"width": 1280, "height": 800}, "movil": {"width": 375, "height": 812}}


@pytest.fixture(params=list(PANTALLAS))
def pantalla(request) -> str:
    return request.param


@pytest.fixture
def pagina(browser, url_app, pantalla) -> Page:
    contexto = browser.new_context(viewport=PANTALLAS[pantalla], accept_downloads=True)
    page = contexto.new_page()
    page.errores_consola = []
    page.on("console", lambda m: page.errores_consola.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: page.errores_consola.append(str(e)))
    yield page
    contexto.close()


def abrir(page: Page, url: str) -> None:
    page.goto(url)
    expect(page.get_by_role("heading", name=TITULO)).to_be_visible(timeout=20_000)
    expect(page.locator(".js-plotly-plot")).to_have_count(3, timeout=30_000)


def test_carga_en_menos_de_20_segundos(pagina, url_app):
    inicio = time.time()
    pagina.goto(url_app)
    expect(pagina.get_by_role("heading", name=TITULO)).to_be_visible(timeout=20_000)
    assert time.time() - inicio < 20


def test_sin_errores_de_streamlit_ni_de_consola(pagina, url_app):
    abrir(pagina, url_app)
    assert pagina.locator('[data-testid="stException"]').count() == 0
    assert pagina.errores_consola == []


def test_se_dibujan_las_tres_graficas(pagina, url_app):
    abrir(pagina, url_app)
    expect(pagina.locator(".js-plotly-plot")).to_have_count(3)


def test_descarga_csv(pagina, url_app):
    abrir(pagina, url_app)
    with pagina.expect_download() as descarga:
        pagina.get_by_role("button", name="Descargar CSV de los datos filtrados").click()
    archivo = descarga.value
    assert archivo.suggested_filename == "llegadas_filtradas.csv"
    with open(archivo.path(), encoding="utf-8") as f:
        assert f.readline().strip() == CSV_ENCABEZADO


def test_cambiar_la_via_actualiza_la_pregunta_1(pagina, url_app):
    abrir(pagina, url_app)
    expect(pagina.get_by_text("Aeropuerto de Liberia (LIR), contra el mismo mes de 2019.")).to_be_visible()
    pagina.get_by_label("Vía de ingreso").click()
    pagina.get_by_role("option", name="Todas las vías").click()
    expect(pagina.get_by_text("Todas las vías, contra el mismo mes de 2019.")).to_be_visible(timeout=20_000)
    assert pagina.locator('[data-testid="stException"]').count() == 0


def test_sin_scroll_horizontal_en_movil(pagina, url_app, pantalla):
    if pantalla != "movil":
        pytest.skip("Solo aplica a móvil")
    abrir(pagina, url_app)
    ancho = pagina.evaluate("() => [document.documentElement.scrollWidth, window.innerWidth]")
    assert ancho[0] <= ancho[1], f"scrollWidth {ancho[0]} > innerWidth {ancho[1]}"
