# UC-39: Administrar modelos de inferencia

- **Objetivo:** el User instala, verifica, consulta y elimina los modelos que usan las operaciones de IA, sabiendo su tamaño, su licencia y su procedencia.
- **Actor principal:** User
- **Disparador:** el User abre la administración de modelos u otra operación necesita un modelo que falta.
- **Prioridad:** media.
- **Significativo para la arquitectura:** sí: descarga, integridad y recuperación de archivos grandes, distinta de las dependencias de UC-27 pero con los mismos mecanismos.
- **Estado:** candidato (propuesta de la instrucción 2.6.0, pendiente de aprobación del Responsable). Horizonte: futuro. Implementación: ausente.
- **Verificación:** sin evidencia de implementación; la especificación está verificada por inspección y por `scripts/check_requirements_model.py`.
- **Origen:** VoiceStudio (`docs/downloading-models.md`: descarga segmentada con hasta ocho rangos de 16 MB, manifiesto de reanudación y comprobación de tamaño y resumen antes de publicar el archivo; `endpoint_race.py`: elección del extremo por sondeo; `model_lifecycle.py`: descargar de memoria; `model_licenses.py`: declaraciones de licencia sin derecho comercial implícito; `memory_budget.py`: aviso de memoria no bloqueante); Edge0 (licencia del modelo distinta de la del motor; el presupuesto de memoria rechaza un modelo antes de leer sus pesos); Janas (descarga tras preguntar). Evidencia y nivel en el [análisis de requisitos, §16](../requirements-analysis.md#16-descubrimiento-260-ia-privacidad-y-modelo-comercial).
- **Independencia:** UC-27 administra las dependencias del motor de descarga (yt-dlp, ffmpeg, Deno); un modelo no es una dependencia del producto sino un recurso de una operación. UC-20 configura dónde se guardan.

## Breve descripción

El sistema lista los modelos disponibles e instalados con tamaño, licencia, requisitos y operaciones que los usan; instala con descarga reanudable y verificada; elimina solo lo propio.

## Precondiciones

- UC-01 completado.

## Flujo básico

1. El User pide la lista de modelos.
2. El sistema muestra, para cada modelo, operaciones, tamaño, requisitos (memoria, GPU), licencia y estado.
3. El User elige instalar un modelo y acepta su licencia si la exige.
4. El sistema comprueba el espacio y descarga con reanudación por rangos.
5. El sistema verifica tamaño y resumen y publica el modelo con escritura atómica.
6. El sistema registra el modelo instalado con su procedencia y su licencia.

## Flujos alternativos

- **A1. Reanudar una descarga** `[estado: ausente]` (paso 4): solo se descargan los rangos que faltan.
- **A2. Eliminar un modelo** `[estado: ausente]` (paso 2): el sistema comprueba que ningún job activo lo usa y elimina solo los archivos propios del modelo.
- **A3. Ubicación compartida o administrada por el User** `[estado: ausente]` (paso 2): el sistema la usa sin moverla ni borrarla; la marca como no propia.
- **A4. Verificar los modelos instalados** `[estado: ausente]` (paso 2): se comprueban tamaño y resumen; uno dañado se marca y se ofrece reinstalarlo.

## Excepciones

- **E1. Licencia no aceptada** `[estado: ausente]` (paso 3): no se instala.
- **E2. Espacio insuficiente** `[estado: ausente]` (paso 4): no se inicia la descarga (UC-17).
- **E3. Origen inaccesible** `[estado: ausente]` (paso 4): la descarga falla con la condición de red clasificada y queda reanudable.

## Postcondiciones

- Cada modelo instalado está verificado y registrado con su licencia; nada se publicó sin verificar.

## Requisitos especiales

- No se descargan modelos grandes en pruebas; las pruebas usan archivos sintéticos de pocos KB.

## Reglas, requisitos y restricciones asociados

- SUP-D03; UC-17, UC-26, UC-27; ADR-0033; diseño, §18.6.

## Criterios de aceptación

1. Una descarga interrumpida se reanuda sin repetir los rangos completos.
2. Un archivo que no coincide con su resumen nunca se publica.
3. Eliminar un modelo en uso por un job activo no se permite.

## Escenarios de prueba

| Escenario | Dónde |
|---|---|
| Descarga simulada con cortes, rangos y resumen incorrecto | Desarrollo |
