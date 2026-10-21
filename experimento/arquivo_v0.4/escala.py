"""Epílogo — vinte anos depois: o custo de ler o ADC quando o ledger cresce (H4).

Script separado (plano), que o notebook lê. Para cada série e tamanho N:
  1. banco novo com o esquema;
  2. os K eventos relevantes ao ADC (os do run do experimento até o fim do
     ato 4) intercalados no tempo com N − K eventos irrelevantes, em ordem e
     com a cadeia de hash válida;
       S1: irrelevantes em outras features (incidentes);
       S2: irrelevantes nas mesmas features do ADC, na camada 'manutencao';
  3. mediana de 21 execuções da projeção do ADC, depois de 3 de aquecimento;
  4. no maior N, os planos (EXPLAIN) das consultas da lente.

Uso: python3 escala.py <banco_do_experimento> <run_id> <t_fim_ato4_event_id>
Grava resultados/escala.json.
"""
import io
import json
import os
import platform
import random
import statistics
import sys
import time
from pathlib import Path

import numpy as np
import psycopg

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "artefato"))
from tg import adc, banco, relogio  # noqa: E402
from tg.canonico import canonico, sha256  # noqa: E402
from tg.ledger import conteudo_para_hash  # noqa: E402

import yaml  # noqa: E402

PROT = yaml.safe_load((RAIZ / "protocolo" / "protocolo.yaml").read_text())["H4"]["desenho"]
SEMENTE = 20261020
TAMANHOS = [int(round(10 ** e)) for e in (3, 3.5, 4, 4.5, 5, 5.5, 6)]
N_MED, N_AQUEC = 21, 3


def dsn(nome):
    base = os.environ.get("TG_DSN_ADMIN", "postgresql://tg@localhost:54329/postgres").rsplit("/", 1)[0]
    return f"{base}/{nome}"


def admin():
    return psycopg.connect(dsn("postgres"), autocommit=True)


def relevantes(origem_db, run_id, t_lim):
    with psycopg.connect(dsn(origem_db)) as c, c.cursor() as cur:
        cur.execute("""SELECT event_id, feature_id, feature_type, event_type, asserted_by, owner_ref, reason, caused_by
                       FROM event WHERE run_id = %s AND event_id <= %s ORDER BY event_id""", (run_id, t_lim))
        evs = cur.fetchall()
        cur.execute("SELECT event_id, path, op, next FROM event_field WHERE run_id = %s AND event_id <= %s",
                    (run_id, t_lim))
        campos = {}
        for eid, p, o, n in cur.fetchall():
            campos.setdefault(eid, []).append({"path": p, "op": o, "next": n})
        cur.execute("SELECT ref_id, corpo FROM referencial")
        refs = cur.fetchall()
    return evs, campos, refs


def gerar(nome, serie, N, evs, campos, refs, rng):
    with admin() as a:
        a.execute(f"DROP DATABASE IF EXISTS {nome}")
        a.execute(f"CREATE DATABASE {nome}")
    conn = psycopg.connect(dsn(nome))
    banco.criar_esquema(conn)
    run = "escala"
    origem = relogio.EPOCA.replace(year=2027)
    with conn.cursor() as cur:
        cur.execute("INSERT INTO run VALUES (%s, 0, %s, %s)", (run, origem, origem))
        for rid, corpo in refs:
            cur.execute("INSERT INTO referencial VALUES (%s, %s)", (rid, json.dumps(corpo)))
    K = len(evs)
    pos_rel = set(sorted(rng.sample(range(N), K)))
    mapa = {}                                  # event_id antigo → novo (para caused_by)
    vivas_adc = []
    incidentes = 0
    prev = None
    ms0 = relogio.ms(origem)
    ev_buf, f_buf = io.StringIO(), io.StringIO()
    it = iter(evs)
    tipo_de = {e[1]: e[2] for e in evs}

    def descarregar():
        with conn.cursor() as cur:
            with cur.copy("COPY event (event_id, run_id, feature_id, feature_type, event_type, asserted_by, owner_ref, "
                          "reason, caused_by, prev_hash, hash) FROM STDIN") as cp:
                cp.write(ev_buf.getvalue())
            with cur.copy("COPY event_field (event_id, run_id, feature_id, path, op, next) FROM STDIN") as cp:
                cp.write(f_buf.getvalue())
        ev_buf.seek(0); ev_buf.truncate(); f_buf.seek(0); f_buf.truncate()

    for i in range(N):
        eid = relogio.compor(ms0 + i, 0, 0)
        if i in pos_rel:
            old, fid, ft, et, by, own, rsn, cb = next(it)
            mapa[old] = eid
            cs = campos.get(old, [])
            env = {"event_id": eid, "run_id": run, "feature_id": fid, "feature_type": ft, "event_type": et,
                   "asserted_by": by, "owner_ref": own, "reason": rsn, "caused_by": mapa.get(cb) if cb else None,
                   "prev_hash": prev}
            if et == "BASELINE" and ft not in ("airport", "restriction"):
                vivas_adc.append(fid)
        else:
            if serie == "S2" and vivas_adc:
                fid = rng.choice(vivas_adc)
                ft = tipo_de[fid]
                et = "DELTA"
                cs = [{"path": "manutencao.registro", "op": "set", "next": i}]
            else:
                if incidentes == 0 or rng.random() < 0.1:
                    incidentes += 1
                    fid, et = f"INC-{incidentes}", "BASELINE"
                else:
                    fid, et = f"INC-{rng.randint(1, incidentes)}", "DELTA"
                ft = "incident"
                cs = [{"path": "observacao.n", "op": "set", "next": i}]
            env = {"event_id": eid, "run_id": run, "feature_id": fid, "feature_type": ft, "event_type": et,
                   "asserted_by": "sintetico", "owner_ref": None, "reason": None, "caused_by": None, "prev_hash": prev}
        h = sha256(conteudo_para_hash(env, cs))
        ev_buf.write("\t".join(_tsv(env[k]) for k in ("event_id", "run_id", "feature_id", "feature_type",
                                                     "event_type", "asserted_by", "owner_ref", "reason",
                                                     "caused_by", "prev_hash")) + "\t" + h + "\n")
        for c in cs:
            f_buf.write("\t".join([str(eid), run, env["feature_id"], c["path"], c["op"],
                                   "\\N" if c["op"] == "removed" else _tsv(canonico(c["next"]).decode())]) + "\n")
        prev = h
        if (i + 1) % 100_000 == 0:
            descarregar()
    descarregar()
    with conn.cursor() as cur:
        cur.execute("UPDATE run SET relogio = %s WHERE run_id = %s", (relogio.instante(eid), run))
    conn.commit()
    conn.autocommit = True
    conn.execute("VACUUM ANALYZE")
    conn.autocommit = False
    return conn, run


def _tsv(v):
    if v is None:
        return "\\N"
    return str(v).replace("\\", "\\\\").replace("\t", "\\t").replace("\n", "\\n")


def medir(conn, run):
    for _ in range(N_AQUEC):
        adc.projetar(conn, run)
    ts = []
    for _ in range(N_MED):
        t0 = time.perf_counter()
        adc.projetar(conn, run)
        ts.append(time.perf_counter() - t0)
    return ts


CONSULTAS = {
    "features_de_tipo": """WITH RECURSIVE f(fid) AS (
        (SELECT e.feature_id FROM event e WHERE e.run_id = %(run)s AND e.feature_type = 'taxiway' ORDER BY e.feature_id LIMIT 1)
        UNION ALL SELECT (SELECT e.feature_id FROM event e WHERE e.run_id = %(run)s AND e.feature_type = 'taxiway'
                          AND e.feature_id > f.fid ORDER BY e.feature_id LIMIT 1) FROM f WHERE f.fid IS NOT NULL)
        SELECT fid FROM f WHERE fid IS NOT NULL""",
    "viva_em": """SELECT event_type <> 'VOID' FROM event WHERE run_id = %(run)s AND feature_id = %(fid)s
        AND event_id <= %(t)s AND event_type IN ('BASELINE', 'VOID') ORDER BY event_id DESC LIMIT 1""",
    "estado_em_camada": """WITH ciclo AS (SELECT max(event_id) AS b FROM event WHERE run_id = %(run)s AND feature_id = %(fid)s
            AND event_type = 'BASELINE' AND event_id <= %(t)s),
        ultimo AS (SELECT DISTINCT ON (f.path) f.path, f.op, f.next FROM event_field f, ciclo c
            WHERE f.run_id = %(run)s AND f.feature_id = %(fid)s AND f.event_id BETWEEN c.b AND %(t)s
            AND f.path >= ('geometria.' COLLATE "C") AND f.path < (('geometria.' || chr(1114111)) COLLATE "C")
            ORDER BY f.path, f.event_id DESC)
        SELECT path, next FROM ultimo WHERE op = 'set'""",
    "referencial": """SELECT corpo FROM referencial WHERE ref_id = %(ref)s""",
}


def planos(conn, run):
    with conn.cursor() as cur:
        cur.execute("SELECT feature_id FROM event WHERE run_id = %s AND feature_type = 'taxiway' LIMIT 1", (run,))
        fid = cur.fetchone()[0]
        cur.execute("SELECT max(event_id) FROM event WHERE run_id = %s", (run,))
        t = cur.fetchone()[0]
        cur.execute("SELECT ref_id FROM referencial LIMIT 1")
        ref = cur.fetchone()[0]
        out = {}
        for nome, sql in CONSULTAS.items():
            cur.execute("EXPLAIN (FORMAT JSON) " + sql, {"run": run, "fid": fid, "t": t, "ref": ref})
            plano = cur.fetchone()[0][0]["Plan"]
            nos = []

            def andar(p):
                nos.append((p["Node Type"], p.get("Relation Name")))
                for q in p.get("Plans", []):
                    andar(q)
            andar(plano)
            out[nome] = {"nos": nos,
                         "seq_scan": [r for n, r in nos if n == "Seq Scan" and r in ("event", "event_field")],
                         "relacoes": sorted({r for _, r in nos if r})}
    return out


def inclinacao(ns, ts_por_n, rng, reps=2000):
    x = np.log10(ns)
    med = [statistics.median(t) for t in ts_por_n]
    b = float(np.polyfit(x, np.log10(med), 1)[0])
    boots = []
    for _ in range(reps):
        m = [statistics.median(rng.choices(t, k=len(t))) for t in ts_por_n]
        boots.append(float(np.polyfit(x, np.log10(m), 1)[0]))
    return b, [float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))], med


def main(origem_db, run_id, t_lim):
    rng = random.Random(SEMENTE)
    evs, campos, refs = relevantes(origem_db, run_id, int(t_lim))
    res = {"K_relevantes": len(evs), "tamanhos": TAMANHOS, "semente": SEMENTE, "n_medidas": N_MED,
           "n_aquecimento": N_AQUEC, "hardware": platform.platform() + " | " + platform.processor(),
           "postgres": None, "series": {}}
    for serie in ("S1", "S2"):
        tempos, cache_ok = [], []
        for N in TAMANHOS:
            nome = f"tg_escala_{serie.lower()}_{N}"
            t0 = time.time()
            conn, run = gerar(nome, serie, N, evs, campos, refs, rng)
            with conn.cursor() as cur:
                cur.execute("SHOW server_version")
                res["postgres"] = cur.fetchone()[0]
            ts = medir(conn, run)
            fresco = adc.conteudo_canonico(adc.projetar(conn, run))
            adc.projetar(conn, run, usar_cache=True)
            em_cache = adc.conteudo_canonico(adc.projetar(conn, run, usar_cache=True))
            cache_ok.append(sha256(fresco) == sha256(em_cache))
            tempos.append(ts)
            print(f"{serie} N={N:>8}: mediana {statistics.median(ts) * 1000:8.2f} ms "
                  f"(geração {time.time() - t0:.0f} s) cache igual: {cache_ok[-1]}", flush=True)
            if N == TAMANHOS[-1]:
                res.setdefault("planos", {})[serie] = planos(conn, run)
            conn.close()
            with admin() as a:
                a.execute(f"DROP DATABASE {nome}")
        b, ic, med = inclinacao(TAMANHOS, tempos, rng)
        res["series"][serie] = {"medianas_s": med, "tempos_s": tempos, "inclinacao": b, "ic95": ic,
                                "cache_igual": cache_ok}
        print(f"{serie}: inclinação {b:.4f}  IC95 {ic}", flush=True)
    (RAIZ / "resultados").mkdir(exist_ok=True)
    (RAIZ / "resultados" / "escala.json").write_text(json.dumps(res, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main(*sys.argv[1:4])
