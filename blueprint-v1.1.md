# Turismo CR v1.1: publicar, probar y mostrar

Complemento del proyecto actual (dashboard Streamlit con datos del ICT, 24 pruebas, README con hallazgos). Se aplica sobre la rama `main` tal como está. Las reglas de `CLAUDE.md` siguen vigentes.

Objetivo: que el proyecto tenga un enlace público estable, pruebas automáticas en CI con Playwright y material para mostrarlo (capturas y video).

---

## Resumen de cambios

| # | Situación actual | Cambio | Paso |
|---|---|---|---|
| 1 | `CLAUDE.md` con cambios sin commit; README con un marcador olvidado; notebook de hallazgos sin terminar | Repo limpio y notebook con los 3 hallazgos ejecutados | 1 |
| 2 | `requirements.txt` con versiones mínimas (`>=`); local usa Python 3.14, DuckDB 2.0, Streamlit 1.67; dependencias de desarrollo mezcladas | Versiones exactas, runtime y desarrollo separados, Python fijado | 2 |
| 3 | Sin pruebas de la app (solo de datos) | Pruebas con `st.testing.AppTest` por cada combinación de filtros | 3 |
| 4 | Sin pruebas en navegador | Pruebas con Playwright: carga, gráficas, CSV, móvil, sin errores | 4 |
| 5 | Sin `.github/` | CI en GitHub Actions con insignia en el README | 5 |
| 6 | "Demo: pendiente" | App publicada en Streamlit Community Cloud | 6 |
| 7 | "Video: pendiente"; una sola captura | Capturas y video de recorrido generados con Playwright | 7 |
| 8 | No hay instrucciones para cargar un informe nuevo | Sección "Actualizar los datos" en el README | 8 |
| 9 | Detalle por país solo 2024-2025 | (Opcional) Anuarios 2019-2023 | 9 |

**Fuera de alcance:** versión en inglés, nuevas preguntas o gráficas, otra plataforma de deploy, base de datos externa.

---

## Pasos

Reglas para todos los pasos:
- Commit al terminar cada uno (`v1.1 paso N: …`).
- Con cambios visibles, revisar con Playwright MCP a 375x812 y 1280x800.
- Antes de cerrar un paso: `ruff check . && ruff format --check . && pytest`.

### Paso 1. Repo limpio y notebook de hallazgos

- Commit de los cambios pendientes de `CLAUDE.md`.
- README: borrar la línea "_Agregar aquí los países o años que falten._".
- `notebooks/01_exploracion.ipynb`: completar la sección "Hallazgos" con 3 celdas de código que calculan desde `data/processed/turismo.duckdb` (usando `src/consultas.py` e `src/indicadores.py`) las cifras de los 3 hallazgos del README, cada una seguida de una celda de texto corta. Borrar las celdas vacías o de plantilla.
- Ejecutar y guardar con resultados: `jupyter nbconvert --to notebook --execute --inplace notebooks/01_exploracion.ipynb`.
- Aceptación: el notebook corre de punta a punta sin errores y sus cifras coinciden exactamente con las del README (2.943.991; -6,2%; +50,9%; 695.273; +2,3%; +6,2%; -22,8%; 55,0%; 4,2 veces).
- Verificar: el comando de `nbconvert` termina sin error + comparar las cifras impresas con el README.

### Paso 2. Dependencias y versión de Python

- Revisar qué versiones de Python ofrece hoy Streamlit Community Cloud (en el formulario de deploy, "Advanced settings") y elegir la más nueva que sea compatible con las librerías. Si 3.14 no está, usar la más alta disponible.
- Crear un entorno nuevo con esa versión (`.venv-deploy`, ignorado por git) y fijar ahí versiones exactas:
  - `requirements.txt` (solo lo que usa la app en producción): `streamlit`, `duckdb`, `pandas`, `plotly`, `python-dateutil`, con `==`.
  - `requirements-dev.txt`: `-r requirements.txt` + `pdfplumber`, `openpyxl`, `pytest`, `pytest-playwright`, `ruff`, `jupyter`, con `==`.
- La versión de DuckDB fijada tiene que abrir el `turismo.duckdb` del repo. Si no lo abre, regenerar la base con esa versión (`python -m src.cargar`), correr `pytest` y commitear la base nueva.
- Agregar `.python-version` con la versión elegida y anotarla en el README ("Correr local").
- Aceptación: en `.venv-deploy` limpio, `pip install -r requirements.txt` + `streamlit run app.py` funciona, y `pip install -r requirements-dev.txt` + `pytest` da todo verde.
- Verificar: los dos comandos en un entorno recién creado + Playwright MCP sobre `localhost:8501`.

### Paso 3. Pruebas de la app con AppTest

- Crear `tests/test_app.py` con `streamlit.testing.v1.AppTest.from_file("app.py", default_timeout=30)`. Casos:
  1. Valores por defecto (vía LIR, 2019 al último año): corre sin excepción y muestra los 3 subtítulos de las preguntas y las métricas de la pregunta 1.
  2. Vía "todas": no muestra la métrica "Todo el país" (ya es el país).
  3. Filtro país "Estados Unidos": aparece "Detalle por país desde 2024" y la pregunta 2 muestra una sola métrica del país.
  4. Filtro región "Europa": el ranking solo tiene países de Europa.
  5. Rango 2020-2021: la pregunta 3 muestra "Hace falta al menos un año completo".
  6. "Restablecer filtros" vuelve a los valores por defecto.
  7. Ninguna combinación de los casos anteriores deja `at.exception` con contenido.
- Aceptación: los 7 casos pasan en menos de 60 segundos en total.
- Verificar: `pytest tests/test_app.py -v`.

### Paso 4. Pruebas en navegador con Playwright

- Instalar el navegador de Playwright (la librería ya está en `requirements-dev.txt`): `python -m playwright install chromium`.
- `tests/e2e/conftest.py`: fixture de sesión que levanta `streamlit run app.py --server.headless true --server.port 8599` en un subproceso, espera a que responda y lo cierra al final. Si existe la variable `BASE_URL`, no levanta nada y usa esa URL (para probar producción).
- Marcar estas pruebas con `@pytest.mark.e2e` (registrado en `pyproject.toml`). `pytest` a secas no las corre; se corren con `pytest -m e2e`.
- `tests/e2e/test_dashboard_e2e.py`, en escritorio (1280x800) y móvil (375x812):
  1. La página carga en menos de 20 segundos y muestra "Llegadas a Costa Rica".
  2. No hay elementos de error de Streamlit (`[data-testid="stException"]`) ni errores en consola.
  3. Se dibujan las 3 gráficas (`.js-plotly-plot` = 3).
  4. "Descargar CSV" descarga un archivo `llegadas_filtradas.csv` con encabezado `fecha,pais,region,via,llegadas`.
  5. Cambiar la vía a "Todas las vías" actualiza el título de la pregunta 1.
  6. En móvil no hay scroll horizontal (`scrollWidth <= innerWidth`).
- Aceptación: todo verde contra local.
- Verificar: `pytest -m e2e -v`.

### Paso 5. CI en GitHub Actions

- `.github/workflows/ci.yml`, en cada push y pull request a `main`:
  - `actions/setup-python` con la versión de `.python-version` y caché de pip.
  - `pip install -r requirements-dev.txt`.
  - `ruff check .` y `ruff format --check .`.
  - `pytest` (datos + AppTest).
  - `python -m playwright install --with-deps chromium` y `pytest -m e2e`.
  - Si falla e2e, subir las capturas de Playwright como artifact.
- Insignia de CI arriba del README.
- Aceptación: el workflow queda en verde en `main`.
- Verificar: `gh run watch` sobre el último run.

### Paso 6. Publicar en Streamlit Community Cloud

- **Pausa:** este paso lo hace el usuario, porque requiere su cuenta. Darle estas instrucciones y esperar la URL:
  1. Entrar a share.streamlit.io con la cuenta de GitHub `Frandercc1234`.
  2. "Create app" → repo `Frandercc1234/turismo-cr`, rama `main`, archivo `app.py`.
  3. En "Advanced settings", elegir la versión de Python del paso 2.
  4. Subdominio: `turismo-cr` (o el más cercano disponible).
  5. Deploy y pasar la URL.
- Con la URL:
  - Correr `BASE_URL=<url> pytest -m e2e` contra producción.
  - README: reemplazar "Demo: _pendiente_" por el enlace y agregar debajo: "Si la app estuvo inactiva, Streamlit puede tardar unos segundos en despertarla."
  - `gh repo edit Frandercc1234/turismo-cr --homepage <url> --description "Dashboard de llegadas internacionales a Costa Rica con datos del ICT: PDF → DuckDB → Streamlit" --add-topic python,duckdb,streamlit,data-analysis,etl,costa-rica`.
- Aceptación: la URL pública carga y las pruebas e2e pasan contra ella.
- Verificar: `BASE_URL=<url> pytest -m e2e -v` + Playwright MCP sobre la URL a 375 y 1280.

### Paso 7. Capturas y video del recorrido

- `scripts/capturas.py` (Playwright, contra `BASE_URL` o local), que genera en `docs/img/`:
  - `app.png`: escritorio 1280x800, vía LIR, primera pantalla (reemplaza la actual).
  - `app-movil.png`: 375x812, primera pantalla.
  - `ranking.png` y `estacionalidad.png`: recorte de cada sección en escritorio.
- `scripts/video.py` (Playwright con `record_video_dir`, 1280x720), recorrido guionado de unos 45-60 segundos:
  1. Carga con LIR y pausa en las métricas de la pregunta 1.
  2. Scroll lento por la gráfica de recuperación.
  3. Pregunta 2: pausa en "Más llegadas", "Mayor crecimiento" e idiomas.
  4. Pregunta 3: pausa en el mapa de calor.
  5. Cambio de vía a "Todas las vías" y vuelta arriba.
- Convertir con ffmpeg: `docs/video/recorrido.mp4` (H.264, `-preset veryfast`) y `docs/img/recorrido.gif` (ancho 800px, máximo 8 MB, 10 fps).
- README: el GIF arriba en lugar de la captura, y "Video: _pendiente_" reemplazado por el enlace al MP4 del repo.
- Aceptación: el GIF se ve en el README de GitHub y pesa menos de 8 MB; el MP4 dura entre 45 y 60 segundos.
- Verificar: `python scripts/capturas.py && python scripts/video.py` + abrir los archivos generados.

### Paso 8. Guía para actualizar los datos

- README, sección nueva "Actualizar los datos" con 5 pasos:
  1. Descargar el informe nuevo del ICT a `data/raw/` sin modificarlo.
  2. Agregar sus cuadros a `data/raw/archivos.csv` (página, cuadro, tipo, año, vía, URL y fecha de descarga), copiando las filas del informe anterior como modelo.
  3. `python -m src.cargar`. Si el ICT cambió el diseño del PDF, falla con "fuera de columna": revisar las páginas con `extraer_cuadro_pdf` en el notebook.
  4. `pytest` (valida contra la fila TOTAL y la serie publicada).
  5. Commit del PDF, el manifiesto y `turismo.duckdb`; Streamlit Cloud redeploya solo.
- Aceptación: alguien sin contexto puede seguirla.
- Verificar: leerla de punta a punta contra el código real (`src/cargar.py`, `archivos.csv`).

### Paso 9 (opcional). Detalle por país desde 2019

Hacer solo si el usuario lo confirma al terminar el paso 8.

- **Pausa:** pedir al usuario los Anuarios Estadísticos de Turismo 2019 a 2023 del sitio del ICT (sección Informes estadísticos → Anuarios), o descargarlos si el sitio es accesible.
- Por cada anuario: ubicar las páginas de los cuadros por país (todas, aérea, SJO, LIR, terrestre y marítima), verificar que el diseño coincide con el del anuario 2024 y agregar sus filas a `archivos.csv`.
- Si un año tiene otro diseño y no se puede leer con la lógica actual, excluirlo y anotarlo en Limitaciones. No forzar la lectura.
- Pruebas nuevas: para cada año cargado, la suma por país coincide con su fila TOTAL, y esa fila TOTAL coincide con `serie_publicada`.
- App y README: cambiar "Detalle por país desde 2024" por el año real; actualizar Cobertura y Limitaciones; agregar un hallazgo nuevo con cifras sobre la recuperación de Estados Unidos y Canadá en LIR contra 2019.
- Aceptación: la pregunta 1 filtrada por país muestra la comparación con 2019 para los años cargados.
- Verificar: `python -m src.cargar && pytest && pytest -m e2e` + Playwright MCP con el filtro "Estados Unidos".

---

## Reglas

1. Seguir el orden. No pasar de paso sin su verificación.
2. Pausas obligatorias: deploy del usuario (paso 6) y confirmación del paso 9.
3. No cambiar la lógica de datos (`src/limpieza.py`, `src/cargar.py`) salvo en el paso 9 y solo si un anuario lo requiere.
4. No agregar preguntas, gráficas ni vistas.
5. No inventar cifras: todo número del README o del notebook sale de la base y coincide con la app.
6. Reportar al terminar cada paso en 2-3 líneas: qué cambió y cómo se verificó.
7. Responder en español.
