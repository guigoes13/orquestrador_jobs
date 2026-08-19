"""Configuração compartilhada pelos jobs do orquestrador."""

from __future__ import annotations

import configparser
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DatabaseConfig:
    host: str
    database: str
    port: int
    user: str
    password: str
    charset: str


@dataclass(frozen=True)
class SharePointConfig:
    tenant_id: str
    site_url: str
    client_id: str
    client_secret: str


@dataclass(frozen=True)
class BranchConfig:
    id: int
    name: str

    @property
    def product_list(self) -> str:
        return f"ProdutosPDV{self.id:03d}"

    @property
    def inventory_id(self) -> int:
        # No SharePoint, as filiais 4, 5 e 6 foram cadastradas como 5, 6 e 7.
        return self.id if self.id <= 3 else self.id + 1


@dataclass(frozen=True)
class AppConfig:
    database: DatabaseConfig
    sharepoint: SharePointConfig
    branch: BranchConfig
    output_dir: Path


def load_config(path: str | Path = "ConfigApp.ini") -> AppConfig:
    """Carrega a configuração compartilhada a partir do arquivo INI."""
    config_path = Path(path).resolve()
    parser = configparser.ConfigParser()
    if not parser.read(config_path, encoding="utf-8"):
        raise FileNotFoundError(
            f"Arquivo de configuração não encontrado: {config_path}"
        )

    try:
        database = DatabaseConfig(
            host=parser.get("databasePDV", "Server"),
            database=parser.get("databasePDV", "DBpdv"),
            port=parser.getint("databasePDV", "port"),
            user=parser.get("databasePDV", "userDB"),
            password=parser.get("databasePDV", "password"),
            charset=parser.get("databasePDV", "charset"),
        )
        sharepoint = SharePointConfig(
            tenant_id=parser.get("SHAREPOINT", "sharepoint_tenentid"),
            site_url=parser.get("SHAREPOINT", "sharepoint_site").rstrip("/"),
            client_id=parser.get("SHAREPOINT", "cliente_id"),
            client_secret=parser.get("SHAREPOINT", "cliente_secret"),
        )
        branch = BranchConfig(
            id=parser.getint("databaseInventario", "IDfilial"),
            name=parser.get("databaseInventario", "Nomefilial"),
        )
    except (configparser.Error, ValueError) as exc:
        raise ValueError(f"Configuração inválida em {config_path}: {exc}") from exc

    if branch.id not in range(1, 7):
        raise ValueError("databaseInventario.IDfilial deve estar entre 1 e 6")

    return AppConfig(database, sharepoint, branch, config_path.parent)
