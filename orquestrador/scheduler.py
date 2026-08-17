"""Orquestrador leve para processos recorrentes executados no servidor local."""

from __future__ import annotations

import configparser
import logging
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from pathlib import Path
from time import monotonic

from .registry import JOBS, JobFunction

LOGGER = logging.getLogger("orchestrator")
PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass
class ScheduledJob:
    name: str
    function: JobFunction
    interval: timedelta
    next_run: datetime
    future: Future[None] | None = None

    @property
    def running(self) -> bool:
        return self.future is not None and not self.future.done()


def configure_logging(log_dir: str | Path = "logs", verbose: bool = False) -> None:
    """Envia logs ao console e a um arquivo limitado a cinco backups."""
    directory = Path(log_dir)
    directory.mkdir(parents=True, exist_ok=True)
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")

    root = logging.getLogger()
    root.setLevel(logging.DEBUG if verbose else logging.INFO)
    root.handlers.clear()
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    file_handler = RotatingFileHandler(
        directory / "orchestrator.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    root.addHandler(console)
    root.addHandler(file_handler)


def load_jobs(path: str | Path, now: datetime | None = None) -> list[ScheduledJob]:
    """Carrega somente jobs habilitados e valida nomes e intervalos."""
    config_path = Path(path)
    parser = configparser.ConfigParser()
    if not parser.read(config_path, encoding="utf-8"):
        raise FileNotFoundError(f"Configuração do orquestrador não encontrada: {config_path.resolve()}")

    current_time = now or datetime.now()
    scheduled: list[ScheduledJob] = []
    for section in parser.sections():
        if not section.startswith("job:") or not parser.getboolean(section, "enabled", fallback=True):
            continue
        name = section.removeprefix("job:").strip()
        if name not in JOBS:
            raise ValueError(f"Job desconhecido em [{section}]. Disponíveis: {', '.join(JOBS)}")
        seconds = parser.getfloat(section, "interval_seconds", fallback=0)
        minutes = parser.getfloat(section, "interval_minutes", fallback=0)
        interval_seconds = seconds or minutes * 60
        if interval_seconds <= 0:
            raise ValueError(f"[{section}] precisa de interval_seconds ou interval_minutes maior que zero")
        run_on_start = parser.getboolean(section, "run_on_start", fallback=False)
        interval = timedelta(seconds=interval_seconds)
        scheduled.append(ScheduledJob(
            name=name,
            function=JOBS[name],
            interval=interval,
            next_run=current_time if run_on_start else current_time + interval,
        ))
    if not scheduled:
        raise ValueError("Nenhum job está habilitado no arquivo do orquestrador")
    return scheduled


def execute_job(name: str, function: JobFunction) -> None:
    """Executa um job registrando início, duração e eventual falha."""
    started = monotonic()
    LOGGER.info("Job %s iniciado", name)
    try:
        function()
    except Exception:
        LOGGER.exception("Job %s falhou apó %.1f segundos", name, monotonic() - started)
        raise
    LOGGER.info("Job %s concluído em %.1f segundos", name, monotonic() - started)


class Orchestrator:
    def __init__(self, jobs: list[ScheduledJob]):
        self.jobs = jobs
        self.stop_event = threading.Event()
        self.executor = ThreadPoolExecutor(max_workers=max(1, len(jobs)), thread_name_prefix="job")
        self._lock = threading.Lock()

    def stop(self, *_args: object) -> None:
        LOGGER.info("Encerramento solicitado; aguardando jobs em execução")
        self.stop_event.set()

    def run_forever(self) -> None:
        LOGGER.info("Orquestrador iniciado com %d job(s)", len(self.jobs))
        for job in self.jobs:
            LOGGER.info("%s: próxima execução em %s", job.name, job.next_run)

        while not self.stop_event.is_set():
            now = datetime.now()
            for job in self.jobs:
                if now < job.next_run:
                    continue
                if job.running:
                    # Nunca abre duas execuções simultâneas do mesmo job.
                    LOGGER.warning("Job %s ainda está executando; ciclo ignorado", job.name)
                else:
                    job.future = self.executor.submit(execute_job, job.name, job.function)
                job.next_run = now + job.interval
            self.stop_event.wait(1)

        self.executor.shutdown(wait=True, cancel_futures=False)
        LOGGER.info("Orquestrador encerrado")

    def start_background(self) -> threading.Thread:
        """Inicia o ciclo do scheduler sem bloquear o servidor Flask."""
        thread = threading.Thread(target=self.run_forever, name="scheduler", daemon=True)
        thread.start()
        return thread

    def run_now(self, name: str) -> bool:
        """Dispara um job se ele existir e não estiver em execução."""
        with self._lock:
            job = next((item for item in self.jobs if item.name == name), None)
            if job is None:
                raise KeyError(name)
            if job.running:
                return False
            job.future = self.executor.submit(execute_job, job.name, job.function)
            job.next_run = datetime.now() + job.interval
            return True

    def status(self) -> list[dict[str, object]]:
        with self._lock:
            return [
                {
                    "name": job.name,
                    "running": job.running,
                    "next_run": job.next_run.isoformat(timespec="seconds"),
                    "interval_seconds": job.interval.total_seconds(),
                }
                for job in self.jobs
            ]
