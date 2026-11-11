"""Indicadores que se calculan sobre la serie mensual ya filtrada (salida de serie_mensual)."""

from __future__ import annotations

from datetime import timedelta

import pandas as pd
from dateutil.easter import easter

PANDEMIA = (2020, 2021)
TEMPORADA_ALTA = (12, 1, 2, 3, 4)


def mes_semana_santa(anio: int) -> int:
    """Mes que contiene el Jueves Santo (Pascua menos 3 días). El ICT avisa que cambia de mes."""
    return (easter(anio) - timedelta(days=3)).month


def marzo_abril_vs_2019(serie: pd.DataFrame, anio: int) -> float | None:
    """Marzo y abril juntos de `anio` contra los mismos meses de 2019 (None si falta alguno)."""
    s = serie[(serie["fecha"].dt.year == anio) & serie["mes"].isin((3, 4))]
    if len(s) < 2 or s["llegadas"].isna().any() or s["llegadas_2019"].isna().any():
        return None
    return float(s["llegadas"].sum() / s["llegadas_2019"].sum() - 1)


def _anios_completos(serie: pd.DataFrame, excluir=PANDEMIA) -> pd.DataFrame:
    """Filas de los años con los 12 meses con dato, sin los años de pandemia."""
    s = serie.dropna(subset=["llegadas"]).copy()
    s["anio"] = s["fecha"].dt.year
    meses = s.groupby("anio")["mes"].transform("nunique")
    return s[(meses == 12) & ~s["anio"].isin(excluir)]


def concentracion_temporada(serie: pd.DataFrame, meses=TEMPORADA_ALTA) -> float | None:
    """Parte de las llegadas anuales que cae en los meses de temporada alta."""
    s = _anios_completos(serie)
    if s.empty:
        return None
    return float(s.loc[s["mes"].isin(meses), "llegadas"].sum() / s["llegadas"].sum())


def perfil_mensual(serie: pd.DataFrame) -> pd.Series | None:
    """Llegadas por mes del calendario (1-12), sumando los años completos."""
    s = _anios_completos(serie)
    return None if s.empty else s.groupby("mes")["llegadas"].sum()


def acumulado_vs_2019(serie: pd.DataFrame, anio: int) -> tuple[float, float | None, int] | None:
    """(llegadas del año, variación contra 2019, meses con dato) usando solo los meses con dato.

    La variación es None si falta la base 2019 de alguno de esos meses.
    """
    s = serie[serie["fecha"].dt.year == anio].dropna(subset=["llegadas"])
    if s.empty:
        return None
    total = float(s["llegadas"].sum())
    base = s["llegadas_2019"]
    variacion = total / base.sum() - 1 if base.notna().all() and base.sum() > 0 else None
    return total, variacion, len(s)
