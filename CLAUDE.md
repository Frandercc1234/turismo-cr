# CLAUDE.md

Proyecto de portafolio: dashboard de llegadas internacionales a Costa Rica con datos del ICT. Plan de 7 días en `PLAN.md`.

## Reglas

- Hablá en español. Directo, código primero, explicaciones mínimas.
- No sobreingenierices. Tres preguntas, tres gráficos. No agregar vistas nuevas sin que lo pida.
- Stack fijo: Python 3.12, pandas + pdfplumber, DuckDB, Plotly, Streamlit, pytest, ruff.
- Nunca inventes ni rellenes datos. Si falta algo, se reduce el alcance y se anota en el README.

## Datos

- `data/raw/` es solo lectura. Nunca modificar los PDF originales.
- Cada cuadro usado va en `data/raw/archivos.csv`: archivo, página, cuadro, tipo (paises/serie), año, vía, URL y fecha de descarga.
- `extraer_cuadro_pdf()` asigna cada número a la columna más cercana por posición x. Si el ICT cambia el layout, falla con "fuera de columna" en vez de cargar mal.
- Cuadros del ICT: fila TOTAL arriba, zonas en MAYÚSCULAS con su subtotal, países debajo. `limpieza.py` descarta TOTAL y zonas; nunca sumarlos.
- La vía "todas" ya incluye aérea y terrestre. Toda consulta filtra por una sola vía.
- Mes sin dato = NaN, no cero.
- `serie_publicada` = totales oficiales 2019+. `fact_llegadas` = detalle por país (solo años con PDF cargado).

## Comandos

```bash
python -m src.cargar     # reconstruye data/processed/turismo.duckdb
pytest                   # correr antes de dar algo por terminado
ruff check . && ruff format .
streamlit run app.py
```

## Hecho significa

Tests en verde, ruff limpio, la app abre sin errores en escritorio y en celular (ancho 375px), y las cifras cuadran con el ICT.
