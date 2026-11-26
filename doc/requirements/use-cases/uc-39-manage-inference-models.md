# UC-39: Administrar modelos de inferencia

- **Objetivo:** el User consulta, obtiene, verifica, actualiza, selecciona y elimina los modelos que usan las operaciones de procesamiento, conociendo su compatibilidad, su tamaño y su licencia.
- **Actor principal:** User
- **Disparador:** el User abre la administración de modelos u otra operación necesita un modelo que falta.
- **Prioridad:** media.
- **Significativo para la arquitectura:** sí: descarga, integridad y recuperación de archivos grandes con los mecanismos existentes (diseño, §18.5 y §18.6).
- **Estado:** aceptado (Responsable, instrucción 2.7.0): el objetivo y su flujo básico están en el alcance del producto. Los flujos alternativos y de excepción son propuestas (instrucciones 2.6.0 y 2.7.0) pendientes de aprobación: aceptar el objetivo no aprueba todos sus flujos, mecanismos, modelos ni runtimes. Implementación: ausente.
- **Verificación:** sin evidencia de implementación; la especificación está verificada por inspección y por `scripts/check_requirements_model.py`.
- **Origen:** VoiceStudio (descarga segmentada con verificación; `model_licenses.py`), Edge0 (licencia del modelo distinta de la del motor; presupuesto de memoria al cargar), Janas (descarga tras preguntar; configuración medida por máquina y modelo). Objetivo aceptado en la instrucción 2.7.0.
- **Independencia:** UC-27 administra las dependencias del producto (yt-dlp, FFmpeg, Deno); UC-32 actualiza la aplicación; un modelo es un recurso de una operación, con su propia licencia y compatibilidad.

## Breve descripción

El sistema distingue el modelo, su identidad, su versión, su formato y cuantización, el runtime y el backend que lo ejecutan, sus capacidades, su compatibilidad con el hardware, su integridad y su licencia. No impone un catálogo de proveedores predeterminados: el User puede usar un modelo que ya tiene.

## Precondiciones

- UC-01 completado.

## Flujo básico

1. El User pide la lista de modelos.
2. El sistema muestra, para cada modelo conocido o instalado, sus operaciones, formato, tamaño, requisitos, compatibilidad con el equipo, licencia y estado.
3. El User elige obtener un modelo y acepta su licencia si la exige.
4. El sistema comprueba el espacio y descarga con reanudación.
5. El sistema verifica la integridad y publica el modelo con escritura atómica.
6. El sistema registra el modelo con su procedencia y su licencia.

## Flujos alternativos

- **A1. Usar un modelo propio** `[estado: ausente; propuesto]` (paso 3): el User indica un archivo o una carpeta que ya tiene; el sistema lo verifica y lo registra como no propio, sin moverlo ni borrarlo.
- **A2. Consultar compatibilidad** `[estado: ausente; propuesto]` (paso 2): el sistema indica si el modelo puede ejecutarse en el equipo con los runtimes y backends disponibles, y con qué cualificación (diseño, §18.4).
- **A3. Reanudar una descarga** `[estado: ausente; propuesto]` (paso 4): solo se descarga lo que falta.
- **A4. Verificar los modelos instalados** `[estado: ausente; propuesto]` (paso 2): se comprueba su integridad; uno dañado se marca y se ofrece obtenerlo de nuevo.
- **A5. Actualizar un modelo** `[estado: ausente; propuesto]` (paso 2): hay otra versión; se obtiene como modelo distinto y la anterior se conserva hasta que el User la elimine o ningún resultado la necesite para reutilizarse.
- **A6. Seleccionar un modelo predeterminado** `[estado: ausente; propuesto]` (paso 2): el User elige el modelo que usa cada operación por defecto.
- **A7. Eliminar un modelo** `[estado: ausente; propuesto]` (paso 2): el sistema comprueba que ningún job activo lo usa y elimina solo los archivos propios.
- **A8. Administrar el almacenamiento** `[estado: ausente; propuesto]` (paso 2): el sistema muestra el espacio por modelo y permite cambiar la ubicación de los propios.

## Excepciones

- **E1. Licencia no aceptada** `[estado: ausente; propuesto]` (paso 3): no se obtiene.
- **E2. Espacio insuficiente** `[estado: ausente; propuesto]` (paso 4): no se inicia la descarga (UC-17).
- **E3. Origen inaccesible** `[estado: ausente; propuesto]` (paso 4): la descarga falla con la condición de red clasificada y queda reanudable.
- **E4. Integridad no verificada** `[estado: ausente; propuesto]` (paso 5): el archivo no se publica y se conserva la versión anterior, si existe.

## Postcondiciones

- Cada modelo registrado está verificado y tiene su licencia y su procedencia; nada se publicó sin verificar.

## Requisitos especiales

- Las pruebas no descargan modelos grandes: usan archivos sintéticos.

## Reglas, requisitos y restricciones asociados

- SUP-D03; UC-17, UC-26, UC-27; ADR-0033; diseño, §18.5 y §18.6.

## Criterios de aceptación

1. Una descarga interrumpida se reanuda sin repetir lo completo.
2. Un archivo cuya integridad no se verifica nunca se publica.
3. Eliminar un modelo en uso por un job activo no se permite.
4. Un modelo propio del User no se mueve ni se borra.

## Escenarios de prueba

| Escenario | Dónde |
|---|---|
| Descarga simulada con cortes, integridad incorrecta, actualización y modelo propio | Desarrollo |
