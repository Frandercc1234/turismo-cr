"""Pruebas de la app Streamlit con AppTest (sin navegador)."""

import json
from pathlib import Path

import pytest

pytest.importorskip("duckdb")
import duckdb  # noqa: E402
from streamlit.testing.v1 import AppTest  # noqa: E402

RAIZ = Path(__file__).parent.parent
APP = RAIZ / "app.py"
DB = RAIZ / "data" / "processed" / "turismo.duckdb"

pytestmark = pytest.mark.skipif(not DB.exists(), reason="Falta data/processed/turismo.duckdb")

DEFAULTS = {"via": "lir", "rango": (2019, 2025), "regiones": [], "paises": []}


def nueva() -> AppTest:
    return AppTest.from_file(str(APP), default_timeout=30).run()


def etiquetas(at: AppTest) -> list[str]:
    return [m.label for m in at.metric]


def paises_del_ranking(at: AppTest) -> list[str]:
    """Nombres de país de la gráfica de ranking (la segunda gráfica de la página)."""
    spec = json.loads(at.get("plotly_chart")[1].proto.spec)
    return [etiqueta.split("<br>")[0] for etiqueta in spec["data"][0]["y"]]


def test_valores_por_defecto():
    at = nueva()
    assert not at.exception
    assert [s.value for s in at.subheader] == [
        "1. ¿El mercado ya se recuperó?",
        "2. ¿Qué países aportan más en 2025?",
        "3. ¿Qué meses concentran la demanda?",
    ]
    assert at.selectbox(key="via").value == "lir"
    assert at.slider(key="rango").value == (2019, 2025)
    p1 = etiquetas(at)[:3]
    assert p1 == ["Dic 2025", "Año 2025", "Todo el país (todas las vías)"]


def test_via_todas_no_muestra_todo_el_pais():
    at = nueva()
    at.selectbox(key="via").set_value("todas").run()
    assert not at.exception
    assert not any(e.startswith("Todo el país") for e in etiquetas(at))
    assert etiquetas(at)[:2] == ["Dic 2025", "Año 2025"]


def test_filtro_pais_muestra_una_sola_metrica_en_la_pregunta_2():
    at = nueva()
    at.multiselect(key="paises").set_value(["Estados Unidos"]).run()
    assert not at.exception
    assert any("Detalle por país desde 2024" in i.value for i in at.info)
    etiq = etiquetas(at)
    assert "Estados Unidos · 2025" in etiq
    assert "Más llegadas" not in etiq
    assert "Mayor crecimiento" not in etiq


def test_filtro_region_europa_solo_rankea_paises_de_europa():
    at = nueva()
    at.multiselect(key="regiones").set_value(["Europa"]).run()
    assert not at.exception
    con = duckdb.connect(str(DB), read_only=True)
    europa = {p for (p,) in con.execute("SELECT pais FROM dim_pais WHERE region = 'Europa'").fetchall()}
    ranking = paises_del_ranking(at)
    assert ranking and set(ranking) <= europa
    lider = next(m.value for m in at.metric if m.label == "Más llegadas")
    assert lider in europa


def test_rango_2020_2021_pide_un_anio_completo():
    at = nueva()
    at.slider(key="rango").set_value((2020, 2021)).run()
    assert not at.exception
    assert any("Hace falta al menos un año completo" in i.value for i in at.info)


def test_restablecer_filtros_vuelve_a_los_valores_por_defecto():
    at = nueva()
    at.selectbox(key="via").set_value("todas").run()
    at.slider(key="rango").set_value((2023, 2025)).run()
    at.multiselect(key="regiones").set_value(["Europa"]).run()
    assert at.selectbox(key="via").value == "todas"
    at.button[0].click().run()
    assert not at.exception
    assert {
        "via": at.selectbox(key="via").value,
        "rango": at.slider(key="rango").value,
        "regiones": at.multiselect(key="regiones").value,
        "paises": at.multiselect(key="paises").value,
    } == DEFAULTS


def test_ninguna_combinacion_deja_excepciones():
    at = nueva()
    vias = list(at.selectbox(key="via").options)
    combinaciones = [(v, (2019, 2025), [], []) for v in vias]
    combinaciones += [
        ("todas", (2024, 2025), ["Europa"], []),
        ("aerea", (2025, 2025), [], ["Estados Unidos"]),
        ("lir", (2020, 2021), [], []),
        ("lir", (2020, 2021), ["Europa"], []),
    ]
    for via, rango, regiones, paises in combinaciones:
        at = nueva()
        at.selectbox(key="via").set_value(via)
        at.slider(key="rango").set_value(rango)
        at.multiselect(key="regiones").set_value(regiones)
        at.multiselect(key="paises").set_value(paises)
        at.run()
        assert not at.exception, f"excepción con {via}, {rango}, {regiones}, {paises}: {at.exception}"
