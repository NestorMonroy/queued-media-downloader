# Origen de esta build de ffmpeg

Build de terceros incluida en el repositorio según [ADR-0005](../../../doc/notes/adr-0005-vendored-ffmpeg-lgpl-shared.md) y [ADR-0018](../../../doc/notes/adr-0018-ffmpeg-build-selection.md). Se distribuye bajo la licencia de `LICENSE.txt` (GNU LGPL, versión 3), no bajo la licencia del proyecto.

## Build

| Dato | Valor |
|---|---|
| Versión | `n9.0.2-39-g7adfbe40dc` (rama `release/9.0` de FFmpeg) |
| Variante | `win64-lgpl-shared` |
| Fuente | BtbN/FFmpeg-Builds (el repositorio se movió a FFmpeg-Builds/FFmpeg-Builds; GitHub redirige la URL antigua) |
| Release | `autobuild-2026-10-31-12-59`, la última build de octubre de 2026 |
| URL | https://github.com/BtbN/FFmpeg-Builds/releases/download/autobuild-2026-10-31-12-59/ffmpeg-n9.0.2-39-g7adfbe40dc-win64-lgpl-shared-9.0.zip |
| SHA-256 del zip | `e907b01fa4783913151237e37df2a10fa97d99a1598a021bf59d4ae62ffed4c0` |
| Descargada | 2026-11-23 |

El SHA-256 se comprobó contra el `checksums.sha256` publicado en la misma release. BtbN conserva dos años la última build de cada mes, así que esta URL debería seguir disponible hasta octubre de 2028.

## Contenido incluido

Del zip solo se incluyen `bin/` (sin `ffplay.exe`, que yt-dlp no usa) y `LICENSE.txt`. No se incluyen `doc/`, `include/`, `lib/` ni `presets/`.

| Archivo de `bin/` | SHA-256 |
|---|---|
| `avcodec-63.dll` | `c20d1a5b282a83b5bc586b65b23cf4837d83c2caa3b4dd4863ede2dd0f1858b5` |
| `avdevice-63.dll` | `a806e0c109646c3dacdfadbf2a9bb33b1e8e4fa8b1d49b6e27c025e27f12ee60` |
| `avfilter-12.dll` | `a56c3f9b6becf4809ee63f85fe1120bbbece56dd2ad700cf2403f8c36499ed4a` |
| `avformat-63.dll` | `7c13073a52f7ad76cfc1c7e76d782e89d88c1155cf2500c3320d034b507605f6` |
| `avutil-61.dll` | `cb50cdee16a5031090330997b51c016fe7788487150cd07fa20ddbda4d108d09` |
| `ffmpeg.exe` | `ac68fc6b9c30b7378b54afccc7e9eff84b318ba1e876d9ab85c8b8cc1dd7e4ea` |
| `ffprobe.exe` | `d339923de7cd0827f634fe4faba661bdbf384dab1e36c2224c51673193537a44` |
| `swresample-7.dll` | `12b907ddfff765e10c3b7da1a7985513dc9282c08953259f337f952f7b8a9f2a` |
| `swscale-10.dll` | `40c20c66f9bdf08a79453056bd40293ff234927e8c4a1bae5fafdcf97da3be42` |

## Código fuente

La LGPL exige ofrecer el código fuente de los binarios distribuidos:

- **FFmpeg**, commit `7adfbe40dcde598f93a6963d2f7b22cd75202ccc` (2026-10-30) de la rama `release/9.0`: https://github.com/FFmpeg/FFmpeg/tree/7adfbe40dcde598f93a6963d2f7b22cd75202ccc, réplica de https://git.ffmpeg.org/ffmpeg.git
- **Scripts de compilación** con los que se generó la build, incluidas las dependencias LGPL enlazadas y su configuración, en el commit `5031c6f1082414e53688d39e521849905071070d` de la etiqueta `autobuild-2026-10-31-12-59`: https://github.com/BtbN/FFmpeg-Builds/tree/autobuild-2026-10-31-12-59

Las DLL son compartidas: se pueden sustituir por otras compiladas desde ese código sin cambiar el proyecto.
