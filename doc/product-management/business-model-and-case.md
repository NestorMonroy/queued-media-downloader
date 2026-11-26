# Modelo de negocio, caso de negocio y finanzas

- **Versión:** 2.0 (instrucción 2.7.0, 2026-11-26: modelo ratificado con su matriz por plataforma; UC-41 reconciliado; D-25 a D-28 descompuestas; retiradas las afirmaciones que convertían límites de autorización en restricciones). 1.0 (instrucción 2.6.0).
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
| Relación | Sin cuentas propias seleccionadas; implementar cuentas obligatorias no está autorizado, lo que no es una restricción del producto | Si alguna vez hacen falta cuentas, identificadores de dispositivo o un servidor de licencias (D-25, D-26) |

## 3. Modelo comercial aprobado

Decisiones del Responsable, ratificadas en la instrucción 2.7.0. Sus mecanismos técnicos están por cualificar.

1. **Periodo inicial:** 15 días gratuitos en todas las plataformas, sin publicidad. La duración está resuelta.
2. **Android e iOS, después del periodo inicial:** pueden continuar con publicidad o adquirir una modalidad sin publicidad.
3. **Windows GUI y CLI:** no usan publicidad; el periodo de 15 días también se aplica.
4. **Modo privado y modalidad sin publicidad son distintos** (BR-49): uno no cambia al otro.
5. **Preservación** (BR-54): el vencimiento del periodo inicial o de una adquisición no borra ni altera jobs, outputs, parciales, perfiles, configuración ni historial. Su efecto en la elegibilidad de jobs nuevos, pendientes o activos está pendiente (D-25, D-27).
6. **Separación** (ADR-0036, orientación aceptada): los componentes multimedia no dependen de proveedores de pago, publicidad ni tiendas, y todas las interfaces usan el mismo contrato de acceso.

| Característica | Windows CLI | Windows GUI | Android | iOS |
|---|---|---|---|---|
| Periodo inicial | 15 días | 15 días | 15 días | 15 días |
| Publicidad durante el periodo | No | No | No | No |
| Publicidad después | No | No | Según modalidad | Según modalidad |
| Adquirir la modalidad sin publicidad | No es un objetivo aplicable por sí mismo | No es un objetivo aplicable por sí mismo | Sí | Sí |
| Continuidad comercial | Por definir (D-27) | Por definir (D-27) | Modalidades establecidas | Modalidades establecidas |
| Precio | Pendiente (D-26) | Pendiente | Pendiente | Pendiente |
| Forma de contratación | Pendiente (D-26) | Pendiente | Pendiente | Pendiente |
| Capacidades de IA incluidas | Pendiente (D-28) | Pendiente | Pendiente | Pendiente |

**Objetivo comercial del User:** UC-41 «Adquirir acceso a la aplicación» (candidato), con la adquisición sin publicidad como escenario de Android e iOS ([análisis, §17.8](../requirements/requirements-analysis.md#178-objetivos-comerciales-y-uc-41)). El inicio del periodo inicial es un comportamiento automático (D-25).

## 4. Condiciones pendientes

Conjunto trazable en el [análisis, §17.9](../requirements/requirements-analysis.md#179-decisiones-comerciales-y-de-ia-pendientes), con alternativas, evidencia, consecuencias, autoridad, trabajo afectado y momento. Resumen por decisión:

| Decisión | Pendiente | Responsabilidad |
|---|---|---|
| D-25 | Evento iniciador, cómputo, persistencia, actualizaciones, reinstalaciones, restauraciones, cambio de dispositivo, sin conexión, transición | Gestión del producto; Arquitectura para los mecanismos |
| D-26 | Precio, pago único o recurrente, modalidades de contratación, por usuario o dispositivo, restauración, entre plataformas, condiciones de actualización, capacidades incluidas | Gestión del producto |
| D-27 | Continuidad de Windows (Estrategia de negocio), capacidades tras el periodo (Gestión del producto), comportamiento de las operaciones (Requisitos), verificación de la adquisición (Arquitectura y diseño técnico), canal (Publicación y distribución) | Cinco responsabilidades separadas |
| D-28 | Capacidades de IA ofrecidas (alcance), incluidas por modalidad (modelo de negocio), costes (finanzas), local, remoto o híbrido (arquitectura), modelos y disponibilidad (cualificación), runtimes (diseño) | Seis responsabilidades separadas |

Ninguna se completa por deducción. No se deduce que la IA sea solo de pago, que la modalidad sin publicidad incluya inferencia remota ilimitada ni que todas las funciones de IA necesiten servicios externos. Ninguna bloquea E3 salvo el punto de extensión de la elegibilidad (plan de E3, §12.4).

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
| Distribución directa en Windows | El canal no ofrece mecanismo | El canal no ofrece mecanismo | El mecanismo está pendiente (D-25, D-27); servidores de licencias, cuentas o identificadores de dispositivo no se seleccionan sin una decisión sustentada |

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
