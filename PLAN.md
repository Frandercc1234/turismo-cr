# Plan

| Día | Tareas | Terminado cuando | Estado |
|---|---|---|---|
| 1 | Descargar archivos del ICT, llenar `data/raw/archivos.csv`, explorar en `notebooks/01_exploracion.ipynb` | Sabés qué columnas, años y problemas tienen | Hecho: 2024 y 2025 |
| 2 | Ajustar `src/limpieza.py` a los PDF reales | DataFrame limpio, sin filas de totales | Hecho |
| 3 | `python -m src.cargar` + `pytest` | Los totales coinciden con el ICT | Base lista |
| 4 | Responder las tres preguntas en el notebook | Tres conclusiones con cifras en el README | |
| 5 | Ajustar la app: filtros, indicadores, tres gráficos | Funciona local en computadora y celular | Base lista |
| 6 | Revisar textos y estados vacíos, publicar en Streamlit Community Cloud | Enlace público funcionando | |
| 7 | README, capturas y video corto | Alguien entiende el proyecto en dos minutos | |

## Datos

- Cargados: informe dic-2025 y Anuario 2024. Ver `data/raw/archivos.csv`.
- El anuario tiene cada cuadro por país en 3 páginas (`paginas = 3` en el manifiesto).
- Anuarios 2019-2023: opcionales. Solo hacen falta para la pregunta 1 filtrada por país antes de 2024.

## Publicar (día 6)

Streamlit Community Cloud lee el repo de GitHub. `turismo.duckdb` pesa poco, así que va en el repo. Cuando lleguen datos nuevos: `python -m src.cargar`, `pytest`, commit.
