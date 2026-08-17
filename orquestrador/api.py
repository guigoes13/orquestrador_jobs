"""API Flask que centraliza o scheduler e seus jobs."""

from __future__ import annotations

from pathlib import Path

from flask import Flask, jsonify

from .scheduler import Orchestrator, load_jobs


def create_app(config_path: str | Path, start_scheduler: bool = True) -> Flask:
    app = Flask(__name__)
    orchestrator = Orchestrator(load_jobs(config_path))
    app.extensions["orchestrator"] = orchestrator
    if start_scheduler:
        orchestrator.start_background()

    @app.get("/health")
    def health():
        return jsonify(status="ok", jobs=len(orchestrator.jobs))

    @app.get("/jobs")
    def jobs_status():
        return jsonify(orchestrator.status())

    @app.post("/jobs/<name>/run")
    def run_job(name: str):
        try:
            started = orchestrator.run_now(name)
        except KeyError:
            return jsonify(error=f"Job desconhecido: {name}"), 404
        if not started:
            return jsonify(error=f"Job {name} já está em execução"), 409
        return jsonify(job=name, status="started"), 202

    return app
