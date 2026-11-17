"""Pruebas de la app Streamlit con AppTest (sin navegador)."""

import json
import re
from pathlib import Path

import pytest

pytest.importorskip("duckdb")
import duckdb  # noqa: E402
from streamlit.testing.v1 import AppTest  # noqa: E402

from src import consultas as q  # noqa: E402
from src import titulos  # noqa: E402

RAIZ = Path(__file__).parent.parent
APP = RAIZ / "app.py"
DB = RAIZ / "data" / "processed" / "turismo.duckdb"

pytestmark = pytest.mark.skipif(not DB.exists(), reason="Falta data/processed/turismo.duckdb")

DEFAULTS = {"via": "lir", "rango": (2019, 2025), "regiones": [], "paises": []}


def nueva() -> AppTest:
    return AppTest.from_file(str(APP), default_timeout=30).run()


def etiquetas(at: AppTest) -> list[str]:
    return [m.label for m in at.metric]


def nombres_de_tarjeta(at: AppTest) -> list[str]:
    """Nombres de país de las tarjetas «Más llegadas» y «Mayor crecimiento» (encabezados h4)."""
    return [m.value.removeprefix("#### ") for m in at.markdown if m.value.startswith("#### ")]


def badges(at: AppTest) -> list[str]:
    """Etiquetas de color de esas tarjetas, por ejemplo ':green-badge[↑ +6,2% vs 2024]'."""
    return [m.value for m in at.markdown if "-badge[" in m.value]


def paises_del_ranking(at: AppTest) -> list[str]:
    """Nombres de país de la gráfica de ranking (la segunda gráfica de la página)."""
    spec = json.loads(at.get("plotly_chart")[1].proto.spec)
    return [etiqueta.split("<br>")[0] for etiqueta in spec["data"][0]["y"]]


def test_valores_por_defecto():
    at = nueva()
    assert not at.exception
    p1, p2, p3 = (s.value for s in at.subheader)
    # cada título repite cifras que la app ya muestra en sus tarjetas: salen de los mismos datos
    tarjeta = {m.label: m for m in at.metric}
    assert p1.startswith("1. Liberia (LIR) ya superó a 2019: ")
    assert tarjeta["Año 2025"].delta.split(" ")[0] in p1
    assert tarjeta["Todo el país (todas las vías)"].delta.split(" ")[0] in p1
    lider, crece = nombres_de_tarjeta(at)
    llegadas, variacion = (re.search(r"\[(?:↑ |↓ )?(\S+)", b).group(1) for b in badges(at))
    assert p2.startswith(f"2. {lider} lidera con {llegadas} llegadas")
    assert crece in p2 and variacion in p2
    assert titulos.mercados_que_cuentan(2025, q.MIN_PARTICIPACION) in p2  # el título dice la regla
    assert p3.startswith("3. Marzo es el mes pico del total")
    assert tarjeta["Temporada alta (dic-abr)"].value in p3
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
    # con detalle por país desde 2019, el filtro de país ya tiene base 2019 para comparar
    assert not any("Detalle por país desde" in i.value for i in at.info)
    assert not any("sin base 2019" in (m.delta or "") for m in at.metric)
    etiq = etiquetas(at)
    assert "Estados Unidos · 2025" in etiq
    assert nombres_de_tarjeta(at) == []  # con un solo país no hay tarjetas de líder ni de crecimiento


def test_filtro_region_europa_solo_rankea_paises_de_europa():
    at = nueva()
    at.multiselect(key="regiones").set_value(["Europa"]).run()
    assert not at.exception
    con = duckdb.connect(str(DB), read_only=True)
    europa = {p for (p,) in con.execute("SELECT pais FROM dim_pais WHERE region = 'Europa'").fetchall()}
    ranking = paises_del_ranking(at)
    assert ranking and set(ranking) <= europa
    lider = nombres_de_tarjeta(at)[0]
    assert lider in europa


def test_un_nombre_largo_va_en_un_encabezado_y_no_en_un_metric_que_lo_recortaria():
    at = nueva()
    at.multiselect(key="regiones").set_value(["Caribe"]).run()
    assert not at.exception
    assert nombres_de_tarjeta(at)[0] == "República Dominicana"
    assert "República Dominicana" not in [m.value for m in at.metric]


@pytest.mark.parametrize(
    ("via", "regiones"), [("lir", []), ("todas", []), ("terrestre", []), ("todas", ["Europa"])]
)
def test_el_pais_del_titulo_es_el_primero_del_grafico_que_cumple_la_regla(via, regiones):
    at = nueva()
    at.selectbox(key="via").set_value(via)
    at.multiselect(key="regiones").set_value(regiones).run()
    assert not at.exception
    titulo = [s.value for s in at.subheader][1]
    grafico = paises_del_ranking(at)  # ordenado por crecimiento, de mayor a menor
    con = duckdb.connect(str(DB), read_only=True)
    rk = q.ranking_paises(con, via=via, desde=2019, hasta=2025, regiones=regiones, paises=[])
    cuenta = dict(zip(rk["pais"], rk["califica"], strict=True))
    primero = next(p for p in grafico if cuenta[p])
    assert primero in titulo and "es el que más crece" in titulo
    assert titulos.mercados_que_cuentan(2025, q.MIN_PARTICIPACION) in titulo
    assert not any(cuenta[p] for p in grafico[: grafico.index(primero)])  # lo que está más arriba no cuenta
    barras = json.loads(at.get("plotly_chart")[1].proto.spec)["data"][0]
    assert [o == 1 for o in barras["marker"]["opacity"]] == [cuenta[p] for p in barras["y"]]


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
        ("lir", (2019, 2019), ["Europa"], []),
        ("todas", (2019, 2020), [], ["Canadá"]),
        ("maritima", (2019, 2023), [], ["Estados Unidos"]),
    ]
    for via, rango, regiones, paises in combinaciones:
        at = nueva()
        at.selectbox(key="via").set_value(via)
        at.slider(key="rango").set_value(rango)
        at.multiselect(key="regiones").set_value(regiones)
        at.multiselect(key="paises").set_value(paises)
        at.run()
        assert not at.exception, f"excepción con {via}, {rango}, {regiones}, {paises}: {at.exception}"
