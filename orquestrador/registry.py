"""Registro dos jobs disponíveis para o orquestrador.

Para adicionar um processamento, crie uma função sem argumentos e inclua-a em
``JOBS``. O agendamento fica separado, no arquivo ``orchestrator.ini``.
"""

from collections.abc import Callable
from pathlib import Path

from jobs.processar_produtos import processar_produtos

JobFunction = Callable[[], None]
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _processar_produtos() -> None:
    """Sincroniza produtos, vendas e inventário usando o ConfigApp.ini."""
    processar_produtos(PROJECT_ROOT / "ConfigApp.ini")


JOBS: dict[str, JobFunction] = {
    "processar_produtos": _processar_produtos,
}
