# Crítica de diseño: Turismo CR (antes del repaso visual)

Método: dual-agent. Dos sub-agentes aislados, uno de revisión de diseño (A) y otro de detector y evidencia del navegador (B), que no vieron el resultado del otro. Modo: Read (entender la historia en menos de un minuto). Estado revisado: rama `main` en `69b3d7c`-`b81664b`, capturas en `docs/img/antes/`.

Notas de método:
- A no abrió pestaña propia: se apoyó en las capturas "antes" (1280 y 375) y en el código.
- B: el CLI `impeccable detect` sobre la URL devolvió 0 hallazgos, pero no ejecuta el JavaScript de Streamlit, así que probablemente no analizó el DOM renderizado. La superposición en el navegador sí corrió y marcó 1 hallazgo.

## Puntaje de heurísticos de Nielsen

| # | Heurístico | Nota | Problema clave |
|---|---|---|---|
| 1 | Estado del sistema | 3 | Falta etiqueta del último valor en el gráfico |
| 2 | Lenguaje real | 3 | "vs", "sin base 2019" y "mismo mes 2019" son jerga de analista |
| 3 | Control y libertad | 3 | "Restablecer filtros" está dentro del popover |
| 4 | Consistencia | 2 | Tarjetas con y sin delta se ven desparejas |
| 5 | Prevención de errores | 3 | Vía "todas" con filtro de país sin aviso visual |
| 6 | Reconocimiento | 2 | Leyenda lejos de las líneas; el criterio de orden del ranking vive en un caption de 12 px |
| 7 | Flexibilidad | 2 | Región y país escondidos en el popover |
| 8 | Estética minimalista | 2 | Caja dentro de caja: tarjetas con borde dentro de contenedores con borde |
| 9 | Recuperación de errores | 3 | Mensajes claros con salida concreta |
| 10 | Ayuda | 3 | El tooltip "?" es un objetivo táctil pequeño |
| | **Total** | **26/40** | **Aceptable** |

## Veredicto de especificidad

Medio-bajo. El sistema de color (un azul, gris cálido, rojo y verde solo para variaciones) y el formato español (`2.943.991`, `+6,2%`) tienen criterio propio. La estructura es la de Streamlit por defecto: H1 grande, `st.metric` con borde, contenedores con borde y preguntas numeradas. Nada dice "Guanacaste" ni "cámara de turismo", y los títulos son preguntas, no respuestas.

Escaneo determinístico: 1 hallazgo, `skipped-heading` (un `<h1>` seguido de un `<h3>` sin `<h2>`), que viene de usar `st.title` y `st.subheader`. No es falso positivo.

## Evidencia medida en el navegador

- Contraste: 30 de 43 textos de los gráficos estaban por debajo de 4,5:1. Todos eran `#898781` sobre `#fcfcfb` (3,5:1): ticks de 12 px, anotaciones y subtítulos del ranking. Los otros 13 (`#52514e`) pasaban con 7,7:1.
- A 375 px no hay scroll horizontal de página (`scrollWidth` 375). El slider de años desborda 6 a 8 px en sus etiquetas de extremos, sin recorte.

## Fortalezas

1. El mapa de calor: escala secuencial de un solo tono, línea de "Temporada alta" y filas ordenadas por mes pico. Es lo más hecho a medida del producto.
2. Disciplina de formato (`fmt`) y color semántico: rojo y verde solo en variaciones, con flecha o signo; los datos faltantes en gris, nunca en cero.
3. Texto honesto: Semana Santa con rombo, pandemia sombreada y metodología accesible.

## Problemas prioritarios

- **P1. La historia no está en los títulos.** Cada sección pregunta y obliga a leer tarjetas, gráfico y leyenda para saber la respuesta. Fix: título con el veredicto calculado desde los datos (`app.py`). Comando sugerido: `clarify`.
- **P1. Contraste del texto secundario.** `TINTA_TENUE` da 3,5:1 sobre la superficie y 3,2:1 sobre el fondo secundario. Fix: oscurecerlo y separar el color de la línea de referencia (`estilo.py`). Comando sugerido: `audit`.
- **P2. El ranking ordena y colorea por crecimiento, no por peso.** China (+12,7% sobre 1.455 llegadas) parece la noticia y Estados Unidos (695.273) casi no se ve. Fix: ordenar por llegadas o atenuar los países de baja participación (`graficos.py`). Comando sugerido: `layout`.
- **P2. Móvil a 375 px.** Las tarjetas se apilan una por pantalla y empujan el gráfico fuera de vista; el heatmap de 12 columnas es difícil de leer. Fix: menos tarjetas apiladas, `st.columns` de 2 y etiquetas de mes más cortas (`app.py`, `graficos.py`). Comando sugerido: `adapt`.
- **P3. Aspecto de Streamlit por defecto.** Fix: una tipografía propia vía `[[theme.fontFaces]]` y un color propio en el tema (`config.toml`, `estilo.py`). Comando sugerido: `typeset`.

## Banderas rojas por persona

- **Alex (analista de la cámara, 60 s):** la respuesta a "¿se recuperó?" exige leer tres tarjetas y el gráfico; el orden por crecimiento hace perder el ranking de volumen.
- **Sam (accesibilidad):** contraste de ticks y captions por debajo de 4,5:1; el mapa de calor solo da valores al pasar el mouse; el ranking depende de rojo y verde con apoyo en texto de 12 px.
- **Casey (móvil, 375 px):** tarjetas apiladas que llenan cada pantalla, tooltip "?" pequeño, scroll largo antes del primer gráfico, heatmap de 12 columnas.

## Observaciones menores

- La leyenda de la línea de tiempo conviene sustituirla por etiquetas directas al final de cada línea.
- El rombo de Semana Santa se parece a la línea punteada de 2019 y solo se explica en la metodología.
- "Mes más bajo" no tiene subtexto, rompe el ritmo de las otras dos tarjetas.
- "Mes pico: Mar" junto a un mapa donde casi todas las filas pican en enero o diciembre: aclarar que es el mes con más llegadas en promedio.
- `page_title` sin ícono; el botón de descarga queda sin jerarquía de pie de página.

## Preguntas para decidir

- Si cada título fuera la respuesta ("Sí, en Liberia"), ¿seguiría haciendo falta la mitad de los captions?
- ¿Un país con 1.455 llegadas merece la misma tinta que uno con 695.273?
- ¿Qué ve quien abre el enlace desde el teléfono: un gráfico o tres tarjetas?

## Qué entra en este repaso y qué no

El repaso cubre los puntos 1 a 4 del pedido (contraste, identidad, títulos con el hallazgo, móvil a 375 px). Quedan fuera, por el alcance acordado, el reordenamiento del ranking por llegadas, la fusión de tarjetas de la pregunta 3 y los cambios de datos o consultas.
