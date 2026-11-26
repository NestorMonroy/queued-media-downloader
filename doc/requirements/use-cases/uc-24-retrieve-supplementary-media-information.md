# UC-24: Obtener la información complementaria de un contenido

- **Objetivo:** el User obtiene y conserva la información asociada a un contenido sin descargar el video ni el audio:
  - subtítulos del sitio, incluidos los automáticos, en los idiomas que elija;
  - descripción, metadatos (autor, fechas, capítulos), miniatura y el `info.json` de yt-dlp.
- **Actor principal:** User
- **Actor secundario:** Media site
- **Disparador:** el User quiere indexar, estudiar o leer un contenido (un curso, una conferencia) sin ocupar espacio con el video, o completar después la información de un contenido ya descargado.
- **Relación:** se ejecuta como un job de la cola (`run`), como UC-03, porque hace peticiones al sitio y puede ir en lote. UC-03 A16 cubre el caso de descargar esta información junto con el contenido. UC-15 la muestra en pantalla sin guardar nada.
- **Prioridad:** media
- **Significativo para la arquitectura:** sí: un job cuyo resultado no es un archivo multimedia (D-15)
- **Estado:** propuesto; no implementado. Depende de D-15 y D-16.
- **Origen:**
  - **yt-dlp:** `skip_download` con `writesubtitles`, `writeautomaticsub`, `subtitleslangs`, `convertsubtitles`, `writedescription`, `writeinfojson`, `writethumbnail`.
  - **YTDownload-2026:** archivos complementarios por defecto y su guía, «modo A».
  - **Seal y Kannagi:** subtítulos y miniaturas.
  - **Revisión de exclusiones:** «leer transcripciones» excluía interpretar los archivos, no obtenerlos.

## Breve descripción

`enqueue URL --info-only` con lo que se quiere obtener (`--subtitles es,en`, `--auto-subtitles`, `--description`, `--thumbnail`, `--metadata`) crea un job que solo descarga esa información. Sus resultados son archivos complementarios con propiedad propia (D-15, [BR-29](../business-rules.md)).

No incluye:
- generar transcripciones o traducciones con inteligencia artificial;
- interpretar el contenido de los archivos.

## Precondiciones

- UC-01 completado.

## Flujo básico

1. El User ejecuta `enqueue URL --info-only --subtitles es,en --description`.
2. El sistema crea el job con esas opciones (UC-02).
3. `run` envía el job; el worker extrae la información sin descargar el contenido.
4. El worker escribe cada resultado pedido junto al nombre del contenido, con la reclamación de ese nombre (BR-31).
5. El job termina `COMPLETED` cuando están todos sus resultados obligatorios ([BR-30](../business-rules.md)). Para cada resultado pedido que el sitio no ofrece, se registra que no estaba disponible.

## Flujos alternativos

- **A1. Subtítulos automáticos:** solo si se piden; se marcan como automáticos en el nombre o en los metadatos.
- **A2. Idioma no disponible:** es un resultado opcional ausente; el job termina `COMPLETED` con un aviso (BR-30).
- **A3. Conversión de subtítulos** (`--subtitle-format srt`): ffmpeg convierte; si falla, se conserva el original y se avisa.
- **A4. Playlist o canal:** se expande como UC-04; cada entrada es un job de información.
- **A5. Contenido ya descargado por otro job:** los archivos complementarios se escriben junto a él solo si el job que lo descargó es del mismo User y su nombre no está reclamado por otro (BR-31); si no, en una carpeta propia.
- **A6. Condición externa:** UC-11 o UC-17.
- **A7. Comentarios** (propuesto, prioridad baja): `--comments` con `getcomments` de yt-dlp. Puede requerir muchas peticiones al sitio, así que se aplica el ritmo de BR-02 y se avisa. Es un resultado opcional.
- **A8. Reglas de metadatos** (propuesto, prioridad baja): derivar o corregir metadatos (por ejemplo, artista y título a partir del título) con la sintaxis de `parse-metadata` de yt-dlp, validada y sin ejecutar comandos; también disponible en UC-02 A7.

## Excepciones

- **E1. El contenido no existe o no está disponible:** como UC-03 A2.
- **E2. No se pidió ninguna información:** código `2`.

## Garantías

- **De éxito:** los archivos pedidos y disponibles quedan escritos y registrados como resultados del job.
- **Mínima:** el job nunca descarga el contenido multimedia ni sobrescribe archivos ajenos.

## Reglas, requisitos y restricciones asociados

- **Reglas:** BR-29, BR-30, BR-31 y BR-32.
- **Requisitos suplementarios:** SUP-R05, SUP-U05 y SUP-I01.
- **Restricciones:** sin inteligencia artificial: solo la información que publica el sitio.
- **Dependencias:** UC-02, UC-04, UC-11 y UC-17; D-15.

## Criterios de aceptación

1. Un job de información nunca escribe un archivo multimedia.
2. Un idioma de subtítulos que no existe no hace fallar el job, pero se informa.
3. Cada archivo escrito está registrado como resultado del job y protegido por su reclamación.

## Escenarios de prueba

| Escenario | Dónde se prueba |
|---|---|
| Subtítulos, descripción, miniatura e `info.json` contra el servidor local | Cualquier sistema |
| Idioma ausente, conversión fallida | Cualquier sistema |
| Contenido real de YouTube con subtítulos automáticos | **Windows**, campaña (`network`) |
