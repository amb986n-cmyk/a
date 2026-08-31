import json
from pathlib import Path

import pytest

from core import paths
from core.repositorio import RepositorioProductos


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """Redirige TODA la persistencia a una carpeta temporal, para que los
    tests nunca toquen los datos reales del usuario."""
    monkeypatch.setattr(paths, "ARCHIVO_DATOS", tmp_path / "inventario.json")
    monkeypatch.setattr(paths, "ARCHIVO_LOG", tmp_path / "historial.log")
    monkeypatch.setattr(paths, "BACKUPS_DIR", tmp_path / "backups")
    (tmp_path / "backups").mkdir()
    return RepositorioProductos()


# ---------------- CRUD básico ----------------

def test_añadir_producto_nuevo(repo):
    p = repo.añadir("Teclado", 10, 49.99)
    assert len(repo.productos) == 1
    assert p.cantidad == 10
    assert p.id  # se le asigna un ID


def test_ids_son_estables_tras_modificar(repo):
    p = repo.añadir("Ratón", 5, 19.99)
    id_original = p.id
    repo.modificar_nombre(id_original, "Ratón inalámbrico")
    repo.modificar_precio(id_original, 24.99)
    repo.modificar_cantidad(id_original, 3)
    encontrado = repo.obtener_por_id(id_original)
    assert encontrado is not None
    assert encontrado.nombre == "Ratón inalámbrico"
    assert encontrado.precio == 24.99


def test_eliminar_producto(repo):
    p = repo.añadir("Silla", 3, 89.0)
    assert repo.eliminar(p.id) is True
    assert repo.esta_vacio()


def test_eliminar_id_inexistente_devuelve_false(repo):
    assert repo.eliminar("noexiste") is False


# ---------------- Duplicados y fusión (FASE C/D) ----------------

def test_detectar_duplicado_por_nombre_normalizado(repo):
    repo.añadir("Monitor", 2, 199.0)
    duplicado = repo.detectar_posible_duplicado("  monitor ")
    assert duplicado is not None
    assert duplicado.nombre == "Monitor"


def test_detectar_duplicado_excluye_el_mismo_producto(repo):
    p = repo.añadir("Cable HDMI", 4, 5.0)
    assert repo.detectar_posible_duplicado("Cable HDMI", excluir_id=p.id) is None


def test_fusionar_suma_stock_y_elimina_secundario(repo):
    principal = repo.añadir("Ratón", 10, 20.0)
    secundario = repo.añadir("Ratón (duplicado)", 5, 25.0)
    ok = repo.fusionar(principal.id, secundario.id, precio_final=22.0)
    assert ok
    assert repo.obtener_por_id(secundario.id) is None
    fusionado = repo.obtener_por_id(principal.id)
    assert fusionado.cantidad == 15
    assert fusionado.precio == 22.0


def test_fusion_combina_categoria_sin_perder_datos(repo):
    principal = repo.añadir("Teclado", 10, 40.0, categoria="Periféricos")
    secundario = repo.añadir("Teclado RGB", 5, 60.0, categoria="Gaming")
    repo.fusionar(principal.id, secundario.id)
    fusionado = repo.obtener_por_id(principal.id)
    assert "Periféricos" in fusionado.categoria
    assert "Gaming" in fusionado.categoria


def test_fusion_se_puede_deshacer(repo):
    principal = repo.añadir("Teclado", 10, 40.0)
    secundario = repo.añadir("Teclado RGB", 5, 60.0)
    repo.fusionar(principal.id, secundario.id)
    assert repo.deshacer() != ""
    nombres = sorted(p.nombre for p in repo.productos)
    assert nombres == ["Teclado", "Teclado RGB"]


# ---------------- Undo genérico ----------------

def test_eliminar_y_deshacer(repo):
    p = repo.añadir("Silla", 3, 89.0)
    repo.eliminar(p.id)
    assert repo.esta_vacio()
    assert repo.deshacer() != ""
    assert not repo.esta_vacio()


def test_deshacer_sin_historial_no_falla(repo):
    assert repo.puede_deshacer() is False
    assert repo.deshacer() == ""


def test_limite_de_15_pasos_de_undo(repo):
    for i in range(20):
        repo.añadir(f"Producto {i}", 1, 1.0)
    assert len(repo._pila_undo) == 15  # se recorta al máximo definido


# ---------------- Stock y estadísticas ----------------

def test_stock_bajo_y_sin_stock(repo):
    repo.añadir("A", 0, 10.0, stock_minimo=5)
    repo.añadir("B", 3, 10.0, stock_minimo=5)
    repo.añadir("C", 20, 10.0, stock_minimo=5)
    assert len(repo.productos_sin_stock()) == 1
    assert len(repo.productos_bajo_stock()) == 2


def test_estadisticas_basicas(repo):
    repo.añadir("A", 10, 2.0)
    repo.añadir("B", 5, 4.0)
    stats = repo.estadisticas()
    assert stats["total_productos"] == 2
    assert stats["total_unidades"] == 15
    assert stats["valor_total"] == 40.0


def test_estadisticas_de_inventario_vacio(repo):
    assert repo.estadisticas() == {}


# ---------------- Persistencia y guardado seguro ----------------

def test_guardar_y_recargar(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "ARCHIVO_DATOS", tmp_path / "inventario.json")
    monkeypatch.setattr(paths, "ARCHIVO_LOG", tmp_path / "historial.log")
    monkeypatch.setattr(paths, "BACKUPS_DIR", tmp_path / "backups")
    (tmp_path / "backups").mkdir()

    repo1 = RepositorioProductos()
    repo1.añadir("Persistente", 7, 3.5)

    repo2 = RepositorioProductos()  # simula reabrir el programa
    assert len(repo2.productos) == 1
    assert repo2.productos[0].nombre == "Persistente"


def test_datos_corruptos_no_rompen_la_carga(tmp_path, monkeypatch):
    archivo = tmp_path / "inventario.json"
    archivo.write_text("esto no es json valido {{{", encoding="utf-8")
    monkeypatch.setattr(paths, "ARCHIVO_DATOS", archivo)
    monkeypatch.setattr(paths, "ARCHIVO_LOG", tmp_path / "historial.log")
    monkeypatch.setattr(paths, "BACKUPS_DIR", tmp_path / "backups")
    (tmp_path / "backups").mkdir()

    repo = RepositorioProductos()
    assert repo.esta_vacio()  # no revienta: simplemente empieza vacío


def test_migracion_asigna_id_y_crea_backup(tmp_path, monkeypatch):
    archivo = tmp_path / "inventario.json"
    datos_antiguos = [{"nombre": "Viejo", "cantidad": 1, "precio": 1.0}]  # formato sin ID
    archivo.write_text(json.dumps(datos_antiguos), encoding="utf-8")
    monkeypatch.setattr(paths, "ARCHIVO_DATOS", archivo)
    monkeypatch.setattr(paths, "ARCHIVO_LOG", tmp_path / "historial.log")
    monkeypatch.setattr(paths, "BACKUPS_DIR", tmp_path / "backups")
    (tmp_path / "backups").mkdir()

    repo = RepositorioProductos()
    assert repo.productos[0].id
    backups = list((tmp_path / "backups").glob("*.json"))
    assert len(backups) == 1


# ---------------- CSV ----------------

def test_exportar_e_importar_csv_actualiza_por_id(repo, tmp_path):
    p = repo.añadir("Exportable", 10, 5.0)
    ruta_csv = repo.exportar_csv(str(tmp_path / "salida.csv"))
    assert Path(ruta_csv).exists()

    resultado = repo.importar_csv(ruta_csv)
    assert len(repo.productos) == 1  # no se duplicó
    assert "actualizados: 1" in resultado


def test_importar_csv_no_fusiona_duplicados_en_silencio(repo, tmp_path):
    repo.añadir("Ya existe", 5, 10.0)
    csv_ruta = tmp_path / "nuevo.csv"
    csv_ruta.write_text("Nombre;Cantidad;Precio\nYa existe;3;12.0\n", encoding="utf-8")

    resultado = repo.importar_csv(str(csv_ruta))
    assert len(repo.productos) == 1  # sigue habiendo solo uno
    assert "posibles duplicados omitidos: 1" in resultado
