# ADR-0034: Coordinación única con ejecución intercambiable; el pool de procesos como mecanismo de escritorio

- **Estado:** Propuesta, recomendada con evidencia (cierre de Analysis and Design, instrucción 2.4.0). Se acepta con la autorización de E3.
- **Fecha:** 2026-11-26
- **Relación:**
  - **revisa** [ADR-0008](adr-0008-process-based-worker-pool.md), sin reemplazarlo: lo preserva y lo especializa como mecanismo de escritorio;
  - conserva [ADR-0013](adr-0013-process-tree-terminator-abstraction.md) y [ADR-0029](adr-0029-process-tree-termination-on-windows.md);
  - realiza el punto 5 de [ADR-0032](adr-0032-reusable-engine-and-platform-capabilities.md);
  - análisis completo en el [diseño, Parte 3, §16](../design/03-target-architecture-and-evolution.md#16-arquitectura-de-ejecución-cualificación-de-adr-0008).

## Contexto

ADR-0008 eligió un pool fijo de procesos por tres razones:
- `YoutubeDL` guarda estado mutable y no documenta seguridad entre hilos;
- la cancelación por hooks no actúa durante la extracción ni durante ffmpeg;
- se quería aislar cada trabajo y pagar el arranque una sola vez.

Desde entonces:
- se implementó la terminación del árbol (ADR-0029, validada en Windows por T33);
- se aceptaron 26 casos de uso y los drivers multiplataforma (ADR-0032).

El Responsable pidió reevaluar el pool sin conservarlo por inercia ni sustituirlo por moda.

**Evidencia** (Linux; [experimentos](experiments/execution-alternatives.md)):
- **Bloqueo:** con el servidor sin responder, la cancelación cooperativa en un hilo esperó al `socket_timeout` (0 llamadas al hook); terminar el proceso tardó 2 ms.
- **Descendientes:** un hijo externo lanzado desde un hilo sobrevive a su cancelación; desde un líder de grupo terminado, no.
- **Fallos nativos:** un `os.abort` en un hilo terminó el proceso y el otro job; en procesos separados, el otro terminó bien.
- **Event loop:** yt-dlp dentro de una corrutina bloqueó el loop 0,526 s; con `asyncio.to_thread`, 6 ms.
- **Rendimiento con 4 jobs:**

  | Alternativa | Tiempo | Memoria |
  |---|---|---|
  | Pool caliente | 0,594 s | 327 MiB |
  | Hilos | 0,691 s | 89 MiB |
  | Un proceso por job | 2,138 s | 371 MiB |
  | Secuencial | 2,107 s | — |

  El arranque de un proceso con yt-dlp: 0,26 s.
- **Coordinación ya separada:** `RunQueue` y `JobEventApplier` ya son el único dueño del estado y no conocen procesos; `MediaSource` no conoce procesos.
- **Referencias:**
  - Seal aísla cada descarga en un proceso aunque coordina con corrutinas;
  - VoiceStudio solo termina antes de tiempo lo que corre en *sidecars*;
  - Ghost-Downloader-3 no interrumpe sus hilos de extracción.

**Alcance de la evidencia** (aclaración, instrucción 2.5.0): los experimentos muestran ventajas de la ejecución aislada en procesos frente a los hilos y al event loop. No muestran que el pool persistente sea superior a cualquier otra modalidad aislada: B también cumple los obligatorios. A se elige por continuidad y coste de migración, no porque sea la única capaz de aislar y cancelar.

## Opciones consideradas

| Opción | Resultado |
|---|---|
| A. Pool persistente de procesos | Cumple los obligatorios |
| B. Un proceso por job | Cumple los obligatorios; sin ventaja obligatoria sobre A; coste de migración real |
| C. Hilos | Incumple la cancelación de operaciones bloqueadas (UC-05 A2), la ausencia de descendientes (SUP-R02) y el aislamiento ante fallos (SUP-R04) |
| D. Event loop | Bloquea si ejecuta yt-dlp; si delega en hilos, hereda C |
| E. Coordinación única con ejecución intercambiable | Es la estructura vigente; se formaliza |
| F. Mecanismos nativos | Alojan la sesión; no ejecutan Python ni yt-dlp por sí mismos |

## Decisión propuesta

1. **E, con A como mecanismo de escritorio.**
2. **ADR-0008 queda:**
   - **Preserve** el pool, el reciclado (la memoria con extractores reales no está medida) y la terminación del árbol;
   - **Specialize:** el proceso es el mecanismo de Windows y POSIX, no el contrato universal;
   - **Separate:** la coordinación ya está separada; se protege con la regla AR-08 de `lint-imports`;
   - **Generalize, mínimo:**
     - el contrato `WorkerPool` entrega eventos con alcance de job, y `WorkerMessage` queda interno de `workers`;
     - la capacidad disponible es una consulta de capacidad;
     - la terminación forzada puede no estar soportada, y entonces la cancelación queda cooperativa y se informa.
   - Ninguna implementación futura está obligada a ofrecer `worker_id`, un handle de proceso ni el reciclado.
3. **Sin `asyncio`.** La coordinación sigue siendo un bucle síncrono con espera acotada; los plazos nuevos se calculan como vencimientos.
4. **Cancelación en tres pasos.** Solicitud persistida, interrupción efectiva y reconciliación del coordinador. `COMPLETED` lo decide siempre el coordinador a partir de los outputs obligatorios persistidos.
5. **Ejecutor móvil diferido.** Un ejecutor en hilos con cancelación cooperativa, con su garantía menor documentada (R-33). En Android, ffmpeg y el runtime de JavaScript pueden seguir siendo procesos; en iOS, no (R-31).
6. **El nombre `workers` se conserva.**

## Consecuencias

- **Cambios en E3 (U2):**
  - la firma de la observación de `RunQueue`;
  - dos operaciones de `WorkerPool`;
  - ningún cambio de comportamiento del pool.
- **Se conservan:** las pruebas y la evidencia de Windows (T33, T42) del pool.
- **B se reconsidera solo si** la medición de SUP-P04 muestra que la memoria de los workers ociosos incumple el presupuesto.
- **Las garantías de Windows** (cancelación forzada, sin descendientes, aislamiento) se verifican en la campaña posterior a E3 (AAC-11).
