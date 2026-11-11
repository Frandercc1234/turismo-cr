from pathlib import Path

import pandas as pd
import pytest

from src.estilo import fmt
from src.indicadores import (
    acumulado_vs_2019,
    concentracion_temporada,
    marzo_abril_vs_2019,
    mes_semana_santa,
    perfil_mensual,
)

DB = Path(__file__).parent.parent / "data" / "processed" / "turismo.duckdb"


def _con(filas):
    pytest.importorskip("duckdb")
    from src.cargar import construir

    datos = pd.DataFrame(filas)
    serie = datos.groupby(["fecha", "via"], as_index=False)["llegadas"].sum()
    return construir(datos, serie, ":memory:")


def test_fmt_formato_espanol():
    assert fmt(2943991) == "2.943.991"
    assert fmt(0.0621, "pct") == "+6,2%"
    assert fmt(-0.2276, "pct") == "-22,8%"
    assert fmt(0.5656, "part") == "56,6%"
    assert fmt(1627807, "corto") == "1,63 M"
    assert fmt(274081, "corto") == "274.081"
    assert fmt(5.28, "dec") == "5,3"
    assert fmt(float("nan")) == "sin dato"
    assert fmt(None, "pct") == "sin dato"


def test_umbral_relativo_evita_saltos_de_numeros_chicos():
    from src.consultas import mas_crece, ranking_paises

    filas = []
    for pais, v24, v25 in [("Chico", 50, 100), ("Grande", 10000, 11000)]:
        for fecha, v in [("2024-01-01", v24), ("2025-01-01", v25)]:
            filas.append({"fecha": pd.Timestamp(fecha), "pais": pais, "region": "Europa",
                          "via": "todas", "llegadas": v})  # fmt: skip
    con = _con(filas)
    filtros = dict(via="todas", desde=2025, hasta=2025, regiones=[], paises=[])
    rk = ranking_paises(con, **filtros)
    # total de la vía en 2024 = 10.050; 0,5% = 50,25 > 50, así que "Chico" no califica
    assert rk.set_index("pais")["califica"].to_dict() == {"Chico": False, "Grande": True}
    assert mas_crece(rk)["pais"] == "Grande"  # +10% (el +100% de Chico no cuenta)
    sin_umbral = ranking_paises(con, min_participacion=0, **filtros)
    assert mas_crece(sin_umbral)["pais"] == "Chico"
    assert mas_crece(ranking_paises(con, min_participacion=1.0, **filtros)) is None  # nadie llega al 100%


@pytest.mark.skipif(not DB.exists(), reason="Falta data/processed/turismo.duckdb")
def test_lir_2025_vs_2024_con_datos_reales():
    import duckdb

    from src.consultas import mas_crece, ranking_paises

    con = duckdb.connect(str(DB), read_only=True)
    rk = ranking_paises(con, via="lir", desde=2025, hasta=2025, regiones=[], paises=[])
    por_pais = rk.set_index("pais")
    assert len(rk) == 10
    assert round(por_pais.loc["Estados Unidos", "crecimiento"] * 100, 1) == 2.3
    assert round(por_pais.loc["Canadá", "crecimiento"] * 100, 1) == 6.2
    assert round(por_pais.loc["Reino Unido", "crecimiento"] * 100, 1) == -22.8
    assert not por_pais.index.str.startswith("Otros ").any()
    crece = mas_crece(rk)
    assert crece["pais"] == "Canadá"
    assert round(crece["crecimiento"] * 100, 1) == 6.2


def test_validar_idiomas_falla_con_pais_nuevo():
    from src.cargar import validar_idiomas

    validar_idiomas(["Canadá", "Otros Europa"])  # mapeados: no falla
    with pytest.raises(ValueError, match="Atlantis"):
        validar_idiomas(["Canadá", "Atlantis"])


@pytest.mark.skipif(not DB.exists(), reason="Falta data/processed/turismo.duckdb")
def test_todo_pais_de_la_base_tiene_idioma():
    import duckdb

    con = duckdb.connect(str(DB), read_only=True)
    sin_idioma = con.execute("SELECT pais FROM dim_pais WHERE idioma IS NULL").fetchall()
    assert sin_idioma == []
    otros = con.execute("SELECT DISTINCT idioma FROM dim_pais WHERE pais LIKE 'Otros %'").fetchall()
    assert otros == [("Varios",)]


def test_idiomas_principales_porcentaje_del_total():
    from src.consultas import idiomas_principales

    filas = [
        {"fecha": pd.Timestamp("2025-01-01"), "pais": p, "region": "Europa", "via": "todas", "llegadas": v}
        for p, v in [("Estados Unidos", 90), ("Alemania", 6), ("España", 3), ("Otros Europa", 1)]
    ]
    con = _con(filas)
    idi = idiomas_principales(con, via="todas", desde=2025, hasta=2025, regiones=[], paises=[])
    assert idi["idioma"].tolist() == ["inglés", "alemán", "español"]  # "Varios" no se lista
    assert idi["participacion"].round(3).tolist() == [0.9, 0.06, 0.03]  # pero cuenta en el total


def test_semana_santa_coincide_con_la_nota_del_ict():
    esperado = {2019: 4, 2020: 4, 2021: 4, 2022: 4, 2023: 4, 2024: 3, 2025: 4}
    assert {a: mes_semana_santa(a) for a in esperado} == esperado


def test_dim_fecha_marca_un_mes_de_semana_santa_por_anio():
    filas = [
        {"fecha": pd.Timestamp(a, m, 1), "pais": "Canadá", "region": "América del Norte",
         "via": "todas", "llegadas": 1}
        for a in range(2019, 2026) for m in (3, 4)
    ]  # fmt: skip
    con = _con(filas)
    marcados = con.execute("SELECT anio, mes FROM dim_fecha WHERE semana_santa ORDER BY anio").fetchall()
    assert marcados == [(2019, 4), (2020, 4), (2021, 4), (2022, 4), (2023, 4), (2024, 3), (2025, 4)]


def test_marzo_abril_juntos_contra_2019():
    fechas = pd.to_datetime(["2024-03-01", "2024-04-01"])
    s = pd.DataFrame(
        {"fecha": fechas, "mes": [3, 4], "llegadas": [150.0, 50.0], "llegadas_2019": [60.0, 140.0]}
    )
    assert marzo_abril_vs_2019(s, 2024) == pytest.approx(0.0)  # 200 contra 200
    assert marzo_abril_vs_2019(s.iloc[:1], 2024) is None  # falta abril
    assert marzo_abril_vs_2019(s.assign(llegadas_2019=float("nan")), 2024) is None


def _serie(anios, valor_mes):
    fechas = pd.date_range(f"{anios[0]}-01-01", f"{anios[-1]}-12-01", freq="MS")
    s = pd.DataFrame({"fecha": fechas, "mes": fechas.month})
    s["llegadas"] = [valor_mes(f) for f in fechas]
    s["llegadas_2019"] = float("nan")
    return s


def test_concentracion_usa_solo_anios_completos_sin_pandemia():
    # temporada alta (dic-abr = 5 meses) vale el doble: 10 / (10 + 7) = 58,8%
    s = _serie([2024, 2025], lambda f: 2 if f.month in (12, 1, 2, 3, 4) else 1)
    assert concentracion_temporada(s) == pytest.approx(10 / 17)
    # 2020 y 2021 se ignoran aunque estén completos
    pandemia = _serie([2020, 2021], lambda f: 100)
    assert concentracion_temporada(pandemia) is None
    # un año incompleto no cuenta
    incompleto = s[s["fecha"] < "2025-07-01"]
    assert concentracion_temporada(incompleto) == pytest.approx(10 / 17)


def test_concentracion_respeta_el_filtro_aplicado():
    # La serie ya llega filtrada: mismo cálculo, otra estacionalidad
    plana = _serie([2024, 2025], lambda f: 1)
    assert concentracion_temporada(plana) == pytest.approx(5 / 12)
    assert perfil_mensual(plana).tolist() == [2] * 12


def test_acumulado_vs_2019():
    s = _serie([2025], lambda f: 12)
    s["llegadas_2019"] = 10.0
    total, var, n = acumulado_vs_2019(s, 2025)
    assert (total, n) == (144, 12)
    assert var == pytest.approx(0.2)
    s["llegadas_2019"] = float("nan")
    assert acumulado_vs_2019(s, 2025)[1] is None
