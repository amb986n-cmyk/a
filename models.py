"""
Modelo de datos: Producto.

Cada producto tiene un ID interno único y estable (8 caracteres
hexadecimales) que nunca cambia aunque cambien su nombre, precio, stock o
categoría. El nombre es solo una etiqueta para mostrar y buscar — nunca se
usa como identificador real. Esto es lo que permite detectar y fusionar
duplicados de forma segura.

Nota para quien lea esto por primera vez: usamos un @dataclass porque nos
ahorra escribir "a mano" el __init__, y from_dict()/to_dict() se encargan de
convertir un Producto en un diccionario "plano" (y viceversa) para poder
guardarlo en JSON.
"""
from dataclasses import dataclass, field, asdict
import uuid


def nuevo_id() -> str:
    """Genera un identificador corto y prácticamente único (8 caracteres)."""
    return uuid.uuid4().hex[:8]


@dataclass
class Producto:
    nombre: str
    id: str = field(default_factory=nuevo_id)
    cantidad: int = 0
    precio: float = 0.0
    stock_minimo: int = 5
    categoria: str = ""
    ubicacion: str = "Sin asignar"
    notas: str = ""

    @property
    def valor_total(self) -> float:
        return round(self.cantidad * self.precio, 2)

    @property
    def estado(self) -> str:
        """Semáforo de stock: 🟢 normal, 🟡 bajo, 🔴 sin stock."""
        if self.cantidad <= 0:
            return "🔴 Sin stock"
        if self.cantidad <= self.stock_minimo:
            return "🟡 Bajo"
        return "🟢 OK"

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "Producto":
        return Producto(
            id=d.get("id") or nuevo_id(),
            nombre=d.get("nombre", ""),
            cantidad=d.get("cantidad", 0),
            precio=d.get("precio", 0.0),
            stock_minimo=d.get("stock_minimo", 5),
            categoria=d.get("categoria", ""),
            ubicacion=d.get("ubicacion", "Sin asignar"),
            notas=d.get("notas", ""),
        )
