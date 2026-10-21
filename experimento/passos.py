"""Apoio do notebook: registro dos vereditos e pequenas funções repetidas.

O notebook usa a biblioteca aeroledger para tudo o que é o artefato (escrever,
ler, derivar, verificar). Este módulo só cuida do que é do experimento:

  * conferir que o protocolo está congelado antes de rodar sobre o SBSJ;
  * registrar cada verificação (observado, predito, tolerância, veredito) em
    resultados/execucoes.jsonl, arquivo em que só se acrescenta;
  * criar um banco só desta execução;
  * montar o referencial e as seeds do SBSJ a partir de fontes.py.

Modo ENSAIO (variável AEROLEDGER_ENSAIO=1): usa o aeródromo fictício de
fontes_ensaio.py, não exige protocolo congelado e não grava no registro. Serve
para conferir que as células rodam antes do congelamento.
"""
import hashlib
import importlib
import json
import os
import re
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

import psycopg
import yaml

import aeroledger as al

RAIZ = Path(__file__).resolve().parent.parent
PROTOCOLO_V04 = RAIZ / "protocolo" / "protocolo.yaml"
PROTOCOLO = RAIZ / "protocolo" / "v0.5" / "protocolo.yaml"
HASHES = RAIZ / "protocolo" / "v0.5" / "PROTOCOLO.sha256"
LOG = RAIZ / "resultados" / "execucoes.jsonl"

ENSAIO = bool(os.environ.get("AEROLEDGER_ENSAIO"))
F = importlib.import_module("fontes_ensaio" if ENSAIO else "fontes")

ADMIN = (os.environ.get("AEROLEDGER_DSN_ADMIN") or os.environ.get("TG_DSN_ADMIN")
         or "postgresql://tg@localhost:54329/postgres")
BASE = ADMIN.rsplit("/", 1)[0]
ELEMENTO = "RWY_16_34"


# ---------------------------------------------------------------- protocolo

def _git(*args):
    return subprocess.run(["git", "-C", str(RAIZ), *args], capture_output=True, text=True).stdout.strip()


def sha256_arquivo(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def conferir_congelamento():
    """O protocolo v0.5 está congelado, com o hash registrado e sem alteração local?"""
    p = yaml.safe_load(PROTOCOLO.read_text())
    no_disco = sha256_arquivo(PROTOCOLO)
    registrado = None
    if HASHES.exists():
        for linha in HASHES.read_text().splitlines():
            if linha.endswith("protocolo.yaml"):
                registrado = linha.split()[0]
    alterado = _git("status", "--porcelain", "--", str(PROTOCOLO.relative_to(RAIZ))) != ""
    commit = _git("log", "-1", "--format=%h", "--", str(PROTOCOLO.relative_to(RAIZ)))
    return {"versao": p["protocolo"]["versao"], "estado": p["protocolo"]["estado"], "sha256": no_disco,
            "registrado": registrado, "commit": commit,
            "congelado": p["protocolo"]["estado"] == "congelado" and registrado == no_disco and not alterado}


def _indice():
    """Predições: as de H2 vêm da v0.4 (reusadas sem alteração), as demais da v0.5."""
    v04 = yaml.safe_load(PROTOCOLO_V04.read_text())
    idx = {}
    for ato in ("ato1", "ato4"):
        for v in v04["H2"][ato]["verificacoes"]:
            idx[v["id"]] = {**v, "experimento": "E2"}
    v05 = yaml.safe_load(PROTOCOLO.read_text())
    for e, corpo in v05["experimentos"].items():
        for v in corpo.get("verificacoes", []):
            if isinstance(v, dict):
                idx[v["id"]] = {**v, "experimento": e}
    return idx, v04, v05


# ---------------------------------------------------------------- registro

class Registro:
    def __init__(self):
        self.ensaio = ENSAIO
        self.congelamento = conferir_congelamento()
        if not self.ensaio and not self.congelamento["congelado"]:
            raise RuntimeError(
                "o protocolo v0.5 não está congelado; rode em modo ensaio (AEROLEDGER_ENSAIO=1) "
                f"ou congele-o antes: {self.congelamento}")
        self.idx, self.v04, self.v05 = _indice()
        self.commit = _git("rev-parse", "--short", "HEAD") or "sem-git"
        self.commit_limpo = _git("status", "--porcelain", "--", "artefato", "experimento") == ""
        prefixo = "ensaio-" if self.ensaio else ""
        self.exec_id = prefixo + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + self.commit
        self.vereditos = []
        self._log({"tipo": "inicio", "protocolo": self.congelamento, "commit_artefato": self.commit,
                   "commit_limpo": self.commit_limpo, "aeroledger": al.__version__})

    def _log(self, d):
        if self.ensaio:
            return
        d = {"exec_id": self.exec_id, "quando": datetime.now(timezone.utc).isoformat(), **d}
        LOG.parent.mkdir(exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(d, ensure_ascii=False, default=str) + "\n")

    def nota(self, texto, **dados):
        self._log({"tipo": "nota", "texto": texto, **dados})

    def escrever(self, conn, run_id, *args, **kw):
        """aeroledger.escrever com registro da escrita."""
        eid, h = al.escrever(conn, run_id, *args, **kw)
        self._log({"tipo": "escrita", "run_id": run_id, "event_id": eid, "feature_id": args[0],
                   "event_type": args[2], "hash": h})
        return eid, h

    def _fechar(self, vid, observado, predito, passou, tolerancia=None, nota=None):
        v = {"id": vid, "experimento": self.idx.get(vid, {}).get("experimento"), "observado": observado,
             "predito": predito, "tolerancia": tolerancia, "veredito": "PASSOU" if passou else "FALHOU", "nota": nota}
        self.vereditos.append(v)
        self._log({"tipo": "verificacao", **v})
        sinal = "✔" if passou else "✘"
        tol = f" ± {tolerancia}" if tolerancia not in (None, 0) else ""
        marca = "[ENSAIO] " if self.ensaio else ""
        print(f"{marca}{sinal} {vid}: observado {fmt(observado)} | predito {fmt(predito)}{tol} → {v['veredito']}"
              + (f"  ({nota})" if nota else ""))
        return passou

    def numerico(self, vid, observado, angular=False):
        v = self.idx[vid]
        pub, tol = v["publicado"], v["tolerancia"]
        dif = abs(observado - pub)
        if angular:
            dif = min(dif, 360 - dif)
        return self._fechar(vid, observado, pub, dif <= tol, tol, f"|Δ| = {dif:.4f}")

    def limite(self, vid, observado, maximo, nota=None):
        return self._fechar(vid, observado, f"≤ {maximo}", observado <= maximo, None, nota)

    def igual(self, vid, observado, esperado, nota=None):
        return self._fechar(vid, observado, esperado, observado == esperado, 0, nota)

    def condicao(self, vid, passou, observado, nota=None):
        """Verificação descrita no protocolo por extenso: o predito é o texto da predição."""
        return self._fechar(vid, observado, self.idx[vid].get("predicao", vid), bool(passou), None, nota)

    def tabela(self):
        linhas = ["| Verificação | Experimento | Observado | Veredito |", "|---|---|---|---|"]
        for v in self.vereditos:
            linhas.append(f"| {v['id']} | {v['experimento']} | {fmt(v['observado'])} | {v['veredito']} |")
        return "\n".join(linhas)

    def resumo(self):
        por = {}
        for v in self.vereditos:
            d = por.setdefault(v["experimento"], {"PASSOU": 0, "FALHOU": 0})
            d[v["veredito"]] += 1
        self._log({"tipo": "resumo", "por_experimento": por})
        return por


def fmt(x):
    if isinstance(x, float):
        return f"{x:.4f}" if abs(x) < 1e4 else f"{x:.1f}"
    if isinstance(x, (list, tuple)) and len(x) > 6:
        return f"[{len(x)} itens]"
    return str(x)


# ---------------------------------------------------------------- banco e tempo

def banco_da_execucao(exec_id):
    """Banco novo, só desta execução, com o esquema da biblioteca. Não é apagado depois."""
    nome = "tg_exp_" + re.sub(r"[^a-z0-9]", "_", exec_id.lower())
    with psycopg.connect(ADMIN, autocommit=True) as a:
        a.execute(f"CREATE DATABASE {nome}")
    conn = psycopg.connect(f"{BASE}/{nome}")
    al.criar_esquema(conn)
    return conn, nome


def reconectar(nome):
    return psycopg.connect(f"{BASE}/{nome}")


def copia_do_banco(origem, destino):
    """Cópia de 'origem' (que não pode ter conexões abertas: o Postgres exige)."""
    with psycopg.connect(ADMIN, autocommit=True) as a:
        a.execute(f"DROP DATABASE IF EXISTS {destino}")
        a.execute(f"CREATE DATABASE {destino} TEMPLATE {origem}")
    return psycopg.connect(f"{BASE}/{destino}")


def apagar_banco(nome):
    with psycopg.connect(ADMIN, autocommit=True) as a:
        a.execute(f"DROP DATABASE IF EXISTS {nome}")


def avancar_ate(conn, run, instante):
    agora = al.agora(conn, run)
    if instante < agora:
        raise al.RelogioError("o relógio só avança")
    return al.avancar(conn, run, segundos=(instante - agora).total_seconds())


def um_segundo_antes(t):
    return t - timedelta(seconds=1)


# ---------------------------------------------------------------- SBSJ no modelo

def referente(p, fonte):
    return {"lat": F.gms(p["lat"]), "lon": F.gms(p["lon"]), "elev_m": p["elev_m"], "gund_m": p["gund_m"],
            "fonte": fonte}


def corpo_referencial(thr34=None, fonte34="eAIP 20-2026, AD 2.12"):
    return {
        "datum": "SIRGAS2000",
        "origem_local": "THR16",
        "referentes": {
            "THR16": referente(F.THR16, "eAIP 20-2026, AD 2.12"),
            "THR34": referente(thr34 or F.THR34, fonte34),
        },
        "elementos_lineares": {ELEMENTO: ["THR16", "THR34"]},
    }


def seed(ref, s=0.0, o=0.0):
    return {"elemento": ELEMENTO, "referente": ref, "s": float(s), "o": float(o)}


def contar(conn, sql, *params):
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchone()[0]


def maior_event_id(conn, run):
    return contar(conn, "SELECT coalesce(max(event_id), 0) FROM event WHERE run_id = %s", run)


def depois_de(conn, run, marco):
    """[(event_id, feature_id, feature_type, event_type, [paths])] escritos depois de 'marco'."""
    with conn.cursor() as cur:
        cur.execute("""SELECT e.event_id, e.feature_id, e.feature_type, e.event_type,
                              array_remove(array_agg(f.path ORDER BY f.path), NULL)
                       FROM event e LEFT JOIN event_field f USING (event_id)
                       WHERE e.run_id = %s AND e.event_id > %s GROUP BY 1, 2, 3, 4 ORDER BY 1""", (run, marco))
        return cur.fetchall()


# ---------------------------------------------------------------- exportação (E5)

def exportar(conn, run, caminho):
    """Publica o run como JSON: eventos (envelope + campos + hash) e corpos de referencial.

    É o que um terceiro receberia. Usa SQL direto, sem a biblioteca, para que o
    formato exportado seja só o que está no banco.
    """
    with conn.cursor() as cur:
        cur.execute("""SELECT event_id, run_id, feature_id, feature_type, event_type, asserted_by, owner_ref,
                              reason, caused_by, prev_hash, hash FROM event WHERE run_id = %s ORDER BY event_id""", (run,))
        nomes = [d.name for d in cur.description]
        eventos = [dict(zip(nomes, r)) for r in cur.fetchall()]
        cur.execute("SELECT event_id, path, op, next FROM event_field WHERE run_id = %s", (run,))
        campos = {}
        for eid, path, op, nxt in cur.fetchall():
            campos.setdefault(eid, []).append({"path": path, "op": op, "next": nxt})
        cur.execute("SELECT ref_id, corpo FROM referencial")
        refs = {rid: corpo for rid, corpo in cur.fetchall()}
    for e in eventos:
        e["campos"] = campos.get(e["event_id"], [])
    Path(caminho).write_text(json.dumps({"run_id": run, "eventos": eventos, "referenciais": refs},
                                        ensure_ascii=False, indent=1))
    return caminho
