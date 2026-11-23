# queued-media-downloader

Descargador de contenidos con cola persistente, construido sobre la librería yt-dlp.

> **Estado:** fin de la fase de Inicio (RUP). Todavía no hay código; la siguiente iteración es E1 de Elaboración.

## Documentación

| Documento | Contenido |
|---|---|
| [doc/requirements/vision.md](doc/requirements/vision.md) | Visión: problema, posicionamiento, alcance y criterios de éxito |
| [doc/requirements/use-case-model.md](doc/requirements/use-case-model.md) | Modelo de casos de uso y especificaciones |
| [doc/requirements/supplementary-specification.md](doc/requirements/supplementary-specification.md) | Requisitos no funcionales (FURPS+) |
| [doc/project-management/risk-list.md](doc/project-management/risk-list.md) | Lista de riesgos |
| [doc/project-management/iteration-plan-e1.md](doc/project-management/iteration-plan-e1.md) | Plan de la iteración E1: slices, tareas y camino crítico |
| [doc/process/development-case.md](doc/process/development-case.md) | Caso de desarrollo: RUP con enfoque híbrido, slices, tareas y roles |
| [doc/notes/](doc/notes/README.md) | Decisiones de arquitectura (ADR) |
| [doc/design/00-vocabulary.md](doc/design/00-vocabulary.md) | Vocabulario: una palabra por concepto |
| [doc/design/01-architecture.md](doc/design/01-architecture.md) | Paquetes por componente, API pública, grafo de dependencias comprobado, entidades y ciclo de vida de un job |
| [doc/design/02-flows-persistence-and-operations.md](doc/design/02-flows-persistence-and-operations.md) | Flujos, esquema SQLite, contrato del worker, línea de comandos y pruebas |
| [doc/reference/](doc/reference/) | Guías de clean code y principios de nombres (referencia obligatoria, ADR-0011) |

## Estructura

```text
queued-media-downloader/
├── README.md
├── LICENSE            The Unlicense + excepción de vendor/ffmpeg (LGPL)
├── .gitignore
└── doc/
    ├── requirements/        Visión, casos de uso, especificación complementaria
    ├── project-management/  Riesgos y planes de iteración
    ├── process/             Caso de desarrollo
    ├── design/              Vocabulario y diseño por partes
    ├── notes/               ADR
    └── reference/           Material de referencia aportado
```

El paquete `queued_media_downloader/`, `tests/` y `vendor/` se crearán en la etapa de implementación, según el [diseño](doc/design/01-architecture.md#2-estructura-de-paquetes).

## Licencia

[The Unlicense](LICENSE), salvo el contenido de `vendor/ffmpeg/`, que conserva su licencia LGPL ([ADR-0007](doc/notes/adr-0007-project-license-unlicense.md)).
