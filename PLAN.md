# Plan

| Día | Tareas | Terminado cuando | Estado |
|---|---|---|---|
| 1 | Descargar archivos del ICT, llenar `data/raw/archivos.csv`, explorar en `notebooks/01_exploracion.ipynb` | Sabés qué columnas, años y problemas tienen | 2025 listo. Falta 2024 |
| 2 | Ajustar `src/limpieza.py` a los PDF reales | DataFrame limpio, sin filas de totales | Hecho para 2025 |
| 3 | `python -m src.cargar` + `pytest` | Los totales coinciden con el ICT | Base lista |
| 4 | Responder las tres preguntas en el notebook | Tres conclusiones con cifras en el README | |
| 5 | Ajustar la app: filtros, indicadores, tres gráficos | Funciona local en computadora y celular | Base lista |
| 6 | Revisar textos y estados vacíos, publicar en Streamlit Community Cloud | Enlace público funcionando | |
| 7 | README, capturas y video corto | Alguien entiende el proyecto en dos minutos | |

## Datos: qué falta

- **Datos por país 2024.** El candidato es el [Anuario Estadístico de Turismo 2024](https://ict.go.cr/en/administrar-estadistica/informes-estadísticos/anuarios/2005-2015/2863-2024-4/file.html) (trae zonas y países por mes 2024). Es otro formato que el informe mensual: revisar páginas y layout antes de agregarlo. Sin él no hay crecimiento por país (pregunta 2). Al agregarlo: copiar el PDF a `data/raw/`, agregar sus filas a `archivos.csv` (mismas páginas si el layout no cambió) y correr `python -m src.cargar` + `pytest`.
- Informes 2019-2023: opcionales. Solo hacen falta si se quiere la pregunta 1 filtrada por país.
- Las páginas 14 y 15 del PDF son gráficos, no tablas. No se usan.

## Publicar (día 6)

Streamlit Community Cloud lee el repo de GitHub. `turismo.duckdb` pesa poco, así que va en el repo. Cuando lleguen datos nuevos: `python -m src.cargar`, `pytest`, commit.
