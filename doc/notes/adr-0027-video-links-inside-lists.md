# ADR-0027: Un enlace a un video dentro de una lista descarga solo el video

- **Estado:** Aceptada
- **Fecha:** 2026-11-23
- **Decisión pendiente que resuelve:** D2 del [plan de E2](../project-management/iteration-plan-e2.md#49-decisiones-pendientes-del-responsable)

## Contexto

Con las playlists (UC-04), un enlace como `youtube.com/watch?v=XXXX&list=YYYY` apunta a la vez a un video y a una lista. Es el enlace que se copia al ver un video dentro de una lista.

- **yt-dlp** trata el caso como una ambigüedad explícita (`_yes_playlist`): solo se aplica cuando la URL apunta a un video y a una lista. En la línea de comandos descarga la lista por defecto y sugiere `--no-playlist` para descargar solo el video. Una URL de lista pura (`playlist?list=…`) se expande igual con cualquiera de las dos opciones.
- **La GUI de referencia analizada (yt-dlp-gui de Kannagi)** pasa siempre `--no-playlist` (`Wrappers/DLP.cs`).

## Decisión

**Solo el video por defecto, con una opción explícita para la lista entera**, como hace yt-dlp con `--no-playlist` y `--yes-playlist`:

- `enqueue "watch?v=…&list=…"` descarga solo el video: cada `YoutubeDL` recibe `noplaylist=True` (`media_extraction/yt_dlp_parameters.py`).
- `enqueue --playlist "watch?v=…&list=…"` descarga la lista entera. La opción se guarda en las download options (`whole_playlist`) y viaja con el job hasta la expansión (T43).
- Una URL de lista pura (`playlist?list=…`) descarga la lista entera, con la opción o sin ella.

## Consecuencias

- Pegar el enlace de un video nunca encola por sorpresa una lista de cientos de entradas, algo costoso en un equipo modesto.
- Las URL de lista, de canal o de pestaña se expanden igual que antes.
- Pruebas con red (marcador `network`): el enlace de "Me at the zoo" dentro de una lista se expande a un solo contenido y, con la opción, a la lista entera. Se ejecutan en la evaluación de E2.
- Los jobs guardados antes de T43 no tienen `whole_playlist` en sus download options; al leerlos vale `False`.
