from collections.abc import Callable
from pathlib import Path

from jobs.processar_caixa import processar_caixa
from jobs.processar_produtos import processar_produtos

JobFunction = Callable[[], None]
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _processar_caixa() -> None:
    processar_caixa(PROJECT_ROOT / "ConfigApp.ini")


def _processar_produtos() -> None:
    processar_produtos(PROJECT_ROOT / "ConfigApp.ini")


JOBS: dict[str, JobFunction] = {
    "processar_caixa": _processar_caixa,
    "processar_produtos": _processar_produtos,
}
