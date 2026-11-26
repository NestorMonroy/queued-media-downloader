# Modelo de negocio, caso de negocio y finanzas

- **Versión:** 1.0 (instrucción 2.6.0, 2026-11-26).
- **Responsabilidad:** Gestión del producto (decide el Responsable del proyecto).
- **Estado:** el modelo comercial de §3 está **aprobado**; las condiciones de §4 están **pendientes** y no se completan por deducción. Nada de este documento autoriza implementar anuncios, pagos, licencias, cuentas ni servicios remotos.

Este espacio pertenece a la gestión del producto (PMBOK 8, §2.3): sobrevive a los proyectos y no es el plan de ninguna iteración. Su hoja de ruta está en [product-roadmap.md](product-roadmap.md); el gobierno del proyecto, en [governance.md](../project-management/governance.md).

## 1. Separación de responsabilidades (D-24)

D-24 conserva su identificador, pero su contenido se reparte entre cuatro responsabilidades que no se mezclan:

| Responsabilidad | Qué decide | Dónde |
|---|---|---|
| Estrategia de negocio | Para quién es el producto, cómo se sostiene, qué modos comerciales existen | §2 y §3 de este documento |
| Gestión del producto | Capacidades por modo, condiciones del periodo inicial y de la adquisición, hoja de ruta | §4, [hoja de ruta](product-roadmap.md) |
| Publicación y distribución | Canales, paquetes, mecanismo de cada canal, condiciones de cada tienda | §6; SUP-C12 y SUP-C13; R-34 a R-36 |
| Arquitectura y diseño técnico | Dónde vive el derecho de uso (*entitlement*) y cómo se aísla del motor | [Diseño, Parte 3, §18.7](../design/03-target-architecture-and-evolution.md#187-frontera-comercial); BR-54 |

## 2. Modelo de negocio

| Elemento | Contenido aprobado o declarado | Pendiente |
|---|---|---|
| Propuesta de valor | Obtener, organizar y administrar resultados multimedia de forma persistente y recuperable; en el horizonte futuro, procesar audio, video y texto (transcripción, traducción, resúmenes, subtítulos, voz y doblaje) | Qué capacidades de IA entran y con qué inferencia (D-28) |
| Segmentos | Usuarios de Windows (CLI y GUI) primero; Android e iOS después | — |
| Canales | Distribución directa en Windows; tiendas cuando corresponda (Google Play, App Store, Microsoft Store) | Qué canales y en qué orden (D-27) |
| Ingresos | En Android e iOS: modo con anuncios o modo sin anuncios adquirido | Pago único o recurrente, precio, alcance de la compra (D-26) |
| Costes | Firma de código, cuentas de desarrollador de cada tienda, comisión de cada canal, infraestructura de inferencia remota si se elige | Importes: no se inventan (§5) |
| Relación | Sin cuenta obligatoria; sin servidor de licencias remoto propio | — |

## 3. Modelo comercial aprobado

1. **Periodo inicial:** 15 días sin anuncios en todas las plataformas.
2. **Android e iOS, después del periodo inicial:** dos modos, con anuncios o sin anuncios adquirido.
3. **Windows GUI y CLI:** nunca muestran anuncios; el periodo inicial de 15 días también se aplica.
4. **Modo privado ≠ modo sin anuncios** (BR-49): adquirir el modo sin anuncios no cambia qué datos se guardan, y activar el modo privado no quita anuncios.
5. **El vencimiento no destruye trabajo** (BR-54): el fin del periodo inicial o de un derecho de uso no borra, detiene ni altera jobs, resultados, parciales, perfiles, configuración ni historial.
6. **Frontera técnica:** los derechos de uso viven fuera del núcleo; `MediaSource`, `WorkerPool`, `JobStore` y las reglas de identidad no dependen de bibliotecas de facturación, StoreKit, SDK de anuncios ni similares.

## 4. Condiciones pendientes

Ninguna se resuelve aquí. Cada fila nombra la decisión que la agrupa en el [análisis de requisitos, §16.9](../requirements/requirements-analysis.md#169-decisiones-pendientes).

| Condición | Decisión |
|---|---|
| Qué inicia el periodo inicial (instalación, primer uso, primer job) y cómo se calcula su duración | D-25 |
| Reinstalación, restauración, cambio de dispositivo y actualización durante o después del periodo | D-25 |
| Uso sin conexión durante el periodo y al comprobarlo | D-25 |
| Jobs activos en el momento del vencimiento (BR-54 fija que no se detienen; falta qué se muestra) | D-25 |
| Pago único o recurrente; precio | D-26 |
| Por usuario o por dispositivo; compra válida en varias plataformas | D-26 |
| Restaurar la compra; reembolsos y su efecto | D-26 |
| Qué ocurre en Windows al terminar el periodo inicial (sin anuncios, por definición) | D-27 |
| Capacidades de cada modo (si difieren más allá de los anuncios) | D-27 |
| Canales de publicación por plataforma y su orden | D-27 |
| Costes de la IA y quién los paga | D-28 |

## 5. Variables financieras

Solo variables, sin importes inventados. Cada una se mide o se fija cuando se decida.

| Variable | Fuente | Depende de |
|---|---|---|
| Comisión del canal sobre cada venta | Términos de cada tienda | D-26, D-27 |
| Cuota de cuenta de desarrollador por canal | Términos de cada tienda | D-27 |
| Coste de firma de código en Windows | Proveedor elegido | Distribución directa |
| Ingreso por anuncio mostrado | Red de anuncios elegida (no elegida) | D-26 |
| Tasa de adquisición del modo sin anuncios | Medición posterior | D-26 |
| Coste por minuto de audio o por carácter de inferencia remota | Proveedor elegido | D-28 |
| Coste de distribución de modelos locales (almacenamiento y transferencia) | Alojamiento elegido | D-28 |
| Coste de soporte por plataforma | Medición posterior | D-27 |

No hay presupuesto aprobado; por eso «Develop Budget» y «Monitor and Control Finances» no aplican todavía ([gobierno, §4.4](../project-management/governance.md#44-finanzas)).

## 6. Mecanismos de cada canal (documentación oficial)

Hechos documentales consultados el 2026-11-26; no se probaron. No sustituyen la revisión de cada política al publicar (SUP-C12).

| Canal | Periodo de prueba | Adquisición | Consecuencia para el producto |
|---|---|---|---|
| Google Play | Las ofertas de suscripción pueden tener una fase de prueba gratuita de 3 días a 3 años; Google Play solo devuelve las ofertas para las que el usuario es elegible | Productos de pago único (antes «in-app products») o suscripciones; un beneficio único no puede presentarse como suscripción; la oferta debe indicar la duración de la prueba y cómo cancelarla | Un periodo de 15 días medido por la tienda solo existe asociado a una suscripción; con pago único, el periodo lo mide la aplicación (D-25, D-26) |
| App Store | Las suscripciones con renovación automática admiten prueba gratuita; las aplicaciones sin suscripción pueden ofrecer una prueba por tiempo con una compra integrada no consumible de precio cero llamada «XX-day Trial» | Desbloquear funciones exige compra integrada (directriz 3.1.1) | El modo sin anuncios adquirido en iOS es una compra integrada; el periodo de 15 días tiene dos formas documentadas (D-25, D-26) |
| Microsoft Store | La aplicación puede configurarse como prueba gratuita en Partner Center y limitar funciones o mostrar elementos durante la prueba (`Windows.Services.Store`) | Compras integradas con la API de la tienda o una API de terceros segura (política 10.8) | Solo aplica si se publica en la tienda; Windows no muestra anuncios en ningún caso |
| Distribución directa en Windows | No hay mecanismo de canal | No hay mecanismo de canal | El periodo lo mediría la aplicación; sin servidor de licencias remoto propio, no hay comprobación fuera del equipo (D-25, D-27) |

**Referencias de implementación consultadas:** ninguna referencia de código abierto revisada implementa periodo de prueba ni compra (Seal, YTDLnis, NewPipe, Parabolic, VidBee, Electrum, Electron Cash; VoiceStudio declara en `model_licenses.py` que no implica derecho comercial). Los dos APK de GreenTuber disponibles están firmados por `TRUMods`, no por el desarrollador. Contienen una actividad VIP, Google Play Billing y SDK de anuncios, y sus cadenas presentan un modo «VIP» sin anuncios que se obtiene comprando, con código de invitación, invitando a amigos o viendo anuncios. Que esa capa sea del desarrollador o de quien firmó los APK no se puede determinar sin la versión de Google Play ([análisis, §16.5](../requirements/requirements-analysis.md#165-mecanismos-comerciales)). No se documenta cómo eludir la comprobación de pago.

**Fuentes:**
- Google Play Console Help, *Understanding subscriptions* (answer 12154973) y *Subscriptions policy* (answer 9900533); *One-time products* (answer 16431770).
- Apple, *App Review Guidelines*, 3.1.1 *In-App Purchase*.
- Microsoft, *Microsoft Store Policies*, 10.8 *Financial Transactions*; *In-app purchases and trials* (`Windows.Services.Store`).

## 7. Alternativas de coste de la IA

Alternativas, no decisiones (D-28). Ninguna es universal: un mismo producto puede ofrecer varias.

| Alternativa | Quién paga la inferencia | Sin conexión | Datos fuera del equipo | Derecho de uso | Evidencia |
|---|---|---|---|---|---|
| Local incluida | Nadie más (recursos del User) | Sí | No | Ninguno | VoiceStudio: motores locales y descarga de modelos con reanudación |
| Local adquirida | El User, por el modelo o la capacidad | Sí, tras adquirirla | No | Sí (frontera comercial) | Edge0: licencia de modelo propia distinta de la del motor |
| Remota por suscripción | El User al producto | No | Sí | Sí | Sin evidencia en las referencias |
| Remota por uso | El User al producto, por consumo | No | Sí | Sí | Sin evidencia en las referencias |
| Proveedor configurado por el User | El User a su proveedor | No | Sí, al proveedor elegido | No | VoiceStudio: traducción con DeepL, Microsoft o un servicio compatible con OpenAI y clave del User |
| Híbrida | Según la operación | Parcial | Parcial | Según la operación | VoiceStudio: motores locales y en línea en la misma lista |

Las claves de proveedor del User son secretos: se guardan y se representan como cualquier credencial (SUP-SEC01, SUP-SEC07, BR-49).

## 8. Caso de negocio

| Elemento | Contenido |
|---|---|
| Necesidad | Administrar obtenciones multimedia de forma persistente y recuperable en Windows primero, con evolución a Android e iOS y al procesamiento con IA |
| Opciones | (a) Solo distribución directa en Windows sin ingresos; (b) modelo aprobado de §3 con canales de tienda en móviles; (c) además, capacidades de IA adquiridas o remotas |
| Beneficios esperados | Cualitativos: alcance en móviles, sostenibilidad por ingresos en móviles; no hay cifras |
| Costes | Variables de §5; ningún importe |
| Riesgos | R-34 a R-41 (canales, código en tiempo de ejecución, objetivo de API, licencias de modelos, calidad, hardware, mecanismo comercial por canal, privacidad de SDK de anuncios) |
| Supuestos | [Gobierno, §7.1](../project-management/governance.md#71-supuestos) |
| Recomendación | Ninguna todavía: depende de D-25 a D-28. El modelo de §3 ya está aprobado como orientación |
