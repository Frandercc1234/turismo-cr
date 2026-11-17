"""Títulos de cada sección: la conclusión, no el nombre de la métrica.

Toda cifra sale de los datos que reciben estas funciones, nunca va escrita a mano.
"""

from __future__ import annotations

from src.estilo import fmt

# Vía como complemento ("Estados Unidos en Liberia (LIR)") y su versión con mayúscula como sujeto
VIA_EN = {
    "lir": "Liberia (LIR)",
    "sjo": "San José (SJO)",
    "aerea": "la vía aérea",
    "terrestre": "la vía terrestre",
    "maritima": "la vía marítima",
}
MESES_LARGOS = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "setiembre",
                "octubre", "noviembre", "diciembre"]  # fmt: skip


def _mayuscula(texto: str) -> str:
    return texto[:1].upper() + texto[1:]


def sujeto(via: str, regiones=(), paises=()) -> str:
    """Quién es el sujeto de la frase: el país entero, una vía, o el país/región filtrados en esa vía."""
    if paises:
        nombre = paises[0] if len(paises) == 1 else f"Los {len(paises)} países elegidos"
    elif regiones:
        nombre = regiones[0] if len(regiones) == 1 else f"Las {len(regiones)} regiones elegidas"
    else:
        return "El país" if via == "todas" else _mayuscula(VIA_EN.get(via, via))
    return nombre if via == "todas" else f"{nombre} en {VIA_EN.get(via, via)}"


def recuperacion(quien: str, variacion, periodo: str, total, variacion_pais=None) -> str:
    """Pregunta 1. `variacion` es la del acumulado del año contra 2019; `variacion_pais` la de todas las vías."""
    if variacion is None or variacion != variacion:
        return f"1. {quien} recibió {fmt(total)} turistas en {periodo}; no hay base 2019 para comparar"
    if variacion >= 0:
        frase = f"1. {quien} ya superó a 2019: {fmt(variacion, 'pct')} en {periodo}"
    else:
        frase = f"1. {quien} sigue por debajo de 2019: {fmt(variacion, 'pct')} en {periodo}"
    if variacion_pais is None or variacion_pais != variacion_pais:
        return frase
    if variacion_pais >= 0:
        return f"{frase}; el país entero también ({fmt(variacion_pais, 'pct')})"
    return f"{frase}; el país entero aún no ({fmt(variacion_pais, 'pct')})"


def mercados_que_cuentan(hasta: int, minimo: float) -> str:
    """Regla de «mayor crecimiento», con el mismo mínimo que usa el cálculo (q.MIN_PARTICIPACION)."""
    return f"países con al menos {fmt(minimo, 'part')} de las llegadas de {hasta - 1}"


def paises(
    hasta: int, lider: dict, crece: dict | None = None, unico: bool = False, minimo: float | None = None
) -> str:
    """Pregunta 2. `lider` y `crece` traen pais, llegadas y crecimiento (puede faltar el crecimiento).

    `minimo` es la participación mínima que usa el cálculo de «mayor crecimiento»; es obligatoria
    cuando hay `crece`, porque «el que más crece» solo vale entre los países que cumplen esa regla.
    """
    if unico:
        frase = f"2. {lider['pais']} recibió {fmt(lider['llegadas'])} turistas en {hasta}"
        c = lider.get("crecimiento")
        return frase if c is None or c != c else f"{frase} ({fmt(c, 'pct')} contra {hasta - 1})"
    frase = f"2. {lider['pais']} lidera con {fmt(lider['llegadas'])} llegadas en {hasta}"
    if crece is None:
        return frase
    if minimo is None:
        raise ValueError("«el que más crece» necesita el mínimo de llegadas que usa el cálculo")
    regla = mercados_que_cuentan(hasta, minimo)
    pct = fmt(crece["crecimiento"], "pct")
    if crece["pais"] == lider["pais"]:
        return f"{frase} y, entre los {regla}, es el que más crece ({pct})"
    return f"{frase}; entre los {regla}, {crece['pais']} es el que más crece ({pct})"


def estacionalidad(concentracion: float, mes_pico: int) -> str:
    """Pregunta 3. `mes_pico` va de 1 a 12; es el del total de llegadas, no el de cada fila del mapa."""
    return (
        f"3. {_mayuscula(MESES_LARGOS[mes_pico - 1])} es el mes pico del total; "
        f"diciembre a abril concentra {fmt(concentracion, 'part')} de las llegadas"
    )
