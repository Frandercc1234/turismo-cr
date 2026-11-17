"""Contraste AA de los colores de src/estilo.py y coherencia con el tema de Streamlit."""

import tomllib
from pathlib import Path

import pytest

from src import estilo as e

TEMA = tomllib.loads(
    (Path(__file__).parent.parent / ".streamlit" / "config.toml").read_text(encoding="utf-8")
)["theme"]


@pytest.mark.parametrize("fondo", [e.SUPERFICIE, e.FONDO_SECUNDARIO])
@pytest.mark.parametrize("texto", [e.TINTA, e.TINTA_2, e.TINTA_TENUE])
def test_el_texto_cumple_aa(texto, fondo):
    assert e.contraste(texto, fondo) >= 4.5


@pytest.mark.parametrize(
    "marca", [e.COLOR_SERIE, e.COLOR_REFERENCIA, e.COLOR_VARIACION["sube"], e.COLOR_VARIACION["baja"]]
)
def test_las_marcas_cumplen_3_a_1(marca):
    assert e.contraste(marca, e.SUPERFICIE) >= 3


def test_la_referencia_sigue_mas_clara_que_la_serie():
    assert e.contraste(e.COLOR_REFERENCIA, e.SUPERFICIE) < e.contraste(e.COLOR_SERIE, e.SUPERFICIE)


def test_el_tema_usa_los_mismos_colores_que_estilo():
    assert TEMA["backgroundColor"].lower() == e.SUPERFICIE
    assert TEMA["secondaryBackgroundColor"].lower() == e.FONDO_SECUNDARIO
