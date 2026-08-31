from core.validaciones import validar_nombre, validar_entero, validar_decimal


def test_validar_nombre_quita_espacios():
    ok, valor, _ = validar_nombre("   Teclado   Mecánico   ")
    assert ok
    assert valor == "Teclado Mecánico"


def test_validar_nombre_vacio():
    ok, _, msg = validar_nombre("   ")
    assert not ok
    assert "vacío" in msg


def test_validar_entero_valido():
    ok, valor, _ = validar_entero("25", minimo=0)
    assert ok and valor == 25


def test_validar_entero_invalido():
    ok, _, msg = validar_entero("abc")
    assert not ok
    assert "entero" in msg


def test_validar_entero_bajo_minimo():
    ok, _, msg = validar_entero("-3", minimo=0)
    assert not ok
    assert "menor que" in msg


def test_validar_decimal_con_coma():
    ok, valor, _ = validar_decimal("49,99")
    assert ok
    assert valor == 49.99


def test_validar_decimal_invalido():
    ok, _, msg = validar_decimal("gratis")
    assert not ok
    assert "válido" in msg
