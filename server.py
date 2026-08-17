"""Servidor Flask que mantém os jobs em execução."""

import configparser
from pathlib import Path

from waitress import serve

from orquestrador.api import create_app
from orquestrador.scheduler import configure_logging


PROJECT_DIR = Path(__file__).resolve().parent
CONFIG_FILE = PROJECT_DIR / "orchestrator.ini"


def main() -> None:
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE, encoding="utf-8")

    host = config.get("server", "host", fallback="127.0.0.1")
    port = config.getint("server", "port", fallback=5000)

    configure_logging(PROJECT_DIR / "logs")
    app = create_app(CONFIG_FILE)

    serve(app, host=host, port=port)


if __name__ == "__main__":
    main()
