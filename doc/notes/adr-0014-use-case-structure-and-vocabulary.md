# ADR-0014: Estructura por casos de uso y vocabulario del proyecto

- **Estado:** Aceptada
- **Fecha:** 2026-11-22
- **Nota:** la estructura de paquetes queda reemplazada por [ADR-0016](adr-0016-component-packages-and-flat-layout.md); el vocabulario sigue vigente.
- **Nota:** el prefijo de variables de entorno pasa a ser `QUEUED_MEDIA_DOWNLOADER_` en [ADR-0015](adr-0015-project-and-package-name.md).
- **Ajusta:** los términos usados en ADR-0006, ADR-0008, ADR-0009 y ADR-0010 (ver la tabla de equivalencias)

## Contexto

La primera versión del diseño organizaba el código por capas técnicas (`domain/`, `application/`, `infrastructure/`, `cli/`) y tenía nombres que violaban los [principios de nombres](../reference/naming-principles/clean-code-naming-principles.md):
- La estructura decía **cómo está hecho** el sistema, no **qué hace** (#9, #12).
- `JobObjectProcessTreeTerminator` usaba *job* con dos significados (#2, #8).
- `attach` necesitaba un docstring para entenderse (#1).
- Un mismo concepto tenía varios nombres: *task* y *job*, *cancel* y *terminate* mezclados en `cancel(force=True)` (#8).
- Codificaciones y ruido: `ix_`/`ux_`, `options_json`, `data_directory`, `YTDLPGC_` (#3, #4, #6).

## Decisión

1. **Estructura por casos de uso.** Los paquetes de primer nivel son `use_cases/` (lo que el usuario puede hacer), `download_queue/` (reglas de la cola e interfaces) y un paquete por herramienta, nombrado por su propósito: `job_storage/`, `job_execution/`, `media_extraction/`, `ffmpeg_discovery/`, `command_line/`. Las herramientas son plugins de las reglas (#10) y las dependencias apuntan hacia dentro (#11). Detalle en el [diseño, Parte 1](../design/01-architecture.md).
2. **Vocabulario único.** El documento [00-vocabulary.md](../design/00-vocabulary.md) fija una palabra por concepto. Todo nombre nuevo sale de ahí; un concepto nuevo se añade ahí antes de usarse.

## Equivalencias con decisiones anteriores

| Término anterior | Término vigente |
|---|---|
| Comando `doctor` | Comando `diagnose` (caso de uso `diagnose_environment`) |
| `JobRepository` | `JobStore` + `JobRequestInbox` |
| `MediaGateway` | `MediaSource` |
| `WorkerPool.cancel(job_id, force)` | `request_cancellation(job_id)` y `terminate_worker_running(job_id)` |
| `CANCEL_REQUESTED` | `CANCELLATION_REQUESTED` |
| `format_id` (del job) | `selected_format_id` |
| `job_commands` | `job_requests` |
| `task_queue` / `control_queue` | `instruction_queue` / `cancellation_queue` |
| `ResolvedAsSingleMedia`, `EntriesDiscovered` | `SingleMediaFound`, `PlaylistEntriesFound` |
| `data_directory`, `YTDLPGC_` | `state_directory`, `YT_DLP_GUI_CLONE_` |
| `add` (comando de la CLI) | `enqueue` |

## Consecuencias

- Al abrir `src/`, lo primero que se ve son los casos de uso.
- Una GUI futura es otro plugin que llama a los mismos casos de uso.
- Los ADR anteriores no se reescriben: esta tabla indica cómo leer sus términos.
- Toda revisión de código comprueba los nombres contra el vocabulario.
