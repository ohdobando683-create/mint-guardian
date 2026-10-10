from pathlib import Path

archivo = Path("mint_guardian_4.py")
codigo = archivo.read_text()

ancla = "        # Velocidad de red.\n"

if "        # Monitor de temperaturas.\n" in codigo:
    print("El panel de temperaturas ya existe. No se hicieron cambios.")
    raise SystemExit(0)

if ancla not in codigo:
    raise SystemExit("No se encontró el punto de inserción. Archivo sin modificar.")

bloque = '''        # Monitor de temperaturas.
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

'''

archivo.write_text(codigo.replace(ancla, bloque + ancla, 1))
print("Panel visual de temperaturas insertado correctamente.")
