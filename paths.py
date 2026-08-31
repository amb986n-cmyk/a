"""
Rutas de la aplicación.

Diseño pensado para dos cosas a la vez:
1. Multiplataforma: usamos pathlib en vez de rutas con '/' o '\\' escritas a mano.
2. Modo portable: los datos viven en una carpeta 'data/' junto al programa
   (o junto al .exe si está empaquetado con PyInstaller), no en el
   directorio desde el que se lanza el comando. Así la carpeta entera se
   puede copiar a otro ordenador sin perder nada.
"""
import sys
from pathlib import Path


def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        # Empaquetado con PyInstaller: los datos deben vivir junto al ejecutable.
        return Path(sys.executable).resolve().parent
    # Ejecución normal con "python main.py": subimos desde core/ a la raíz del proyecto.
    return Path(__file__).resolve().parent.parent


BASE_DIR = _base_dir()
DATA_DIR = BASE_DIR / "data"
BACKUPS_DIR = BASE_DIR / "backups"

DATA_DIR.mkdir(parents=True, exist_ok=True)
BACKUPS_DIR.mkdir(parents=True, exist_ok=True)

ARCHIVO_DATOS = DATA_DIR / "inventario.json"
ARCHIVO_LOG = DATA_DIR / "historial.log"
ARCHIVO_CSV_DEFECTO = DATA_DIR / "inventario.csv"
