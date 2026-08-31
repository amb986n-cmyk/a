"""
Validación de entradas de usuario.

Vive en 'core' (no en la CLI) a propósito: la futura GUI debe poder
validar exactamente igual, sin duplicar reglas ni arriesgarse a que
diverjan con el tiempo.

Cada función devuelve (ok, valor_limpio, mensaje_de_error).
"""
from typing import Tuple


def validar_nombre(texto: str) -> Tuple[bool, str, str]:
    limpio = " ".join((texto or "").split())  # colapsa espacios/tabs repetidos
    if not limpio:
        return False, "", "El nombre no puede estar vacío."
    if len(limpio) > 80:
        return False, "", "El nombre es demasiado largo (máx. 80 caracteres)."
    return True, limpio, ""


def validar_entero(texto: str, minimo: int = 0, etiqueta: str = "El valor") -> Tuple[bool, int, str]:
    try:
        n = int(str(texto).strip())
    except (TypeError, ValueError):
        return False, 0, f"{etiqueta} debe ser un número entero (sin decimales)."
    if n < minimo:
        return False, 0, f"{etiqueta} no puede ser menor que {minimo}."
    return True, n, ""


def validar_decimal(texto: str, minimo: float = 0.0, etiqueta: str = "El valor") -> Tuple[bool, float, str]:
    try:
        n = float(str(texto).strip().replace(",", "."))
    except (TypeError, ValueError, AttributeError):
        return False, 0.0, f"{etiqueta} debe ser un número válido (ej: 49.99)."
    if n < minimo:
        return False, 0.0, f"{etiqueta} no puede ser menor que {minimo}."
    return True, n, ""
