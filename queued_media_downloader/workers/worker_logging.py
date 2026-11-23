"""Lleva los registros de logging de los workers al proceso principal.

Un worker arrancado con spawn no hereda la configuración de logging, y varios
procesos no deben escribir en el mismo archivo (en Windows, además, el archivo
queda bloqueado). Cada worker envía sus registros por su propia cola; el
proceso principal los entrega a su logging, que decide dónde escribirlos.
"""

import logging
from logging.handlers import QueueHandler
from typing import Any


def configure_worker_logging(log_queue: Any) -> None:
    """Envía por log_queue todos los registros del proceso del worker.

    Se llama al empezar el worker, antes de crear la MediaSource.
    """
    root_logger = logging.getLogger()
    root_logger.handlers = [QueueHandler(log_queue)]
    root_logger.setLevel(logging.DEBUG)


def forward_log_record(record: logging.LogRecord) -> None:
    """Entrega un registro de un worker al logger del mismo nombre en este proceso.

    Así pasa por los handlers y filtros del proceso principal como si se
    hubiera emitido aquí.
    """
    logging.getLogger(record.name).handle(record)
