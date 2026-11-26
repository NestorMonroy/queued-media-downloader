# Experimentos: alternativas de arquitectura de ejecución

- **Fecha:** 2026-11-26
- **Script:** `scripts/experiments/execution_alternatives.py` (no es código de producción)
- **Resultados en bruto:** [execution-alternatives-linux.json](execution-alternatives-linux.json)
- **Ambiente:** Linux x86_64 (kernel 6.18), 2 CPU, Python 3.13.18, yt-dlp 2026.11.23; commit base `ff21776`
- **Procedimiento:** `uv run python scripts/experiments/execution_alternatives.py --output RUTA`; código de salida 0
- **Aislamiento:**
  - servidor HTTP en 127.0.0.1, que limita cada conexión a 2 MiB/s o no responde (`/stall`);
  - directorios temporales;
  - una instalación aislada para el programa cliente;
  - sin red externa, sin datos ni credenciales del User.
- **Consumidores:** [diseño, Parte 3, §16](../../design/03-target-architecture-and-evolution.md#16-arquitectura-de-ejecución-cualificación-de-adr-0008) y [ADR-0034](../adr-0034-single-coordinator-and-isolated-execution.md)

**Variables comunes:**
- los mismos medios (1 MiB) y la misma velocidad;
- un `YoutubeDL` nuevo por descarga;
- `socket_timeout` de 3 s y sin reintentos;
- un nombre de archivo único por descarga;
- el pool se mide ya arrancado y calentado; el proceso por job incluye su arranque.

| Experimento | Pregunta | Hipótesis | Alternativa y baseline | Carga | Métricas | Resultado (mediana) | Requisito |
|---|---|---|---|---|---|---|---|
| `startup` | ¿Cuánto cuesta un proceso con yt-dlp listo? | Décimas de segundo | Proceso `spawn` frente a un `YoutubeDL` en un intérprete caliente | 5 y 20 repeticiones | Segundos | 0,263 s frente a 0,032 s | ADR-0008 (arranque) |
| `concurrency` | ¿Qué cuestan N jobs en cada alternativa? | Los hilos y el pool, parecidos en tiempo; los procesos, más memoria | Secuencial (baseline), hilos, proceso por job, pool | 4 jobs × 1 MiB, 3 repeticiones | Segundos, memoria máxima del árbol (`/proc`), procesos | Secuencial 2,107 s y 90,6 MiB; hilos 0,691 s y 88,8 MiB; proceso por job 2,138 s y 370,7 MiB; pool 0,594 s y 327,2 MiB | SUP-P01, SUP-P04 |
| `blocked_cancellation` | ¿Se detiene una operación bloqueada? | El hilo espera al timeout; el proceso se detiene | Hilo con cancelación en el hook frente a terminar el proceso | Petición sin respuesta; cancelación a los 0,5 s | Segundos hasta detenerse; llamadas al hook | Hilo 2,561 s, 0 llamadas, `future.cancel()` = `False`; proceso 0,002 s | UC-05 A2 |
| `descendants` | ¿Sobrevive un hijo externo a la cancelación? | Desde un hilo, sí | Hilo frente a líder de grupo con `killpg` | `sleep 60` como hijo | Hijo vivo | Hilo: sobrevive; grupo: no | SUP-R02 |
| `crash_isolation` | ¿Un fallo nativo afecta a otro job? | En hilos, sí | Dos hilos frente a dos procesos | `os.abort()` | Código de salida; terminación del otro job | Hilos: −6, el otro no termina; procesos: −6 y 0 | SUP-R03, SUP-R04 |
| `event_loop` | ¿yt-dlp bloquea un event loop? | Sí, si se llama directamente | Llamada en la corrutina frente a `asyncio.to_thread` | 1 descarga de 0,5 s | Retardo máximo de un temporizador de 10 ms | 0,526 s frente a 0,006 s | Capacidad de respuesta de las interfaces |
| `event_overhead` | ¿Cuesta el transporte entre procesos? | Microsegundos | Cola `spawn` frente a una llamada local | 20 000 mensajes | µs por mensaje | 7,29 frente a 1,35 | A-2 |
| `memory_growth` | ¿Crece la memoria con jobs sucesivos? | Poco con el extractor genérico | Un proceso, 30 descargas | 30 × 1 MiB | VmRSS tras 1, 5, 10, 20 y 30 jobs | 59,6 → 61,0 MiB | Reciclado (UC-03 A6), SUP-P04 |
| `consumer_without_cli` | ¿Se puede usar el producto sin la CLI? | Sí, pero con módulos internos | Componentes del producto sin `command_line` | 1 job local | Estado, output, módulos necesarios, tipo observado | `COMPLETED` con su output; 6 módulos internos; observa `WorkerMessage` | A-1, A-2, AAC-02 |

**Reproducibilidad.** Una segunda ejecución completa del script, ya en su forma publicada ([execution-alternatives-linux-run2.json](execution-alternatives-linux-run2.json)), da las mismas conclusiones con diferencias de pocos puntos porcentuales:

| Medida | Ejecución 1 | Ejecución 2 |
|---|---|---|
| Arranque de un proceso | 0,263 s | 0,280 s |
| 4 jobs: secuencial | 2,107 s | 2,154 s |
| 4 jobs: hilos | 0,691 s | 0,714 s |
| 4 jobs: un proceso por job | 2,138 s | 2,157 s |
| 4 jobs: pool | 0,594 s | 0,619 s |
| Cancelación bloqueada en un hilo | 2,561 s | 2,583 s |
| Cancelación bloqueada en un proceso | 0,002 s | 0,002 s |
| Retardo del event loop | 0,526 s | 0,523 s |
| Memoria tras 30 jobs | 61,0 MiB | 61,1 MiB |

Los resultados cualitativos (descendientes, aislamiento ante fallos, programa cliente) son idénticos.

**Limitaciones:**
- Solo Linux. En Windows, `spawn` es el único método y Job Objects sustituye a `killpg`; T33 ya lo demostró para la terminación, y los tiempos y la memoria se miden en la campaña posterior a E3.
- Descargas locales sin extractores reales: la memoria no representa YouTube.
- Dos CPU: el arranque concurrente penaliza más que con más núcleos.
- No demuestra el comportamiento en Android ni en iOS.
