# ADR-0005: ffmpeg incluido en el repositorio (LGPL compartida)

- **Estado:** Aceptada
- **Fecha:** 2026-11-22
- **Nota:** la build concreta (BtbN, rama 9.0, `win64-lgpl-shared`) y la medición del límite por archivo están en [ADR-0018](adr-0018-ffmpeg-build-selection.md).

## Contexto

yt-dlp necesita **ffmpeg y ffprobe** para unir audio y video, cambiar de contenedor y extraer audio. Se decidió que ffmpeg vaya incluido con el proyecto, y que el proyecto controle la versión.

Opciones de PyPI descartadas:
- `imageio-ffmpeg`: solo trae `ffmpeg.exe`, no `ffprobe` (comprobado abriendo el wheel `win_amd64`).
- `static-ffmpeg`: descarga ffmpeg en tiempo de ejecución; no está realmente incluido.

## Opciones consideradas

1. **A. Binarios versionados en el repositorio.**
2. **B. El usuario los descarga; el proyecto los detecta** (enfoque de yt-dlp-gui).
3. **C. El proyecto los descarga en la instalación**, con versión y hash fijados.

## Decisión

**Opción A.** Los binarios se versionan en:

```
vendor/
└── ffmpeg/
    └── <versión>-win64-lgpl-shared/
        ├── bin/          ffmpeg.exe, ffprobe.exe y sus DLL (sin ffplay)
        ├── LICENSE.txt   Licencia de la build
        └── SOURCE.md     Origen de la build y ubicación de su código fuente
```

- **Variante LGPL compartida:** obligaciones de licencia más ligeras que GPL y aproximadamente la mitad de tamaño que la estática. Funcionalmente basta: unir, cambiar de contenedor y extraer audio no recodifican video.
- **Sin `ffplay.exe`:** yt-dlp no lo usa.
- **Git LFS desde el primer commit:** evita reescribir el historial más adelante y el límite de 100 MB por archivo de GitHub.
- El nombre `vendor/` (y no `tools/`) indica código de terceros versionado dentro del repositorio.

## Consecuencias

- El proyecto **distribuye** ffmpeg: hay que cumplir la LGPL (texto de licencia y referencia al código fuente de esa build exacta). Ver [ADR-0007](adr-0007-project-license-unlicense.md).
- Cada actualización de ffmpeg queda en el historial y aumenta el tamaño del clon.
- Los binarios se localizan respecto a la raíz del proyecto (`vendor/` está fuera del paquete Python).
- El proyecto **no se publica en PyPI con ffmpeg dentro**.
- La LGPL no incluye codificadores H.264/H.265: si más adelante se necesita recodificar video, hay que revisar esta decisión.
- Pendiente: elegir la versión concreta de ffmpeg y verificar que la build elegida respeta el límite por archivo.
