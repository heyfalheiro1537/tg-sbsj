"""Conexão e criação do esquema."""
import os
from pathlib import Path

import psycopg
from psycopg.types.json import Jsonb  # noqa: F401  (reexportado)

DB = Path(__file__).resolve().parent.parent / "db"
DSN_PADRAO = "postgresql://tg@localhost:54329/tg"


def conectar(dsn=None):
    return psycopg.connect(dsn or os.environ.get("TG_DSN", DSN_PADRAO), autocommit=False)


def criar_esquema(conn, postgis=False):
    arquivos = ["01_esquema.sql", "02_leitura.sql"] + (["03_postgis.sql"] if postgis else [])
    with conn.cursor() as cur:
        for a in arquivos:
            cur.execute((DB / a).read_text())
    conn.commit()
