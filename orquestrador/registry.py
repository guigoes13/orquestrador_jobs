"""Registro dos jobs disponíveis para o orquestrador.

Para adicionar um processamento, crie uma função sem argumentos e inclua-a em
``JOBS``. O agendamento fica separado, no arquivo ``orchestrator.ini``.
"""

from collections.abc import Callable
from pathlib import Path

from jobs.processar_produtos import run

JobFunction = Callable[[], None]
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def processar_produtos() -> None:
    """Sincroniza produtos, vendas e inventário usando o ConfigApp.ini."""
    run(PROJECT_ROOT / "ConfigApp.ini")


JOBS: dict[str, JobFunction] = {
    "processar_produtos": processar_produtos,
}
