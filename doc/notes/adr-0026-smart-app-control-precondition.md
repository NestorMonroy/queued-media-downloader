# ADR-0026: Smart App Control desactivado como precondición de E1

- **Estado:** Aceptada
- **Fecha:** 2026-11-23
- **Ajusta:** [ADR-0004](adr-0004-windows-x64-target-platform.md) (plataforma objetivo)

## Contexto

En la evaluación de E1 en Windows (T19), `uv sync` no llegó a ejecutarse: Windows bloqueó `uv.exe` con el mensaje "Una directiva de Control de aplicaciones bloqueó este archivo". El diagnóstico en el equipo del Evaluador mostró:

| Comprobación | Resultado |
|---|---|
| Registro de Code Integrity | Eventos 3033 y 3077: `uv.exe` no cumple el nivel de firma exigido |
| `VerifiedAndReputablePolicyState` | `1`: Smart App Control activado, bloqueando |
| Firma de `uv.exe` | Sin firmar |
| Firma de los 9 binarios de `vendor/ffmpeg/` | Sin firmar |
| Antivirus | Sin detecciones |
| Equipo administrado | No (sin dominio, Azure AD ni Enterprise) |

Smart App Control bloquea el código sin firmar que no tiene reputación conocida. Desde Windows 11 25H2 puede activarse en cualquier equipo, no solo en una instalación limpia, así que el caso afectará a parte de los usuarios objetivo.

El diseño ejecuta varios binarios que el proyecto no firma y, en parte, no controla: `uv.exe`, el Python que descarga uv, los lanzadores que uv genera en `.venv\Scripts`, `deno.exe` y la build de ffmpeg ([ADR-0003](adr-0003-packaging-with-uv-and-pyproject.md), [ADR-0005](adr-0005-vendored-ffmpeg-lgpl-shared.md)).

Opciones evaluadas:
1. **Exigir Smart App Control desactivado.** Sin cambios de código; excluye a quien lo tenga activo y le pide reducir su seguridad.
2. **Soportar Smart App Control.** Cada binario ejecutado debe estar firmado o tener reputación. No es viable con uv, porque no controlamos uv, su Python ni sus lanzadores: exige otra forma de distribución (por ejemplo, un instalador MSIX firmado con un certificado de firma de código).
3. **Híbrido:** la opción 1 como precondición documentada durante Elaboración, y la opción 2 evaluada al planificar la distribución.

## Decisión

**Opción 3.**

- **Precondición de E1:** Smart App Control desactivado o en modo de evaluación (`VerifiedAndReputablePolicyState` distinto de `1`). Se documenta en UC-01 y en el guion de evaluación.
- **Riesgo nuevo, R-13,** de impacto alto: Smart App Control impide ejecutar el proyecto.
- **La opción 2 se evalúa en la fase de Transición,** al planificar la distribución. Allí se decide si se firma (y con qué certificado), si se cambia el empaquetado o si se mantiene la precondición.

## Consecuencias

- El Evaluador decide si desactiva Smart App Control en su equipo o si evalúa en otra máquina o en una máquina virtual. Es una decisión de seguridad de quien administra el equipo, no del proyecto.
- UC-01 gana un flujo alternativo: el sistema no puede ejecutar uv, o un binario del proyecto, por Smart App Control.
- `diagnose` no puede detectar este caso cuando el bloqueado es `uv.exe`, porque nada del proyecto llega a ejecutarse. El guion de evaluación incluye la comprobación manual.
- Pendiente para la fase de Transición: medir qué binarios bloquea Smart App Control además de uv, verificar la firma de `deno.exe`, del Python de uv y de los lanzadores, y estimar el coste de un certificado de firma de código.
