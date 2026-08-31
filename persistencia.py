"""
Módulo de persistencia segura para JSON.
Maneja escrituras atómicas (archivo temporal + reemplazo) y backups rotativos.

Importante para quien lo edite: aquí siempre escribimos `paths.ARCHIVO_DATOS`
(y no `from core.paths import ARCHIVO_DATOS`). La diferencia es sutil pero
clave: así, si algo cambia esa ruta en tiempo de ejecución (por ejemplo los
tests, que redirigen los datos a una carpeta temporal), este módulo se entera
al momento en vez de quedarse con el valor "congelado" del arranque.
"""
import json
import os
import shutil
from datetime import datetime
from typing import List, Dict, Any

from . import paths

MAX_BACKUPS = 10  # Límite de copias para no llenar el disco


def crear_backup() -> str | None:
    """Crea una copia de seguridad timestamped en la carpeta de backups."""
    if not paths.ARCHIVO_DATOS.exists():
        return None

    paths.BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ruta_backup = paths.BACKUPS_DIR / f"inventario_{timestamp}.json"

    shutil.copy2(paths.ARCHIVO_DATOS, ruta_backup)
    _limpiar_backups_antiguos()
    return str(ruta_backup)


def _limpiar_backups_antiguos():
    """Mantiene solo las últimas MAX_BACKUPS copias de seguridad."""
    if not paths.BACKUPS_DIR.exists():
        return

    archivos = [
        f for f in paths.BACKUPS_DIR.glob("inventario_*.json")
    ]
    archivos.sort(key=lambda p: p.stat().st_mtime)  # más antiguos primero

    while len(archivos) > MAX_BACKUPS:
        archivo_viejo = archivos.pop(0)
        try:
            archivo_viejo.unlink()
        except OSError:
            pass


def guardar_json_seguro(datos: List[Dict[str, Any]]) -> None:
    """Guarda los datos en JSON de forma atómica usando un archivo temporal."""
    paths.ARCHIVO_DATOS.parent.mkdir(parents=True, exist_ok=True)
    ruta_temp = paths.ARCHIVO_DATOS.with_suffix(".tmp")

    # 1. Crear backup del estado anterior antes de sobrescribir
    crear_backup()

    # 2. Escribir en el archivo temporal
    with open(ruta_temp, "w", encoding="utf-8") as f:
        json.dump(datos, f, indent=4, ensure_ascii=False)

    # 3. Reemplazar el archivo original (operación atómica del sistema operativo)
    os.replace(ruta_temp, paths.ARCHIVO_DATOS)


def cargar_json() -> List[Dict[str, Any]]:
    """Carga los datos del inventario. Si el archivo está corrupto, intenta
    recuperar el backup más reciente."""
    if not paths.ARCHIVO_DATOS.exists():
        return []

    try:
        with open(paths.ARCHIVO_DATOS, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return _restaurar_ultimo_backup()


def _restaurar_ultimo_backup() -> List[Dict[str, Any]]:
    """Busca el backup más reciente en caso de fallo crítico en el archivo principal."""
    if not paths.BACKUPS_DIR.exists():
        return []

    archivos = list(paths.BACKUPS_DIR.glob("inventario_*.json"))
    if not archivos:
        return []

    ultimo_backup = max(archivos, key=lambda p: p.stat().st_mtime)

    try:
        with open(ultimo_backup, "r", encoding="utf-8") as f:
            datos = json.load(f)
        guardar_json_seguro(datos)  # restauramos también el archivo principal
        return datos
    except (json.JSONDecodeError, OSError):
        return []
