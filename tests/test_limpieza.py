from pathlib import Path

import pandas as pd
import pytest

from src.limpieza import leer_cuadro, normalizar_texto, validar

MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio",
         "Agosto", "Setiembre", "Octubre", "Noviembre", "Diciembre"]  # fmt: skip
RAW = Path(__file__).resolve().parents[1] / "data" / "raw"


def fila(etiqueta, valores):
    return [etiqueta, *valores, sum(v for v in valores if isinstance(v, (int, float)))]


@pytest.fixture
def cuadro():
    """Imita el layout del ICT: título, TOTAL, zonas con subtotal, países, filas vacías."""
    usa = [100] * 12
    can = [50] * 11 + ["-"]  # diciembre sin dato
    nic = [30] * 12
    tot = [180] * 11 + [130]
    filas = [
        ["LLEGADAS INTERNACIONALES DE TURISTAS", *[None] * 13],
        [None] * 14,
        ["Zonas y países", *MESES, "Ene-Dic"],
        fila("TOTAL", tot),
        [None] * 14,
        fila("AMÉRICA DEL NORTE", [a + (b if b != "-" else 0) for a, b in zip(usa, can, strict=True)]),
        fila("Estados Unidos", usa),
        fila("Canadá 1/", can),
        [None] * 14,
        fila("AMÉRICA CENTRAL", nic),
        fila("  Nicaragua ", nic),
        ["Fuente: ICT", *[None] * 13],
    ]
    return pd.DataFrame(filas, dtype=object)


def test_no_carga_totales_ni_zonas(cuadro):
    datos, _ = leer_cuadro(cuadro, anio=2024, via="todas")
    assert set(datos["pais"]) == {"Estados Unidos", "Canadá", "Nicaragua"}


def test_suma_coincide_con_total_publicado(cuadro):
    datos, totales = leer_cuadro(cuadro, anio=2024, via="todas")
    validar(datos, totales)  # lanza error si no coincide


def test_mes_sin_dato_no_es_cero(cuadro):
    datos, _ = leer_cuadro(cuadro, anio=2024, via="todas")
    canada = datos[datos["pais"] == "Canadá"]
    assert len(canada) == 11
    assert 0 not in canada["llegadas"].values


def test_sin_duplicados_ni_negativos(cuadro):
    datos, _ = leer_cuadro(cuadro, anio=2024, via="todas")
    assert not datos.duplicated(["fecha", "pais", "via"]).any()
    assert (datos["llegadas"] >= 0).all()


def test_todos_los_paises_tienen_region(cuadro):
    datos, _ = leer_cuadro(cuadro, anio=2024, via="todas")
    assert datos["region"].notna().all()
    assert datos.set_index("pais")["region"].to_dict()["Nicaragua"] == "América Central"


def test_validar_detecta_duplicados(cuadro):
    datos, _ = leer_cuadro(cuadro, anio=2024, via="todas")
    with pytest.raises(ValueError, match="Duplicados"):
        validar(pd.concat([datos, datos.head(1)]))


@pytest.mark.parametrize(
    "entrada, esperado",
    [("Canadá 1/", "Canadá"), ("  Reino   Unido ", "Reino Unido"), ("Otros*", "Otros"), (None, "")],
)
def test_normalizar_texto(entrada, esperado):
    assert normalizar_texto(entrada) == esperado


def test_variacion_interanual():
    duckdb = pytest.importorskip("duckdb")  # noqa: F841
    from src.cargar import construir
    from src.consultas import variacion_interanual

    fechas = pd.date_range("2023-01-01", "2024-12-01", freq="MS")
    datos = pd.DataFrame({
        "fecha": fechas, "pais": "Estados Unidos", "region": "América del Norte",
        "via": "todas", "llegadas": [100] * 12 + [150] * 12,
    })  # fmt: skip
    serie = datos.groupby(["fecha", "via"], as_index=False)["llegadas"].sum()
    con = construir(datos, serie, ":memory:")
    var = variacion_interanual(con, via="todas", desde=2024, hasta=2024)
    assert len(var) == 12
    assert var["variacion_interanual"].round(4).eq(0.5).all()


PDF_2025 = RAW / "2025-12_Llegadas_internacionales.pdf"


def test_unificar_nombres_entre_cuadros():
    from src.cargar import unificar_paises

    datos = pd.DataFrame({"pais": ["PANAMA", "Panamá", "REPÚBLICA CHECA", "Republica Checa"]})
    assert unificar_paises(datos)["pais"].tolist() == [
        "Panamá",
        "Panamá",
        "República Checa",
        "República Checa",
    ]


@pytest.mark.skipif(not PDF_2025.exists(), reason="Falta el PDF del ICT en data/raw")
def test_pdf_real_cuadra_con_ict():
    """Cada cuadro por país suma igual que su fila TOTAL, y el TOTAL coincide con la serie 2019-2025."""
    from src.cargar import leer_todo

    datos, serie = leer_todo()  # falla si algo no cuadra
    anual = serie[serie["via"] == "todas"].groupby(serie["fecha"].dt.year)["llegadas"].sum()
    assert anual[2019] == 3_139_008  # Ene-Dic publicado en el Cuadro 11
    assert anual[2025] == 2_943_991
    assert datos.loc[datos["via"] == "todas", "llegadas"].sum() == 2_943_991
    assert datos["region"].notna().all()
