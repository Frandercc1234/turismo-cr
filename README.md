# Turismo CR: de dónde vienen los turistas y cuándo

[![CI](https://github.com/Frandercc1234/turismo-cr/actions/workflows/ci.yml/badge.svg)](https://github.com/Frandercc1234/turismo-cr/actions/workflows/ci.yml)

Dashboard que responde tres preguntas para una cámara de turismo de Guanacaste, con datos públicos del Instituto Costarricense de Turismo (ICT).

![Recorrido por el dashboard con el aeropuerto de Liberia (LIR) seleccionado](docs/img/recorrido.gif)

| Pregunta | Cómo se responde | Decisión que permite |
|---|---|---|
| ¿Cómo evolucionó la llegada de turistas después de 2020? | Serie mensual vs. mismo mes de 2019 | Saber si el mercado ya se recuperó |
| ¿Qué países aportan más y cuáles crecen más rápido? | Ranking y variación interanual por país | Enfocar promoción e idiomas de atención |
| ¿Qué meses concentran la demanda por mercado? | Mapa de calor país x mes | Planificar personal e inventario |

**Demo:** [abrir la app](https://turismo-cr-7juydxs6ebdqwumreibouf.streamlit.app/) · **Video:** [recorrido de 50 segundos](docs/video/recorrido.mp4)

Si la app estuvo inactiva, Streamlit puede tardar unos segundos en despertarla.

## El reto de los datos

El ICT publica PDF, no Excel. Las celdas vacías no dejan marca en el texto del PDF. Por eso cada número se ubica por su posición x bajo el encabezado de su columna.

![Recorte del Cuadro 7 del PDF junto a la tabla limpia](docs/img/pdf_vs_tabla.png)

Problemas resueltos en `src/limpieza.py` y `src/cargar.py`:

- Separador de miles con espacio: "298 475" se une en 298475.
- Notas al pie pegadas al nombre: "Puerto Rico1" pasa a "Puerto Rico".
- Cuadros de 3 páginas en el anuario.
- Un mismo país escrito distinto entre cuadros: "PANAMA" y "Panamá" quedan como uno.

Cada cuadro suma igual a su fila TOTAL publicada. El informe 2025 y el anuario 2024 coinciden en los 72 meses de 2019-2024. Los anuarios de 2019 a 2023 también cuadran con esas series, mes a mes. Si el ICT cambia el diseño del PDF, la carga falla con "fuera de columna" en vez de cargar mal.

## Hallazgos

Cifras que muestra la app con LIR (aeropuerto de Liberia, la medida de Guanacaste) y el rango 2019-2025.

1. **Por aire el país ya superó 2019; por tierra no, y eso explica el total.** En 2025 llegaron 2.943.991 turistas por todas las vías, 6,2% menos que en 2019. La vía aérea subió 11,2% y la terrestre cayó 65,3%. Por LIR llegaron 904.762 (+50,9%) y en diciembre 114.686 (+63,5% contra diciembre de 2019).
2. **Estados Unidos y Canadá sostienen a LIR; Europa cae.** LIR creció 2,7% contra 2024. Estados Unidos lidera con 695.273 llegadas (+2,3%) y Canadá es el que más crece entre los 10 principales (+6,2%). Reino Unido bajó 22,8%, y el inglés es el idioma de 97,5% de las llegadas.
3. **La demanda pica en marzo y toca fondo en setiembre.** Con años completos y sin 2020 y 2021, diciembre a abril concentra 55,0% de las llegadas. Marzo tiene 4,2 veces las llegadas de setiembre. Semana Santa cambia de mes (2024 en marzo, 2025 en abril) y mueve las comparaciones de marzo y abril.
4. **Estados Unidos y Canadá ya superan con holgura a 2019 en LIR.** En 2025 Estados Unidos llegó a 695.273 turistas por LIR (+57,8% contra 2019) y Canadá a 173.618 (+55,4%). Estados Unidos superó el nivel de 2019 en 2022 y Canadá en 2023. Juntos son 96,0% de las llegadas a LIR, contra 92,1% en 2019.

## Datos

- **Fuente:** ICT, Informes Estadísticos > Llegadas internacionales. Datos de la Dirección General de Migración y Extranjería.
- **Archivos usados:** informe mensual dic-2025 y Anuarios Estadísticos de Turismo 2019 a 2024. Cada cuadro va en `data/raw/archivos.csv` (archivo, página, cuadro, tipo, año, vía, URL y fecha de descarga). Los PDF originales están en `data/raw/` sin modificar.
- **Cobertura actual:**
  - Detalle por país x mes: 2019 a 2025, 74 países en 8 regiones. Vías: todas, aérea, SJO, LIR y terrestre hasta 2025; marítima hasta 2024.
  - Serie mensual publicada 2012-2025 para todas, aérea, SJO, LIR y terrestre. Marítima 2012-2024.
  - Los cuadros de los informes y de los anuarios coinciden mes a mes en las vías y meses que comparten. Si dos cuadros dan cifras distintas, la carga falla.

### Limitaciones

- Detalle por país solo desde 2019. Antes de 2019 existe solo la serie total publicada (desde 2012); con filtro de país o región la pregunta 1 cubre 2019 a 2025.
- El informe 2025 no trae vía marítima; esa vía llega hasta 2024.
- 2020 y 2021 están afectados por el cierre de fronteras. Las variaciones de esos años no son demanda normal.
- Un mes sin dato queda vacío, no como cero.
- El idioma se asigna por país de residencia y es una aproximación: Canadá cuenta como inglés.

## Modelo

Esquema estrella en DuckDB (`data/processed/turismo.duckdb`):

- `fact_llegadas (fecha, pais_id, via, llegadas)`
- `dim_fecha (fecha, anio, mes, nombre_mes, temporada, semana_santa)`: temporada alta = diciembre a abril; `semana_santa` marca el mes que contiene el Jueves Santo (Pascua menos 3 días)
- `dim_pais (pais_id, pais, region, idioma)`: la región es la zona que usa el ICT; el idioma sale de `IDIOMA_POR_PAIS` en `src/cargar.py` y es el idioma en que conviene atender, no el oficial
- `serie_publicada (fecha, via, llegadas)`: totales mensuales del ICT (cuadros 11-14 y filas TOTAL). Alimenta la pregunta 1 sin filtro de país y sirve para validar

## Correr local

Python 3.14 (versión en `.python-version`). `requirements.txt` trae solo lo que usa la app; `requirements-dev.txt` agrega lo de carga, pruebas y notebook. Las versiones están fijadas.

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements-dev.txt

# 1. Poner los PDF del ICT en data/raw/ y listar cada cuadro en data/raw/archivos.csv
python -m src.cargar            # crea data/processed/turismo.duckdb
pytest                          # valida limpieza y totales contra el ICT
streamlit run app.py
```

## Actualizar los datos

El ICT publica un informe nuevo cada mes. Para cargarlo:

1. Descargar el informe del ICT a `data/raw/` sin modificarlo.
2. Agregar sus cuadros a `data/raw/archivos.csv`, copiando las filas del informe anterior como modelo. Columnas: `archivo`, `pagina` (primera página del cuadro), `paginas` (cuántas ocupa), `cuadro` (número en el PDF), `tipo` (`paises` o `serie`), `anio` (solo en `paises`), `via` (`todas`, `aerea`, `sjo`, `lir`, `terrestre` o `maritima`), `url` y `fecha_descarga`.
3. Correr `python -m src.cargar`, que reconstruye `data/processed/turismo.duckdb`. Si el ICT cambió el diseño del PDF, falla con "fuera de columna" o "Encabezado distinto": revisar esas páginas con `extraer_cuadro_pdf` en `notebooks/01_exploracion.ipynb`. Si aparece un país nuevo, falla con "Países sin idioma": agregarlo a `IDIOMA_POR_PAIS` en `src/cargar.py`.
4. Correr `pytest`. Valida cada cuadro del manifiesto contra su fila TOTAL y exige que dos informes den las mismas cifras para un mismo mes. Si el informe agrega un año, algunas pruebas y cifras del README llevan valores fijos de 2025 (LIR contra 2024, el rango por defecto, los hallazgos): actualizarlas con las cifras de la base nueva.
5. Hacer commit del PDF, del manifiesto y de `turismo.duckdb`, y `git push`. Streamlit Cloud redeploya solo.

## Estructura

```
data/raw/            PDF originales del ICT + archivos.csv
data/processed/      turismo.duckdb (se genera)
notebooks/           exploración y hallazgos
src/limpieza.py      PDF del ICT -> tabla larga (sin TOTAL ni subtotales de zona)
src/cargar.py        crea el modelo y carga las tablas
src/consultas.py     SQL parametrizado que usa la app
src/indicadores.py   temporada, acumulados y Semana Santa sobre la serie filtrada
src/estilo.py        paleta, formato español (fmt) y plantilla Plotly
src/graficos.py      las tres gráficas
.streamlit/          tema de Streamlit (colores, barra de herramientas mínima)
docs/img/            capturas de la app, GIF del recorrido y recorte del PDF contra la tabla limpia
docs/video/          recorrido.mp4
scripts/             capturas.py y video.py (Playwright) regeneran las capturas y el video; vigilar_produccion.py abre la app publicada y la despierta si duerme
.github/workflows/   ci.yml (pruebas en cada push) y produccion.yml (revisa la app publicada cada 6 horas)
app.py               Streamlit
tests/               pytest
```

## Pruebas

- La suma de países por mes coincide con la fila TOTAL publicada, en los cuadros de cada año de 2019 a 2025.
- Para cada año con detalle por país, el TOTAL de cada cuadro coincide con la serie publicada, y la suma de países de la base coincide con ella.
- El TOTAL de 2025 coincide con la serie 2019-2025 y los totales anuales con el Ene-Dic publicado.
- Un país escrito distinto entre cuadros ("PANAMA" / "Panamá") queda como uno solo.
- No hay duplicados de (fecha, país, vía) ni llegadas negativas.
- Todo país tiene región.
- Un mes sin dato no se convierte en cero.
- La variación interanual da el resultado esperado con datos de ejemplo.
- Todo país de la base tiene idioma. Un país nuevo sin mapear hace fallar la carga y la prueba.
- Los meses de Semana Santa coinciden con la nota del ICT: abril de 2019 a 2023 y 2025, marzo de 2024.
- En LIR 2025 contra 2024: Estados Unidos +2,3%, Canadá +6,2% y Reino Unido -22,8%.
- En LIR 2025 contra 2019: Estados Unidos +57,8% y Canadá +55,4%; superan 2019 en 2022 y 2023.
- La app corre como en producción: con la base copiada a la carpeta temporal, con 8 sesiones a la vez, y con una base vacía, dañada o copiada a medias muestra un mensaje claro en vez de una traza.

## Capturas

<p align="center">
  <img src="docs/img/app.png" alt="Dashboard en escritorio con el aeropuerto de Liberia (LIR) seleccionado" height="420">
  &nbsp;
  <img src="docs/img/app-movil.png" alt="Dashboard en celular (375 px de ancho)" height="420">
</p>
- El ranking excluye las filas "Otros" y un país de 50 a 100 llegadas no gana a uno de 10.000 a 11.000.
