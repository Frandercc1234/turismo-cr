"""Graba un recorrido guionado de la app y lo convierte a MP4 y GIF.

Uso:
    python scripts/video.py                  # contra la app local
    BASE_URL=https://... python scripts/video.py   # contra producción

Genera docs/video/recorrido.mp4 (H.264) y docs/img/recorrido.gif (800 px, máximo 8 MB, 10 fps).
"""

import re
import subprocess
import tempfile
from pathlib import Path

import imageio_ffmpeg
from _comun import RAIZ, abrir, servidor
from playwright.sync_api import sync_playwright

MP4 = RAIZ / "docs" / "video" / "recorrido.mp4"
GIF = RAIZ / "docs" / "img" / "recorrido.gif"
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
MAX_GIF_MB = 8


def desplazar(page, total: int, pasos: int = 16, pausa_ms: int = 120) -> None:
    """Scroll lento con la rueda del mouse, en pasos pequeños."""
    page.mouse.move(640, 400)
    for _ in range(pasos):
        page.mouse.wheel(0, total / pasos)
        page.wait_for_timeout(pausa_ms)


def ir_a(page, app, patron: str) -> None:
    """Lleva la pregunta (por su número) a la parte alta de la pantalla, con scroll lento."""
    titulo = app.get_by_role("heading", name=re.compile(rf"^{re.escape(patron)}"))
    y = titulo.evaluate("(h) => h.getBoundingClientRect().top")
    desplazar(page, y - 70, pasos=14, pausa_ms=100)


def recorrido(page, url: str) -> None:
    app = abrir(page, url)
    # 1. Métricas de la pregunta 1
    page.wait_for_timeout(3000)
    # 2. Gráfica de recuperación, scroll lento
    desplazar(page, 330, pasos=18, pausa_ms=140)
    page.wait_for_timeout(3000)
    # 3. Pregunta 2: métricas e idiomas, y luego el ranking
    ir_a(page, app, "2.")
    page.wait_for_timeout(3500)
    desplazar(page, 260, pasos=14, pausa_ms=140)
    page.wait_for_timeout(3000)
    # 4. Pregunta 3: métricas y mapa de calor
    ir_a(page, app, "3.")
    page.wait_for_timeout(3000)
    desplazar(page, 300, pasos=14, pausa_ms=140)
    page.wait_for_timeout(3000)
    # 5. Filtro "Estados Unidos": la pregunta 1 compara con 2019 (detalle por país desde 2019)
    desplazar(page, -6000, pasos=24, pausa_ms=60)
    page.wait_for_timeout(800)
    app.get_by_text("Más filtros").click()
    page.wait_for_timeout(500)
    app.locator('[data-testid="stMultiSelect"]').nth(1).click()
    page.keyboard.type("Estados", delay=60)
    page.wait_for_timeout(500)
    page.keyboard.press("Enter")
    page.wait_for_timeout(800)
    page.keyboard.press("Escape")
    page.mouse.click(300, 60)  # cierra el menú
    page.wait_for_timeout(5000)
    app.get_by_text("Más filtros").click()
    page.wait_for_timeout(500)
    app.get_by_role("button", name="Restablecer filtros").click()
    page.keyboard.press("Escape")
    page.mouse.click(300, 60)
    page.wait_for_timeout(1200)
    # 6. Cambio de vía
    app.get_by_label("Vía de ingreso").click()
    page.wait_for_timeout(800)
    app.get_by_role("option", name="Todas las vías").click()
    page.wait_for_timeout(3500)


def grabar(url: str, carpeta: Path) -> Path:
    with sync_playwright() as p:
        navegador = p.chromium.launch()
        contexto = navegador.new_context(
            viewport={"width": 1280, "height": 720},
            record_video_dir=str(carpeta),
            record_video_size={"width": 1280, "height": 720},
        )
        page = contexto.new_page()
        recorrido(page, url)
        ruta = Path(page.video.path())
        contexto.close()  # cierra y escribe el video
        navegador.close()
    return ruta


def ffmpeg(*args: str) -> str:
    resultado = subprocess.run(
        [FFMPEG, "-y", "-hide_banner", *args], capture_output=True, text=True, check=False
    )
    if resultado.returncode != 0:
        raise RuntimeError(resultado.stderr[-1500:])
    return resultado.stderr


def duracion(ruta: Path) -> float:
    salida = subprocess.run(
        [FFMPEG, "-hide_banner", "-i", str(ruta)], capture_output=True, text=True, check=False
    )
    h, m, s = re.search(r"Duration: (\d+):(\d+):([\d.]+)", salida.stderr).groups()
    return int(h) * 3600 + int(m) * 60 + float(s)


def convertir(webm: Path) -> None:
    MP4.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg("-i", str(webm), "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
           "-movflags", "+faststart", "-an", str(MP4))  # fmt: skip
    # GIF: se prueba con menos colores hasta que pese menos de 8 MB
    for colores in (256, 128, 64, 32):
        filtro = (
            f"fps=10,scale=800:-1:flags=lanczos,split[a][b];"
            f"[a]palettegen=max_colors={colores}:stats_mode=diff[p];"
            f"[b][p]paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle"
        )
        ffmpeg("-i", str(MP4), "-vf", filtro, "-loop", "0", str(GIF))
        peso = GIF.stat().st_size / 1_048_576
        print(f"GIF con {colores} colores: {peso:.1f} MB")
        if peso <= MAX_GIF_MB:
            return
    raise RuntimeError(f"El GIF pesa más de {MAX_GIF_MB} MB incluso con 32 colores")


def main() -> None:
    with servidor() as url, tempfile.TemporaryDirectory() as tmp:
        webm = grabar(url, Path(tmp))
        convertir(webm)
    segundos = duracion(MP4)
    print(f"MP4: {MP4.stat().st_size / 1_048_576:.1f} MB, {segundos:.1f} s")
    if not 45 <= segundos <= 60:
        raise SystemExit(f"El video dura {segundos:.1f} s y debe durar entre 45 y 60 s")


if __name__ == "__main__":
    main()
