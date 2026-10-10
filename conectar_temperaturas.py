from pathlib import Path

archivo = Path("mint_guardian_4.py")
codigo = archivo.read_text()

if "    def actualizar_temperaturas(self):" in codigo:
    print("El método de temperaturas ya existe. No se hicieron cambios.")
    raise SystemExit(0)

ancla = "    def actualizar_ahora(self):\n"
if ancla not in codigo:
    raise SystemExit("No se encontró actualizar_ahora(). Archivo sin modificar.")

metodo = '''    def actualizar_temperaturas(self):
        """Lee temperaturas disponibles mediante lm-sensors."""
        try:
            resultado = subprocess.run(
                ["sensors", "-j"],
                capture_output=True,
                text=True,
                timeout=3,
                check=True
            )
            import json
            datos = json.loads(resultado.stdout)
            lecturas = []

            def recorrer(objeto, nombre=""):
                if isinstance(objeto, dict):
                    for clave, valor in objeto.items():
                        if isinstance(valor, (int, float)) and (
                            clave.endswith("_input")
                            and ("temp" in clave.lower()
                                 or "edge" in clave.lower()
                                 or "junction" in clave.lower())
                        ):
                            lecturas.append((nombre, clave, float(valor)))
                        elif isinstance(valor, dict):
                            recorrer(valor, nombre or clave)
                elif isinstance(objeto, list):
                    for elemento in objeto:
                        recorrer(elemento, nombre)

            recorrer(datos)

            cpu = next(
                (v for n, k, v in lecturas
                 if "k10temp" in n.lower() and "temp" in k.lower()),
                None
            )
            gpu = [
                v for n, k, v in lecturas
                if ("amdgpu" in n.lower()
                    and ("edge" in k.lower() or "junction" in k.lower()))
            ]

            self.lbl_temp_cpu.config(
                text=f"CPU: {cpu:.1f} °C" if cpu is not None
                else "CPU: -- °C"
            )
            self.lbl_temp_gpu1.config(
                text=f"GPU 1: {gpu[0]:.1f} °C" if len(gpu) > 0
                else "GPU 1: -- °C"
            )
            self.lbl_temp_gpu2.config(
                text=f"GPU 2: {gpu[1]:.1f} °C" if len(gpu) > 1
                else "GPU 2: -- °C"
            )
            self.lbl_temp_estado.config(
                text="Sensores actualizados"
                if cpu is not None or gpu
                else "No se encontraron temperaturas compatibles"
            )

        except (OSError, subprocess.SubprocessError, ValueError) as error:
            self.lbl_temp_estado.config(
                text=f"No se pudieron leer los sensores: {error}"
            )

'''

codigo = codigo.replace(ancla, metodo + ancla, 1)

llamada = "            self.actualizar_procesos()\\n"
if llamada not in codigo:
    raise SystemExit("No se encontró actualizar_procesos(). Archivo sin modificar.")

codigo = codigo.replace(
    llamada,
    llamada + "            self.actualizar_temperaturas()\\n",
    1
)

archivo.write_text(codigo)
print("Lectura de temperaturas integrada.")
