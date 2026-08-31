import json
import os
import time
import tkinter as tk
import customtkinter as ctk
import unicodedata
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk
from core.repositorio import RepositorioProductos
from core.validaciones import validar_nombre

# Configuración inicial del tema moderno
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

CONFIG_FILE = "config_preferencias.json"
RUTA_LOGO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "logo.png")


# --- Atajo global: Ctrl+A para seleccionar todo -----------------------------
# Se registran como "class bindings" (bind_class), así que funcionan
# automáticamente en CUALQUIER campo de texto, cuadro de texto o tabla de la
# aplicación, se cree donde se cree, sin tener que enlazarlo widget por widget.

def _seleccionar_todo_entry(event):
    try:
        event.widget.select_range(0, "end")
        event.widget.icursor("end")
    except tk.TclError:
        pass
    return "break"


def _seleccionar_todo_texto(event):
    try:
        event.widget.tag_add("sel", "1.0", "end-1c")
        event.widget.mark_set("insert", "end-1c")
    except tk.TclError:
        pass
    return "break"


def _seleccionar_todo_tabla(event):
    try:
        tabla = event.widget
        tabla.selection_set(tabla.get_children(""))
    except tk.TclError:
        pass
    return "break"


def _registrar_atajo_seleccionar_todo(root):
    """Registra Ctrl+A en esta ventana raíz (y en cualquier ventana hija que
    se abra sobre ella, ya que comparten el mismo intérprete de Tcl/Tk) para
    que seleccione todo el texto de un campo de entrada o cuadro de texto,
    o todas las filas de una tabla."""
    root.bind_class("Entry", "<Control-a>", _seleccionar_todo_entry)
    root.bind_class("Entry", "<Control-A>", _seleccionar_todo_entry)
    root.bind_class("Text", "<Control-a>", _seleccionar_todo_texto)
    root.bind_class("Text", "<Control-A>", _seleccionar_todo_texto)
    root.bind_class("Treeview", "<Control-a>", _seleccionar_todo_tabla)
    root.bind_class("Treeview", "<Control-A>", _seleccionar_todo_tabla)


class DialogoAviso(ctk.CTkToplevel):
    def __init__(self, parent, titulo, mensaje, tema, texto_boton="Aceptar", icono="ℹ️"):
        super().__init__(parent)
        self._tema = tema

        self.title(titulo)
        self.geometry("380x100")
        self.resizable(False, False)
        self.configure(fg_color=tema["main"])
        self.attributes("-topmost", True)

        lbl_icono = ctk.CTkLabel(self, text=icono, font=ctk.CTkFont(size=30))
        lbl_icono.pack(pady=(26, 4))

        lbl_msg = ctk.CTkLabel(
            self, text=mensaje, font=ctk.CTkFont(size=13),
            text_color="#f8fafc", wraplength=320, justify="center"
        )
        lbl_msg.pack(pady=(0, 22), padx=24)

        frame_botones = ctk.CTkFrame(self, fg_color="transparent")
        frame_botones.pack(pady=(0, 24))

        self.btn_aceptar = ctk.CTkButton(
            frame_botones, text=texto_boton, width=120, height=34,
            fg_color=tema["activo"], border_width=2, border_color=tema["activo"],
            text_color="#ffffff", hover_color=tema["borde"],
            command=self._cerrar
        )
        self.btn_aceptar.pack()

        self.bind("<Return>", lambda e: self._cerrar())
        self.bind("<KP_Enter>", lambda e: self._cerrar())
        self.bind("<Escape>", lambda e: self._cerrar())
        self.protocol("WM_DELETE_WINDOW", self._cerrar)

        self._ajustar_tamano_y_centrar()
        self.after(20, self._activar_modal)

    def _ajustar_tamano_y_centrar(self):
        self.withdraw()
        self.update_idletasks()
        ancho, alto = 380, self.winfo_reqheight()
        x = (self.winfo_screenwidth() - ancho) // 2
        y = (self.winfo_screenheight() - alto) // 2
        self.geometry(f"{ancho}x{alto}+{max(x, 0)}+{max(y, 0)}")
        self.deiconify()

    def _activar_modal(self):
        self.grab_set()
        self.btn_aceptar.focus_force()

    def _cerrar(self):
        self.grab_release()
        self.destroy()


class DialogoConfirmacion(ctk.CTkToplevel):
    def __init__(self, parent, titulo, mensaje, tema, texto_si="Sí", texto_no="No"):
        super().__init__(parent)
        self.resultado = False
        self._tema = tema

        self.title(titulo)
        self.geometry("380x100")
        self.resizable(False, False)
        self.configure(fg_color=tema["main"])
        self.attributes("-topmost", True)

        lbl_icono = ctk.CTkLabel(self, text="⚠️", font=ctk.CTkFont(size=30))
        lbl_icono.pack(pady=(26, 4))

        lbl_msg = ctk.CTkLabel(
            self, text=mensaje, font=ctk.CTkFont(size=13),
            text_color="#f8fafc", wraplength=320, justify="center"
        )
        lbl_msg.pack(pady=(0, 22), padx=24)

        frame_botones = ctk.CTkFrame(self, fg_color="transparent")
        frame_botones.pack(pady=(0, 24))

        self.btn_no = ctk.CTkButton(
            frame_botones, text=texto_no, width=110, height=34,
            fg_color="transparent", border_width=2, border_color=tema["borde"],
            text_color="#e2e8f0", hover_color=tema["borde"],
            command=self._cancelar
        )
        self.btn_no.pack(side="left", padx=8)

        self.btn_si = ctk.CTkButton(
            frame_botones, text=texto_si, width=110, height=34,
            fg_color=tema["activo"], border_width=2, border_color=tema["activo"],
            text_color="#ffffff", hover_color=tema["borde"],
            command=self._confirmar
        )
        self.btn_si.pack(side="left", padx=8)

        self.botones = [self.btn_no, self.btn_si]
        self.indice_foco = 0
        self._resaltar_foco()

        self.bind("<Left>", lambda e: self._mover_foco(-1))
        self.bind("<Right>", lambda e: self._mover_foco(1))
        self.bind("<Tab>", lambda e: self._mover_foco(1))
        self.bind("<Return>", lambda e: self._activar_actual())
        self.bind("<KP_Enter>", lambda e: self._activar_actual())
        self.bind("<Escape>", lambda e: self._cancelar())
        self.protocol("WM_DELETE_WINDOW", self._cancelar)

        self._ajustar_tamano_y_centrar()
        self.after(20, self._activar_modal)

    def _ajustar_tamano_y_centrar(self):
        self.withdraw()
        self.update_idletasks()
        ancho, alto = 380, self.winfo_reqheight()
        x = (self.winfo_screenwidth() - ancho) // 2
        y = (self.winfo_screenheight() - alto) // 2
        self.geometry(f"{ancho}x{alto}+{max(x, 0)}+{max(y, 0)}")
        self.deiconify()

    def _activar_modal(self):
        self.grab_set()
        self.focus_force()

    def _mover_foco(self, direccion):
        self.indice_foco = (self.indice_foco + direccion) % len(self.botones)
        self._resaltar_foco()

    def _resaltar_foco(self):
        for i, btn in enumerate(self.botones):
            es_si = btn is self.btn_si
            if i == self.indice_foco:
                btn.configure(border_color="#f8fafc")
            else:
                btn.configure(border_color=self._tema["activo"] if es_si else self._tema["borde"])

    def _activar_actual(self):
        (self._confirmar if self.indice_foco == 1 else self._cancelar)()

    def _confirmar(self):
        self.resultado = True
        self.grab_release()
        self.destroy()

    def _cancelar(self):
        self.resultado = False
        self.grab_release()
        self.destroy()


class DialogoEntrada(ctk.CTkToplevel):
    def __init__(self, parent, titulo, mensaje, tema, valor_inicial="", permitir_omitir_todo=False):
        super().__init__(parent)
        self.resultado = None
        self.omitir_todo = False
        self._tema = tema
        self._permitir_omitir_todo = permitir_omitir_todo

        self.title(titulo)
        self.geometry("380x100")
        self.resizable(False, False)
        self.configure(fg_color=tema["main"])
        self.attributes("-topmost", True)

        lbl_msg = ctk.CTkLabel(
            self, text=mensaje, font=ctk.CTkFont(size=13),
            text_color="#f8fafc", wraplength=320, justify="center"
        )
        lbl_msg.pack(pady=(24, 12), padx=24)

        self.entry = ctk.CTkEntry(
            self, width=300, height=34,
            fg_color=tema["sidebar"], border_color=tema["borde"], border_width=1,
            text_color="#f8fafc"
        )
        if valor_inicial:
            self.entry.insert(0, valor_inicial)
        self.entry.pack(pady=(0, 18))

        frame_botones = ctk.CTkFrame(self, fg_color="transparent")
        frame_botones.pack(pady=(0, 12 if permitir_omitir_todo else 24))

        self.btn_cancelar = ctk.CTkButton(
            frame_botones, text="Cancelar", width=100, height=34,
            fg_color="transparent", border_width=2, border_color=tema["borde"],
            text_color="#e2e8f0", hover_color=tema["borde"],
            command=self._cancelar
        )
        self.btn_cancelar.pack(side="left", padx=6)

        self.btn_aceptar = ctk.CTkButton(
            frame_botones, text="Aceptar", width=100, height=34,
            fg_color=tema["activo"], border_width=2, border_color=tema["activo"],
            text_color="#ffffff", hover_color=tema["borde"],
            command=self._aceptar
        )
        self.btn_aceptar.pack(side="left", padx=6)

        if permitir_omitir_todo:
            self.btn_omitir_todo = ctk.CTkButton(
                frame_botones, text="⏭️ Omitir todo", width=130, height=34,
                fg_color="transparent", border_width=2, border_color="#475569",
                text_color="#94a3b8", hover_color="#334155",
                command=self._omitir_todo
            )
            self.btn_omitir_todo.pack(side="left", padx=6)

            ctk.CTkLabel(
                self, text="\"Omitir todo\" deja este y el resto de campos sin modificar.",
                font=ctk.CTkFont(size=10), text_color="#64748b"
            ).pack(pady=(0, 16))

        # Navegación con teclado entre el campo de texto y los botones:
        # ↓/↑/Tab se mueven entre el campo y los botones; ←/→ se mueven
        # entre los botones una vez que uno de ellos tiene el foco;
        # Enter activa lo que esté seleccionado en cada momento.
        self.elementos_foco = [self.entry, self.btn_cancelar, self.btn_aceptar]
        if permitir_omitir_todo:
            self.elementos_foco.append(self.btn_omitir_todo)
        self.indice_foco = 0

        for btn in self.elementos_foco[1:]:
            btn.bind("<Left>", lambda e: self._mover_foco(-1))
            btn.bind("<Right>", lambda e: self._mover_foco(1))

        # ---- NUEVO: enlazar las flechas izquierda/derecha también en el campo de entrada
        self.entry.bind("<Left>", lambda e: self._mover_foco(-1))
        self.entry.bind("<Right>", lambda e: self._mover_foco(1))

        self.bind("<Down>", lambda e: self._mover_foco(1))
        self.bind("<Up>", lambda e: self._mover_foco(-1))
        self.bind("<Tab>", lambda e: self._mover_foco(1))
        self.bind("<Return>", lambda e: self._activar_actual())
        self.bind("<KP_Enter>", lambda e: self._activar_actual())
        self.bind("<Escape>", lambda e: self._cancelar())
        self.protocol("WM_DELETE_WINDOW", self._cancelar)

        self._ajustar_tamano_y_centrar()
        self.after(20, self._activar_modal)

    def _ajustar_tamano_y_centrar(self):
        self.withdraw()
        self.update_idletasks()
        ancho = 460 if self._permitir_omitir_todo else 380
        alto = self.winfo_reqheight()
        x = (self.winfo_screenwidth() - ancho) // 2
        y = (self.winfo_screenheight() - alto) // 2
        self.geometry(f"{ancho}x{alto}+{max(x, 0)}+{max(y, 0)}")
        self.deiconify()

    def _activar_modal(self):
        self.grab_set()
        self._aplicar_foco()

    def _mover_foco(self, direccion):
        self.indice_foco = (self.indice_foco + direccion) % len(self.elementos_foco)
        self._aplicar_foco()
        return "break"

    def _aplicar_foco(self):
        elemento = self.elementos_foco[self.indice_foco]
        elemento.focus_set()
        if elemento is self.entry:
            self.entry.select_range(0, "end")
            self.entry.icursor("end")
        self._resaltar_foco()

    def _resaltar_foco(self):
        colores_normales = {
            self.btn_cancelar: self._tema["borde"],
            self.btn_aceptar: self._tema["activo"],
        }
        if self._permitir_omitir_todo:
            colores_normales[self.btn_omitir_todo] = "#475569"
        for i, elemento in enumerate(self.elementos_foco):
            if elemento is self.entry:
                continue
            if i == self.indice_foco:
                elemento.configure(border_color="#f8fafc")
            else:
                elemento.configure(border_color=colores_normales[elemento])

    def _activar_actual(self):
        elemento = self.elementos_foco[self.indice_foco]
        if elemento is self.btn_cancelar:
            self._cancelar()
        elif elemento is self.btn_aceptar:
            self._aceptar()
        elif self._permitir_omitir_todo and elemento is self.btn_omitir_todo:
            self._omitir_todo()
        else:
            self._aceptar()

    def _aceptar(self):
        self.resultado = self.entry.get()
        self.grab_release()
        self.destroy()

    def _cancelar(self):
        self.resultado = None
        self.grab_release()
        self.destroy()

    def _omitir_todo(self):
        self.resultado = None
        self.omitir_todo = True
        self.grab_release()
        self.destroy()


class DialogoBusqueda(ctk.CTkToplevel):
    def __init__(self, parent, titulo, tema, repositorio):
        super().__init__(parent)
        self.resultado = None
        self.repo = repositorio
        self._tema = tema

        self.title(titulo)
        self.geometry("380x250")
        self.resizable(False, False)
        self.configure(fg_color=tema["main"])
        self.attributes("-topmost", True)

        self.entry = ctk.CTkEntry(
            self, width=320, height=34, placeholder_text="Empieza a escribir...",
            fg_color=tema["sidebar"], border_color=tema["borde"]
        )
        self.entry.pack(pady=(20, 10))
        self.entry.bind("<KeyRelease>", self._actualizar_sugerencias) 
        self.entry.bind("<Down>", self._enfocar_lista)
        self.entry.bind("<Up>", self._enfocar_lista)
        self.entry.bind("<Escape>", lambda e: self._cancelar())

        self.lista_sug = tk.Listbox(
            self, width=45, height=8, bg=tema["sidebar"], fg="#f8fafc",
            bd=1, highlightthickness=0, selectbackground=tema["activo"], font=('Sans', 11)
        )
        self.lista_sug.pack(pady=(0, 20), padx=30, fill="both", expand=True)
        
        self.lista_sug.bind("<Double-Button-1>", self._seleccionar)
        self.lista_sug.bind("<Return>", self._seleccionar)
        self.entry.bind("<Return>", self._seleccionar)
        self.lista_sug.bind("<Up>", self._volver_al_buscador)
        self.lista_sug.bind("<Escape>", lambda e: self._cancelar())

        self.protocol("WM_DELETE_WINDOW", self._cancelar)

        self.entry.focus_force()
        self._ajustar_tamano_y_centrar()

    def _ajustar_tamano_y_centrar(self):
        self.withdraw()
        self.update_idletasks()
        ancho, alto = 380, self.winfo_reqheight()
        x = (self.winfo_screenwidth() - ancho) // 2
        y = (self.winfo_screenheight() - alto) // 2
        self.geometry(f"{ancho}x{alto}+{max(x, 0)}+{max(y, 0)}")
        self.deiconify()

    def _quitar_tildes(self, texto):
        texto = "" if texto is None else str(texto)
        mapa_tildes = {
            'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
            'Á': 'A', 'É': 'E', 'Í': 'I', 'Ó': 'O', 'Ú': 'U',
            'à': 'a', 'è': 'e', 'ì': 'i', 'ò': 'o', 'ù': 'u',
            'À': 'A', 'È': 'E', 'Ì': 'I', 'Ò': 'O', 'Ù': 'U',
            'ä': 'a', 'ë': 'e', 'ï': 'i', 'ö': 'o', 'ü': 'u',
            'Ä': 'A', 'Ë': 'E', 'Ï': 'I', 'Ö': 'O', 'Ü': 'U',
            'â': 'a', 'ê': 'e', 'î': 'i', 'ô': 'o', 'û': 'u',
            'Â': 'A', 'Ê': 'E', 'Î': 'I', 'Ô': 'O', 'Û': 'U'
        }
        resultado = ""
        for c in texto:
            resultado += mapa_tildes.get(c, c)
        return resultado

    def _normalizar_busqueda(self, texto):
        texto = "" if texto is None else str(texto)
        return self._quitar_tildes(texto).lower()

    def _actualizar_sugerencias(self, event):
        if event.keysym in ("Up", "Down", "Left", "Right", "Return", "Escape"):
            return

        termino_bruto = self.entry.get().strip()
        self.lista_sug.delete(0, tk.END)
        
        if termino_bruto:
            termino_norm = self._normalizar_busqueda(termino_bruto)
            resultados = []
            
            for p in self.repo.productos:
                nombre_norm = self._normalizar_busqueda(p.nombre)
                id_str = str(p.id)
                id_norm = self._normalizar_busqueda(id_str)
                if termino_norm in nombre_norm or termino_norm in id_norm:
                    resultados.append(p)

            for r in resultados[:8]:
                self.lista_sug.insert(tk.END, f"{r.id} | {r.nombre}")

    def _enfocar_lista(self, event):
        if self.lista_sug.size() > 0:
            self.lista_sug.focus_set()
            self.lista_sug.selection_clear(0, tk.END)
            self.lista_sug.selection_set(0)
            self.lista_sug.activate(0)
        return "break"

    def _volver_al_buscador(self, event):
        if self.lista_sug.curselection() and self.lista_sug.curselection()[0] == 0:
            self.entry.focus_set()
            return "break"

    def _seleccionar(self, event=None):
        if self.lista_sug.curselection():
            seleccion = self.lista_sug.get(self.lista_sug.curselection())
            id_str = seleccion.split(" | ")[0].strip()
            if id_str.isdigit():
                self.resultado = id_str
            else:
                self.resultado = self.entry.get().strip()
        else:
            self.resultado = self.entry.get().strip()
        self.destroy()

    def _cancelar(self, event=None):
        self.resultado = None
        self.grab_release()
        self.destroy()


class InventarioApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        _registrar_atajo_seleccionar_todo(self)

        self.repo = RepositorioProductos()
        self._reorganizar_ids()

        self.title("AMB Stock — Gestor de Inventario Moderno")
        self.geometry("1150x800")
        self._aplicar_icono_ventana()

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.menu_activo = True
        self.componente_tabla_actual = None
        self.modo_vista_inventario = "clasica"
        
        self.bg_image_raw = None
        self.bg_image_tk = None
        self.lbl_fondo = None
        self.ruta_fondo_actual = ""
        self.toast_frame = None
        self._resize_after_id = None

        self._modo_widget_actual = None
        self._tabla_clasica = None
        self._lbl_valor_clasica = None
        self._estilo_tabla_configurado = False

        self.temas = [
            {"nombre": "🔵 Azul Ejecutivo", "sidebar": "#0f172a", "main": "#1e293b", "borde": "#334155", "activo": "#6366f1"},
            {"nombre": "🔴 Rojo Oscuro / Gaming", "sidebar": "#180c0c", "main": "#261212", "borde": "#451a1a", "activo": "#ef4444"},
            {"nombre": "⬛ Negro Minimalista / OLED", "sidebar": "#000000", "main": "#121212", "borde": "#27272a", "activo": "#3f3f46"},
            {"nombre": "🟢 Verde Esmeralda / Naturaleza", "sidebar": "#062014", "main": "#0d2e1f", "borde": "#14532d", "activo": "#22c55e"},
            {"nombre": "🟣 Púrpura Neón / Cyberpunk", "sidebar": "#110c1d", "main": "#1a102f", "borde": "#3b0764", "activo": "#a855f7"},
            {"nombre": "🌅 Naranja Atardecer / Cálido", "sidebar": "#1c140c", "main": "#2b1d12", "borde": "#7c2d12", "activo": "#f97316"},
            {"nombre": "🌊 Turquesa Océano / Teal", "sidebar": "#041b1d", "main": "#0a2a2d", "borde": "#134e4a", "activo": "#14b8a6"},
            {"nombre": "🌸 Rosado Pastel / Sakura", "sidebar": "#1c0d15", "main": "#2b1420", "borde": "#831843", "activo": "#ec4899"},
            {"nombre": "☀️ Amarillo Brillante / Solar", "sidebar": "#1c190c", "main": "#2b2612", "borde": "#713f12", "activo": "#eab308"},
            {"nombre": "🩵 Azul Cielo / Ice", "sidebar": "#08101a", "main": "#111c2e", "borde": "#1e3a8a", "activo": "#38bdf8"},
            {"nombre": "🪻 Lavanda / Estilo Suave", "sidebar": "#14101c", "main": "#1e172b", "borde": "#4c1d95", "activo": "#c084fc"},
            {"nombre": "🌲 Bosque Nórdico / Menta", "sidebar": "#041511", "main": "#0a211b", "borde": "#065f46", "activo": "#34d399"}
        ]
        self.indice_tema_actual = 0

        self._cargar_preferencias()
        tema_inicial = self.temas[self.indice_tema_actual]
        
        self.sidebar_outer = ctk.CTkFrame(self, width=270, corner_radius=14, fg_color=tema_inicial["sidebar"])
        self.sidebar_outer.grid(row=0, column=0, padx=(15, 5), pady=15, sticky="nsew")
        self.sidebar_outer.grid_columnconfigure(0, weight=1)
        self.sidebar_outer.grid_rowconfigure(3, weight=1)

        self.logo_sidebar_tk = self._cargar_logo_sidebar()
        cabecera_marca = ctk.CTkFrame(self.sidebar_outer, fg_color="transparent")
        cabecera_marca.grid(row=0, column=0, pady=(18, 2))

        if self.logo_sidebar_tk:
            lbl_logo = ctk.CTkLabel(cabecera_marca, text="", image=self.logo_sidebar_tk)
            lbl_logo.pack(side="left", padx=(0, 8))

        lbl_brand = ctk.CTkLabel(cabecera_marca, text="AMB STOCK", font=ctk.CTkFont(size=18, weight="bold"), text_color="#f8fafc")
        lbl_brand.pack(side="left")

        lbl_brand_sub = ctk.CTkLabel(self.sidebar_outer, text="Gestor de inventario — AMB Solucions", font=ctk.CTkFont(size=10), text_color="#64748b")
        lbl_brand_sub.grid(row=1, column=0, padx=20, pady=(0, 6))

        self.linea_acento_marca = ctk.CTkFrame(self.sidebar_outer, height=2, fg_color=tema_inicial["activo"], corner_radius=2)
        self.linea_acento_marca.grid(row=2, column=0, padx=20, pady=(0, 10), sticky="ew")

        self.sidebar = ctk.CTkFrame(self.sidebar_outer, fg_color="transparent")
        self.sidebar.grid(row=3, column=0, sticky="nsew", padx=2, pady=5)
        self.sidebar.grid_columnconfigure(0, weight=1)
        

        self.opciones_menu = [
            ("➕ Añadir producto (Ctrl+N)", self.asistente_añadir_producto),
            ("✏️ Modificar producto (Ctrl+M)", self.vista_modificar_terminal),
            ("🗑 Eliminar producto (Ctrl+D)", self.vista_eliminar),
            ("🗑️ Eliminación múltiple (F2)", self.vista_eliminar_multiples),
            ("📁 Explorador / Alternar (Ctrl+E)", self.alternar_vista_inventario),
            ("🔍 Buscar producto (Ctrl+F)", self.vista_buscar),
            ("⚠️ Alertas de stock", self.vista_alertas),
            ("📊 Ver estadísticas (F3)", self.vista_estadisticas),
            ("🖼️ Cambiar fondo...", self.cambiar_fondo_personalizado),
            ("🎨 Cambiar tema colores", self.cambiar_tema_colores),
            ("📤 Exportar a CSV", self.accion_exportar),
            ("📥 Importar desde CSV", self.accion_importar),
            ("↩ Deshacer (Ctrl+Z)", self.accion_deshacer),
            ("💾 Guardar todo (Ctrl+S)", self.accion_guardar),
            ("📜 Ver historial", self.vista_historial),
            ("🚪 Salir (Ctrl+Q)", self.salir_aplicacion)
        ]

        self.botones_menu = []
        self.indice_seleccionado = 0

        for i, (texto, comando) in enumerate(self.opciones_menu):
            btn = ctk.CTkButton(
                self.sidebar,
                text=texto,
                command=self._crear_comando_menu(i, comando),
                anchor="w",
                fg_color="transparent",
                text_color="#94a3b8",
                hover_color=tema_inicial["borde"],
                font=ctk.CTkFont(size=13),
                corner_radius=8,
                height=25
            )
            btn.pack(padx=4, pady=2, fill="x")
            self.botones_menu.append(btn)

        self.pie_sidebar = ctk.CTkLabel(
            self.sidebar_outer,
            text="AMB Solucions",
            font=ctk.CTkFont(size=10),
            text_color="#475569"
        )
        self.pie_sidebar.grid(row=4, column=0, pady=(4, 14))

        self.update_idletasks()
        altura_necesaria = self.sidebar_outer.winfo_reqheight() + 30
        altura_minima = max(680, altura_necesaria + 40)
        self.minsize(950, altura_minima)
        if self.winfo_height() < altura_minima:
            self.geometry(f"1150x{altura_minima}")

        self.main_container = ctk.CTkFrame(self, corner_radius=14, fg_color=tema_inicial["main"])
        self.main_container.grid(row=0, column=1, padx=(5, 15), pady=15, sticky="nsew")
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_rowconfigure(0, weight=1)

        # Botón de usuario (arriba a la derecha): al pulsarlo despliega un menú
        # con "Cambiar contraseña", "Cerrar sesión" y, si el usuario es admin,
        # "Gestionar usuarios" y "Ver auditoría".
        self._popup_usuario_actual = None
        self.opciones_menu_usuario = []
        self.btn_usuario_menu = ctk.CTkButton(
            self,
            text="👤 Usuario  ▾",
            command=self._alternar_menu_usuario,
            fg_color=tema_inicial["sidebar"],
            hover_color=tema_inicial["borde"],
            text_color="#f8fafc",
            border_width=1,
            border_color=tema_inicial["borde"],
            corner_radius=8,
            height=32,
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.btn_usuario_menu.place(relx=1.0, x=-28, y=22, anchor="ne")

        self._vincular_teclas_menu()
        self.bind("<Right>", self._activar_panel_tabla)

        self.bind("<Control-n>", lambda e: self.asistente_añadir_producto())
        self.bind("<Control-N>", lambda e: self.asistente_añadir_producto())
        self.bind("<Control-m>", lambda e: self.vista_modificar_terminal())
        self.bind("<Control-M>", lambda e: self.vista_modificar_terminal())
        self.bind("<Control-f>", lambda e: self.vista_buscar())
        self.bind("<Control-F>", lambda e: self.vista_buscar())
        self.bind("<Control-d>", lambda e: self.vista_eliminar())
        self.bind("<Control-D>", lambda e: self.vista_eliminar())
        self.bind("<Control-z>", lambda e: self.accion_deshacer())
        self.bind("<Control-Z>", lambda e: self.accion_deshacer())
        self.bind("<Control-s>", lambda e: self.accion_guardar())
        self.bind("<Control-S>", lambda e: self.accion_guardar())
        self.bind("<Control-e>", lambda e: self.alternar_vista_inventario())
        self.bind("<Control-E>", lambda e: self.alternar_vista_inventario())
        self.bind("<F2>", lambda e: self.vista_eliminar_multiples())
        self.bind("<F3>", lambda e: self.vista_estadisticas())
        self.bind("<Control-q>", lambda e: self.salir_aplicacion())
        self.bind("<Control-Q>", lambda e: self.salir_aplicacion())
        self.bind("<Escape>", lambda e: self.renderizar_vista_actual())

        self.protocol("WM_DELETE_WINDOW", self.salir_aplicacion)
        self.bind("<Configure>", self._redimensionar_fondo)

        self._configurar_estilo_tabla()
        self._actualizar_foco_menu()
        self.vista_inventario_clasica()
        
        if self.ruta_fondo_actual and os.path.exists(self.ruta_fondo_actual):
            try:
                self.bg_image_raw = Image.open(self.ruta_fondo_actual)
                self.after(100, self._aplicar_fondo)
            except Exception:
                pass

    def _configurar_estilo_tabla(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Inventario.Treeview",
            background="#0f172a", foreground="#f8fafc", fieldbackground="#0f172a",
            rowheight=32, borderwidth=0, font=('Sans', 10)
        )
        style.configure(
            "Inventario.Treeview.Heading",
            background="#1e293b", foreground="#f8fafc", relief="flat",
            font=('Sans', 10, 'bold'), padding=(8, 8)
        )
        style.layout("Inventario.Treeview", style.layout("Treeview"))

        style.configure(
            "Inventario.Horizontal.TScrollbar",
            background="#475569", troughcolor="#0f172a", bordercolor="#0f172a",
            arrowcolor="#0f172a", darkcolor="#475569", lightcolor="#475569",
            arrowsize=1, gripcount=0, relief="flat", borderwidth=0
        )
        style.map("Inventario.Horizontal.TScrollbar", background=[("active", "#64748b")])

        self._actualizar_color_seleccion_tabla()
        self._estilo_tabla_configurado = True

    def _actualizar_color_seleccion_tabla(self):
        tema_actual = self.temas[self.indice_tema_actual]
        style = ttk.Style()
        style.map("Inventario.Treeview", background=[("selected", tema_actual["activo"])])
        if self._tabla_clasica and self._tabla_clasica.winfo_exists():
            self._tabla_clasica.tag_configure("par", background="#0f172a")
            self._tabla_clasica.tag_configure("impar", background="#152238")
            self._tabla_clasica.tag_configure("bajo_stock", foreground="#fbbf24")
            self._tabla_clasica.tag_configure("sin_stock", foreground="#f87171")

    def mostrar_toast(self, mensaje, tipo="exito"):
        if self.toast_frame and self.toast_frame.winfo_exists():
            self.toast_frame.destroy()

        iconos = {"exito": "✔", "error": "✘", "info": "ℹ"}
        color_fondo = "#22c55e" if tipo == "exito" else "#ef4444" if tipo == "error" else "#3b82f6"

        self.toast_frame = ctk.CTkFrame(self, fg_color=color_fondo, corner_radius=10)
        lbl_toast = ctk.CTkLabel(
            self.toast_frame, 
            text=f"  {iconos.get(tipo, '')}  {mensaje}  ", 
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#ffffff"
        )
        lbl_toast.pack(padx=12, pady=9)

        self._animar_toast(rely_actual=1.15, rely_destino=0.95)
        self.after(3000, self._ocultar_toast)

    def _animar_toast(self, rely_actual, rely_destino, paso=0.045):
        if not (self.toast_frame and self.toast_frame.winfo_exists()):
            return
        if rely_actual <= rely_destino:
            self.toast_frame.place(relx=0.97, rely=rely_destino, anchor="se")
            return
        self.toast_frame.place(relx=0.97, rely=rely_actual, anchor="se")
        self.after(12, lambda: self._animar_toast(rely_actual - paso, rely_destino, paso))

    def _ocultar_toast(self):
        if self.toast_frame and self.toast_frame.winfo_exists():
            self.toast_frame.destroy()
            self.toast_frame = None

    def _reorganizar_ids(self):
        for i, prod in enumerate(self.repo.productos, start=1):
            prod.id = i

    def _cargar_preferencias(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    datos = json.load(f)
                    self.indice_tema_actual = datos.get("tema_idx", 0)
                    self.ruta_fondo_actual = datos.get("fondo_ruta", "")
            except Exception:
                pass

    def _guardar_preferencias(self):
        try:
            datos = {
                "tema_idx": self.indice_tema_actual,
                "fondo_ruta": self.ruta_fondo_actual
            }
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(datos, f, indent=4)
        except Exception as e:
            print(f"Error al guardar preferencias: {e}")

    def _verificar_permiso(self, permiso):
        if not hasattr(self, 'sistema_usuarios') or not self.sistema_usuarios:
            return False
        if self.sistema_usuarios.tiene_permiso(permiso):
            return True
        else:
            self._mostrar_aviso("Permiso denegado", "No tienes permiso para realizar esta acción.", icono="🚫")
            return False

    def configurar_menu_usuario(self, texto_boton, opciones):
        """Actualiza el texto del botón de usuario (arriba a la derecha) y las
        opciones que se muestran al desplegarlo."""
        self.btn_usuario_menu.configure(text=texto_boton)
        self.opciones_menu_usuario = opciones

    def _alternar_menu_usuario(self):
        if self._popup_usuario_actual is not None and self._popup_usuario_actual.winfo_exists():
            self._popup_usuario_actual.destroy()
            self._popup_usuario_actual = None
            return

        if not self.opciones_menu_usuario:
            return

        tema = self.temas[self.indice_tema_actual]
        self._popup_usuario_actual = MenuUsuarioPopup(
            self, self.btn_usuario_menu, tema, self.opciones_menu_usuario
        )
        self._popup_usuario_actual.bind(
            "<Destroy>", lambda e: setattr(self, "_popup_usuario_actual", None), add="+"
        )

    def cambiar_tema_colores(self):
        self.indice_tema_actual = (self.indice_tema_actual + 1) % len(self.temas)
        tema = self.temas[self.indice_tema_actual]

        self.sidebar_outer.configure(fg_color=tema["sidebar"])
        self.main_container.configure(fg_color=tema["main"])
        self.linea_acento_marca.configure(fg_color=tema["activo"])
        self.btn_usuario_menu.configure(
            fg_color=tema["sidebar"], hover_color=tema["borde"], border_color=tema["borde"]
        )

        for btn in self.botones_menu:
            btn.configure(hover_color=tema["borde"])

        self._actualizar_color_seleccion_tabla()
        self._actualizar_foco_menu()
        self.renderizar_vista_actual()
        self.mostrar_toast(f"Tema cambiado a: {tema['nombre']}", "info")

    def _cargar_logo_sidebar(self):
        if not os.path.exists(RUTA_LOGO):
            return None
        try:
            imagen = Image.open(RUTA_LOGO)
            return ctk.CTkImage(light_image=imagen, dark_image=imagen, size=(34, 34))
        except Exception:
            return None

    def _aplicar_icono_ventana(self):
        if not os.path.exists(RUTA_LOGO):
            return
        try:
            imagen_icono = Image.open(RUTA_LOGO)
            self._icono_ventana_tk = ImageTk.PhotoImage(imagen_icono)
            self.iconphoto(True, self._icono_ventana_tk)
        except Exception:
            pass

    def cambiar_fondo_personalizado(self):
        ruta_imagen = filedialog.askopenfilename(
            title="Seleccionar fondo de pantalla",
            filetypes=[("Imágenes", "*.png *.jpg *.jpeg *.webp")]
        )
        if ruta_imagen:
            try:
                self.bg_image_raw = Image.open(ruta_imagen)
                self.ruta_fondo_actual = ruta_imagen
                self._aplicar_fondo()
                self.mostrar_toast("¡Fondo de pantalla actualizado!", "exito")
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo cargar la imagen:\n{e}")

    def _aplicar_fondo(self):
        if self.bg_image_raw:
            ancho, alto = self.winfo_width(), self.winfo_height()
            if ancho < 100 or alto < 100:
                return

            img_redimensionada = self.bg_image_raw.resize((ancho, alto), Image.Resampling.LANCZOS)
            self.bg_image_tk = ImageTk.PhotoImage(img_redimensionada)

            if not self.lbl_fondo:
                self.lbl_fondo = ctk.CTkLabel(self, text="", image=self.bg_image_tk)
                self.lbl_fondo.place(x=0, y=0, relwidth=1, relheight=1)
            else:
                self.lbl_fondo.configure(image=self.bg_image_tk)

            self.sidebar_outer.lift()
            self.main_container.lift()
            self.btn_usuario_menu.lift()

    def _redimensionar_fondo(self, event):
        if event.widget != self or not self.bg_image_raw:
            return
        if self._resize_after_id is not None:
            self.after_cancel(self._resize_after_id)
        self._resize_after_id = self.after(120, self._aplicar_fondo)

    def _vincular_teclas_menu(self):
        self.bind("<Up>", self._mover_menu_arriba)
        self.bind("<Down>", self._mover_menu_abajo)
        self.bind("<Return>", self._ejecutar_opcion_seleccionada)
        self.bind("<Left>", lambda e: None)

    def _desvincular_teclas_menu(self):
        self.unbind("<Up>")
        self.unbind("<Down>")
        self.unbind("<Return>")

    def _crear_comando_menu(self, indice, comando):
        def wrapper():
            self.indice_seleccionado = indice
            self._activar_menu_lateral()
            comando()
        return wrapper

    def _actualizar_foco_menu(self):
        tema_activo = self.temas[self.indice_tema_actual]["activo"]
        for i, btn in enumerate(self.botones_menu):
            if i == self.indice_seleccionado and self.menu_activo:
                btn.configure(fg_color=tema_activo, text_color="#ffffff") 
            else:
                btn.configure(fg_color="transparent", text_color="#94a3b8")

    def _activar_menu_lateral(self, event=None):
        self.menu_activo = True
        self._vincular_teclas_menu()
        self._actualizar_foco_menu()
        self.focus_set()

    def _activar_panel_tabla(self, event=None):
        if self.componente_tabla_actual and self.componente_tabla_actual.winfo_exists():
            self.menu_activo = False
            self._desvincular_teclas_menu()
            self._actualizar_foco_menu()
            self.componente_tabla_actual.focus_set()
            items = self.componente_tabla_actual.get_children()
            if items and not self.componente_tabla_actual.selection():
                self.componente_tabla_actual.selection_set(items[0])
                self.componente_tabla_actual.focus(items[0])

    def _mover_menu_arriba(self, event=None):
        if not self.menu_activo:
            return
        self.indice_seleccionado = (self.indice_seleccionado - 1) % len(self.botones_menu)
        self._actualizar_foco_menu()

    def _mover_menu_abajo(self, event=None):
        if not self.menu_activo:
            return
        self.indice_seleccionado = (self.indice_seleccionado + 1) % len(self.botones_menu)
        self._actualizar_foco_menu()

    def _ejecutar_opcion_seleccionada(self, event=None):
        if not self.menu_activo:
            return
        _, comando = self.opciones_menu[self.indice_seleccionado]
        comando()

    def _limpiar_panel_principal(self):
        self.componente_tabla_actual = None
        self._modo_widget_actual = None
        self._tabla_clasica = None
        self._lbl_valor_clasica = None
        for child in self.main_container.winfo_children():
            child.destroy()

    def _mostrar_aviso(self, titulo, mensaje, icono="ℹ️"):
        tema = self.temas[self.indice_tema_actual]
        dialogo = DialogoAviso(self, titulo, mensaje, tema, icono=icono)
        self.wait_window(dialogo)

    def _pedir_entrada(self, titulo, texto, permitir_omitir_todo=False):
        tema = self.temas[self.indice_tema_actual]
        dialogo = DialogoEntrada(self, titulo, texto, tema, permitir_omitir_todo=permitir_omitir_todo)
        self.wait_window(dialogo)
        if permitir_omitir_todo:
            return dialogo.resultado, dialogo.omitir_todo
        return dialogo.resultado

    def _confirmar(self, titulo, mensaje, texto_si="Sí", texto_no="No"):
        tema = self.temas[self.indice_tema_actual]
        dialogo = DialogoConfirmacion(self, titulo, mensaje, tema, texto_si, texto_no)
        self.wait_window(dialogo)
        return dialogo.resultado

    def _configurar_eventos_tabla(self, componente):
        def al_enfocar(event):
            self.menu_activo = False
            self._desvincular_teclas_menu()
            self._actualizar_foco_menu()
            componente.focus_set()

        def volver_al_menu(event):
            self._activar_menu_lateral()
            return "break"

        componente.bind("<Button-1>", al_enfocar)
        componente.bind("<FocusIn>", al_enfocar)
        componente.bind("<Left>", volver_al_menu)
        componente.bind("<Up>", lambda e: self._mover_seleccion_tabla(componente, -1))
        componente.bind("<Down>", lambda e: self._mover_seleccion_tabla(componente, 1))

    def _obtener_items_visibles(self, componente):
        items = []
        def recorrer(padre):
            for item in componente.get_children(padre):
                items.append(item)
                if componente.item(item, "open"):
                    recorrer(item)
        recorrer("")
        return items

    def _mover_seleccion_tabla(self, componente, direccion):
        items = self._obtener_items_visibles(componente)
        if not items:
            return "break"
        actual = componente.focus()
        indice_actual = items.index(actual) if actual in items else 0
        nuevo_indice = (indice_actual + direccion) % len(items)
        nuevo_item = items[nuevo_indice]
        componente.selection_set(nuevo_item)
        componente.focus(nuevo_item)
        componente.see(nuevo_item)
        return "break"

    def _configurar_ordenacion_columnas(self, tabla, columnas):
        for col in columnas:
            tabla.heading(col, command=lambda _col=col: self._ordenar_por_columna(tabla, _col, False))

    def _ordenar_por_columna(self, tabla, col, reverso):
        lineas = [(tabla.set(k, col), k) for k in tabla.get_children('')]
        def parse_valor(val):
            v_str = val[0].replace('€', '').replace('⚠️ ', '').strip()
            try:
                return float(v_str)
            except ValueError:
                return val[0].lower()
        lineas.sort(key=parse_valor, reverse=reverso)
        for index, (val, k) in enumerate(lineas):
            tabla.move(k, '', index)
        tabla.heading(col, command=lambda: self._ordenar_por_columna(tabla, col, not reverso))

    def _habilitar_edicion_directa(self, tabla):
        tabla.bind("<Double-1>", lambda e: self._al_doble_clic_celda(e, tabla))

    def _al_doble_clic_celda(self, event, tabla):
        if not self._verificar_permiso("editar"):
            return

        region = tabla.identify_region(event.x, event.y)
        if region != "cell":
            return
        column = tabla.identify_column(event.x)
        item = tabla.identify_row(event.y)
        col_idx = int(column.replace("#", "")) - 1
        cols_editables = ["nombre", "cantidad", "precio", "categoria", "ubicacion", "stock_min"]
        cols_totales = ("id", "nombre", "cantidad", "precio", "valor", "categoria", "ubicacion", "stock_min")
        nombre_col = cols_totales[col_idx]

        if nombre_col not in cols_editables:
            return

        x, y, w, h = tabla.bbox(item, column)
        valores = tabla.item(item, "values")
        id_prod = str(valores[0]).strip()
        prod = self.repo.obtener_por_id(id_prod)
        if not prod:
            return

        entry = ctk.CTkEntry(tabla, width=w, height=h)
        entry.place(x=x, y=y)
        
        val_actual = ""
        if nombre_col == "stock_min":
            val_actual = prod.stock_minimo
        elif nombre_col == "ubicacion":
            val_actual = getattr(prod, "ubicacion", "Sin asignar")
        else:
            val_actual = getattr(prod, nombre_col, "")

        entry.insert(0, str(val_actual))
        entry.focus_set()

        def guardar_cambio(e=None):
            nuevo_val = entry.get().strip()
            entry.destroy()
            if not nuevo_val and nombre_col != "ubicacion":
                return
            try:
                if nombre_col == "cantidad":
                    prod.cantidad = max(0, int(nuevo_val))
                elif nombre_col == "precio":
                    prod.precio = max(0.0, float(nuevo_val.replace(',', '.')))
                elif nombre_col == "stock_min":
                    prod.stock_minimo = max(0, int(nuevo_val))
                elif nombre_col == "nombre":
                    ok_v, nom_val, msg = validar_nombre(nuevo_val)
                    if ok_v:
                        prod.nombre = nom_val
                    else:
                        messagebox.showerror("Error", msg)
                        return
                elif nombre_col == "categoria":
                    prod.categoria = nuevo_val
                elif nombre_col == "ubicacion":
                    prod.ubicacion = nuevo_val if nuevo_val else "Sin asignar"

                self.repo.guardar()
                self.renderizar_vista_actual()
                self.mostrar_toast("Producto actualizado correctamente", "exito")
            except ValueError:
                messagebox.showerror("Error", "El valor introducido no es válido.")

        entry.bind("<Return>", guardar_cambio)
        entry.bind("<FocusOut>", lambda e: entry.destroy())

    def alternar_vista_inventario(self):
        if self.modo_vista_inventario == "clasica":
            self.modo_vista_inventario = "explorador"
            self.vista_inventario_explorador()
        else:
            self.modo_vista_inventario = "clasica"
            self.vista_inventario_clasica()

    def renderizar_vista_actual(self, lista_custom=None):
        self._reorganizar_ids()
        if self.modo_vista_inventario == "explorador":
            self.vista_inventario_explorador(lista_custom)
        else:
            self.vista_inventario_clasica(lista_custom)

    def vista_inventario_clasica(self, lista_custom=None):
        prods = lista_custom if lista_custom is not None else self.repo.productos

        if self._modo_widget_actual == "clasica" and self._tabla_clasica and self._tabla_clasica.winfo_exists():
            self._rellenar_tabla_clasica(self._tabla_clasica, prods)
            self._lbl_valor_clasica.configure(text=f"Valor total: {self.repo.valor_total():.2f}€")
            return

        self._limpiar_panel_principal()
        frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        frame.pack(padx=20, pady=20, fill="both", expand=True)

        cabecera = ctk.CTkFrame(frame, fg_color="transparent")
        cabecera.pack(anchor="w", fill="x", pady=(0, 15))

        lbl_tit = ctk.CTkLabel(cabecera, text="📋 INVENTARIO GENERAL", font=ctk.CTkFont(size=17, weight="bold"), text_color="#f8fafc")
        lbl_tit.pack(anchor="w", pady=(0, 2))
        lbl_sub = ctk.CTkLabel(cabecera, text="💡 Consejo: Haz doble clic en cualquier celda para editarla directamente.", font=ctk.CTkFont(size=11), text_color="#94a3b8")
        lbl_sub.pack(anchor="w")

        if not self._estilo_tabla_configurado:
            self._configurar_estilo_tabla()

        cols = ("id", "nombre", "cantidad", "precio", "valor", "categoria", "ubicacion", "stock_min")
        tabla = ttk.Treeview(frame, columns=cols, show="headings", selectmode="browse", style="Inventario.Treeview")
        self.componente_tabla_actual = tabla
        self._tabla_clasica = tabla
        self._modo_widget_actual = "clasica"

        tabla.heading("id", text="ID ↕")
        tabla.heading("nombre", text="Nombre ↕")
        tabla.heading("cantidad", text="Stock ↕")
        tabla.heading("precio", text="Precio € ↕")
        tabla.heading("valor", text="Valor € ↕")
        tabla.heading("categoria", text="Categoría ↕")
        tabla.heading("ubicacion", text="Ubicación ↕")
        tabla.heading("stock_min", text="Alerta ↕")

        tabla.column("id", width=55, minwidth=55, anchor="center")
        tabla.column("nombre", width=150, minwidth=100)
        tabla.column("cantidad", width=85, minwidth=85, anchor="center")
        tabla.column("precio", width=100, minwidth=100, anchor="e")
        tabla.column("valor", width=100, minwidth=95, anchor="e")
        tabla.column("categoria", width=120, minwidth=115)
        tabla.column("ubicacion", width=120, minwidth=115)
        tabla.column("stock_min", width=95, minwidth=90, anchor="center")

        scroll_h = ttk.Scrollbar(frame, orient="horizontal", command=tabla.xview, style="Inventario.Horizontal.TScrollbar")
        tabla.configure(xscrollcommand=lambda primero, ultimo: self._autoocultar_scrollbar(scroll_h, primero, ultimo))

        tabla.pack(fill="both", expand=True, pady=(5, 0))
        self._actualizar_color_seleccion_tabla()
        self._rellenar_tabla_clasica(tabla, prods)

        info_frame = ctk.CTkFrame(frame, fg_color="transparent")
        info_frame.pack(fill="x", pady=(10, 0))

        self._lbl_valor_clasica = ctk.CTkLabel(
            info_frame, 
            text=f"Valor total: {self.repo.valor_total():.2f}€", 
            font=ctk.CTkFont(size=13, weight="bold"), 
            text_color="#38bdf8"
        )
        self._lbl_valor_clasica.pack(side="left")

        self._configurar_eventos_tabla(tabla)
        self._configurar_ordenacion_columnas(tabla, cols)
        self._habilitar_edicion_directa(tabla)

    def _autoocultar_scrollbar(self, scrollbar, primero, ultimo):
        if float(primero) <= 0.0 and float(ultimo) >= 1.0:
            scrollbar.pack_forget()
        elif not scrollbar.winfo_ismapped():
            scrollbar.pack(fill="x", pady=(0, 5))
        scrollbar.set(primero, ultimo)

    def _rellenar_tabla_clasica(self, tabla, prods):
        tabla.delete(*tabla.get_children())
        for i, p in enumerate(prods):
            alerta_str = f"⚠️ {p.stock_minimo}" if p.cantidad <= p.stock_minimo else str(p.stock_minimo)
            ubicacion_val = getattr(p, 'ubicacion', 'Sin asignar') or 'Sin asignar'

            etiquetas = ["par" if i % 2 == 0 else "impar"]
            if p.cantidad <= 0:
                etiquetas.append("sin_stock")
            elif p.cantidad <= p.stock_minimo:
                etiquetas.append("bajo_stock")

            tabla.insert("", "end", values=(
                p.id, p.nombre, p.cantidad, f"{p.precio:.2f}€", f"{p.valor_total:.2f}€", 
                p.categoria or "Sin categoría", ubicacion_val, alerta_str
            ), tags=tuple(etiquetas))

    def vista_inventario_explorador(self, lista_custom=None):
        self._limpiar_panel_principal()
        frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        frame.pack(padx=20, pady=20, fill="both", expand=True)

        lbl_tit = ctk.CTkLabel(frame, text="📁 EXPLORADOR DE INVENTARIO", font=ctk.CTkFont(size=16, weight="bold"), text_color="#f8fafc")
        lbl_tit.pack(anchor="w", pady=(0, 15))

        if not self._estilo_tabla_configurado:
            self._configurar_estilo_tabla()

        cols = ("id", "stock", "precio", "valor", "ubicacion", "stock_min")
        arbol = ttk.Treeview(frame, columns=cols, show="tree headings", selectmode="browse", style="Inventario.Treeview")
        self.componente_tabla_actual = arbol
        self._modo_widget_actual = "explorador"

        arbol.heading("#0", text="Categoría / Producto", anchor="w")
        arbol.heading("id", text="ID")
        arbol.heading("stock", text="Stock")
        arbol.heading("precio", text="Precio (€)")
        arbol.heading("valor", text="Valor Total")
        arbol.heading("ubicacion", text="Ubicación")
        arbol.heading("stock_min", text="Alerta Stock")

        arbol.column("#0", width=220, anchor="w")
        arbol.column("id", width=50, anchor="center")
        arbol.column("stock", width=60, anchor="center")
        arbol.column("precio", width=80, anchor="e")
        arbol.column("valor", width=90, anchor="e")
        arbol.column("ubicacion", width=120, anchor="w")
        arbol.column("stock_min", width=80, anchor="center")

        arbol.pack(fill="both", expand=True, pady=5)

        prods = lista_custom if lista_custom is not None else self.repo.productos
        nodos_carpetas = {}

        for p in prods:
            cat_path = p.categoria.strip() if p.categoria else "Sin categoría"
            partes = [parte.strip() for parte in cat_path.split("/") if parte.strip()]
            parent_id = ""
            path_acumulado = ""

            for parte in partes:
                path_acumulado = f"{path_acumulado}/{parte}" if path_acumulado else parte
                if path_acumulado not in nodos_carpetas:
                    nodo_id = arbol.insert(parent_id, "end", text=f"📁 {parte}", open=True)
                    nodos_carpetas[path_acumulado] = nodo_id
                parent_id = nodos_carpetas[path_acumulado]

            alerta_str = f"⚠️ {p.stock_minimo}" if p.cantidad <= p.stock_minimo else str(p.stock_minimo)
            ubicacion_val = getattr(p, 'ubicacion', 'Sin asignar') or 'Sin asignar'
            
            if p.cantidad <= 0:
                color = "#f87171"
            elif p.cantidad <= p.stock_minimo:
                color = "#fbbf24"
            else:
                color = "#f8fafc"
                
            arbol.insert(
                parent_id, "end", 
                text=f"📦 {p.nombre}", 
                values=(p.id, p.cantidad, f"{p.precio:.2f}€", f"{p.valor_total:.2f}€", ubicacion_val, alerta_str),
                tags=("producto",)
            )

        arbol.tag_configure("producto", foreground="#f8fafc")
        
        def aplicar_colores(item):
            values = arbol.item(item, "values")
            if values and len(values) >= 2:
                try:
                    stock = int(values[1])
                    prod_id = values[0]
                    prod = self.repo.obtener_por_id(str(prod_id))
                    if prod:
                        if prod.cantidad <= 0:
                            arbol.tag_configure(f"item_{item}", foreground="#f87171")
                            arbol.item(item, tags=(f"item_{item}",))
                        elif prod.cantidad <= prod.stock_minimo:
                            arbol.tag_configure(f"item_{item}", foreground="#fbbf24")
                            arbol.item(item, tags=(f"item_{item}",))
                except (ValueError, IndexError):
                    pass
            
            for child in arbol.get_children(item):
                aplicar_colores(child)
        
        for child in arbol.get_children(""):
            aplicar_colores(child)

        lbl_val = ctk.CTkLabel(
            frame, 
            text=f"Valor total del inventario: {self.repo.valor_total():.2f}€", 
            font=ctk.CTkFont(size=14, weight="bold"), 
            text_color="#38bdf8"
        )
        lbl_val.pack(anchor="w", pady=(10, 0))

        self._configurar_eventos_tabla(arbol)

    def _quitar_tildes(self, texto):
        texto = "" if texto is None else str(texto)
        mapa_tildes = {
            'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
            'Á': 'A', 'É': 'E', 'Í': 'I', 'Ó': 'O', 'Ú': 'U',
            'à': 'a', 'è': 'e', 'ì': 'i', 'ò': 'o', 'ù': 'u',
            'À': 'A', 'È': 'E', 'Ì': 'I', 'Ò': 'O', 'Ù': 'U',
            'ä': 'a', 'ë': 'e', 'ï': 'i', 'ö': 'o', 'ü': 'u',
            'Ä': 'A', 'Ë': 'E', 'Ï': 'I', 'Ö': 'O', 'Ü': 'U',
            'â': 'a', 'ê': 'e', 'î': 'i', 'ô': 'o', 'û': 'u',
            'Â': 'A', 'Ê': 'E', 'Î': 'I', 'Ô': 'O', 'Û': 'U'
        }
        resultado = ""
        for c in texto:
            resultado += mapa_tildes.get(c, c)
        return resultado

    def _normalizar_busqueda(self, texto):
        texto = "" if texto is None else str(texto)
        return self._quitar_tildes(texto).lower()

    def _buscar_sin_tildes(self, termino):
        termino_norm = self._normalizar_busqueda(termino)
        if not termino_norm:
            return []

        resultados = []
        for producto in self.repo.productos:
            nombre_norm = self._normalizar_busqueda(getattr(producto, "nombre", ""))
            id_norm = self._normalizar_busqueda(str(getattr(producto, "id", "")))
            if termino_norm in nombre_norm or termino_norm in id_norm:
                resultados.append(producto)
        return resultados

    def vista_buscar(self):
        tema = self.temas[self.indice_tema_actual]
        dialogo = DialogoBusqueda(self, "Buscar Producto", tema, self.repo)
        self.wait_window(dialogo)
        q = dialogo.resultado
        if q is not None and str(q).strip():
            termino = str(q).strip()
            if termino.isdigit():
                prod = self.repo.obtener_por_id(termino)
                if prod:
                    self.renderizar_vista_actual([prod])
                else:
                    self._mostrar_aviso("No encontrado", f"No se encontró el producto con ID {termino}", "⚠️")
            else:
                res = self._buscar_sin_tildes(termino)
                self.renderizar_vista_actual(res)

    def vista_modificar_terminal(self):
        if not self._verificar_permiso("editar"):
            return
        if self.repo.esta_vacio():
            self._mostrar_aviso("Alerta", "No hay nada en el inventario.", icono="⚠️")
            return
            
        busqueda = self._pedir_entrada("Modificar Producto", "Introduce el ID o Nombre del producto a modificar:")
        if busqueda is None or not busqueda.strip():
            return

        busqueda = busqueda.strip()
        prod = self.repo.obtener_por_id(busqueda)
        if not prod:
            resultados = self._buscar_sin_tildes(busqueda)
            if len(resultados) == 1:
                prod = resultados[0]
            elif len(resultados) > 1:
                exacto = [p for p in resultados if self._normalizar_busqueda(p.nombre) == self._normalizar_busqueda(busqueda)]
                if len(exacto) == 1:
                    prod = exacto[0]
                else:
                    messagebox.showwarning("Atención", f"Hay varios productos que coinciden con '{busqueda}'. Especifica el ID.")
                    return

        if prod:
            self.ejecutar_asistente_modificar(prod)
        else:
            messagebox.showerror("Error", "No se encontró ningún producto con ese ID o Nombre.")

    def ejecutar_asistente_modificar(self, prod):
        if not self._verificar_permiso("editar"):
            return

        def _finalizar():
            self.repo.guardar()
            self.mostrar_toast(f"'{prod.nombre}' actualizado correctamente", "exito")
            self.renderizar_vista_actual()

        nuevo_nom, omitir_todo = self._pedir_entrada(
            "Modificar Nombre", f"Nombre actual: '{prod.nombre}'\nNuevo nombre (en blanco para mantener):",
            permitir_omitir_todo=True
        )
        if nuevo_nom is not None and nuevo_nom.strip():
            ok_v, nom_validado, msg = validar_nombre(nuevo_nom.strip())
            if ok_v:
                prod.nombre = nom_validado
            else:
                messagebox.showerror("Error", msg)
                return
        if omitir_todo:
            _finalizar()
            return

        nueva_cant, omitir_todo = self._pedir_entrada(
            "Modificar Cantidad", f"Cantidad actual: {prod.cantidad}\nNueva cantidad (en blanco para mantener):",
            permitir_omitir_todo=True
        )
        if nueva_cant is not None and nueva_cant.strip():
            try:
                prod.cantidad = max(0, int(nueva_cant.strip()))
            except ValueError:
                messagebox.showerror("Error", "La cantidad debe ser un número entero.")
                return
        if omitir_todo:
            _finalizar()
            return

        nuevo_precio, omitir_todo = self._pedir_entrada(
            "Modificar Precio", f"Precio actual: {prod.precio:.2f}€\nNuevo precio (en blanco para mantener):",
            permitir_omitir_todo=True
        )
        if nuevo_precio is not None and nuevo_precio.strip():
            try:
                prod.precio = max(0.0, float(nuevo_precio.strip()))
            except ValueError:
                messagebox.showerror("Error", "El precio debe ser decimal.")
                return
        if omitir_todo:
            _finalizar()
            return

        nueva_cat, omitir_todo = self._pedir_entrada(
            "Modificar Categoría", f"Categoría actual: '{prod.categoria}'\nNueva categoría (en blanco para mantener):",
            permitir_omitir_todo=True
        )
        if nueva_cat is not None and nueva_cat.strip():
            prod.categoria = nueva_cat.strip()
        if omitir_todo:
            _finalizar()
            return

        ubicacion_actual = getattr(prod, 'ubicacion', 'Sin asignar')
        nueva_ubicacion, omitir_todo = self._pedir_entrada(
            "Modificar Ubicación", f"Ubicación actual: '{ubicacion_actual}'\nNueva ubicación física (en blanco para mantener):",
            permitir_omitir_todo=True
        )
        if nueva_ubicacion is not None and nueva_ubicacion.strip():
            prod.ubicacion = nueva_ubicacion.strip()
        if omitir_todo:
            _finalizar()
            return

        nuevo_stock_min, omitir_todo = self._pedir_entrada(
            "Modificar Stock Mínimo", f"Stock mínimo actual: {prod.stock_minimo}\nNuevo stock mínimo (en blanco para mantener):",
            permitir_omitir_todo=True
        )
        if nuevo_stock_min is not None and nuevo_stock_min.strip():
            try:
                prod.stock_minimo = max(0, int(nuevo_stock_min.strip()))
            except ValueError:
                messagebox.showerror("Error", "El stock mínimo debe ser un entero.")
                return

        _finalizar()

    def vista_eliminar(self):
        if not self._verificar_permiso("eliminar"):
            return
        if self.repo.esta_vacio():
            self._mostrar_aviso("Alerta", "No hay nada en el inventario.", icono="⚠️")
            return

        busqueda = self._pedir_entrada("Eliminar Producto", "Introduce el ID o Nombre del producto a eliminar:")
        if busqueda is None or not busqueda.strip():
            return

        busqueda = busqueda.strip()
        prod = self.repo.obtener_por_id(busqueda)
        if not prod:
            resultados = self._buscar_sin_tildes(busqueda)
            if len(resultados) == 1:
                prod = resultados[0]
            elif len(resultados) > 1:
                exacto = [p for p in resultados if self._normalizar_busqueda(p.nombre) == self._normalizar_busqueda(busqueda)]
                if len(exacto) == 1:
                    prod = exacto[0]
                else:
                    messagebox.showwarning("Atención", f"Hay varios productos que coinciden con '{busqueda}'. Especifica el ID.")
                    return

        if prod:
            if self._confirmar("Confirmar eliminación", f"¿Seguro que deseas eliminar '{prod.nombre}' (ID: {prod.id})?", texto_si="Sí, eliminar", texto_no="Cancelar"):
                self.repo.eliminar(prod.id)
                self.mostrar_toast(f"'{prod.nombre}' eliminado", "error")
                self.renderizar_vista_actual()
        else:
            messagebox.showerror("Error", "No se encontró ningún producto con ese ID o Nombre.")

    def vista_eliminar_multiples(self):
        if not self._verificar_permiso("eliminar"):
            return
        if self.repo.esta_vacio():
            self._mostrar_aviso("Alerta", "No hay nada en el inventario.", icono="⚠️")
            return

        entrada = self._pedir_entrada("Eliminación Múltiple", "Introduce IDs o Nombres separados por comas:")
        if entrada is None or not entrada.strip():
            return

        items_busqueda = [item.strip() for item in entrada.split(",") if item.strip()]
        ids_a_eliminar = set()
        encontrados_nombres = []

        for item in items_busqueda:
            prod = self.repo.obtener_por_id(item)
            if prod:
                ids_a_eliminar.add(prod.id)
                encontrados_nombres.append(prod.nombre)
            else:
                resultados = self._buscar_sin_tildes(item)
                for r in resultados:
                    ids_a_eliminar.add(r.id)
                    if r.nombre not in encontrados_nombres:
                        encontrados_nombres.append(r.nombre)

        if not ids_a_eliminar:
            messagebox.showerror("Error", "No se encontró ningún producto coincidente.")
            return

        lista_str = "\n".join([f"• {nom}" for nom in encontrados_nombres[:10]])
        mas_texto = f"\n... y {len(encontrados_nombres) - 10} más." if len(encontrados_nombres) > 10 else ""
        
        if self._confirmar("Confirmar eliminación múltiple", f"¿Deseas eliminar estos {len(ids_a_eliminar)} productos?\n\n{lista_str}{mas_texto}", texto_si="Sí, eliminar", texto_no="Cancelar"):
            for id_p in sorted(list(ids_a_eliminar), reverse=True):
                self.repo.eliminar(id_p)
            self.mostrar_toast(f"Se eliminaron {len(ids_a_eliminar)} productos", "error")
            self.renderizar_vista_actual()

    def asistente_añadir_producto(self):
        if not self._verificar_permiso("crear"):
            return

        nombre_bruto = self._pedir_entrada("Añadir Producto", "Paso 1/6: Nombre del producto:")
        if nombre_bruto is None or not nombre_bruto.strip():
            return

        ok_v, nombre, msg = validar_nombre(nombre_bruto)
        if not ok_v:
            messagebox.showerror("Error", msg)
            return

        cant_str = self._pedir_entrada("Añadir Producto", "Paso 2/6: Cantidad inicial:")
        if cant_str is None:
            return
        try:
            cant = int(cant_str.strip()) if cant_str.strip() else 0
        except ValueError:
            messagebox.showerror("Error", "La cantidad debe ser un entero.")
            return

        precio_str = self._pedir_entrada("Añadir Producto", "Paso 3/6: Precio en €:")
        if precio_str is None:
            return
        try:
            precio = float(precio_str.strip()) if precio_str.strip() else 0.0
        except ValueError:
            messagebox.showerror("Error", "El precio debe ser un número decimal.")
            return

        cat_str = self._pedir_entrada("Añadir Producto", "Paso 4/6: Categoría (Usa '/' para subcategorías):")
        if cat_str is None:
            return
        categoria = cat_str.strip()

        ubicacion_str = self._pedir_entrada("Añadir Producto", "Paso 5/6: Ubicación física:")
        if ubicacion_str is None:
            return
        ubicacion = ubicacion_str.strip() if ubicacion_str.strip() else "Sin asignar"

        stock_str = self._pedir_entrada("Añadir Producto", "Paso 6/6: Stock mínimo para alerta:")
        if stock_str is None:
            return
        try:
            stock_min = int(stock_str.strip()) if stock_str.strip() else 0
        except ValueError:
            stock_min = 0

        duplicado = self.repo.detectar_posible_duplicado(nombre)
        if duplicado:
            if messagebox.askyesno("Conflicto de Duplicado", f"Ya existe un producto similar: '{duplicado.nombre}'.\n¿Deseas UNIFICAR este nuevo registro?"):
                self.repo.modificar_cantidad(duplicado.id, duplicado.cantidad + cant)
                self.repo.modificar_precio(duplicado.id, precio)
                if categoria and not duplicado.categoria:
                    self.repo.modificar_categoria(duplicado.id, categoria)
                if ubicacion and (not getattr(duplicado, 'ubicacion', '') or duplicado.ubicacion == "Sin asignar"):
                    self.repo.modificar_ubicacion(duplicado.id, ubicacion)
                self.repo.guardar()
                self.mostrar_toast(f"Stock de '{duplicado.nombre}' unificado", "exito")
                self.renderizar_vista_actual()
                return

        self.repo.añadir(nombre, cant, precio, stock_min, categoria, ubicacion)
        self.repo.guardar()
        self.mostrar_toast(f"'{nombre}' añadido con éxito", "exito")
        self.renderizar_vista_actual()

    def vista_alertas(self):
        bajos = self.repo.productos_bajo_stock()
        self.renderizar_vista_actual(bajos)

    def vista_estadisticas(self):
        self._limpiar_panel_principal()
        tema_actual = self.temas[self.indice_tema_actual]
        frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        frame.pack(padx=20, pady=20, fill="both", expand=True)

        lbl_tit = ctk.CTkLabel(frame, text="📊 PANEL DE ESTADÍSTICAS Y MÉTRICAS", font=ctk.CTkFont(size=16, weight="bold"), text_color="#f8fafc")
        lbl_tit.pack(anchor="w", pady=(0, 15))

        stats = self.repo.estadisticas()
        if not stats:
            ctk.CTkLabel(frame, text="El inventario está vacío.", text_color="#94a3b8").pack(pady=20)
            return

        mv = stats["producto_mas_valioso"]
        grid_frame = ctk.CTkFrame(frame, fg_color="transparent")
        grid_frame.pack(fill="both", expand=True, pady=5)
        grid_frame.grid_columnconfigure((0, 1), weight=1, uniform="col")

        def crear_tarjeta(parent, row, col, icono, titulo, valor, color_valor="#38bdf8"):
            wrapper = ctk.CTkFrame(parent, fg_color="transparent")
            wrapper.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")
            wrapper.grid_columnconfigure(1, weight=1)
            ctk.CTkFrame(wrapper, width=4, fg_color=color_valor, corner_radius=2).grid(row=0, column=0, sticky="ns")
            card = ctk.CTkFrame(wrapper, fg_color=tema_actual["sidebar"], corner_radius=10)
            card.grid(row=0, column=1, sticky="nsew")
            ctk.CTkLabel(card, text=f"{icono}  {titulo}", font=ctk.CTkFont(size=12), text_color="#94a3b8").pack(anchor="w", padx=15, pady=(12, 2))
            ctk.CTkLabel(card, text=str(valor), font=ctk.CTkFont(size=20, weight="bold"), text_color=color_valor).pack(anchor="w", padx=15, pady=(0, 14))

        crear_tarjeta(grid_frame, 0, 0, "📦", "PRODUCTOS DISTINTOS", stats["total_productos"], "#f8fafc")
        crear_tarjeta(grid_frame, 0, 1, "🧮", "UNIDADES TOTALES", stats["total_unidades"], "#38bdf8")
        crear_tarjeta(grid_frame, 1, 0, "💰", "VALOR TOTAL", f"{stats['valor_total']:.2f}€", tema_actual["activo"])
        crear_tarjeta(grid_frame, 1, 1, "🏷️", "PRECIO MEDIO", f"{stats['precio_medio']:.2f}€", "#34d399")
        crear_tarjeta(grid_frame, 2, 0, "🟡", "STOCK BAJO", stats["bajo_stock"], "#ef4444" if stats["bajo_stock"] > 0 else "#34d399")
        crear_tarjeta(grid_frame, 2, 1, "🔴", "SIN STOCK", stats["sin_stock"], "#ef4444" if stats["sin_stock"] > 0 else "#34d399")

        wrapper_mv = ctk.CTkFrame(grid_frame, fg_color="transparent")
        wrapper_mv.grid(row=3, column=0, columnspan=2, padx=8, pady=8, sticky="nsew")
        wrapper_mv.grid_columnconfigure(1, weight=1)
        ctk.CTkFrame(wrapper_mv, width=4, fg_color="#eab308", corner_radius=2).grid(row=0, column=0, sticky="ns")
        card_mv = ctk.CTkFrame(wrapper_mv, fg_color=tema_actual["sidebar"], corner_radius=10)
        card_mv.grid(row=0, column=1, sticky="nsew")
        ctk.CTkLabel(card_mv, text="⭐ PRODUCTO MÁS VALIOSO", font=ctk.CTkFont(size=12), text_color="#94a3b8").pack(anchor="w", padx=15, pady=(12, 2))
        texto_mv = f"{mv.nombre} — {mv.valor_total:.2f}€ en total ({mv.cantidad} uds. a {mv.precio:.2f}€ c/u)"
        ctk.CTkLabel(card_mv, text=texto_mv, font=ctk.CTkFont(size=14, weight="bold"), text_color="#eab308").pack(anchor="w", padx=15, pady=(0, 14))

    def accion_exportar(self):
        if not self._verificar_permiso("exportar"):
            return
        if not self.repo.esta_vacio():
            self.repo.exportar_csv()
            self.mostrar_toast("Inventario exportado a CSV", "exito")

    def accion_importar(self):
        if not self._verificar_permiso("importar"):
            return
        ruta = self._pedir_entrada("Importar CSV", "Ruta del archivo CSV:")
        if ruta is not None and ruta.strip():
            self.repo.importar_csv(ruta.strip())
            self.mostrar_toast("Importación completada", "exito")
            self.renderizar_vista_actual()

    def accion_deshacer(self):
        if self.repo.puede_deshacer():
            tipo = self.repo.deshacer()
            self.mostrar_toast(f"Acción deshecha: {tipo}", "info")
            self.renderizar_vista_actual()
        else:
            messagebox.showwarning("Aviso", "No hay acciones para deshacer.")

    def accion_guardar(self):
        self.repo.guardar()
        self._guardar_preferencias()
        self.mostrar_toast("¡Cambios guardados correctamente!", "exito")

    def salir_aplicacion(self):
        if self._confirmar("Salir", "¿Seguro que quieres salir de AMB Stock?\n\nSe guardará todo automáticamente.", texto_si="Sí, salir", texto_no="Cancelar"):
            self.repo.guardar()
            self._guardar_preferencias()
            self.destroy()

    def vista_historial(self):
        self._limpiar_panel_principal()
        frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        frame.pack(padx=20, pady=20, fill="both", expand=True)
        txt = ctk.CTkTextbox(frame, font=ctk.CTkFont(family="monospace"), fg_color="#0f172a", text_color="#38bdf8")
        txt.pack(fill="both", expand=True)
        lineas = self.repo.leer_historial(50)
        txt.insert("0.0", "".join(lineas) if lineas else "Sin historial.")


# ============================================================
# SISTEMA DE USUARIOS Y LOGIN (COMPLETO Y CORREGIDO)
# ============================================================

import hashlib
import datetime

USERS_FILE = "usuarios.json"
LOG_FILE = "auditoria.log"


class SistemaUsuarios:
    def __init__(self):
        self.usuario_actual = None
        self._cargar_usuarios()

    def _cargar_usuarios(self):
        if os.path.exists(USERS_FILE):
            try:
                with open(USERS_FILE, "r", encoding="utf-8") as f:
                    self.usuarios = json.load(f)
            except:
                self.usuarios = {}
        else:
            self.usuarios = {}

    def _guardar_usuarios(self):
        try:
            with open(USERS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.usuarios, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Error guardando usuarios: {e}")

    def hay_usuarios(self):
        return len(self.usuarios) > 0

    def hay_admin(self):
        for data in self.usuarios.values():
            if data.get("rol") == "admin":
                return True
        return False

    def _hash(self, pwd):
        return hashlib.sha256(pwd.encode()).hexdigest()

    def login(self, usuario, password):
        if usuario in self.usuarios:
            if self.usuarios[usuario]["password"] == self._hash(password):
                self.usuario_actual = usuario
                self.usuarios[usuario]["ultimo_acceso"] = datetime.datetime.now().isoformat()
                self._guardar_usuarios()
                self._log(f"Login exitoso: {usuario} ({self.usuarios[usuario]['rol']})")
                return True, "Login exitoso"
            else:
                self._log(f"Login fallido: {usuario}")
                return False, "❌ Contraseña incorrecta"
        else:
            self._log(f"Login usuario inexistente: {usuario}")
            return False, "❌ Usuario no encontrado"

    def logout(self):
        if self.usuario_actual:
            self._log(f"Logout: {self.usuario_actual}")
            user = self.usuario_actual
            self.usuario_actual = None
            return user
        return None

    def cambiar_password(self, usuario, actual, nueva):
        if usuario not in self.usuarios:
            return False, "Usuario no encontrado"
        if self.usuarios[usuario]["password"] != self._hash(actual):
            return False, "Contraseña actual incorrecta"
        if len(nueva) < 4:
            return False, "La nueva contraseña debe tener al menos 4 caracteres"
        self.usuarios[usuario]["password"] = self._hash(nueva)
        self._guardar_usuarios()
        self._log(f"Cambio de contraseña: {usuario}")
        return True, "✅ Contraseña actualizada"

    def crear_usuario(self, usuario, password, rol, nombre):
        if usuario in self.usuarios:
            return False, "❌ El usuario ya existe"
        if len(usuario) < 3:
            return False, "❌ El usuario debe tener al menos 3 caracteres"
        if len(password) < 4:
            return False, "❌ La contraseña debe tener al menos 4 caracteres"
        if rol not in ["admin", "editor", "visitante"]:
            return False, "❌ Rol no válido"
        if not self.hay_usuarios() and rol != "admin":
            return False, "❌ El primer usuario debe ser administrador"

        self.usuarios[usuario] = {
            "password": self._hash(password),
            "rol": rol,
            "nombre": nombre if nombre else usuario,
            "creado": datetime.datetime.now().isoformat(),
            "ultimo_acceso": None
        }
        self._guardar_usuarios()
        self._log(f"Usuario creado: {usuario} ({rol}) por {self.usuario_actual or 'sistema'}")
        return True, f"✅ Usuario {usuario} creado correctamente"

    def eliminar_usuario(self, usuario):
        if usuario not in self.usuarios:
            return False, "❌ Usuario no encontrado"
        if self.usuarios[usuario]["rol"] == "admin":
            admins = [u for u, d in self.usuarios.items() if d.get("rol") == "admin"]
            if len(admins) <= 1:
                return False, "❌ No se puede eliminar el único administrador"
        if usuario == self.usuario_actual:
            return False, "❌ No puedes eliminar tu propio usuario"
        del self.usuarios[usuario]
        self._guardar_usuarios()
        self._log(f"Usuario eliminado: {usuario} por {self.usuario_actual}")
        return True, f"✅ Usuario {usuario} eliminado"

    def obtener_usuarios(self):
        return {u: {"rol": d["rol"], "nombre": d["nombre"], "creado": d["creado"], "ultimo_acceso": d["ultimo_acceso"]}
                for u, d in self.usuarios.items()}

    def tiene_permiso(self, permiso):
        if not self.usuario_actual:
            return False
        rol = self.usuarios[self.usuario_actual]["rol"]
        permisos = {
            "admin": ["ver", "crear", "editar", "eliminar", "gestionar_usuarios", "importar", "exportar", "cambiar_rol"],
            "editor": ["ver", "crear", "editar", "importar", "exportar"],
            "visitante": ["ver"]
        }
        return permiso in permisos.get(rol, [])

    def cambiar_rol(self, usuario, nuevo_rol):
        if not self.tiene_permiso("cambiar_rol"):
            return False, "❌ No tienes permisos para cambiar roles"
        if usuario not in self.usuarios:
            return False, "❌ Usuario no encontrado"
        if usuario == self.usuario_actual:
            return False, "❌ No puedes cambiar tu propio rol"
        if self.usuarios[usuario]["rol"] == "admin" and nuevo_rol != "admin":
            admins = [u for u, d in self.usuarios.items() if d.get("rol") == "admin"]
            if len(admins) <= 1:
                return False, "❌ No se puede quitar el rol admin al único administrador"
        self.usuarios[usuario]["rol"] = nuevo_rol
        self._guardar_usuarios()
        self._log(f"Rol cambiado: {usuario} a {nuevo_rol} por {self.usuario_actual}")
        return True, f"✅ Rol de {usuario} cambiado a {nuevo_rol}"

    def _log(self, mensaje):
        try:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {mensaje}\n")
        except:
            pass

    def leer_auditoria(self, lineas=100):
        try:
            if not os.path.exists(LOG_FILE):
                return ["No hay registros."]
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                return f.readlines()[-lineas:]
        except:
            return ["Error al leer auditoría."]


class DialogoCrearAdmin(ctk.CTkToplevel):
    def __init__(self, parent, sistema):
        super().__init__(parent)
        self.sistema = sistema
        self.resultado = False
        self.title("👑 Configuración Inicial")
        self.geometry("450x550")
        self.resizable(False, False)
        self.configure(fg_color="#1e293b")
        self.attributes("-topmost", True)

        if os.path.exists(RUTA_LOGO):
            try:
                img = Image.open(RUTA_LOGO)
                logo = ctk.CTkImage(light_image=img, dark_image=img, size=(80, 80))
                ctk.CTkLabel(self, text="", image=logo).pack(pady=(30, 10))
            except:
                pass

        ctk.CTkLabel(self, text="👑 Configuración Inicial", font=ctk.CTkFont(size=22, weight="bold"),
                     text_color="#f8fafc").pack(pady=(0, 5))
        ctk.CTkLabel(self, text="Crea el usuario administrador para comenzar",
                     font=ctk.CTkFont(size=13), text_color="#94a3b8").pack(pady=(0, 20))

        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(padx=40, fill="x")

        ctk.CTkLabel(frame, text="👤 Usuario", font=ctk.CTkFont(size=12), text_color="#94a3b8").pack(anchor="w", pady=(0, 5))
        self.entry_usuario = ctk.CTkEntry(frame, placeholder_text="mínimo 3 caracteres", height=40)
        self.entry_usuario.pack(fill="x", pady=(0, 15))
        self.entry_usuario.focus()

        ctk.CTkLabel(frame, text="👤 Nombre completo", font=ctk.CTkFont(size=12), text_color="#94a3b8").pack(anchor="w", pady=(0, 5))
        self.entry_nombre = ctk.CTkEntry(frame, placeholder_text="opcional", height=40)
        self.entry_nombre.pack(fill="x", pady=(0, 15))

        ctk.CTkLabel(frame, text="🔑 Contraseña", font=ctk.CTkFont(size=12), text_color="#94a3b8").pack(anchor="w", pady=(0, 5))
        self.entry_pass = ctk.CTkEntry(frame, placeholder_text="mínimo 4 caracteres", show="●", height=40)
        self.entry_pass.pack(fill="x", pady=(0, 15))

        ctk.CTkLabel(frame, text="🔑 Confirmar contraseña", font=ctk.CTkFont(size=12), text_color="#94a3b8").pack(anchor="w", pady=(0, 5))
        self.entry_confirm = ctk.CTkEntry(frame, placeholder_text="repite la contraseña", show="●", height=40)
        self.entry_confirm.pack(fill="x", pady=(0, 20))

        info = ctk.CTkFrame(self, fg_color="#0f172a", corner_radius=8)
        info.pack(padx=40, pady=(10, 20), fill="x")
        ctk.CTkLabel(info, text="ℹ️ Este usuario tendrá permisos de administrador",
                     font=ctk.CTkFont(size=11), text_color="#94a3b8").pack(anchor="w", padx=15, pady=(10, 5))
        ctk.CTkLabel(info, text="Podrás crear más usuarios desde la aplicación",
                     font=ctk.CTkFont(size=11), text_color="#64748b").pack(anchor="w", padx=15, pady=(0, 10))

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=(10, 20))
        self.btn_crear = ctk.CTkButton(btn_frame, text="✅ Crear Administrador", width=200, height=45,
                                       font=ctk.CTkFont(size=14, weight="bold"), command=self._crear)
        self.btn_crear.pack(pady=5)

        self.entry_usuario.bind("<Return>", lambda e: self.entry_nombre.focus())
        self.entry_nombre.bind("<Return>", lambda e: self.entry_pass.focus())
        self.entry_pass.bind("<Return>", lambda e: self.entry_confirm.focus())
        self.entry_confirm.bind("<Return>", lambda e: self._crear())
        self.bind("<Escape>", lambda e: self._cancelar())
        self.protocol("WM_DELETE_WINDOW", self._cancelar)
        self._centrar()
        self.after(20, lambda: self.grab_set())

    def _centrar(self):
        self.withdraw()
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 450) // 2
        y = (self.winfo_screenheight() - 550) // 2
        self.geometry(f"450x550+{max(x,0)}+{max(y,0)}")
        self.deiconify()

    def _crear(self):
        usuario = self.entry_usuario.get().strip()
        nombre = self.entry_nombre.get().strip()
        passw = self.entry_pass.get()
        confirm = self.entry_confirm.get()

        if not usuario or len(usuario) < 3:
            messagebox.showwarning("Aviso", "El usuario debe tener al menos 3 caracteres.", parent=self)
            return
        if not nombre:
            nombre = usuario
        if not passw or len(passw) < 4:
            messagebox.showwarning("Aviso", "La contraseña debe tener al menos 4 caracteres.", parent=self)
            return
        if passw != confirm:
            messagebox.showerror("Error", "Las contraseñas no coinciden.", parent=self)
            return
        if self.sistema.hay_admin():
            messagebox.showerror("Error", "Ya existe un administrador.", parent=self)
            self.destroy()
            return

        self.btn_crear.configure(state="disabled", text="⏳ Creando...")
        self.update()
        ok, msg = self.sistema.crear_usuario(usuario, passw, "admin", nombre)
        if ok:
            messagebox.showinfo("Éxito", f"¡Administrador '{usuario}' creado!\n\nAhora inicia sesión.", parent=self)
            self.resultado = True
            self.grab_release()
            self.destroy()
        else:
            messagebox.showerror("Error", msg, parent=self)
            self.btn_crear.configure(state="normal", text="✅ Crear Administrador")

    def _cancelar(self):
        self.resultado = False
        self.grab_release()
        self.destroy()


class DialogoLogin(ctk.CTkToplevel):
    def __init__(self, parent, sistema):
        super().__init__(parent)
        self.sistema = sistema
        self.resultado = False
        self.title("🔐 Inicio de Sesión - AMB Stock")
        self.geometry("400x500")
        self.resizable(False, False)
        self.configure(fg_color="#1e293b")
        self.attributes("-topmost", True)

        if os.path.exists(RUTA_LOGO):
            try:
                img = Image.open(RUTA_LOGO)
                logo = ctk.CTkImage(light_image=img, dark_image=img, size=(80, 80))
                ctk.CTkLabel(self, text="", image=logo).pack(pady=(30, 10))
            except:
                pass

        ctk.CTkLabel(self, text="AMB STOCK", font=ctk.CTkFont(size=24, weight="bold"),
                     text_color="#f8fafc").pack(pady=(0, 5))
        ctk.CTkLabel(self, text="Sistema de Gestión de Inventario",
                     font=ctk.CTkFont(size=12), text_color="#94a3b8").pack(pady=(0, 20))

        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(padx=40, fill="x")

        ctk.CTkLabel(frame, text="👤 Usuario", font=ctk.CTkFont(size=12), text_color="#94a3b8").pack(anchor="w", pady=(0, 5))
        self.entry_user = ctk.CTkEntry(frame, placeholder_text="Introduce tu usuario", height=40)
        self.entry_user.pack(fill="x", pady=(0, 15))
        self.entry_user.focus()

        ctk.CTkLabel(frame, text="🔑 Contraseña", font=ctk.CTkFont(size=12), text_color="#94a3b8").pack(anchor="w", pady=(0, 5))
        self.entry_pass = ctk.CTkEntry(frame, placeholder_text="Introduce tu contraseña", show="●", height=40)
        self.entry_pass.pack(fill="x", pady=(0, 20))

        self.btn_login = ctk.CTkButton(frame, text="🔓 Iniciar Sesión", height=45,
                                       font=ctk.CTkFont(size=14, weight="bold"), command=self._login)
        self.btn_login.pack(fill="x", pady=(0, 10))

        ctk.CTkFrame(frame, height=1, fg_color="#334155").pack(fill="x", pady=10)

        self.btn_crear = ctk.CTkButton(frame, text="📝 Crear nueva cuenta", height=35,
                                       font=ctk.CTkFont(size=12), fg_color="transparent",
                                       border_width=1, border_color="#334155", hover_color="#334155",
                                       text_color="#94a3b8", command=self._mostrar_crear)
        self.btn_crear.pack(fill="x", pady=(0, 5))

        info = ctk.CTkFrame(self, fg_color="#0f172a", corner_radius=8)
        info.pack(padx=40, pady=(15, 20), fill="x")
        ctk.CTkLabel(info, text="💡 ¿Primera vez?", font=ctk.CTkFont(size=11, weight="bold"),
                     text_color="#94a3b8").pack(anchor="w", padx=15, pady=(8, 2))
        ctk.CTkLabel(info, text="Si no tienes cuenta, haz clic en 'Crear nueva cuenta'",
                     font=ctk.CTkFont(size=11), text_color="#64748b").pack(anchor="w", padx=15, pady=(0, 8))

        self.entry_pass.bind("<Return>", lambda e: self._login())
        self.entry_user.bind("<Return>", lambda e: self.entry_pass.focus())
        self.bind("<Escape>", lambda e: self._cancelar())
        self.protocol("WM_DELETE_WINDOW", self._cancelar)
        self._centrar()
        self.after(20, lambda: self.grab_set())

    def _centrar(self):
        self.withdraw()
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 400) // 2
        y = (self.winfo_screenheight() - 500) // 2
        self.geometry(f"400x500+{max(x,0)}+{max(y,0)}")
        self.deiconify()

    def _login(self):
        user = self.entry_user.get().strip()
        pwd = self.entry_pass.get()
        if not user or not pwd:
            messagebox.showwarning("Aviso", "Completa todos los campos.", parent=self)
            return
        self.btn_login.configure(state="disabled", text="⏳ Verificando...")
        self.update()
        ok, msg = self.sistema.login(user, pwd)
        if ok:
            self.resultado = True
            self.grab_release()
            self.destroy()
        else:
            messagebox.showerror("Error de Login", msg, parent=self)
            self.entry_pass.delete(0, tk.END)
            self.entry_pass.focus()
            self.btn_login.configure(state="normal", text="🔓 Iniciar Sesión")
            self.lift()

    def _mostrar_crear(self):
        if not self.sistema.hay_admin():
            messagebox.showwarning("Aviso", "No hay administradores. Contacta con el administrador.", parent=self)
            return

        self.grab_release()
        self.btn_login.configure(state="disabled")
        self.btn_crear.configure(state="disabled")

        dlg = DialogoCrearUsuario(self, self.sistema)
        self.wait_window(dlg)

        self.btn_login.configure(state="normal")
        self.btn_crear.configure(state="normal")
        self.grab_set()
        self.lift()
        self.focus_force()

    def _cancelar(self):
        self.resultado = False
        self.grab_release()
        self.destroy()


class DialogoCrearUsuario(ctk.CTkToplevel):
    def __init__(self, parent, sistema):
        super().__init__(parent)
        self.sistema = sistema
        self.title("📝 Crear Nueva Cuenta")
        self.geometry("500x650")
        self.minsize(400, 500)  # Tamaño mínimo redimensionable
        self.configure(fg_color="#1e293b")
        self.attributes("-topmost", True)

        # Configurar distribución con grid
        self.grid_rowconfigure(0, weight=0)  # logo
        self.grid_rowconfigure(1, weight=0)  # título
        self.grid_rowconfigure(2, weight=0)  # subtítulo
        self.grid_rowconfigure(3, weight=1)  # campos (se expande)
        self.grid_rowconfigure(4, weight=0)  # botones (fijo)
        self.grid_columnconfigure(0, weight=1)

        # Logo (si existe)
        if os.path.exists(RUTA_LOGO):
            try:
                img = Image.open(RUTA_LOGO)
                logo = ctk.CTkImage(light_image=img, dark_image=img, size=(50, 50))
                ctk.CTkLabel(self, text="", image=logo).grid(row=0, column=0, pady=(15, 5))
            except:
                pass

        ctk.CTkLabel(self, text="📝 Crear Nueva Cuenta", font=ctk.CTkFont(size=20, weight="bold"),
                     text_color="#f8fafc").grid(row=1, column=0, pady=(5, 5))
        ctk.CTkLabel(self, text="Completa los datos para crear tu cuenta",
                     font=ctk.CTkFont(size=13), text_color="#94a3b8").grid(row=2, column=0, pady=(0, 15))

        # Frame contenedor de los campos (con scroll)
        frame_campos = ctk.CTkFrame(self, fg_color="transparent")
        frame_campos.grid(row=3, column=0, padx=40, pady=(0, 10), sticky="nsew")
        frame_campos.grid_columnconfigure(0, weight=1)

        # ScrollableFrame para que siempre se puedan ver todos los campos
        scroll_frame = ctk.CTkScrollableFrame(frame_campos, fg_color="transparent")
        scroll_frame.pack(fill="both", expand=True)

        # --- Campos dentro del scroll ---
        ctk.CTkLabel(scroll_frame, text="👤 Usuario", font=ctk.CTkFont(size=12), text_color="#94a3b8").pack(anchor="w", pady=(0, 5))
        self.entry_user = ctk.CTkEntry(scroll_frame, placeholder_text="mínimo 3 caracteres", height=38)
        self.entry_user.pack(fill="x", pady=(0, 10))
        self.entry_user.focus()

        ctk.CTkLabel(scroll_frame, text="👤 Nombre completo", font=ctk.CTkFont(size=12), text_color="#94a3b8").pack(anchor="w", pady=(0, 5))
        self.entry_name = ctk.CTkEntry(scroll_frame, placeholder_text="opcional", height=38)
        self.entry_name.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(scroll_frame, text="🔑 Contraseña", font=ctk.CTkFont(size=12), text_color="#94a3b8").pack(anchor="w", pady=(0, 5))
        self.entry_pass = ctk.CTkEntry(scroll_frame, placeholder_text="mínimo 4 caracteres", show="●", height=38)
        self.entry_pass.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(scroll_frame, text="🔑 Confirmar contraseña", font=ctk.CTkFont(size=12), text_color="#94a3b8").pack(anchor="w", pady=(0, 5))
        self.entry_confirm = ctk.CTkEntry(scroll_frame, placeholder_text="repite la contraseña", show="●", height=38)
        self.entry_confirm.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(scroll_frame, text="🎯 Selecciona tu rol", font=ctk.CTkFont(size=12), text_color="#94a3b8").pack(anchor="w", pady=(5, 5))
        self.combo_rol = ctk.CTkOptionMenu(scroll_frame, values=["editor", "visitante"], height=38)
        self.combo_rol.pack(fill="x", pady=(0, 10))

        info = ctk.CTkFrame(scroll_frame, fg_color="#0f172a", corner_radius=6)
        info.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(info, text="📌 Editor: Puede ver, crear, editar e importar",
                     font=ctk.CTkFont(size=10), text_color="#94a3b8").pack(anchor="w", padx=10, pady=3)
        ctk.CTkLabel(info, text="👀 Visitante: Solo puede ver el inventario",
                     font=ctk.CTkFont(size=10), text_color="#94a3b8").pack(anchor="w", padx=10, pady=3)

        # --- Botones fijos al final ---
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=4, column=0, pady=20, sticky="ew")
        btn_frame.grid_columnconfigure(0, weight=1)
        btn_frame.grid_columnconfigure(1, weight=1)

        self.btn_crear = ctk.CTkButton(btn_frame, text="✅ Crear Cuenta", command=self._crear, width=150, height=40)
        self.btn_crear.grid(row=0, column=0, padx=10)

        ctk.CTkButton(btn_frame, text="❌ Cancelar", command=self.destroy, width=150, height=40,
                      fg_color="transparent", border_width=1, border_color="#334155", hover_color="#334155").grid(row=0, column=1, padx=10)

        self.bind("<Escape>", lambda e: self.destroy())

        # Centrar y activar
        self._centrar()
        self.after(20, self._activar)

    def _activar(self):
        self.grab_set()
        self.lift()
        self.focus_force()

    def _centrar(self):
        self.withdraw()
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 500) // 2
        y = (self.winfo_screenheight() - 650) // 2
        self.geometry(f"500x650+{max(x,0)}+{max(y,0)}")
        self.deiconify()

    def _crear(self):
        user = self.entry_user.get().strip()
        name = self.entry_name.get().strip()
        pwd = self.entry_pass.get()
        confirm = self.entry_confirm.get()
        rol = self.combo_rol.get()

        if not user or len(user) < 3:
            messagebox.showwarning("Aviso", "El usuario debe tener al menos 3 caracteres.", parent=self)
            return
        if not name:
            name = user
        if not pwd or len(pwd) < 4:
            messagebox.showwarning("Aviso", "La contraseña debe tener al menos 4 caracteres.", parent=self)
            return
        if pwd != confirm:
            messagebox.showerror("Error", "Las contraseñas no coinciden.", parent=self)
            return

        self.btn_crear.configure(state="disabled", text="⏳ Creando...")
        self.update()
        ok, msg = self.sistema.crear_usuario(user, pwd, rol, name)
        if ok:
            messagebox.showinfo("Éxito", f"¡Usuario '{user}' creado!\n\nAhora inicia sesión.", parent=self)
            self.grab_release()
            self.destroy()
        else:
            messagebox.showerror("Error", msg, parent=self)
            self.btn_crear.configure(state="normal", text="✅ Crear Cuenta")


class DialogoGestionUsuarios(ctk.CTkToplevel):
    def __init__(self, parent, sistema):
        super().__init__(parent)
        self.sistema = sistema
        self.title("👥 Gestión de Usuarios")
        self.geometry("750x500")
        self.resizable(True, True)
        self.minsize(600, 400)
        self.configure(fg_color="#1e293b")
        self.attributes("-topmost", True)

        ctk.CTkLabel(self, text="👥 Gestión de Usuarios", font=ctk.CTkFont(size=20, weight="bold"),
                     text_color="#f8fafc").pack(pady=(15, 5))
        ctk.CTkLabel(self, text="Administra los usuarios del sistema",
                     font=ctk.CTkFont(size=13), text_color="#94a3b8").pack(pady=(0, 15))

        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(padx=20, pady=10, fill="both", expand=True)

        self.tree = ttk.Treeview(frame, columns=("Nombre", "Rol", "Creado", "Último acceso"), show="headings", height=12)
        self.tree.heading("Nombre", text="Nombre")
        self.tree.heading("Rol", text="Rol")
        self.tree.heading("Creado", text="Creado")
        self.tree.heading("Último acceso", text="Último acceso")
        self.tree.column("Nombre", width=150)
        self.tree.column("Rol", width=100)
        self.tree.column("Creado", width=180)
        self.tree.column("Último acceso", width=180)

        scroll = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=15)

        self.btn_cambiar_rol = ctk.CTkButton(btn_frame, text="🔄 Cambiar Rol", command=self._cambiar_rol, width=150)
        self.btn_cambiar_rol.pack(side="left", padx=5)

        self.btn_eliminar = ctk.CTkButton(btn_frame, text="🗑️ Eliminar Usuario", command=self._eliminar_usuario, width=150,
                                          fg_color="#ef4444", hover_color="#b91c1c")
        self.btn_eliminar.pack(side="left", padx=5)

        ctk.CTkButton(btn_frame, text="❌ Cerrar", command=self.destroy, width=120,
                      fg_color="transparent", border_width=1, border_color="#334155").pack(side="left", padx=5)

        self.bind("<Escape>", lambda e: self.destroy())

        self._cargar_usuarios()
        self._centrar()
        self.after(20, lambda: self.grab_set())

    def _centrar(self):
        self.withdraw()
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 750) // 2
        y = (self.winfo_screenheight() - 500) // 2
        self.geometry(f"750x500+{max(x,0)}+{max(y,0)}")
        self.deiconify()

    def _cargar_usuarios(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        usuarios = self.sistema.obtener_usuarios()
        for user, data in usuarios.items():
            creado = data["creado"][:16] if data["creado"] else "N/A"
            ultimo = data["ultimo_acceso"][:16] if data["ultimo_acceso"] else "Nunca"
            self.tree.insert("", "end", values=(user, data["nombre"], data["rol"], creado, ultimo), tags=(user,))

    def _cambiar_rol(self):
        seleccion = self.tree.selection()
        if not seleccion:
            messagebox.showwarning("Aviso", "Selecciona un usuario.", parent=self)
            return
        user = self.tree.item(seleccion[0], "tags")[0]
        if user == self.sistema.usuario_actual:
            messagebox.showwarning("Aviso", "No puedes cambiar tu propio rol.", parent=self)
            return

        roles = ["admin", "editor", "visitante"]
        dlg = ctk.CTkToplevel(self)
        dlg.title("Cambiar Rol")
        dlg.geometry("300x150")
        dlg.configure(fg_color="#1e293b")
        dlg.attributes("-topmost", True)

        ctk.CTkLabel(dlg, text=f"Usuario: {user}", font=ctk.CTkFont(size=12), text_color="#f8fafc").pack(pady=(15, 5))
        combo = ctk.CTkOptionMenu(dlg, values=roles, height=35)
        combo.pack(pady=10)
        combo.set(self.tree.item(seleccion[0], "values")[2])

        def aplicar():
            nuevo_rol = combo.get()
            ok, msg = self.sistema.cambiar_rol(user, nuevo_rol)
            if ok:
                messagebox.showinfo("Éxito", msg, parent=self)
                dlg.destroy()
                self._cargar_usuarios()
            else:
                messagebox.showerror("Error", msg, parent=self)

        ctk.CTkButton(dlg, text="Aplicar", command=aplicar, width=100).pack(pady=10)
        dlg.bind("<Escape>", lambda e: dlg.destroy())
        dlg.transient(self)
        dlg.grab_set()
        self.wait_window(dlg)

    def _eliminar_usuario(self):
        seleccion = self.tree.selection()
        if not seleccion:
            messagebox.showwarning("Aviso", "Selecciona un usuario.", parent=self)
            return
        user = self.tree.item(seleccion[0], "tags")[0]
        if user == self.sistema.usuario_actual:
            messagebox.showwarning("Aviso", "No puedes eliminarte a ti mismo.", parent=self)
            return
        if not messagebox.askyesno("Confirmar", f"¿Eliminar al usuario '{user}'?", parent=self):
            return
        ok, msg = self.sistema.eliminar_usuario(user)
        if ok:
            messagebox.showinfo("Éxito", msg, parent=self)
            self._cargar_usuarios()
        else:
            messagebox.showerror("Error", msg, parent=self)


class DialogoAuditoria(ctk.CTkToplevel):
    def __init__(self, parent, sistema):
        super().__init__(parent)
        self.sistema = sistema
        self.title("📋 Auditoría")
        self.geometry("800x500")
        self.resizable(True, True)
        self.minsize(600, 300)
        self.configure(fg_color="#1e293b")
        self.attributes("-topmost", True)

        ctk.CTkLabel(self, text="📋 Registro de Auditoría", font=ctk.CTkFont(size=20, weight="bold"),
                     text_color="#f8fafc").pack(pady=(15, 5))
        ctk.CTkLabel(self, text="Últimas acciones registradas en el sistema",
                     font=ctk.CTkFont(size=13), text_color="#94a3b8").pack(pady=(0, 10))

        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(padx=20, pady=10, fill="both", expand=True)

        self.txt_log = ctk.CTkTextbox(frame, font=ctk.CTkFont(family="Consolas", size=11),
                                      fg_color="#0f172a", text_color="#38bdf8", wrap="none")
        self.txt_log.pack(side="left", fill="both", expand=True)

        scroll_y = ctk.CTkScrollbar(frame, orientation="vertical", command=self.txt_log.yview)
        scroll_y.pack(side="right", fill="y")
        self.txt_log.configure(yscrollcommand=scroll_y.set)

        lineas = self.sistema.leer_auditoria(100)
        self.txt_log.insert("0.0", "".join(lineas) if lineas else "No hay registros.")
        self.txt_log.configure(state="disabled")

        ctk.CTkButton(self, text="Cerrar", command=self.destroy, width=120,
                      fg_color="transparent", border_width=1, border_color="#334155").pack(pady=15)

        self.bind("<Escape>", lambda e: self.destroy())

        self._centrar()
        self.after(20, lambda: self.grab_set())

    def _centrar(self):
        self.withdraw()
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 800) // 2
        y = (self.winfo_screenheight() - 500) // 2
        self.geometry(f"800x500+{max(x,0)}+{max(y,0)}")
        self.deiconify()


class DialogoCambiarPassword(ctk.CTkToplevel):
    def __init__(self, parent, sistema):
        super().__init__(parent)
        self.sistema = sistema
        self.title("🔑 Cambiar Contraseña")
        self.geometry("400x520")
        self.resizable(False, False)
        self.configure(fg_color="#1e293b")
        self.attributes("-topmost", True)

        ctk.CTkLabel(self, text="🔑 Cambiar Contraseña", font=ctk.CTkFont(size=20, weight="bold"),
                     text_color="#f8fafc").pack(pady=(20, 10))

        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(padx=30, fill="x", expand=True)

        ctk.CTkLabel(frame, text="Usuario actual:", font=ctk.CTkFont(size=12), text_color="#94a3b8").pack(anchor="w", pady=(0, 5))
        ctk.CTkLabel(frame, text=self.sistema.usuario_actual, font=ctk.CTkFont(size=13, weight="bold"),
                     text_color="#f8fafc").pack(anchor="w", pady=(0, 10))

        ctk.CTkLabel(frame, text="Contraseña actual:", font=ctk.CTkFont(size=12), text_color="#94a3b8").pack(anchor="w", pady=(0, 5))
        self.entry_old = ctk.CTkEntry(frame, show="●", height=35)
        self.entry_old.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(frame, text="Nueva contraseña:", font=ctk.CTkFont(size=12), text_color="#94a3b8").pack(anchor="w", pady=(0, 5))
        self.entry_new = ctk.CTkEntry(frame, show="●", height=35)
        self.entry_new.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(frame, text="Confirmar nueva:", font=ctk.CTkFont(size=12), text_color="#94a3b8").pack(anchor="w", pady=(0, 5))
        self.entry_confirm = ctk.CTkEntry(frame, show="●", height=35)
        self.entry_confirm.pack(fill="x", pady=(0, 10))

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=20)
        ctk.CTkButton(btn_frame, text="✅ Cambiar", command=self._cambiar, width=140, height=38).pack(side="left", padx=8)
        ctk.CTkButton(btn_frame, text="Cancelar", command=self.destroy, width=140, height=38,
                      fg_color="transparent", border_width=1, border_color="#334155").pack(side="left", padx=8)

        self.entry_old.bind("<Return>", lambda e: self.entry_new.focus())
        self.entry_new.bind("<Return>", lambda e: self.entry_confirm.focus())
        self.entry_confirm.bind("<Return>", lambda e: self._cambiar())
        self.bind("<Escape>", lambda e: self.destroy())
        self._centrar()
        self.after(20, lambda: self.grab_set())

    def _centrar(self):
        self.withdraw()
        self.update_idletasks()
        ancho = 400
        alto = max(520, self.winfo_reqheight() + 20)
        x = (self.winfo_screenwidth() - ancho) // 2
        y = (self.winfo_screenheight() - alto) // 2
        self.geometry(f"{ancho}x{alto}+{max(x,0)}+{max(y,0)}")
        self.deiconify()

    def _cambiar(self):
        old = self.entry_old.get()
        new = self.entry_new.get()
        confirm = self.entry_confirm.get()
        if not old or not new or not confirm:
            messagebox.showwarning("Aviso", "Completa todos los campos.", parent=self)
            return
        if new != confirm:
            messagebox.showerror("Error", "Las contraseñas nuevas no coinciden.", parent=self)
            return
        ok, msg = self.sistema.cambiar_password(self.sistema.usuario_actual, old, new)
        if ok:
            messagebox.showinfo("Éxito", msg, parent=self)
            self.destroy()
        else:
            messagebox.showerror("Error", msg, parent=self)


class MenuUsuarioPopup(ctk.CTkToplevel):
    """Pequeño menú desplegable sin bordes que aparece bajo el botón de
    usuario (arriba a la derecha). Se cierra al pulsar cualquier opción,
    al pulsar fuera de él o con Escape."""

    def __init__(self, parent, boton_anclaje, tema, opciones):
        super().__init__(parent)
        self._parent_ref = parent
        self._click_id = None

        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(fg_color=tema["borde"])

        contenedor = ctk.CTkFrame(
            self, fg_color=tema["sidebar"], corner_radius=10,
            border_width=1, border_color=tema["borde"]
        )
        contenedor.pack(fill="both", expand=True, padx=1, pady=1)

        for texto, comando in opciones:
            btn = ctk.CTkButton(
                contenedor, text=texto, command=lambda c=comando: self._ejecutar(c),
                anchor="w", fg_color="transparent", text_color="#e2e8f0",
                hover_color=tema["borde"], font=ctk.CTkFont(size=13),
                corner_radius=6, height=32, width=210
            )
            btn.pack(padx=6, pady=3, fill="x")

        self.update_idletasks()
        x = boton_anclaje.winfo_rootx() + boton_anclaje.winfo_width() - self.winfo_reqwidth()
        y = boton_anclaje.winfo_rooty() + boton_anclaje.winfo_height() + 6
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")

        self.bind("<Escape>", lambda e: self.destroy())
        self.bind("<Destroy>", self._al_destruir)
        self._click_id = parent.bind("<Button-1>", self._al_clicar_fuera, add="+")
        self.after(30, self._intentar_foco)

    def _intentar_foco(self):
        try:
            if self.winfo_exists():
                self.focus_force()
        except tk.TclError:
            pass

    def _al_clicar_fuera(self, event):
        try:
            if not self.winfo_exists():
                return
            wx, wy = self.winfo_rootx(), self.winfo_rooty()
            ww, wh = self.winfo_width(), self.winfo_height()
            if not (wx <= event.x_root <= wx + ww and wy <= event.y_root <= wy + wh):
                self.destroy()
        except tk.TclError:
            pass

    def _al_destruir(self, event):
        if event.widget is not self:
            return
        if self._click_id is not None:
            try:
                self._parent_ref.unbind("<Button-1>", self._click_id)
            except Exception:
                pass
            self._click_id = None
        # Al cerrarse el menú (por click fuera, Escape o al elegir una
        # opción), devolvemos el foco de teclado a la ventana principal
        # para que los atajos (Ctrl+N, Ctrl+M, etc.) vuelvan a funcionar
        # sin necesidad de hacer clic manualmente en un botón.
        try:
            self._parent_ref.focus_force()
        except Exception:
            pass

    def _ejecutar(self, comando):
        self.destroy()
        self._parent_ref.after(10, comando)


class AppLauncher:
    def __init__(self):
        self.sistema = SistemaUsuarios()
        self._iniciar()

    def _iniciar(self):
        if not self.sistema.hay_usuarios():
            self._mostrar_wizard_admin()
        else:
            self._mostrar_login()

    def _mostrar_wizard_admin(self):
        root = ctk.CTk()
        root.withdraw()
        _registrar_atajo_seleccionar_todo(root)
        d = DialogoCrearAdmin(root, self.sistema)
        root.wait_window(d)
        if d.resultado:
            root.destroy()
            self._mostrar_login()
        else:
            root.destroy()
            import sys
            sys.exit()

    def _mostrar_login(self):
        root = ctk.CTk()
        root.withdraw()
        _registrar_atajo_seleccionar_todo(root)
        d = DialogoLogin(root, self.sistema)
        root.wait_window(d)
        if d.resultado:
            root.destroy()
            self._lanzar_app()
        else:
            root.destroy()
            import sys
            sys.exit()

    def _lanzar_app(self):
        app = InventarioApp()
        app.sistema_usuarios = self.sistema
        self._inyectar_opciones(app)
        app.mainloop()

    def _inyectar_opciones(self, app):
        user_info = self.sistema.usuarios[self.sistema.usuario_actual]
        rol_emoji = "👑" if user_info["rol"] == "admin" else "✏️" if user_info["rol"] == "editor" else "👀"

        if hasattr(app, 'pie_sidebar'):
            app.pie_sidebar.configure(text="AMB Solucions")

        # Opciones del menú desplegable de usuario (arriba a la derecha).
        # "Cambiar contraseña" y "Cerrar sesión" están siempre disponibles;
        # "Gestionar usuarios" y "Ver auditoría" solo si el usuario es admin.
        opciones_usuario = []

        if self.sistema.tiene_permiso("gestionar_usuarios"):
            opciones_usuario.append(("👥 Gestionar usuarios", lambda: self._abrir_gestion_usuarios(app)))
            opciones_usuario.append(("📋 Ver auditoría", lambda: self._abrir_auditoria(app)))

        opciones_usuario.append(("🔑 Cambiar contraseña", lambda: self._cambiar_password(app)))
        opciones_usuario.append(("🚪 Cerrar sesión", lambda: self._cerrar_sesion(app)))

        if hasattr(app, 'configurar_menu_usuario'):
            texto_boton = f"{rol_emoji} {self.sistema.usuario_actual}  ▾"
            app.configurar_menu_usuario(texto_boton, opciones_usuario)

    def _abrir_gestion_usuarios(self, app):
        DialogoGestionUsuarios(app, self.sistema)

    def _abrir_auditoria(self, app):
        DialogoAuditoria(app, self.sistema)

    def _cambiar_password(self, app):
        DialogoCambiarPassword(app, self.sistema)

    def _cerrar_sesion(self, app):
        if app._confirmar("Cerrar Sesión", f"¿Cerrar sesión como '{self.sistema.usuario_actual}'?", "Sí, cerrar", "Cancelar"):
            self.sistema.logout()
            app.destroy()
            nueva = AppLauncher()
            nueva._iniciar()


# Punto de entrada único
if __name__ == "__main__":
    lanzador = AppLauncher()