"""Convierte los cuadros de llegadas del ICT a formato largo.

El ICT publica un PDF por año. extraer_cuadro_pdf() saca la tabla de una página
ubicando cada número por su posición (las celdas vacías no dejan marca en el texto).

Cuadros por país (1, 3, 5, 7 y 9):
    fila TOTAL arriba, luego cada ZONA EN MAYÚSCULAS con su subtotal,
    debajo sus países, filas vacías entre zonas, columnas Enero..Diciembre + Ene-Dic.

Reglas:
    - TOTAL y zonas no se cargan como datos (evita duplicar cifras).
    - Celda vacía o "-" = sin dato (NaN), nunca cero.
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import pandas as pd
import pdfplumber

MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "setiembre": 9, "septiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
}  # fmt: skip

ZONAS = {
    "AMERICA DEL NORTE": "América del Norte",
    "AMERICA CENTRAL": "América Central",
    "AMERICA DEL SUR": "América del Sur",
    "CARIBE": "Caribe",
    "EUROPA": "Europa",
    "ASIA Y EL PACIFICO": "Asia y el Pacífico",
    "AFRICA": "África",
    "ORIENTE MEDIO": "Oriente Medio",
    "OTROS": "Otros",
}

VIAS = {"todas", "aerea", "terrestre", "maritima", "sjo", "lir"}


def _sin_tildes(texto: str) -> str:
    nfkd = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def normalizar_texto(valor: object) -> str:
    """Quita espacios extra, notas al pie ('1/', '*') y saltos de línea."""
    if pd.isna(valor):
        return ""
    texto = str(valor).replace("\n", " ")
    texto = re.sub(r"\s*(\d+/|\*+)\s*$", "", texto)
    texto = re.sub(r"(?<=[^\W\d_])\d$", "", texto.strip())  # "Puerto Rico1" -> "Puerto Rico"
    return re.sub(r"\s+", " ", texto).strip()


def clave_zona(texto: str) -> str | None:
    clave = _sin_tildes(texto).upper()
    return clave if clave in ZONAS else None


def a_numero(valor: object) -> float:
    if pd.isna(valor):
        return float("nan")
    if isinstance(valor, (int, float)):
        return float(valor)
    texto = str(valor).strip().replace(" ", "").replace(" ", "")
    if texto in {"", "-", "–", "n.d.", "nd"}:
        return float("nan")
    return float(texto.replace(",", ""))


NUM = re.compile(r"^\d{1,3}$")


def _lineas(palabras: list[dict], tolerancia: float = 4.0) -> list[list[dict]]:
    lineas: list[list[dict]] = []
    for w in sorted(palabras, key=lambda w: (round(w["top"]), w["x0"])):
        if lineas and abs(lineas[-1][0]["top"] - w["top"]) <= tolerancia:
            lineas[-1].append(w)
        else:
            lineas.append([w])
    return [sorted(linea, key=lambda w: w["x0"]) for linea in lineas]


def _numeros(tokens: list[dict]) -> list[tuple[float, int]]:
    """Une '298' '475' -> (x1, 298475). Separador de miles = espacio angosto."""
    nums: list[tuple[float, str]] = []
    prev = None
    for w in tokens:
        if prev is not None and len(w["text"]) == 3 and w["x0"] - prev["x1"] < 3.5:
            nums[-1] = (w["x1"], nums[-1][1] + w["text"])
        else:
            nums.append((w["x1"], w["text"]))
        prev = w
    return [(x, int(t)) for x, t in nums]


def _es_anual(texto: str) -> bool:
    return re.sub(r"[^a-z]", "", texto.lower()) == "enedic"  # "Ene-Dic", "Ene.-Dic."


def _grilla_pagina(palabras: list[dict], cuadro: int | None) -> list[list]:
    """Filas de una página. Si `cuadro` viene, recorta a ese cuadro (puede haber dos por página)."""
    lineas = _lineas(palabras)
    if cuadro is not None:
        titulos = [i for i, ln in enumerate(lineas) if ln[0]["text"].lower() == "cuadro" and len(ln) > 1]
        inicio = next(i for i in titulos if lineas[i][1]["text"] == str(cuadro))
        fin = next((i for i in titulos if i > inicio), len(lineas))
        lineas = lineas[inicio:fin]

    def es_col(t: str) -> bool:
        return _sin_tildes(t).lower() in MESES or re.fullmatch(r"(19|20)\d\d", t) is not None

    i_enc = next(i for i, ln in enumerate(lineas) if sum(es_col(w["text"]) for w in ln) >= 5)
    columnas = [(w["x1"], w["text"]) for w in lineas[i_enc] if es_col(w["text"])]
    # columna anual en cuadros por mes: aparece arriba del encabezado
    anual = [w for ln in lineas[: i_enc + 1] for w in ln if _es_anual(w["text"])]
    if anual and _sin_tildes(columnas[0][1]).lower() in MESES:
        columnas.append((anual[0]["x1"], "Ene-Dic"))
    xs = [x for x, _ in columnas]
    borde = min(xs) - 45  # los números están a la derecha de esto
    # tolerancia = media distancia entre columnas (los encabezados no siempre alinean igual que los datos)
    tol = min(b - a for a, b in zip(xs, xs[1:], strict=False)) / 2

    filas = [["", *[c for _, c in columnas]]]
    for ln in lineas[i_enc + 1 :]:
        if re.match(r"(nota|fuente)", ln[0]["text"], re.I):
            continue
        es_dato = [w["x1"] >= borde and NUM.match(w["text"]) is not None for w in ln]
        etiqueta = " ".join(w["text"] for w, dato in zip(ln, es_dato, strict=True) if not dato)
        valores: list[int | None] = [None] * len(columnas)
        for x, n in _numeros([w for w, dato in zip(ln, es_dato, strict=True) if dato]):
            j = min(range(len(xs)), key=lambda k: abs(xs[k] - x))
            if abs(xs[j] - x) > tol:
                raise ValueError(f"Número {n} fuera de columna en '{etiqueta}' (x={x:.0f})")
            valores[j] = n
        if etiqueta or any(v is not None for v in valores):
            filas.append([etiqueta, *valores])
    return filas


def extraer_cuadro_pdf(pdf: str | Path, pagina: int, cuadro: int, paginas: int = 1) -> pd.DataFrame:
    """Devuelve la tabla del cuadro como grilla: fila 0 = encabezados, col 0 = etiqueta.

    `paginas` > 1 para cuadros que siguen en las páginas siguientes (anuario).
    Encabezados válidos: meses (cuadros por país) o años (series). Celdas vacías = None.
    """
    filas: list[list] = []
    with pdfplumber.open(pdf) as doc:
        for k in range(paginas):
            palabras = doc.pages[pagina - 1 + k].extract_words()
            grilla = _grilla_pagina(palabras, cuadro if k == 0 else None)
            if filas and grilla[0] != filas[0]:
                raise ValueError(f"Encabezado distinto en página {pagina + k}: {grilla[0]}")
            filas += grilla if k == 0 else grilla[1:]
    return pd.DataFrame(filas, dtype=object)


def leer_serie(grilla: pd.DataFrame, via: str) -> pd.DataFrame:
    """Cuadros 11-14: filas = meses, columnas = años. Devuelve fecha, via, llegadas."""
    anios = {j: int(v) for j, v in grilla.iloc[0].items() if str(v).isdigit()}
    filas = []
    for _, fila in grilla.iloc[1:].iterrows():
        mes = MESES.get(_sin_tildes(normalizar_texto(fila[0])).lower())
        if mes is None:  # Ene - Dic, notas
            continue
        for j, anio in anios.items():
            if fila[j] is not None and not pd.isna(fila[j]):
                filas.append((pd.Timestamp(anio, mes, 1), via, int(fila[j])))
    return pd.DataFrame(filas, columns=["fecha", "via", "llegadas"])


def clave_pais(nombre: str) -> str:
    return _sin_tildes(nombre).upper()


def nombre_preferido(variantes: list[str]) -> str:
    """Entre 'REPÚBLICA CHECA' y 'Republica Checa' arma 'República Checa'."""
    base = max(variantes, key=lambda v: (v != v.upper(), v != _sin_tildes(v), v))
    con_tilde = next((v for v in variantes if v != _sin_tildes(v) and len(v) == len(base)), None)
    if con_tilde is None or base != _sin_tildes(base):
        return base
    return "".join(t.lower() if b.islower() else t for b, t in zip(base, con_tilde, strict=True))


def _ubicar_encabezado(crudo: pd.DataFrame) -> tuple[int, dict[int, int]]:
    """Devuelve la fila del encabezado y {columna: mes}."""
    for i, fila in crudo.iterrows():
        columnas = {
            j: MESES[_sin_tildes(normalizar_texto(v)).lower()]
            for j, v in fila.items()
            if _sin_tildes(normalizar_texto(v)).lower() in MESES
        }
        if len(columnas) == 12:
            return i, columnas
    raise ValueError("No encontré una fila con los 12 meses como encabezado")


def leer_cuadro(
    origen: str | Path | pd.DataFrame, anio: int, via: str, hoja: str | int = 0
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Lee un cuadro del ICT.

    Retorna:
        datos: fecha, pais, region, via, llegadas (solo países, sin NaN)
        totales: fecha, total_publicado (fila TOTAL del cuadro, para validar)
    """
    if via not in VIAS:
        raise ValueError(f"via debe ser una de {sorted(VIAS)}")

    if isinstance(origen, pd.DataFrame):
        crudo = origen
    elif str(origen).lower().endswith(".pdf"):
        raise ValueError("Para PDF usá extraer_cuadro_pdf() y pasá la grilla")
    else:
        crudo = pd.read_excel(origen, sheet_name=hoja, header=None, dtype=object)
    fila_enc, col_mes = _ubicar_encabezado(crudo)
    col_etiqueta = crudo.columns[0]

    filas, totales, zona = [], [], None
    for _, fila in crudo.iloc[fila_enc + 1 :].iterrows():
        etiqueta = normalizar_texto(fila[col_etiqueta])
        if not etiqueta:
            continue
        if _sin_tildes(etiqueta).upper() == "TOTAL":
            totales += [(mes, a_numero(fila[c])) for c, mes in col_mes.items()]
            continue
        if clave := clave_zona(etiqueta):
            zona = ZONAS[clave]
            continue
        if zona is None:  # notas o texto antes de la primera zona
            continue
        for c, mes in col_mes.items():
            filas.append((mes, etiqueta, zona, a_numero(fila[c])))

    datos = pd.DataFrame(filas, columns=["mes", "pais", "region", "llegadas"])
    datos = datos.dropna(subset=["llegadas"])
    datos["fecha"] = pd.to_datetime(dict(year=anio, month=datos["mes"], day=1))
    datos["via"] = via
    datos["llegadas"] = datos["llegadas"].astype("int64")

    tot = pd.DataFrame(totales, columns=["mes", "total_publicado"])
    tot["fecha"] = pd.to_datetime(dict(year=anio, month=tot["mes"], day=1))

    return (
        datos[["fecha", "pais", "region", "via", "llegadas"]].reset_index(drop=True),
        tot[["fecha", "total_publicado"]],
    )


def validar(datos: pd.DataFrame, totales: pd.DataFrame | None = None) -> None:
    """Falla rápido si la limpieza dejó algo inconsistente."""
    clave = ["fecha", "pais", "via"]
    if datos.duplicated(clave).any():
        raise ValueError(f"Duplicados en {clave}:\n{datos[datos.duplicated(clave, keep=False)]}")
    if (datos["llegadas"] < 0).any():
        raise ValueError("Hay llegadas negativas")
    if datos["region"].isna().any():
        raise ValueError(f"Países sin región: {datos.loc[datos.region.isna(), 'pais'].unique()}")
    if totales is not None and not totales.empty:
        suma = datos.groupby("fecha")["llegadas"].sum().rename("suma")
        cmp = totales.dropna().set_index("fecha").join(suma)
        malos = cmp[cmp["total_publicado"] != cmp["suma"]]
        if not malos.empty:
            raise ValueError(f"La suma por mes no coincide con el TOTAL publicado:\n{malos}")
