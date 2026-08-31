"""
Repositorio de productos: aquí vive TODA la lógica de negocio del
inventario (altas, bajas, modificaciones, fusiones, deshacer, CSV...).

Tanto la GUI (gui.py) como la CLI (cli/ui.py + main.py) usan esta misma
clase, así que si algo se corrige u optimiza aquí, se corrige para las dos
interfaces a la vez. Ninguna de las dos toca archivos directamente: siempre
pasan por aquí, y este módulo delega el guardado real en core/persistencia.py.
"""
import csv
import datetime
import os
from typing import List, Optional

from . import paths
from . import persistencia
from .models import Producto

MAX_PASOS_UNDO = 15  # cuántas acciones recordamos para poder deshacer


class RepositorioProductos:
    def __init__(self):
        self.productos: List[Producto] = []
        self._pila_undo = []   # guarda snapshots para poder deshacer
        self._pila_redo = []
        self.cargar()

    # ------------------------------------------------------------------
    # Carga / guardado
    # ------------------------------------------------------------------

    def cargar(self):
        datos = persistencia.cargar_json()
        productos = [Producto.from_dict(d) for d in datos]

        # Compatibilidad con formatos antiguos: si algún producto no traía
        # ID (versiones muy viejas del programa), se le asigna uno nuevo y
        # se vuelve a guardar ya migrado.
        habia_productos_sin_id = any(not d.get("id") for d in datos)
        self.productos = productos
        if habia_productos_sin_id and self.productos:
            self.guardar()

    def guardar(self):
        try:
            datos = [p.to_dict() for p in self.productos]
            persistencia.guardar_json_seguro(datos)
        except OSError as e:
            print(f"Error al guardar en disco: {e}")

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------

    def esta_vacio(self) -> bool:
        return len(self.productos) == 0

    def obtener_por_id(self, producto_id) -> Optional[Producto]:
        for p in self.productos:
            if str(p.id) == str(producto_id):
                return p
        return None

    def buscar(self, texto: str) -> List[Producto]:
        texto = (texto or "").lower().strip()
        if not texto:
            return []
        return [
            p for p in self.productos
            if texto in p.nombre.lower()
            or texto in str(p.id).lower()
            or texto in (p.categoria or "").lower()
            or texto in (p.ubicacion or "").lower()
        ]

    def valor_total(self) -> float:
        return round(sum(p.valor_total for p in self.productos), 2)

    def productos_bajo_stock(self) -> List[Producto]:
        return [p for p in self.productos if p.cantidad <= p.stock_minimo]

    def productos_sin_stock(self) -> List[Producto]:
        return [p for p in self.productos if p.cantidad <= 0]

    def detectar_posible_duplicado(self, nombre: str, excluir_id=None) -> Optional[Producto]:
        """Busca un producto con el mismo nombre (ignorando mayúsculas y
        espacios). `excluir_id` sirve para no compararse a sí mismo cuando
        se está renombrando un producto ya existente."""
        nombre_norm = (nombre or "").lower().strip()
        for p in self.productos:
            if excluir_id is not None and str(p.id) == str(excluir_id):
                continue
            if p.nombre.lower().strip() == nombre_norm:
                return p
        return None

    def estadisticas(self) -> dict:
        """Devuelve un diccionario con métricas generales, o {} si no hay
        productos (un diccionario vacío también se evalúa como "falso" en
        Python, así que `if not stats:` sigue funcionando igual)."""
        if self.esta_vacio():
            return {}

        total_prods = len(self.productos)
        total_unds = sum(p.cantidad for p in self.productos)
        val_tot = self.valor_total()
        precio_med = round(sum(p.precio for p in self.productos) / total_prods, 2)
        bajo_stk = len(self.productos_bajo_stock())
        sin_stk = len(self.productos_sin_stock())
        mas_val = max(self.productos, key=lambda p: p.valor_total)

        return {
            "total_productos": total_prods,
            "total_unidades": total_unds,
            "valor_total": val_tot,
            "precio_medio": precio_med,
            "bajo_stock": bajo_stk,
            "sin_stock": sin_stk,
            "producto_mas_valioso": mas_val,
        }

    # ------------------------------------------------------------------
    # Deshacer / rehacer
    # ------------------------------------------------------------------

    def _registrar_undo(self, accion: str, datos: dict):
        self._pila_undo.append((accion, datos))
        if len(self._pila_undo) > MAX_PASOS_UNDO:
            self._pila_undo.pop(0)  # olvidamos la acción más antigua
        self._pila_redo.clear()

    def puede_deshacer(self) -> bool:
        return len(self._pila_undo) > 0

    def deshacer(self) -> str:
        """Deshace la última acción y devuelve su nombre (p. ej. "añadir").
        Si no hay nada que deshacer, devuelve "" (cadena vacía, no None)."""
        if not self.puede_deshacer():
            return ""

        accion, datos = self._pila_undo.pop()
        self._pila_redo.append((accion, datos))

        if accion == "añadir":
            self.productos = [p for p in self.productos if p.id != datos["nuevo"]["id"]]
        elif accion == "eliminar":
            self.productos.append(Producto.from_dict(datos["eliminado"]))
        elif accion == "fusionar":
            # Se restauran ambos productos tal y como estaban antes de fusionar
            self.productos = [p for p in self.productos if p.id != datos["principal_id"]]
            self.productos.append(Producto.from_dict(datos["principal_antes"]))
            self.productos.append(Producto.from_dict(datos["secundario_antes"]))
        elif accion == "modificar":
            p = self.obtener_por_id(datos["id"])
            if p:
                for campo, valor_antes in datos["antes"].items():
                    setattr(p, campo, valor_antes)

        self.guardar()
        self.registrar_historial(f"Deshecho: {accion}")
        return accion

    # ------------------------------------------------------------------
    # Altas / bajas / modificaciones
    # ------------------------------------------------------------------

    def añadir(self, nombre, cantidad, precio, stock_minimo=0, categoria="", ubicacion="Sin asignar") -> Producto:
        nuevo_prod = Producto(
            nombre=nombre,
            cantidad=int(cantidad),
            precio=float(precio),
            stock_minimo=int(stock_minimo),
            categoria=categoria or "",
            ubicacion=ubicacion or "Sin asignar",
        )
        self.productos.append(nuevo_prod)
        self._registrar_undo("añadir", {"nuevo": nuevo_prod.to_dict()})
        self.guardar()
        self.registrar_historial(f"Añadido producto: {nuevo_prod.nombre}")
        return nuevo_prod

    def eliminar(self, producto_id) -> bool:
        """Devuelve True si se eliminó, False si no se encontró el producto."""
        prod = self.obtener_por_id(producto_id)
        if not prod:
            return False

        self._registrar_undo("eliminar", {"eliminado": prod.to_dict()})
        self.productos = [p for p in self.productos if p.id != prod.id]
        self.guardar()
        self.registrar_historial(f"Eliminado producto: {prod.nombre} (ID {prod.id})")
        return True

    def _modificar_campo(self, producto_id, campo: str, valor_nuevo, etiqueta: str = None) -> bool:
        """Punto único por el que pasan todas las modificaciones de un
        campo. Así el "deshacer" funciona igual para cantidad, precio,
        nombre, categoría, ubicación o stock mínimo, sin repetir código."""
        p = self.obtener_por_id(producto_id)
        if not p:
            return False

        valor_antes = getattr(p, campo)
        if valor_antes == valor_nuevo:
            return True  # nada que hacer, pero no es un error

        self._registrar_undo("modificar", {"id": p.id, "antes": {campo: valor_antes}})
        setattr(p, campo, valor_nuevo)
        self.guardar()
        self.registrar_historial(f"{etiqueta or campo.capitalize()} de '{p.nombre}' actualizado")
        return True

    def modificar_nombre(self, producto_id, nuevo_nombre):
        return self._modificar_campo(producto_id, "nombre", nuevo_nombre, "Nombre")

    def modificar_cantidad(self, producto_id, nueva_cantidad):
        return self._modificar_campo(producto_id, "cantidad", int(nueva_cantidad), "Cantidad")

    def modificar_precio(self, producto_id, nuevo_precio):
        return self._modificar_campo(producto_id, "precio", float(nuevo_precio), "Precio")

    def modificar_categoria(self, producto_id, nueva_categoria):
        return self._modificar_campo(producto_id, "categoria", nueva_categoria or "", "Categoría")

    def modificar_ubicacion(self, producto_id, nueva_ubicacion):
        return self._modificar_campo(producto_id, "ubicacion", nueva_ubicacion or "Sin asignar", "Ubicación")

    def modificar_stock_minimo(self, producto_id, nuevo_stock_minimo):
        return self._modificar_campo(producto_id, "stock_minimo", int(nuevo_stock_minimo), "Stock mínimo")

    def fusionar(self, principal_id, secundario_id, precio_final: float = None) -> bool:
        """Une dos productos duplicados en uno solo: suma el stock, combina
        las categorías y (opcionalmente) fija un precio final acordado. El
        producto "secundario" desaparece; el "principal" se queda con todo."""
        principal = self.obtener_por_id(principal_id)
        secundario = self.obtener_por_id(secundario_id)
        if not principal or not secundario or principal.id == secundario.id:
            return False

        datos_undo = {
            "principal_id": principal.id,
            "principal_antes": principal.to_dict(),
            "secundario_antes": secundario.to_dict(),
        }

        principal.cantidad += secundario.cantidad
        if precio_final is not None:
            principal.precio = float(precio_final)

        # Combinamos las categorías de ambos sin duplicar ni perder ninguna
        combinadas = []
        for c in (principal.categoria, secundario.categoria):
            if c and c not in combinadas:
                combinadas.append(c)
        principal.categoria = " / ".join(combinadas)

        self.productos = [p for p in self.productos if p.id != secundario.id]
        self._registrar_undo("fusionar", datos_undo)
        self.guardar()
        self.registrar_historial(f"Fusionado '{secundario.nombre}' dentro de '{principal.nombre}'")
        return True

    # ------------------------------------------------------------------
    # Historial (se guarda en disco para que sobreviva a cerrar el programa)
    # ------------------------------------------------------------------

    def registrar_historial(self, mensaje: str):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        linea = f"[{timestamp}] {mensaje}\n"
        try:
            paths.ARCHIVO_LOG.parent.mkdir(parents=True, exist_ok=True)
            with open(paths.ARCHIVO_LOG, "a", encoding="utf-8") as f:
                f.write(linea)
        except OSError:
            pass

    def leer_historial(self, limite=50) -> List[str]:
        if not paths.ARCHIVO_LOG.exists():
            return []
        try:
            with open(paths.ARCHIVO_LOG, "r", encoding="utf-8") as f:
                lineas = f.readlines()
            return lineas[-limite:]
        except OSError:
            return []

    # ------------------------------------------------------------------
    # Importar / exportar CSV
    # ------------------------------------------------------------------

    def exportar_csv(self, ruta: str = None) -> str:
        ruta = ruta or str(paths.ARCHIVO_CSV_DEFECTO)
        with open(ruta, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow(["ID", "Nombre", "Cantidad", "Precio", "Stock Minimo", "Categoria", "Ubicacion"])
            for p in self.productos:
                writer.writerow([p.id, p.nombre, p.cantidad, p.precio, p.stock_minimo, p.categoria, p.ubicacion])
        return ruta

    def importar_csv(self, ruta: str) -> str:
        """Importa productos desde un CSV. Si una fila trae un ID que ya
        existe, ACTUALIZA ese producto. Si no trae ID pero el nombre ya
        existe, se OMITE (para no fusionar nada a ciegas: eso lo decide el
        usuario a mano). En cualquier otro caso, se añade como nuevo."""
        if not os.path.exists(ruta):
            return f"No se encontró el archivo: {ruta}"

        añadidos = 0
        actualizados = 0
        omitidos = 0

        with open(ruta, mode="r", encoding="utf-8") as f:
            muestra = f.read(2048)
            f.seek(0)
            try:
                delimitador = csv.Sniffer().sniff(muestra, delimiters=";,").delimiter
            except csv.Error:
                delimitador = ";"

            reader = csv.DictReader(f, delimiter=delimitador)
            for fila in reader:
                nombre = (fila.get("Nombre") or "").strip()
                if not nombre:
                    continue

                try:
                    cantidad = int(fila.get("Cantidad", 0) or 0)
                    precio = float(fila.get("Precio", 0) or 0)
                    stock_min = int(fila.get("Stock Minimo", 0) or 0)
                except ValueError:
                    omitidos += 1
                    continue

                categoria = fila.get("Categoria", "") or ""
                ubicacion = fila.get("Ubicacion", "Sin asignar") or "Sin asignar"
                id_fila = (fila.get("ID") or "").strip()

                existente = self.obtener_por_id(id_fila) if id_fila else None
                if existente:
                    existente.nombre = nombre
                    existente.cantidad = cantidad
                    existente.precio = precio
                    existente.stock_minimo = stock_min
                    existente.categoria = categoria
                    existente.ubicacion = ubicacion
                    actualizados += 1
                    continue

                if self.detectar_posible_duplicado(nombre):
                    omitidos += 1
                    continue

                self.productos.append(Producto(
                    nombre=nombre, cantidad=cantidad, precio=precio,
                    stock_minimo=stock_min, categoria=categoria, ubicacion=ubicacion,
                ))
                añadidos += 1

        self.guardar()
        self.registrar_historial(
            f"Importación CSV: añadidos {añadidos}, actualizados {actualizados}, omitidos {omitidos}"
        )
        return (
            f"Importación completada — añadidos: {añadidos}, "
            f"actualizados: {actualizados}, posibles duplicados omitidos: {omitidos}"
        )
