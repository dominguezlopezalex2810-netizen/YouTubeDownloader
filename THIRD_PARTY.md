# Componentes externos

- **Python 3.12 runtime**: incluido por PyInstaller para ejecutar el backend local.
- **FastAPI, Starlette, Uvicorn y Pydantic**: API HTTP local, validación de entradas y servidor en `127.0.0.1`.
- **yt-dlp**: análisis y descarga de formatos de YouTube mediante su API de Python.
- **pywebview y pythonnet**: ventana estándar de Windows que aloja la interfaz con WebView2.
- **FFmpeg/FFprobe N-126342-gf88b741dbf (BtbN LGPL, win64, 31-08-2026)**: incluidos en `bin/` para combinar pistas y convertir audio sin depender de `PATH`. El paquete de origen se fija por asset y SHA-256 en `prepare_ffmpeg.ps1`; su licencia se conserva en `bin/FFMPEG-LICENSE.txt`.
- **PyInstaller**: empaquetado de la aplicación. Se configura como `onedir`, sin UPX, ofuscación ni cargadores externos.
- **Inno Setup 6**: creación opcional del instalador convencional, registro de desinstalación y accesos directos.

La aplicación no instala servicios, controladores, tareas programadas, extensiones de navegador ni entradas de inicio automático. No inyecta código, no modifica otros procesos y no descarga ni ejecuta código arbitrario.
