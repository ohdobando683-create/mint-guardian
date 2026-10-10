# Mint Guardian
## Características

- Monitor de CPU, RAM y disco.
- Gráficas de CPU y RAM en tiempo real.
- Velocidad de descarga y subida de red.
- Lista de procesos con mayor consumo de memoria.
- Notificaciones de consumo elevado.
- Desplazamiento vertical con la rueda del ratón.
- Acceso desde el menú de aplicaciones.

## Instalar en Linux Mint o Ubuntu

1. Abre la sección Releases de este repositorio:
   https://github.com/ohdobando683-create/mint-guardian/releases
2. Descarga el archivo `mintguardian_1.0.1_amd64.deb` de la versión correspondiente.
3. Abre el archivo descargado e instálalo con el instalador de paquetes.
4. Busca Mint Guardian en el menú de aplicaciones.

También puedes instalarlo desde una terminal, situándote en la carpeta donde descargaste el archivo:

    sudo apt install ./mintguardian_1.0.1_amd64.deb

El paquete `amd64` está destinado a sistemas Linux de arquitectura x86-64.

## Código fuente

El archivo principal de la aplicación es `mint_guardian_4.py`.

Para ejecutar el código desde el proyecto se necesitan Python 3, Tkinter, psutil y matplotlib.

## Licencia

Consulta el archivo LICENSE de este repositorio.
