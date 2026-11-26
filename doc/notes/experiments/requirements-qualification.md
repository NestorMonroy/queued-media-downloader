# Experimentos de cualificación de las decisiones de requisitos

- **Fecha:** 2026-11-26
- **Script:** `scripts/experiments/requirements_qualification.py` (no es código de producción)
- **Resultados en bruto:** [requirements-qualification-linux.json](requirements-qualification-linux.json)
- **Entorno:** Linux x86_64, Python 3.13, yt-dlp 2026.11.23 (la versión fijada), commit base `7dc9842`
- **Aislamiento:**
  - cada experimento usa un directorio temporal propio y un servidor HTTP en `127.0.0.1`;
  - no toca la cola, el estado, las descargas ni la configuración reales;
  - no usa credenciales ni red externa.
- **Consumidor:** [análisis de requisitos, §9](../../requirements/requirements-analysis.md#9-decisiones)

## 1. Reintentos de yt-dlp (R-24, D-3)

- **Pregunta:** ¿basta con pasar `retries` y `fragment_retries` para que una descarga sobreviva a respuestas 503 transitorias?
- **Hipótesis:** con los parámetros actuales del producto, la librería usa 0 reintentos y falla a la primera.
- **Entrada:**
  - un servidor local responde bien a la petición de extracción, con 503 a las dos siguientes y bien a partir de entonces;
  - parámetros de `build_yt_dlp_parameters`, sin cambios o con `retries=10` y `fragment_retries=10`.

| Variante | Resultado | Peticiones |
|---|---|---|
| Parámetros del producto | `FAILED` `NETWORK` | 2 (extracción y un intento) |
| Con 10 reintentos | Completado | 4 (extracción, dos 503 y el intento bueno) |

**Conclusión:**
- se confirma R-24;
- la corrección es solo de configuración, sin un mecanismo propio;
- el experimento es la base del criterio de regresión de D-3.

## 2. Copia de seguridad de SQLite con escrituras concurrentes (UC-23)

- **Pregunta:** ¿la API de copia de seguridad (`sqlite3.Connection.backup`) produce una copia íntegra y transaccionalmente coherente mientras otro hilo escribe en modo WAL?
- **Entrada:** un hilo inserta un job e incrementa un contador en la misma transacción sin parar; se hacen 5 copias, de 8 páginas por paso.
- **Resultado:**
  - las 5 copias tienen `integrity_check = ok`;
  - en las 5, el número de filas coincide con el contador (de 200 a 224);
  - hubo 230 escrituras durante el experimento.
- **Conclusión:** la copia de la base de datos es coherente con `run` activo. No cubre las reclamaciones, que viven fuera de SQLite; por eso la restauración concilia con UC-06 (§13.18 del análisis).

## 3. Cadena de causas en los errores de almacenamiento (R-28, D-12)

- **Pregunta:** en los cinco caminos de error de almacenamiento de yt-dlp, ¿qué códigos recupera un recorrido completo de la cadena (`exc_info`, `__cause__`, `__context__`, con protección contra ciclos), frente al clasificador actual?
- **Entrada:** `OSError(ENOSPC)` provocado en el mismo punto que en yt-dlp 2026.11.23.

| Camino | Clasificador actual | Código en la cadena | Necesita el texto |
|---|---|---|---|
| Escribir datos de la descarga | `FILESYSTEM` | `errno` 28 | No |
| Crear la carpeta de destino | `FILESYSTEM` | `errno` 28 | No |
| Acceso a archivo tras agotar los reintentos | **`UNKNOWN`** | Ninguno | **Sí** |
| `OSError` al procesar (`UnavailableVideoError`) | **`UNKNOWN`** | `errno` 28 (en `__context__`) | No |
| ffmpeg al escribir | `POSTPROCESSING` | Ninguno | **Sí** |

**Conclusión:**
- el recorrido completo recupera el código en 3 de los 5 caminos;
- dos caminos solo conservan el texto, que queda como último recurso con pruebas de contrato (SUP-V03);
- confirma el defecto R-28 y la regla BR-25.

**Limitación:** el camino de `UnavailableVideoError` se reconstruyó asignando `__context__` como lo deja Python al lanzar dentro de un `except`. Las traducciones de `winerror` se confirman en Windows.

## Evidencia por inspección (sin experimento)

| Pregunta | Evidencia | Decisión |
|---|---|---|
| ¿El límite de velocidad es global? | `downloader/common.py` lee `ratelimit` en cada bloque de cada transferencia; `fragment.py` da a cada descargador de fragmentos una copia de los parámetros. Es por transferencia; con N fragmentos concurrentes, el agregado puede llegar a N veces el límite (inferido) | D-20 |
| ¿yt-dlp respeta `Retry-After`? | No aparece en el código de yt-dlp 2026.11.23; `HTTPError.response` conserva las cabeceras | D-4 |
| ¿Cómo espera yt-dlp un directo programado? | `wait_for_video` espera dentro del proceso (`YoutubeDL.py`); `live_status` y `release_timestamp` están en la información | D-10 |
| ¿Qué tamaño estima yt-dlp? | Suma `filesize_approx` de los formatos unidos y lo estima por `tbr` × duración (`YoutubeDL.py`) | D-5 |
| ¿Cómo se configura el proxy? | `YoutubeDL.proxies`: sin parámetro, `getproxies()`; `""`, `__noproxy__`; URL, para todo; en modo detallado se escribe `Proxy map` | D-7 |
| ¿Se escribe el archivo de cookies? | `YoutubeDL.save_cookies` lo reescribe al cerrar | D-1 |
| ¿Hay codificadores H.264 y HEVC en la build LGPL? | Configuración en `avcodec-63.dll`: `libopenh264`, `libkvazaar`, `libvpx`, `libaom`, `librav1e`, `libsvtav1`, `libvvenc` y codificadores por hardware; sin `libx264` ni `libx265` | D-18 |
| ¿Dónde están los parciales? | `Job.partial_directory` está dentro de la carpeta de descargas, así que la publicación es un renombrado en la misma unidad | D-9 |
