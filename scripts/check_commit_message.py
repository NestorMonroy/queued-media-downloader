"""Comprueba un mensaje de commit con las convenciones del proyecto.

Reglas de Tim Pope: asunto de 50 caracteres como máximo, en mayúscula y sin
punto final; una línea en blanco tras el asunto; líneas del cuerpo de 72
caracteres como máximo.

Uso, desde la raíz del repositorio (Linux o Windows):

    uv run python scripts/check_commit_message.py RUTA_DEL_MENSAJE

Termina con 0 si el mensaje cumple las reglas y con 1 si no; escribe el
asunto, su longitud y los incumplimientos.
"""

import sys
from pathlib import Path

MAX_SUBJECT_LENGTH = 50
MAX_BODY_LINE_LENGTH = 72


def commit_message_problems(message: str) -> list[str]:
    """Incumplimientos de las reglas en el texto del mensaje; vacía si cumple."""
    lines = message.rstrip("\n").split("\n")
    subject = lines[0]
    problems: list[str] = []
    if len(subject) > MAX_SUBJECT_LENGTH:
        problems.append(
            f"subject has {len(subject)} characters (max {MAX_SUBJECT_LENGTH})"
        )
    if not subject[:1].isupper():
        problems.append("subject is not capitalized")
    if subject.endswith("."):
        problems.append("subject ends with a period")
    if len(lines) < 3 or lines[1] != "":
        problems.append("no blank line between subject and body")
    long_lines = [
        number
        for number, line in enumerate(lines[2:], start=3)
        if len(line) > MAX_BODY_LINE_LENGTH
    ]
    if long_lines:
        problems.append(
            f"body lines over {MAX_BODY_LINE_LENGTH} characters: {long_lines}"
        )
    return problems


def main() -> int:
    """Comprueba el archivo indicado y devuelve el código de salida."""
    if len(sys.argv) != 2:
        print("usage: check_commit_message.py MESSAGE_FILE", file=sys.stderr)
        return 2
    message = Path(sys.argv[1]).read_text(encoding="utf-8")
    subject = message.split("\n", 1)[0]
    problems = commit_message_problems(message)
    verdict = "OK" if not problems else "; ".join(problems)
    print(f"[{len(subject)}] {subject}: {verdict}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
