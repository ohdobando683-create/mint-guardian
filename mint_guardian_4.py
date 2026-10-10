import tkinter as tk
from tkinter import ttk
from collections import deque
from datetime import datetime
import platform
import shutil
import subprocess
import time

import psutil
import matplotlib
matplotlib.use("TkAgg")

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


# ------------ CONFIGURACION ------------

INTERVALO_MS = 1000
HISTORIAL = 60

LIMITE_CPU = 90
LIMITE_RAM = 90
LIMITE_DISCO = 90

# Tiempo minimo entre notificaciones del mismo tipo.
COOLDOWN_ALERTA = 120

FONDO = "#101820"
PANEL = "#1b2836"
TEXTO = "#e8eef5"
SECUNDARIO = "#9aafc4"
VERDE = "#4ade80"
AZUL = "#60a5fa"
AMARILLO = "#fbbf24"
ROJO = "#fb7185"


class MintGuardian:
    def __init__(self, root):
        self.root = root
        self.root.title("Mint Guardian 4.0")
        self.root.geometry("1050x850")
        self.root.minsize(820, 680)
        self.root.configure(bg=FONDO)

        self.detenido = False
        self.after_id = None
        self.segundo = 0

        self.tiempos = deque(maxlen=HISTORIAL)
        self.cpus = deque(maxlen=HISTORIAL)
        self.rams = deque(maxlen=HISTORIAL)

        self.alertas_enviadas = {}
        self.bytes_anteriores = psutil.net_io_counters()
        self.tiempo_red_anterior = time.monotonic()
        self.red_inicializada = False

        psutil.cpu_percent(interval=None)

        self.estilos()
        self.interfaz()
        self.root.protocol("WM_DELETE_WINDOW", self.cerrar)
        self.actualizar()

    def estilos(self):
        estilo = ttk.Style()
        estilo.theme_use("clam")

        estilo.configure(
            "Treeview",
            background=PANEL,
            foreground=TEXTO,
            fieldbackground=PANEL,
            rowheight=25,
            borderwidth=0
        )
        estilo.configure(
            "Treeview.Heading",
            background="#26384a",
            foreground=TEXTO,
            font=("DejaVu Sans", 9, "bold")
        )
        estilo.map(
            "Treeview",
            background=[("selected", "#285b75")],
            foreground=[("selected", "white")]
        )

    def etiqueta(self, parent, texto, **kwargs):
        return tk.Label(
            parent,
            text=texto,
            bg=kwargs.pop("bg", FONDO),
            fg=kwargs.pop("fg", TEXTO),
            font=kwargs.pop(
                "font", ("DejaVu Sans", 10)
            ),
            **kwargs
        )

    def interfaz(self):
        # Área principal con desplazamiento vertical.
        exterior = tk.Frame(self.root, bg=FONDO)
        exterior.pack(fill="both", expand=True)

        self.scroll_canvas = tk.Canvas(
            exterior, bg=FONDO, highlightthickness=0
        )
        barra = ttk.Scrollbar(
            exterior, orient="vertical",
            command=self.scroll_canvas.yview
        )
        self.scroll_canvas.configure(yscrollcommand=barra.set)
        barra.pack(side="right", fill="y")
        self.scroll_canvas.pack(side="left", fill="both", expand=True)

        self.contenido = tk.Frame(self.scroll_canvas, bg=FONDO)
        self.ventana_scroll = self.scroll_canvas.create_window(
            (0, 0), window=self.contenido, anchor="nw"
        )

        self.contenido.bind(
            "<Configure>",
            lambda e: self.scroll_canvas.configure(
                scrollregion=self.scroll_canvas.bbox("all")
            )
        )
        self.scroll_canvas.bind(
            "<Configure>",
            lambda e: self.scroll_canvas.itemconfigure(
                self.ventana_scroll, width=e.width
            )
        )

        def rueda(event):
            if isinstance(event.widget, ttk.Treeview):
                return
            if getattr(event, "num", None) == 4:
                pasos = -1
            elif getattr(event, "num", None) == 5:
                pasos = 1
            else:
                delta = getattr(event, "delta", 0)
                if not delta:
                    return
                pasos = -1 if delta > 0 else 1
            self.scroll_canvas.yview_scroll(pasos, "units")
            return "break"

        self.scroll_canvas.bind_all("<MouseWheel>", rueda)
        self.scroll_canvas.bind_all("<Button-4>", rueda)
        self.scroll_canvas.bind_all("<Button-5>", rueda)

        cabecera = tk.Frame(self.contenido, bg=FONDO)
        cabecera.pack(fill="x", padx=20, pady=(14, 8))

        self.etiqueta(
            cabecera, "MINT GUARDIAN 4.0",
            fg=VERDE, font=("DejaVu Sans", 22, "bold")
        ).pack(anchor="w")

        self.lbl_sistema = self.etiqueta(
            cabecera, "Iniciando monitor...",
            fg=SECUNDARIO
        )
        self.lbl_sistema.pack(anchor="w", pady=4)

        # Tarjetas de recursos.
        fila = tk.Frame(self.contenido, bg=FONDO)
        fila.pack(fill="x", padx=14, pady=5)

        self.tarjetas = {}

        for clave, nombre, color in [
            ("CPU", "Procesador", AZUL),
            ("RAM", "Memoria RAM", VERDE),
            ("DISCO", "Disco raíz", AMARILLO),
        ]:
            tarjeta = tk.Frame(
                fila, bg=PANEL, padx=12, pady=10
            )
            tarjeta.pack(
                side="left", fill="both",
                expand=True, padx=6
            )

            self.etiqueta(
                tarjeta, nombre, bg=PANEL, fg=SECUNDARIO
            ).pack(anchor="w")

            valor = self.etiqueta(
                tarjeta, "--%", bg=PANEL, fg=color,
                font=("DejaVu Sans", 20, "bold")
            )
            valor.pack(anchor="w", pady=5)

            barra = ttk.Progressbar(
                tarjeta, maximum=100, mode="determinate"
            )
            barra.pack(fill="x", pady=4)

            detalle = self.etiqueta(
                tarjeta, "Esperando datos...",
                bg=PANEL, font=("DejaVu Sans", 9)
            )
            detalle.pack(anchor="w")

            self.tarjetas[clave] = {
                "valor": valor,
                "barra": barra,
                "detalle": detalle,
                "color": color
            }

        # Monitor de temperaturas.
        temperaturas = tk.Frame(
            self.contenido, bg=PANEL, padx=14, pady=10
        )
        temperaturas.pack(fill="x", padx=20, pady=7)

        self.etiqueta(
            temperaturas, "TEMPERATURAS DEL SISTEMA",
            bg=PANEL, fg=SECUNDARIO,
            font=("DejaVu Sans", 10, "bold")
        ).pack(anchor="w")

        fila_temperaturas = tk.Frame(temperaturas, bg=PANEL)
        fila_temperaturas.pack(fill="x", pady=(8, 0))

        self.lbl_temp_cpu = self.etiqueta(
            fila_temperaturas, "CPU: -- °C",
            bg=PANEL, fg=AZUL,
            font=("DejaVu Sans", 12, "bold")
        )
        self.lbl_temp_cpu.pack(side="left", padx=(0, 24))

        self.lbl_temp_gpu1 = self.etiqueta(
            fila_temperaturas, "GPU 1: -- °C",
            bg=PANEL, fg=VERDE,
            font=("DejaVu Sans", 12, "bold")
        )
        self.lbl_temp_gpu1.pack(side="left", padx=(0, 24))

        self.lbl_temp_gpu2 = self.etiqueta(
            fila_temperaturas, "GPU 2: -- °C",
            bg=PANEL, fg=AMARILLO,
            font=("DejaVu Sans", 12, "bold")
        )
        self.lbl_temp_gpu2.pack(side="left")

        self.lbl_temp_estado = self.etiqueta(
            temperaturas, "Consultando sensores...",
            bg=PANEL, fg=SECUNDARIO,
            font=("DejaVu Sans", 9)
        )
        self.lbl_temp_estado.pack(anchor="w", pady=(6, 0))

        # Velocidad de red.
        red = tk.Frame(
            self.contenido, bg=PANEL, padx=14, pady=10
        )
        red.pack(fill="x", padx=20, pady=7)

        self.etiqueta(
            red, "MONITOR DE RED",
            bg=PANEL, fg=SECUNDARIO,
            font=("DejaVu Sans", 10, "bold")
        ).pack(anchor="w")

        velocidades = tk.Frame(red, bg=PANEL)
        velocidades.pack(fill="x", pady=(6, 0))

        self.lbl_descarga = self.etiqueta(
            velocidades, "↓ Descarga: calculando...",
            bg=PANEL, fg=AZUL,
            font=("DejaVu Sans", 12, "bold")
        )
        self.lbl_descarga.pack(side="left", padx=(0, 28))

        self.lbl_subida = self.etiqueta(
            velocidades, "↑ Subida: calculando...",
            bg=PANEL, fg=VERDE,
            font=("DejaVu Sans", 12, "bold")
        )
        self.lbl_subida.pack(side="left")

        # Gráficas.
        zona_graficas = tk.Frame(self.contenido, bg=PANEL)
        zona_graficas.pack(
            fill="both", expand=True,
            padx=20, pady=7
        )

        self.figura = Figure(
            figsize=(8, 3.4), dpi=90,
            facecolor=PANEL
        )
        self.ax_cpu = self.figura.add_subplot(211)
        self.ax_ram = self.figura.add_subplot(212)

        self.configurar_eje(self.ax_cpu, "Uso de CPU", AZUL)
        self.configurar_eje(self.ax_ram, "Uso de RAM", VERDE)

        self.linea_cpu, = self.ax_cpu.plot(
            [], [], color=AZUL, linewidth=2
        )
        self.linea_ram, = self.ax_ram.plot(
            [], [], color=VERDE, linewidth=2
        )

        self.figura.tight_layout(pad=1.8)

        self.canvas = FigureCanvasTkAgg(
            self.figura, master=zona_graficas
        )
        self.canvas.get_tk_widget().pack(
            fill="both", expand=True
        )

        # Estado y alertas.
        caja_estado = tk.Frame(
            self.contenido, bg=PANEL, padx=12, pady=9
        )
        caja_estado.pack(fill="x", padx=20, pady=7)

        self.etiqueta(
            caja_estado, "ESTADO DEL SISTEMA",
            bg=PANEL, fg=SECUNDARIO
        ).pack(anchor="w")

        self.lbl_estado = self.etiqueta(
            caja_estado, "Analizando...",
            bg=PANEL, fg=VERDE,
            font=("DejaVu Sans", 10, "bold"),
            justify="left", anchor="w"
        )
        self.lbl_estado.pack(fill="x", pady=(5, 0))

        # Procesos.
        self.etiqueta(
            self.contenido, "Procesos con mayor uso de RAM",
            font=("DejaVu Sans", 12, "bold")
        ).pack(anchor="w", padx=22, pady=(5, 5))
       # Busqueda de procesos.
        barra_busqueda = tk.Frame(self.contenido, bg=FONDO)
        barra_busqueda.pack(fill="x", padx=20, pady=(0, 7))

        self.filtro_procesos = tk.StringVar()

        self.etiqueta(
            barra_busqueda, "Buscar:",
            fg=SECUNDARIO
        ).pack(side="left", padx=(0, 8))

        entrada_busqueda = ttk.Entry(
            barra_busqueda,
            textvariable=self.filtro_procesos
        )
        entrada_busqueda.pack(side="left", fill="x", expand=True)

        self.filtro_procesos.trace_add(
            "write",
            lambda *_: self.actualizar_procesos()
        )

        marco_tabla = tk.Frame(self.contenido, bg=FONDO)
        marco_tabla.pack(
            fill="both", expand=True, padx=20, pady=(0, 7)
        )

        self.tabla = ttk.Treeview(
            marco_tabla,
            columns=("pid", "nombre", "ram", "cpu"),
            show="headings",
            height=5
        )

        for columna, titulo, ancho in [
            ("pid", "PID", 75),
            ("nombre", "Proceso", 390),
            ("ram", "RAM", 90),
            ("cpu", "CPU", 90)
        ]:
            self.tabla.heading(
    columna,
    text=titulo,
    command=lambda c=columna: self.ordenar_tabla(c)
)
            self.tabla.column(
                columna, width=ancho,
                anchor="w" if columna == "nombre" else "center"
            )

        scroll = ttk.Scrollbar(
            marco_tabla, orient="vertical",
            command=self.tabla.yview
        )
        self.tabla.configure(yscrollcommand=scroll.set)
        self.tabla.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        # Botones.
        pie = tk.Frame(self.contenido, bg=FONDO)
        pie.pack(fill="x", padx=20, pady=(0, 12))

        tk.Button(
            pie,
            text="Ver detalles",
            command=self.ver_detalles,
            bg="#245b70",
            fg="white",
            activebackground="#347b96",
            relief="flat",
            padx=12,
            pady=7
        ).pack(side="left", padx=(10, 0))

        tk.Button(
            pie, text="Actualizar ahora",
            command=self.actualizar_ahora,
            bg="#245b70", fg="white",
            activebackground="#347b96",
            relief="flat", padx=12, pady=7
        ).pack(side="left")

        tk.Button(
            pie, text="Salir",
            command=self.cerrar,
            bg="#3b4654", fg="white",
            activebackground="#566578",
            relief="flat", padx=18, pady=7
        ).pack(side="right")

        self.lbl_hora = self.etiqueta(
            pie, "Preparando...",
            fg=SECUNDARIO, font=("DejaVu Sans", 9)
        )
        self.lbl_hora.pack(side="left", padx=12)
    def ver_detalles(self):
        seleccion = self.tabla.selection()

        if not seleccion:
            from tkinter import messagebox
            messagebox.showinfo(
                "Detalles del proceso",
                "Selecciona primero un proceso de la tabla."
            )
            return

        valores = self.tabla.item(seleccion[0], "values")

        if not valores:
            return

        pid, nombre, ram, cpu = valores

        from tkinter import messagebox
        messagebox.showinfo(
            "Detalles del proceso",
            f"Nombre: {nombre}\n"
            f"PID: {pid}\n"
            f"RAM: {ram}\n"
            f"CPU: {cpu}"
        )
    def configurar_eje(self, eje, titulo, color):
        eje.set_facecolor(PANEL)
        eje.set_title(titulo, color=color, loc="left")
        eje.set_ylim(0, 100)
        eje.set_xlim(0, HISTORIAL - 1)
        eje.set_ylabel("%", color=TEXTO)
        eje.set_yticks([0, 25, 50, 75, 100])
        eje.tick_params(colors=SECUNDARIO, labelsize=8)
        eje.grid(True, color="#344454", linestyle="--",
                 linewidth=0.6)

        for borde in eje.spines.values():
            borde.set_color("#344454")

    def notificar(self, clave, titulo, mensaje):
        ahora = time.monotonic()
        ultima = self.alertas_enviadas.get(clave, 0)

        if ahora - ultima < COOLDOWN_ALERTA:
            return

        # Evita ejecutar un comando de shell.
        if not shutil.which("notify-send"):
            return

        try:
            subprocess.Popen(
                [
                    "notify-send",
                    "--app-name=Mint Guardian",
                    "--icon=dialog-warning",
                    titulo,
                    mensaje
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            self.alertas_enviadas[clave] = ahora
        except OSError:
            pass

    @staticmethod
    def formato_velocidad(bytes_segundo):
        if bytes_segundo < 1024:
            return f"{bytes_segundo:.0f} B/s"
        if bytes_segundo < 1024 ** 2:
            return f"{bytes_segundo / 1024:.1f} KB/s"
        return f"{bytes_segundo / (1024 ** 2):.2f} MB/s"

    def actualizar_red(self):
        ahora = time.monotonic()
        contadores = psutil.net_io_counters()

        dt = ahora - self.tiempo_red_anterior

        if dt <= 0:
            return

        if self.red_inicializada:
            bajada = max(
                0, contadores.bytes_recv - self.bytes_anteriores.bytes_recv
            ) / dt
            subida = max(
                0, contadores.bytes_sent - self.bytes_anteriores.bytes_sent
            ) / dt

            self.lbl_descarga.config(
                text="↓ Descarga: " + self.formato_velocidad(bajada)
            )
            self.lbl_subida.config(
                text="↑ Subida: " + self.formato_velocidad(subida)
            )
        else:
            self.red_inicializada = True
            self.lbl_descarga.config(text="↓ Descarga: calculando...")
            self.lbl_subida.config(text="↑ Subida: calculando...")

        self.bytes_anteriores = contadores
        self.tiempo_red_anterior = ahora

    def actualizar_tarjeta(self, clave, valor, detalle, limite):
        tarjeta = self.tarjetas[clave]
        valor = max(0, min(100, valor))

        tarjeta["valor"].config(text=f"{valor:.1f}%")
        tarjeta["barra"]["value"] = valor
        tarjeta["detalle"].config(text=detalle)

        color = ROJO if valor >= limite else tarjeta["color"]
        tarjeta["valor"].config(fg=color)

    def actualizar_graficas(self, cpu, ram):
        self.tiempos.append(self.segundo)
        self.cpus.append(cpu)
        self.rams.append(ram)

        x = list(range(len(self.tiempos)))

        self.linea_cpu.set_data(x, list(self.cpus))
        self.linea_ram.set_data(x, list(self.rams))

        izquierda = max(0, len(x) - HISTORIAL)
        derecha = max(HISTORIAL - 1, len(x) - 1)

        self.ax_cpu.set_xlim(izquierda, derecha)
        self.ax_ram.set_xlim(izquierda, derecha)

        self.canvas.draw_idle()
    def ordenar_tabla(self, columna):
        columnas = ("pid", "nombre", "ram", "cpu")
        indice = columnas.index(columna)

        if not hasattr(self, "_orden_columnas"):
            self._orden_columnas = {}

        descendente = not self._orden_columnas.get(columna, False)
        self._orden_columnas[columna] = descendente

        filas = []

        for item in self.tabla.get_children():
            valores = self.tabla.item(item, "values")

            try:
                if columna == "nombre":
                    clave = str(valores[indice]).lower()
                else:
                    clave = float(
                        str(valores[indice]).replace("%", "")
                    )
                filas.append((clave, item))
            except (ValueError, IndexError):
                continue

        filas.sort(key=lambda fila: fila[0], reverse=descendente)

        for posicion, (_, item) in enumerate(filas):
            self.tabla.move(item, "", posicion)
    def actualizar_procesos(self):
        procesos = []

        for proc in psutil.process_iter(
            ["pid", "name", "memory_percent", "cpu_percent"]
        ):
            try:
                info = proc.info
                procesos.append((
                    info["memory_percent"] or 0,
                    info["pid"],
                    info["name"] or "Desconocido",
                    info["cpu_percent"] or 0
                ))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        procesos.sort(key=lambda p: p[0], reverse=True)

        for item in self.tabla.get_children():
            self.tabla.delete(item)

        for ram, pid, nombre, cpu in procesos[:10]:
            self.tabla.insert(
                "", "end",
                values=(pid, nombre[:55], f"{ram:.1f}%", f"{cpu:.1f}%")
            )

    def actualizar_alertas(self, cpu, ram, disco):
        alertas = []

        datos = [
            ("cpu", "CPU", cpu, LIMITE_CPU),
            ("ram", "RAM", ram, LIMITE_RAM),
            ("disco", "Disco", disco, LIMITE_DISCO)
        ]

        for clave, nombre, valor, limite in datos:
            if valor >= limite:
                alertas.append(f"{nombre}: {valor:.1f}%")
                self.notificar(
                    clave,
                    f"Mint Guardian: {nombre} elevado",
                    f"{nombre} ha alcanzado {valor:.1f}%."
                )

        if alertas:
            self.lbl_estado.config(
                text="⚠ Consumo elevado: " + " | ".join(alertas),
                fg=ROJO
            )
        else:
            self.lbl_estado.config(
                text="✓ Recursos dentro de los límites configurados",
                fg=VERDE
            )

    def actualizar_ahora(self):
        if self.after_id is not None:
            try:
                self.root.after_cancel(self.after_id)
            except tk.TclError:
                pass
            self.after_id = None

        self.actualizar()

    def actualizar(self):
        if self.detenido:
            return

        try:
            cpu = psutil.cpu_percent(interval=None)
            memoria = psutil.virtual_memory()
            ram = memoria.percent

            disco = shutil.disk_usage("/")
            porcentaje_disco = disco.used / disco.total * 100

            self.actualizar_tarjeta(
                "CPU", cpu,
                f"{psutil.cpu_count() or '?'} CPU(s) lógicos",
                LIMITE_CPU
            )
            self.actualizar_tarjeta(
                "RAM", ram,
                f"{memoria.available / (1024 ** 3):.2f} GB disponibles",
                LIMITE_RAM
            )
            self.actualizar_tarjeta(
                "DISCO", porcentaje_disco,
                f"{disco.free / (1024 ** 3):.2f} GB libres",
                LIMITE_DISCO
            )

            self.lbl_sistema.config(
                text=(
                    f"{platform.system()} {platform.release()} | "
                    f"{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
                )
            )

            self.actualizar_red()
            self.actualizar_graficas(cpu, ram)
            self.actualizar_procesos()
            self.actualizar_alertas(cpu, ram, porcentaje_disco)

            self.segundo += 1
            self.lbl_hora.config(
                text="Actualizado " + datetime.now().strftime("%H:%M:%S")
            )

        except Exception as error:
            self.lbl_estado.config(
                text=f"Error de lectura: {error}",
                fg=ROJO
            )

        self.after_id = self.root.after(
            INTERVALO_MS, self.actualizar
        )

    def cerrar(self):
        self.detenido = True

        if self.after_id is not None:
            try:
                self.root.after_cancel(self.after_id)
            except tk.TclError:
                pass

        self.root.destroy()


if __name__ == "__main__":
    ventana = tk.Tk()
    app = MintGuardian(ventana)
    ventana.mainloop()

