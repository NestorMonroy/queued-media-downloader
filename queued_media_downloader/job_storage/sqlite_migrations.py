"""Migraciones del esquema SQLite, versionadas con PRAGMA user_version."""

import sqlite3
from dataclasses import dataclass
from importlib.resources import files

MIGRATIONS_DIRECTORY = files(__package__) / "migrations"


@dataclass(frozen=True, slots=True)
class Migration:
    """Script SQL numerado que lleva el esquema a la versión number."""

    number: int
    script: str


def load_migrations() -> list[Migration]:
    """Lee los scripts NNNN_descripcion.sql en orden de número."""
    migrations = [
        Migration(number=int(resource.name[:4]), script=resource.read_text("utf-8"))
        for resource in MIGRATIONS_DIRECTORY.iterdir()
        if resource.name.endswith(".sql")
    ]
    return sorted(migrations, key=lambda migration: migration.number)


LATEST_SCHEMA_VERSION = max(migration.number for migration in load_migrations())


def apply_migrations(connection: sqlite3.Connection) -> None:
    """Aplica, cada una en su transacción, las migraciones aún no aplicadas."""
    current_version = connection.execute("PRAGMA user_version").fetchone()[0]
    for migration in load_migrations():
        if migration.number > current_version:
            # executescript confirma cualquier transacción abierta; BEGIN y
            # COMMIT explícitos hacen atómicos el script y el cambio de versión.
            try:
                connection.executescript(
                    f"BEGIN;\n{migration.script}\n"
                    f"PRAGMA user_version = {migration.number};\nCOMMIT;"
                )
            except BaseException:
                # Si una sentencia falla, executescript se detiene con la
                # transacción abierta: se deshace para que la base de datos
                # quede en la última versión completa, no a medio migrar.
                if connection.in_transaction:
                    connection.rollback()
                raise
