# Turismo CR: de dónde vienen los turistas y cuándo

Dashboard que responde tres preguntas para una cámara de turismo de Guanacaste, con datos públicos del Instituto Costarricense de Turismo (ICT).

| Pregunta | Cómo se responde | Decisión que permite |
|---|---|---|
| ¿Cómo evolucionó la llegada de turistas después de 2020? | Serie mensual vs. mismo mes de 2019 | Saber si el mercado ya se recuperó |
| ¿Qué países aportan más y cuáles crecen más rápido? | Ranking y variación interanual por país | Enfocar promoción e idiomas de atención |
| ¿Qué meses concentran la demanda por mercado? | Mapa de calor país x mes | Planificar personal e inventario |

**Demo:** _pendiente_ · **Video:** _pendiente_

## Hallazgos

_Pendiente (día 4). Tres conclusiones con cifras._

## Datos

- **Fuente:** ICT, Informes Estadísticos > Llegadas internacionales. Datos de la Dirección General de Migración y Extranjería.
- **Archivos usados:** `data/raw/archivos.csv` (archivo, hoja, año, vía, URL y fecha de descarga). Los originales están en `data/raw/` sin modificar.
- **Formato:** el ICT publica un PDF por año. `src/limpieza.py` lee las tablas del PDF ubicando cada número por su posición en la página.
- **Cobertura actual (informe dic-2025):**
  - Detalle por país x mes: 2025, 72 países en 8 regiones, vías todas / aérea / SJO / LIR / terrestre (cuadros 1, 3, 5, 7, 9).
  - Serie nacional mensual 2019-2025: todas / aérea / SJO / LIR (cuadros 11-14).

### Limitaciones

- Cada informe anual trae el detalle país x mes de un solo año. La pregunta 1 usa la serie nacional 2019-2025; el crecimiento por país necesita el informe del año anterior.
- No hay tabla de llegadas por vía marítima. Las vías disponibles son: todas, aérea, terrestre, y los aeropuertos SJO y LIR.
- 2020 y 2021 están afectados por el cierre de fronteras. Las variaciones de esos años no son demanda normal.
- Un mes sin dato queda vacío, no como cero.
- _Agregar aquí los países o años que falten._

## Modelo

Esquema estrella en DuckDB (`data/processed/turismo.duckdb`):

- `fact_llegadas (fecha, pais_id, via, llegadas)`
- `dim_fecha (fecha, anio, mes, nombre_mes, temporada)`: temporada alta = diciembre a abril
- `dim_pais (pais_id, pais, region)`: la región es la zona que usa el ICT
- `serie_publicada (fecha, via, llegadas)`: totales mensuales del ICT (cuadros 11-14 y filas TOTAL). Alimenta la pregunta 1 sin filtro de país y sirve para validar

## Correr local

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt

# 1. Poner los PDF del ICT en data/raw/ y listar cada cuadro en data/raw/archivos.csv
python -m src.cargar            # crea data/processed/turismo.duckdb
pytest                          # valida limpieza y totales contra el ICT
streamlit run app.py
```

## Estructura

```
data/raw/            PDF originales del ICT + archivos.csv
data/processed/      turismo.duckdb (se genera)
notebooks/           exploración y hallazgos
src/limpieza.py      PDF del ICT -> tabla larga (sin TOTAL ni subtotales de zona)
src/cargar.py        crea el modelo y carga las tablas
src/consultas.py     SQL parametrizado que usa la app
app.py               Streamlit
tests/               pytest
```

## Pruebas

- La suma de países por mes coincide con la fila TOTAL publicada, en los 5 cuadros.
- El TOTAL de 2025 coincide con la serie 2019-2025 y los totales anuales con el Ene-Dic publicado.
- Un país escrito distinto entre cuadros ("PANAMA" / "Panamá") queda como uno solo.
- No hay duplicados de (fecha, país, vía) ni llegadas negativas.
- Todo país tiene región.
- Un mes sin dato no se convierte en cero.
- La variación interanual da el resultado esperado con datos de ejemplo.
