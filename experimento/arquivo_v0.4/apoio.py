"""Funções pequenas que o notebook usa para não repetir código nas células."""
import os
import re
from datetime import timedelta

import psycopg

from fontes import ARP, THR16, THR34, gms
from tg import banco, relogio

ADMIN = os.environ.get("TG_DSN_ADMIN", "postgresql://tg@localhost:54329/postgres")
BASE = ADMIN.rsplit("/", 1)[0]
ELEMENTO = "RWY_16_34"


def banco_da_execucao(exec_id):
    """Banco novo, só desta execução, com o esquema carregado. Não é apagado depois."""
    nome = "tg_exp_" + re.sub(r"[^a-z0-9]", "_", exec_id.lower())
    with psycopg.connect(ADMIN, autocommit=True) as a:
        a.execute(f"CREATE DATABASE {nome}")
    conn = psycopg.connect(f"{BASE}/{nome}")
    banco.criar_esquema(conn)
    return conn, nome


def reconectar(nome):
    return psycopg.connect(f"{BASE}/{nome}")


def avancar_ate(conn, run, instante):
    agora = relogio.agora(conn, run)
    if instante < agora:
        raise relogio.RelogioError("o relógio só avança")
    return relogio.avancar(conn, run, segundos=(instante - agora).total_seconds())


def referente(p, fonte):
    return {"lat": gms(p["lat"]), "lon": gms(p["lon"]), "elev_m": p["elev_m"], "gund_m": p["gund_m"], "fonte": fonte}


def corpo_referencial(thr34=THR34, fonte34="eAIP 20-2026, AD 2.12"):
    return {
        "datum": "SIRGAS2000",
        "origem_local": "THR16",
        "referentes": {
            "THR16": referente(THR16, "eAIP 20-2026, AD 2.12"),
            "THR34": referente(thr34, fonte34),
            "ARP": {"lat": gms(ARP["lat"]), "lon": gms(ARP["lon"]), "fonte": "ADC AIRAC 2604A1 (AD 2.2)"},
        },
        "elementos_lineares": {ELEMENTO: ["THR16", "THR34"]},
    }


def seed(ref, s=0.0, o=0.0, elemento=ELEMENTO):
    return {"elemento": elemento, "referente": ref, "s": float(s), "o": float(o)}


def contar(conn, sql, *params):
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchone()[0]


def maior_event_id(conn, run):
    return contar(conn, "SELECT coalesce(max(event_id), 0) FROM event WHERE run_id = %s", run)


def depois_de(conn, run, marco):
    with conn.cursor() as cur:
        cur.execute("""SELECT e.event_id, e.feature_id, e.feature_type, e.event_type, array_agg(f.path ORDER BY f.path)
                       FROM event e LEFT JOIN event_field f USING (event_id)
                       WHERE e.run_id = %s AND e.event_id > %s GROUP BY 1, 2, 3, 4 ORDER BY 1""", (run, marco))
        return cur.fetchall()


def um_segundo_antes(t):
    return t - timedelta(seconds=1)
