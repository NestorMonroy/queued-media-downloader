# ADR-0004: Plataforma objetivo — Windows x64

- **Estado:** Aceptada
- **Fecha:** 2026-11-22

## Contexto

El caso de uso principal es un usuario de Windows con recursos mínimos. Al revisar PyPI, el paquete `deno` 2.9.8 solo publica wheel `win_amd64` para Windows: no hay soporte para Windows ARM64.

## Decisión

La plataforma soportada es **Windows 10/11 x64**. Windows ARM64 queda fuera de alcance por ahora.

## Consecuencias

- `[tool.uv] environments` declara la plataforma para que uv falle con un error claro en plataformas no soportadas, en lugar de fallar a mitad de instalación. Si se desarrolla en Linux o macOS, se añaden sus entornos a la lista.
- Particularidades de Windows que el diseño debe resolver:
  - **Procesos con *spawn*:** guard `if __name__ == "__main__"` y función `main()`.
  - **Procesos hijos:** al terminar un worker, ffmpeg y deno no mueren solos ([ADR-0008](adr-0008-process-based-worker-pool.md)).
  - **Rutas largas:** límite de 260 caracteres; limitar nombres con `trim_file_name` y elegir con cuidado la carpeta de descargas.
  - **Antivirus:** puede bloquear archivos `.part`; mitigar con `file_access_retries`.
  - **Cookies de navegador:** verificar en el prototipo la lectura de cookies de Chrome; Firefox suele funcionar.
