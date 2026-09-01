# YouTube Video Downloader

Aplicación de escritorio para Windows que permite analizar un vídeo de YouTube y descargar las calidades disponibles mediante una interfaz sencilla. Este **YouTube downloader for Windows** combina un frontend HTML5/JavaScript con un backend local en Python y FastAPI, utiliza `yt-dlp` para obtener los formatos y FFmpeg para procesar vídeo y audio.

Puede guardar vídeo en MP4 hasta 4K cuando la fuente lo permite, o extraer solo el audio en M4A/AAC o MP3. Todo el procesamiento se realiza localmente en el ordenador del usuario.

> **Estado del proyecto:** versión funcional para Windows 10/11 de 64 bits. Actualmente procesa vídeos individuales; no descarga listas de reproducción ni importa sesiones o cookies de usuario.

## ✨ Features

- Análisis de URL con miniatura, título, duración y canal.
- Detección de las resoluciones que realmente ofrece cada vídeo.
- Descarga de vídeo en 2160p (4K), 1440p, 1080p, 720p, 480p, 360p, 240p o 144p cuando estén disponibles.
- Selección automática de la mejor pista de audio para la resolución de vídeo elegida.
- Combinación de vídeo y audio en MP4 mediante FFmpeg.
- Modo **Solo audio** con:
  - M4A con AAC-LC, 44,1 kHz, estéreo y bitrate objetivo de 160 kbps.
  - MP3 como formato alternativo independiente.
- Metadatos M4A obtenidos de YouTube: título, artista/canal, álbum y fecha cuando existen.
- Validación automática de los M4A generados mediante FFprobe.
- Progreso, porcentaje, velocidad y tamaño descargado/total cuando la fuente lo informa.
- Cancelación de descargas y limpieza de archivos temporales.
- Selector nativo de carpeta y acceso directo a la carpeta al finalizar.
- Interfaz inspirada en Windows 11, responsive, con modo claro y oscuro.
- FFmpeg y FFprobe incluidos en las distribuciones compiladas para Windows; no dependen del `PATH` del usuario.

## 📥 Download

Los usuarios que solo quieran utilizar la aplicación deben visitar la sección [**Releases**](../../releases) y descargar la última versión estable publicada para Windows.

La distribución utiliza el formato `onedir`: conserva completa la carpeta extraída, incluida su subcarpeta `bin`. No copies ni ejecutes únicamente `YouTube Video Downloader.exe`, porque FFmpeg, FFprobe y las dependencias del runtime viajan junto a él.

El código fuente que GitHub adjunta automáticamente a cada versión está destinado a desarrolladores y no es la aplicación compilada.

## 🖥️ Requirements

### Para usuarios de la versión compilada

- Windows 10 u 11 de 64 bits.
- Microsoft Edge WebView2 Runtime, incluido normalmente en Windows 11 y en instalaciones actualizadas de Windows 10.
- Conexión a Internet para analizar y descargar el contenido.

No se necesita instalar Python ni FFmpeg globalmente. Una distribución completa contiene:

```text
YouTube Video Downloader/
├── YouTube Video Downloader.exe
├── bin/
│   ├── ffmpeg.exe
│   ├── ffprobe.exe
│   └── FFMPEG-LICENSE.txt
└── _internal/
```

### Para desarrollo

- Windows 10/11 de 64 bits.
- Python 3.11 o 3.12; el proyecto se valida y empaqueta actualmente con Python 3.12.
- PowerShell.
- Conexión a Internet para instalar dependencias y preparar los binarios verificados de FFmpeg.
- WebView2 Runtime para abrir la ventana de escritorio.

Inno Setup 6 solo es necesario para crear el instalador. Windows SDK y un certificado Authenticode son opcionales y se utilizan únicamente para firmar una publicación.

## 🚀 Usage

1. Abre **YouTube Video Downloader**.
2. Introduce la URL de un vídeo de YouTube.
3. Pulsa **Analizar vídeo**.
4. Revisa la información detectada y elige una resolución o **Solo audio**.
5. Para audio, selecciona **M4A (AAC)** —recomendado— o **MP3**.
6. Elige la carpeta de destino.
7. Pulsa **Descargar** y sigue el progreso desde la aplicación.
8. Al finalizar, utiliza **Abrir carpeta** para localizar el archivo.

Las opciones 4K, 2160p, 1440p, 1080p o 720p solo aparecen si esa resolución existe realmente en la fuente.

## 🧩 How it works

```text
HTML5/CSS/JavaScript
        │ API local + Server-Sent Events
        ▼
FastAPI en 127.0.0.1
        │
        ├── yt-dlp: análisis, formatos y descarga
        ├── FFmpeg: combinación, conversión y metadatos
        └── FFprobe: validación del audio final
```

- `pywebview` abre la interfaz como una ventana de escritorio basada en WebView2.
- FastAPI sirve el frontend y expone una API exclusivamente local.
- Las descargas se ejecutan en hilos de trabajo para no bloquear la interfaz.
- Server-Sent Events comunica los cambios de progreso al frontend.
- Para vídeo, `yt-dlp` elige la pista de la altura solicitada y el mejor audio disponible; FFmpeg las combina en MP4 cuando vienen separadas.
- Para M4A, la aplicación recodifica realmente a AAC-LC. No se limita a cambiar la extensión del archivo.

La configuración M4A de 44,1 kHz y 160 kbps se eligió porque fue aceptada en una prueba práctica con Dispositivos Apple para Windows y un iPhone, mientras que la configuración anterior de 48 kHz/192 kbps fue rechazada por ese flujo concreto. Esto no significa que 48 kHz/192 kbps sea incompatible con iPhone en general.

## 🛠️ Development

Después de clonar el repositorio, abre PowerShell en su carpeta raíz.

### 1. Crear y activar el entorno virtual

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

### 2. Instalar dependencias

```powershell
python -m pip install -r requirements-dev.txt
```

`requirements-dev.txt` incluye las dependencias de ejecución y añade Pytest, HTTPX y PyInstaller.

### 3. Preparar FFmpeg y FFprobe

```powershell
.\prepare_ffmpeg.ps1
```

El script descarga durante la preparación una build win64 LGPL fijada de BtbN, comprueba su SHA-256 y copia `ffmpeg.exe`, `ffprobe.exe` y su licencia a `bin/`. La aplicación instalada no descarga ni ejecuta actualizaciones de FFmpeg automáticamente.

### 4. Ejecutar la aplicación

```powershell
python run_app.py
```

Para trabajar con el backend en modo de recarga:

```powershell
python run_dev.py
```

El servidor de desarrollo queda disponible en `http://127.0.0.1:8765`. El selector nativo de carpeta solo está disponible al ejecutar `run_app.py` mediante `pywebview`.

### 5. Ejecutar las pruebas

```powershell
python -m pytest
```

## 🏗️ Building

Prepara primero FFmpeg si `bin/ffmpeg.exe` todavía no existe:

```powershell
.\prepare_ffmpeg.ps1
```

Genera la distribución Windows con:

```powershell
.\build_windows.ps1
```

Este script instala las dependencias de desarrollo fijadas, ejecuta las pruebas y llama a PyInstaller con `YouTubeDownloader.spec`. El resultado se guarda en:

```text
dist\YouTube Video Downloader\
```

La build utiliza `onedir`, sin UPX ni ofuscación. Debe distribuirse la carpeta completa, no únicamente el `.exe`.

Para analizar el resultado con Microsoft Defender:

```powershell
.\scan_defender.ps1
```

### Instalador opcional

El proyecto incluye una definición de Inno Setup para una instalación por usuario en `%LOCALAPPDATA%\Programs`:

```powershell
winget install JRSoftware.InnoSetup
.\build_installer.ps1
```

El instalador se genera en `dist-installer/`, registra la desinstalación y ofrece un acceso directo de escritorio opcional.

El script `sign_release.ps1` deja preparado el uso de `signtool.exe` con SHA-256 y sellado de tiempo. El repositorio no contiene certificados, claves privadas ni credenciales.

## 🔐 Security

- Las URL se limitan a `youtube.com`, sus subdominios y `youtu.be`; se rechazan otros hosts, direcciones IP y URLs con credenciales.
- La carpeta de destino debe existir y ser un directorio válido.
- El frontend no accede directamente al sistema de archivos ni inicia procesos externos.
- `yt-dlp` se utiliza mediante su API de Python; no se construyen comandos de shell con valores proporcionados por el usuario.
- Las llamadas directas a FFprobe y a utilidades del sistema utilizan listas de argumentos, no cadenas de comandos del usuario.
- El servidor escucha exclusivamente en `127.0.0.1`.
- Cada trabajo utiliza una carpeta temporal propia, eliminada al completar, cancelar o producirse un error.
- Al cerrar la aplicación se solicita la cancelación de los trabajos activos y se detiene el servidor local.
- La distribución no instala servicios, tareas programadas ni mecanismos de persistencia.
- FFmpeg no se descarga durante la ejecución de la aplicación.

Los vídeos privados, con restricción de edad, región o inicio de sesión pueden no estar disponibles. La aplicación no importa cookies ni credenciales del navegador.

## 📦 Third-party software

| Componente | Uso |
|---|---|
| [FastAPI](https://fastapi.tiangolo.com/) | API HTTP local |
| [Uvicorn](https://www.uvicorn.org/) | Servidor ASGI local |
| [Pydantic](https://docs.pydantic.dev/) | Validación de solicitudes |
| [yt-dlp](https://github.com/yt-dlp/yt-dlp) | Análisis y descarga de formatos |
| [FFmpeg](https://ffmpeg.org/) | Combinación de vídeo/audio y conversión multimedia |
| FFprobe | Inspección y validación de los archivos generados |
| [pywebview](https://pywebview.flowrl.com/) | Ventana de escritorio para el frontend web |
| Microsoft Edge WebView2 | Motor de renderizado de la interfaz en Windows |
| [PyInstaller](https://pyinstaller.org/) | Creación de la distribución `onedir` |
| [Inno Setup](https://jrsoftware.org/isinfo.php) | Instalador opcional para Windows |

Las versiones fijadas de los paquetes Python están en `requirements.txt` y `requirements-dev.txt`. Los detalles de redistribución se documentan en [THIRD_PARTY.md](THIRD_PARTY.md), y la licencia de la build incluida de FFmpeg se conserva en [bin/FFMPEG-LICENSE.txt](bin/FFMPEG-LICENSE.txt).

Los ejecutables de FFmpeg no se almacenan en Git debido a su tamaño. `prepare_ffmpeg.ps1` recupera exactamente el paquete verificado necesario para compilar.

## 🧪 Testing

La suite actual contiene **10 pruebas automatizadas** y se ejecuta con Pytest. Comprueba, entre otros aspectos:

- validación de URLs y rechazo de hosts no permitidos;
- detección de resoluciones reales;
- progreso, finalización, cancelación y limpieza de temporales;
- errores de la API;
- localización de FFmpeg independientemente del directorio de trabajo;
- detección de una distribución incompleta;
- combinación real de pistas separadas mediante FFmpeg;
- generación M4A con AAC-LC, 44,1 kHz, estéreo y bitrate objetivo de 160 kbps;
- escritura de metadatos y decodificación completa del audio resultante.

Resultado verificado en la versión actual:

```text
10 passed
```

Las pruebas multimedia requieren que `bin/ffmpeg.exe` y `bin/ffprobe.exe` hayan sido preparados previamente.

## 📄 License

Este repositorio **no incluye actualmente una licencia propia**. Que el código sea visible públicamente no concede automáticamente permiso para usarlo, modificarlo o redistribuirlo. Si se desea aceptar contribuciones o permitir reutilización, deberá añadirse una licencia explícita en una decisión separada.

Las dependencias y herramientas de terceros conservan sus propias licencias y condiciones. Consulta [THIRD_PARTY.md](THIRD_PARTY.md) y [bin/FFMPEG-LICENSE.txt](bin/FFMPEG-LICENSE.txt).

## ⚠️ Disclaimer

Utiliza este video downloader únicamente para contenido propio, de dominio público, con una licencia que permita su descarga o para el que tengas autorización. Es responsabilidad del usuario respetar los derechos de autor, los términos de servicio de YouTube y otras plataformas, y la legislación aplicable.

YouTube cambia periódicamente su plataforma. Si el análisis deja de funcionar, puede ser necesario actualizar `yt-dlp` y volver a validar la aplicación antes de publicar una nueva versión.
