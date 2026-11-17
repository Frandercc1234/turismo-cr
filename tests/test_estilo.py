"""Contraste AA de los colores de src/estilo.py y coherencia con el tema de Streamlit."""

import tomllib
from pathlib import Path

import pytest

from src import estilo as e

RAIZ = Path(__file__).parent.parent
CONFIG = tomllib.loads((RAIZ / ".streamlit" / "config.toml").read_text(encoding="utf-8"))
TEMA = CONFIG["theme"]


@pytest.mark.parametrize("fondo", [e.SUPERFICIE, e.FONDO_SECUNDARIO])
@pytest.mark.parametrize("texto", [e.TINTA, e.TINTA_2, e.TINTA_TENUE, e.VERDE, e.ROJO])
def test_el_texto_cumple_aa(texto, fondo):
    assert e.contraste(texto, fondo) >= 4.5


@pytest.mark.parametrize("marca", [e.COLOR_SERIE, e.COLOR_REFERENCIA, e.VERDE, e.ROJO])
def test_las_marcas_cumplen_3_a_1(marca):
    assert e.contraste(marca, e.SUPERFICIE) >= 3


def test_la_referencia_sigue_mas_clara_que_la_serie():
    assert e.contraste(e.COLOR_REFERENCIA, e.SUPERFICIE) < e.contraste(e.COLOR_SERIE, e.SUPERFICIE)


def test_la_escala_secuencial_tiene_7_pasos_de_luminancia_decreciente():
    assert len(e.SECUENCIAL) == 7
    lum = [e._luminancia(c) for c in e.SECUENCIAL]
    assert lum == sorted(lum, reverse=True) and len(set(lum)) == 7
    assert e.COLOR_SERIE in e.SECUENCIAL


def test_el_color_propio_no_es_el_azul_de_streamlit():
    assert e.COLOR_SERIE != "#0068c9" and e.COLOR_SERIE != "#2a78d6"


def test_el_tema_usa_los_mismos_colores_que_estilo():
    assert TEMA["backgroundColor"].lower() == e.SUPERFICIE
    assert TEMA["secondaryBackgroundColor"].lower() == e.FONDO_SECUNDARIO
    assert TEMA["textColor"].lower() == e.TINTA
    assert TEMA["primaryColor"].lower() == e.COLOR_SERIE
    assert TEMA["greenColor"].lower() == e.VERDE
    assert TEMA["redColor"].lower() == e.ROJO


def test_la_fuente_de_titulos_del_tema_coincide_con_la_de_plotly_y_existe_el_archivo():
    assert e.FUENTE_TITULO.startswith(f'"{TEMA["headingFont"]}"')
    cara = TEMA["fontFaces"][0]
    assert cara["family"] == TEMA["headingFont"]
    archivo = RAIZ / cara["url"].replace("app/static/", "static/")
    assert archivo.exists() and archivo.stat().st_size > 10_000
    assert CONFIG["server"]["enableStaticServing"] is True
