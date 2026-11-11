# Turismo CR: de dónde vienen los turistas y cuándo

Dashboard que responde tres preguntas para una cámara de turismo de Guanacaste, con datos públicos del Instituto Costarricense de Turismo (ICT).

| Pregunta | Cómo se responde | Decisión que permite |
|---|---|---|
| ¿Cómo evolucionó la llegada de turistas después de 2020? | Serie mensual vs. mismo mes de 2019 | Saber si el mercado ya se recuperó |
| ¿Qué países aportan más y cuáles crecen más rápido? | Ranking y variación interanual por país | Enfocar promoción e idiomas de atención |
| ¿Qué meses concentran la demanda por mercado? | Mapa de calor país x mes | Planificar personal e inventario |

**Demo:** _pendiente_ · **Video:** _pendiente_

## Hallazgos

Preliminares, a validar en el notebook (día 4):

1. **El país no volvió a 2019, Guanacaste sí lo superó.** En 2025 llegaron 2.943.991 turistas por todas las vías, 6,2% menos que en 2019. Por LIR llegaron 904.762, 50,9% más que en 2019.
2. **Norteamérica sostiene el crecimiento, Europa cae.** En LIR, Canadá creció 6,2% y Estados Unidos 2,3% frente a 2024. Reino Unido bajó 22,8% y Francia 11,2%.
3. **La temporada alta en LIR pica en marzo y toca fondo en setiembre.** En 2025 marzo tuvo 117.044 llegadas y setiembre 22.176, cinco veces menos.

## Datos

- **Fuente:** ICT, Informes Estadísticos > Llegadas internacionales. Datos de la Dirección General de Migración y Extranjería.
- **Archivos usados:** `data/raw/archivos.csv` (archivo, hoja, año, vía, URL y fecha de descarga). Los originales están en `data/raw/` sin modificar.
- **Formato:** el ICT publica un PDF por año. `src/limpieza.py` lee las tablas del PDF ubicando cada número por su posición en la página.
- **Archivos:** informe mensual dic-2025 y Anuario Estadístico de Turismo 2024.
- **Cobertura actual:**
  - Detalle por país x mes: 2024 y 2025, 73 países en 8 regiones. Vías: todas, aérea, SJO, LIR, terrestre. Marítima solo 2024.
  - Serie mensual publicada 2012-2025 para todas, aérea, SJO, LIR y terrestre. Marítima 2012-2024.
  - Los dos PDF coinciden mes a mes en 2019-2024 para las cuatro vías que comparten.

### Limitaciones

- Detalle por país solo para 2024 y 2025. La pregunta 1 sin filtro usa la serie publicada; con filtro de país arranca en 2024.
- El informe 2025 no trae vía marítima; solo existe para 2024 y antes.
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
