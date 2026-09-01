# YouTube Video Downloader

Aplicación de escritorio local para Windows con interfaz HTML5, API FastAPI y motor `yt-dlp`. Analiza un vídeo, muestra únicamente sus resoluciones reales, descarga la pista de vídeo elegida junto con el mejor audio disponible y las combina mediante FFmpeg. También permite extraer audio a M4A o MP3.

El formato de audio recomendado es M4A con AAC-LC, 44,1 kHz, estéreo y 160 kbps. Esta configuración se eligió porque fue aceptada en una prueba práctica con el flujo Dispositivos Apple para Windows + iPhone, mientras que la configuración anterior de 48 kHz/192 kbps fue rechazada por ese flujo concreto. Esto no implica que 48 kHz/192 kbps sea incompatible con iPhone en general. La pista siempre se recodifica realmente con el FFmpeg incluido y se valida después con FFprobe; no se limita a cambiar la extensión.

> Usa la aplicación solo para contenido propio, con licencia compatible o que tengas autorización para descargar. YouTube puede cambiar su plataforma y algunas descargas pueden estar limitadas por sus condiciones de servicio.

## Requisitos

- Windows 10/11 de 64 bits.
- Python 3.11 o 3.12.
- FFmpeg incluido en `bin/`. No se necesita una instalación global ni modificar `PATH`.
- Microsoft Edge WebView2 Runtime (incluido de serie en Windows 11 y en la mayoría de equipos con Windows 10).

Para comprobar el FFmpeg incluido:

```powershell
.\bin\ffmpeg.exe -version
.\bin\ffprobe.exe -version
```

Si los binarios faltan en una copia nueva del código fuente, prepáralos con:

```powershell
.\prepare_ffmpeg.ps1
```

El script descarga una build estática LGPL de BtbN fijada por identificador y comprueba su SHA-256 antes de copiar los binarios y su licencia. La aplicación instalada nunca descarga ejecutables.

## Instalación y desarrollo

Desde la carpeta del proyecto:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

Para ejecutar la aplicación como ventana nativa:

```powershell
python run_app.py
```

Para desarrollar el frontend con recarga automática del backend:

```powershell
python run_dev.py
```

Después abre `http://127.0.0.1:8765`. Este modo de navegador sirve para desarrollar la interfaz y API; el selector nativo de carpeta solo está disponible al ejecutar `run_app.py`.

## Crear el `.exe`

La opción más sencilla es:

```powershell
.\build_windows.ps1
```

El script instala las dependencias de compilación, ejecuta las pruebas y genera una distribución estándar `onedir`:

```text
dist\YouTube Video Downloader\YouTube Video Downloader.exe
```

### FFmpeg dentro de la distribución

`build_windows.ps1` exige que `bin\ffmpeg.exe` exista. PyInstaller copia ambos binarios a `dist\YouTube Video Downloader\bin\`. El backend calcula la ruta desde el ejecutable, no desde el directorio de trabajo, y pasa esa carpeta a `yt-dlp` mediante `ffmpeg_location`.

## Ejecutar en otro ordenador

1. Copia completa la carpeta `dist\YouTube Video Downloader\` al equipo de destino, o usa el instalador Inno Setup.
2. Verifica que la subcarpeta `bin\` viaja junto al ejecutable; no muevas únicamente el `.exe` fuera de la distribución.
3. Comprueba que WebView2 Runtime está instalado; si falta, instala el runtime Evergreen desde Microsoft.
4. Abre el `.exe`. No se necesita Python ni FFmpeg global.

La configuración no usa UPX, ofuscación ni autoextracción en memoria. `onedir` produce más archivos, pero es más transparente para antivirus y diagnóstico que un único ejecutable autoextraíble.

## Instalador convencional

Instala [Inno Setup 6](https://jrsoftware.org/isinfo.php) y ejecuta:

```powershell
winget install JRSoftware.InnoSetup
.\build_installer.ps1
```

El instalador se crea en `dist-installer\`, instala por defecto en `%LOCALAPPDATA%\Programs\YouTube Video Downloader`, registra la desinstalación en Windows y ofrece un acceso directo de escritorio opcional. No solicita permisos de administrador en la instalación normal.

## Firma digital y SmartScreen

Para distribución pública, adquiere un certificado Authenticode de firma de código emitido por una autoridad de certificación reconocida. Los certificados EV suelen obtener reputación de SmartScreen con mayor rapidez; los certificados OV también son válidos, pero la reputación puede construirse con el tiempo. Ningún certificado garantiza que nunca aparezca una advertencia.

1. Guarda el certificado de forma segura en el almacén de certificados de Windows o, preferiblemente, en un token/HSM. No copies claves privadas al repositorio.
2. Instala Windows SDK para disponer de `signtool.exe`.
3. Compila la aplicación y el instalador.
4. Firma primero el ejecutable principal y después el instalador, usando SHA-256 y sellado de tiempo RFC 3161.

El proyecto deja preparado el comando:

```powershell
.\sign_release.ps1 -CertificateThumbprint "HUELLA_DEL_CERTIFICADO"
```

El script usa `signtool sign /fd SHA256 /tr ... /td SHA256` y verifica la firma con la política Authenticode. La huella se pasa en el momento de firmar; no se almacena ningún certificado, contraseña o clave.

Para una cadena reproducible, compila siempre desde un entorno limpio con las versiones fijadas en `requirements.txt` y conserva el hash SHA-256 de cada entrega:

```powershell
Get-FileHash -Algorithm SHA256 ".\dist-installer\YouTubeVideoDownloader-Setup-1.0.0.exe"
```

## Comprobación con Microsoft Defender

Después de compilar:

```powershell
.\scan_defender.ps1
```

El script ejecuta un análisis personalizado sobre la carpeta de distribución con la herramienta oficial `MpCmdRun.exe` y no desactiva ni modifica Defender. Si se produce una detección, no publiques el archivo: guarda el nombre exacto de la detección, el archivo afectado, su SHA-256, la versión de inteligencia de seguridad y el registro `%LOCALAPPDATA%\Temp\MpCmdRun.log`. Revisa primero dependencias y comportamiento; si resulta ser un falso positivo, envía el archivo a Microsoft Security Intelligence para revisión.

SmartScreen evalúa reputación además de malware, por lo que un binario nuevo y limpio puede mostrar advertencia si aún no está firmado o no ha acumulado reputación. La solución legítima es firma consistente, origen HTTPS, metadatos estables y publicación mantenida, nunca desactivar o eludir la protección.

## Arquitectura

```text
frontend/        Interfaz HTML5/CSS/JavaScript
backend/         API, validación, análisis y gestor de descargas
tests/           Pruebas sin acceder a YouTube
bin/             FFmpeg opcional para el empaquetado
run_app.py       Ventana de escritorio y servidor local
run_dev.py       Servidor con recarga para desarrollo
```

El frontend nunca ejecuta procesos ni escribe directamente al sistema de archivos. Las descargas se ejecutan en hilos del backend y el progreso llega por Server-Sent Events. `yt-dlp` se usa mediante su API de Python, sin construir comandos de shell con datos del usuario.

Consulta [THIRD_PARTY.md](THIRD_PARTY.md) para conocer todos los componentes externos y su finalidad.

## Limitaciones reales

- Los vídeos privados, con restricciones de edad, región o sesión pueden requerir autenticación. Esta versión no importa cookies por seguridad; muestra un error comprensible.
- El tamaño total puede ser una estimación o no estar disponible hasta avanzada la descarga, según lo que informe YouTube.
- Para resoluciones modernas, YouTube suele separar vídeo y audio; FFmpeg es obligatorio para producir el archivo final.
- Cancelar es cooperativo: se interrumpe en el siguiente evento de progreso de `yt-dlp`. Los fragmentos temporales del trabajo se eliminan al terminar o cancelar.
- YouTube cambia con frecuencia. Actualiza `yt-dlp` si el análisis deja de funcionar: `python -m pip install -U yt-dlp`.
