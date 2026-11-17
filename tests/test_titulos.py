"""Los títulos arman la frase con las cifras que reciben, sin ninguna escrita a mano."""

import pytest

from src import titulos as t


def test_sujeto():
    assert t.sujeto("todas") == "El país"
    assert t.sujeto("lir") == "Liberia (LIR)"
    assert t.sujeto("aerea") == "La vía aérea"
    assert t.sujeto("lir", paises=["Canadá"]) == "Canadá en Liberia (LIR)"
    assert t.sujeto("todas", paises=["Canadá"]) == "Canadá"
    assert t.sujeto("aerea", paises=["Canadá"]) == "Canadá en la vía aérea"
    assert t.sujeto("lir", paises=["Canadá", "México"]) == "Los 2 países elegidos en Liberia (LIR)"
    assert t.sujeto("todas", regiones=["Europa"]) == "Europa"


def test_recuperacion_cambia_de_frase_segun_los_datos():
    arriba = t.recuperacion("Liberia (LIR)", 0.509, "2025", 904_762, -0.062)
    assert arriba == "1. Liberia (LIR) ya superó a 2019: +50,9% en 2025; el país entero aún no (-6,2%)"
    abajo = t.recuperacion("La vía terrestre", -0.653, "2025", 246_184, -0.062)
    assert (
        abajo == "1. La vía terrestre sigue por debajo de 2019: -65,3% en 2025; el país entero aún no (-6,2%)"
    )
    assert t.recuperacion("El país", 0.04, "2025", 3_000_000).endswith("+4,0% en 2025")
    assert "también (+3,0%)" in t.recuperacion("Liberia (LIR)", 0.5, "2025", 1, 0.03)
    assert "no hay base 2019" in t.recuperacion("Canadá", float("nan"), "2025", 1_234)
    assert t.recuperacion("Canadá", None, "2025", 1_234) == (
        "1. Canadá recibió 1.234 turistas en 2025; no hay base 2019 para comparar"
    )


def test_paises():
    eeuu = {"pais": "Estados Unidos", "llegadas": 695273, "crecimiento": 0.023}
    canada = {"pais": "Canadá", "llegadas": 173618, "crecimiento": 0.062}
    assert t.paises(2025, eeuu, canada, minimo=0.005) == (
        "2. Estados Unidos lidera con 695.273 llegadas en 2025; entre los países con al menos 0,5% "
        "de las llegadas de 2024, Canadá es el que más crece (+6,2%)"
    )
    # el mínimo sale del argumento: otro valor, otra frase
    assert "al menos 2,0% de las llegadas de 2024" in t.paises(2025, eeuu, canada, minimo=0.02)
    assert t.paises(2025, eeuu, eeuu, minimo=0.005).endswith("es el que más crece (+2,3%)")
    assert t.paises(2025, eeuu) == "2. Estados Unidos lidera con 695.273 llegadas en 2025"
    with pytest.raises(ValueError, match="mínimo"):  # no se puede decir «el que más crece» sin la regla
        t.paises(2025, eeuu, canada)
    assert (
        t.paises(2025, eeuu, unico=True)
        == "2. Estados Unidos recibió 695.273 turistas en 2025 (+2,3% contra 2024)"
    )
    assert t.paises(2024, {"pais": "Chile", "llegadas": 10, "crecimiento": float("nan")}, unico=True) == (
        "2. Chile recibió 10 turistas en 2024"
    )


def test_estacionalidad():
    assert (
        t.estacionalidad(0.55, 3)
        == "3. Marzo es el mes pico del total; diciembre a abril concentra 55,0% de las llegadas"
    )
    assert t.estacionalidad(0.5125, 9).startswith("3. Setiembre es el mes pico del total")
