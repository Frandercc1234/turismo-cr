"""La app tal como corre en producción: base copiada a la carpeta temporal y varias sesiones a la vez."""

import shutil
import tempfile
import threading
from pathlib import Path

import duckdb
import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from src.cargar import ESQUEMA

RAIZ = Path(__file__).parent.parent
APP = RAIZ / "app.py"
DB = RAIZ / "data" / "processed" / "turismo.duckdb"

pytestmark = pytest.mark.skipif(not DB.exists(), reason="Falta data/processed/turismo.duckdb")

SUBTITULOS = 3


def correr(app: Path) -> AppTest:
    return AppTest.from_file(str(app), default_timeout=60).run()


def app_con_base(tmp_path: Path, origen: Path | None = None, contenido: bytes | None = None) -> Path:
    """Copia app.py a una carpeta propia con su propia base, para probar bases rotas sin tocar la real."""
    (tmp_path / "data" / "processed").mkdir(parents=True)
    destino = tmp_path / "data" / "processed" / "turismo.duckdb"
    if origen is not None:
        shutil.copy(origen, destino)
    elif contenido is not None:
        destino.write_bytes(contenido)
    shutil.copy(APP, tmp_path / "app.py")
    return tmp_path / "app.py"


def copia_temporal(app: Path) -> Path:
    """Ruta donde la app deja su copia de la base (nombre con la fecha del archivo)."""
    base = app.parent / "data" / "processed" / "turismo.duckdb"
    return Path(tempfile.gettempdir()) / f"turismo-{base.stat().st_mtime}.duckdb"


def test_corre_con_la_base_copiada_como_en_produccion(tmp_path):
    app = app_con_base(tmp_path, origen=DB)
    copia = copia_temporal(app)
    copia.unlink(missing_ok=True)
    st.cache_resource.clear()
    at = correr(app)
    assert not at.exception and not at.error
    assert len(at.subheader) == SUBTITULOS
    assert copia.exists() and copia.stat().st_size == DB.stat().st_size
    assert not list(copia.parent.glob(f"{copia.stem}.*.tmp")), "quedó una copia parcial"


def test_varias_sesiones_a_la_vez_no_pisan_los_resultados():
    """Al despertar la app entran varias sesiones juntas; con una conexión compartida salían
    resultados vacíos (max(fecha) = None) o 'connection is busy'."""
    st.cache_resource.clear()
    at = correr(APP)  # abre y cachea la conexión, como la primera visita
    assert not at.exception
    fallos: list[str] = []

    def sesion():
        resultado = correr(APP)
        if resultado.exception or len(resultado.subheader) != SUBTITULOS:
            fallos.append(
                str(resultado.exception[0].value)[:120] if resultado.exception else "sin subtítulos"
            )

    for _ in range(3):
        hilos = [threading.Thread(target=sesion) for _ in range(8)]
        [h.start() for h in hilos]
        [h.join() for h in hilos]
    assert not fallos, fallos[:3]


def test_base_vacia_muestra_un_error_claro(tmp_path):
    vacia = tmp_path / "vacia.duckdb"
    con = duckdb.connect(str(vacia))
    con.execute(ESQUEMA)
    con.close()
    app = app_con_base(tmp_path / "app_vacia", origen=vacia)
    st.cache_resource.clear()
    at = correr(app)
    assert not at.exception
    assert any("no tiene llegadas cargadas" in e.value for e in at.error)
    assert len(at.subheader) == 0


def test_base_dañada_muestra_un_error_claro(tmp_path):
    app = app_con_base(tmp_path, contenido=b"esto no es una base de datos" * 1000)
    st.cache_resource.clear()
    at = correr(app)
    assert not at.exception
    assert any("No se pudo abrir la base de datos" in e.value for e in at.error)


def test_copia_a_medias_en_la_carpeta_temporal_se_rehace(tmp_path):
    app = app_con_base(tmp_path, origen=DB)
    copia = copia_temporal(app)
    copia.write_bytes(DB.read_bytes()[: DB.stat().st_size // 3])  # lo que deja un proceso cortado
    st.cache_resource.clear()
    at = correr(app)
    assert not at.exception and not at.error
    assert len(at.subheader) == SUBTITULOS
    assert copia.stat().st_size == DB.stat().st_size
