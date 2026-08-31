# 📦 Inventory Pro Terminal

CLI profesional de gestión de inventario. Rápida, con teclado como método
principal de control, e integridad de datos (IDs estables, guardado
atómico, backups, undo).

> Esta es la **Fase 1** (terminal). La Fase 2 (Inventory Pro Desktop, GUI)
> reutilizará el paquete `core/` sin cambios — ver "Arquitectura".

---

## Instalación

Requiere Python 3.9+.

```bash
pip install -r requirements.txt
```

## Ejecución

```bash
python main.py
```

## Requisitos y solución de problemas

- **Emojis/Unicode no se ven bien**: usa una terminal moderna (Windows
  Terminal, iTerm2, GNOME Terminal, Alacritty...). La app sigue
  funcionando igual sin ellos, solo cambia la estética.
- **Un atajo Ctrl+ no responde**: algunos emuladores de terminal o
  sistemas capturan esa combinación antes de que llegue al programa.
  Escribe el número de la opción y pulsa Enter — siempre funciona.
- **"No se pudo escribir el archivo"**: revisa que la carpeta `data/` no
  esté marcada como solo lectura y que haya espacio en disco.

---

## ⌨️ Atajos de teclado

Disponibles en el **menú principal** (por diseño no interfieren con la
escritura normal dentro de un campo de texto):

| Atajo | Acción |
|---|---|
| `Ctrl+N` | Nuevo producto |
| `Ctrl+E` | Editar producto (elige de la lista) |
| `Delete` | Eliminar producto (elige de la lista) |
| `Ctrl+Z` | Deshacer última acción |
| `Ctrl+F` | Buscar |
| `Ctrl+S` | Guardar ahora (ya es automático) |
| `F5` | Actualizar / recalcular estadísticas |
| `Esc` | Salir (con confirmación) |
| `Número + Enter` | Ir directo a esa opción |
| `↑ ↓ + Enter` | Navegar listas y submenús |

También disponible en la app: opción **12. Ver atajos de teclado**.

---

## 🔀 Sistema de duplicados y fusión

Cada producto tiene un **ID único interno** (no visible normalmente, pero
sí en las tablas) que nunca cambia, aunque cambie el nombre. Esto es lo
que soluciona el bug del programa original: antes, renombrar un producto
al nombre de otro ya existente creaba dos productos idénticos sin avisar.

Ahora, al **añadir** un producto o **renombrar** uno existente, si el
nombre coincide con otro ya existente, se muestra:

```
⚠ PRODUCTO DUPLICADO
Ya existe un producto llamado: Ratón
...
❯ 🔀 Fusionar
  📦 Mantener separados
  ❌ Cancelar
```

- **Fusionar**: suma el stock, te deja elegir qué precio conservar si
  difieren, combina categorías y notas sin perder información, y elimina
  el producto duplicado. Se puede deshacer con Ctrl+Z.
- **Mantener separados**: continúa la operación aunque queden dos
  productos con nombres parecidos (identidad real ya no depende del
  nombre, así que no rompe nada; es una decisión consciente del usuario).
- **Cancelar**: no hace ningún cambio.

La importación de CSV usa la misma filosofía: **nunca fusiona en
silencio**. Si detecta un posible duplicado por nombre, omite esa fila y
lo indica en el resumen; si el CSV trae el mismo ID que un producto
existente, actualiza sus datos.

---

## ↩️ Undo (deshacer)

Guarda hasta **15 pasos** de historial en memoria. Cubre creación,
edición, eliminación y **fusión** de productos. Cada deshacer restaura el
inventario exacto de antes de la acción y queda registrado en el
historial.

## 📜 Historial (`data/historial.log`)

Registro de texto plano con fecha y hora de cada operación relevante
(altas, bajas, cambios, fusiones, deshacer, importaciones/exportaciones).
Consultable desde la opción 11 del menú.

## 💾 Guardado seguro

Cada cambio se guarda **automáticamente y de forma atómica**: se escribe
primero en un archivo temporal y solo al final se sustituye
`inventario.json` (operación atómica en Windows/Linux/macOS). Si el
programa se cierra a mitad de una escritura, el archivo previo nunca
queda corrupto.

## 🛡️ Backups (`backups/`)

Se crea una copia de seguridad automática antes de operaciones
potencialmente delicadas (migración de datos antiguos, fusión de
productos, importación de CSV). Se conservan como máximo **10** copias;
las más antiguas se eliminan automáticamente.

## 📄 Exportar/Importar CSV

- Exporta con `;` como separador y codificación `utf-8-sig` (para que
  Excel en Windows muestre bien tildes y "ñ"). Incluye columna de ID.
- Importa actualizando por ID si coincide, creando si es nuevo, y
  omitiendo (sin fusionar solo) si detecta un posible duplicado por
  nombre.

---

## 🧩 Arquitectura

```
core/                  ← lógica de negocio, SIN dependencias de interfaz
  paths.py             ← rutas multiplataforma / modo portable
  models.py            ← Producto (con ID único estable)
  validaciones.py       ← reglas de validación reutilizables
  repositorio.py        ← CRUD, duplicados, fusión, undo, backups, CSV, stats

cli/                   ← todo lo que depende de questionary/rich/prompt_toolkit
  ui.py                ← menús, tablas, entrada de datos, atajos
  atajos.py             ← catálogo centralizado de atajos

main.py                ← conecta cli/ con core/

tests/                 ← pytest sobre core/ (no depende de terminal real)

data/                  ← inventario.json, historial.log (se crea solo)
backups/               ← copias de seguridad automáticas (se crea solo)
```

`core/` no importa nada de `cli/`. La futura GUI (Inventory Pro Desktop)
podrá importar `core.repositorio.RepositorioProductos` directamente y
tener toda la lógica —incluyendo duplicados, fusión y undo— sin
reescribir nada.

---

## 🧪 Tests

```bash
pip install -r requirements-dev.txt
pytest
```

27 tests cubren: CRUD, detección de duplicados, fusión (incluido su
undo), guardado/carga, datos corruptos, migración de formato antiguo,
backups, stock bajo/sin stock, estadísticas, exportación/importación CSV
sin duplicar. No incluyen pruebas de la capa de terminal en sí (requiere
una TTY real); esa parte se verificó manualmente de extremo a extremo.

---

## 📦 Empaquetado (para distribuir sin que el usuario necesite Python)

Se recomienda **PyInstaller**, ejecutado *en cada sistema operativo de
destino* (no se puede generar el `.exe` de Windows desde Linux, por
ejemplo):

```bash
pip install pyinstaller
pyinstaller --onefile --name InventoryPro main.py
```

- **Windows**: ejecutar el comando anterior en Windows → genera
  `dist/InventoryPro.exe`.
- **Linux**: ejecutar en Linux → genera `dist/InventoryPro` (binario ELF).
- **macOS**: ejecutar en macOS → genera `dist/InventoryPro` (Mach-O).
  Puede requerir firmar/notarizar el binario si se va a distribuir
  fuera de tu propio Mac (Gatekeeper).

### Modo portable

Como los datos se guardan junto al ejecutable (ver `core/paths.py`),
basta con copiar `InventoryPro.exe` (o `InventoryPro`) junto a las
carpetas `data/` y `backups/` a otro ordenador para llevarte todo el
inventario:

```
InventoryPro/
├── InventoryPro.exe
├── data/
└── backups/
```

---

## Estado actual y próximos pasos

**Hecho en esta fase:** arquitectura core/cli separada, IDs estables,
detección y fusión de duplicados con undo, guardado atómico, backups
rotativos, atajos en el menú principal, tabla adaptativa al ancho de
terminal, estadísticas con caché, tests automatizados del núcleo.

**Pendiente / conocido, para una siguiente iteración:**
- Los atajos Ctrl+ solo están activos en el menú principal (a propósito,
  para no interferir con la escritura), no dentro de los submenús de
  edición. Si quieres atajos también ahí, es una ampliación razonable.
- No se ha generado ningún ejecutable real: solo se dan las instrucciones,
  porque compilar para Windows/macOS requiere ejecutarlo en esos sistemas.
- Los tests cubren `core/` a fondo; la capa de terminal (`cli/`) se probó
  manualmente pero no tiene suite automatizada (requeriría emular una TTY).

**Fase 2 (futura, no iniciada):** Inventory Pro Desktop, una GUI que
importará `core.repositorio.RepositorioProductos` tal cual.
