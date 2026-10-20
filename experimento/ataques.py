"""Bateria de adulteração de H3, sobre cópias do banco (protocolo H3.execucao).

Cada ataque roda numa cópia nova do banco do experimento, feita ao fim do ato
5: o original nunca é tocado. O atacante escreve direto no Postgres, sem
passar por append_event (modelo de ameaça do protocolo).

k = evento do meio: o primeiro, a partir da metade da cadeia, que tem campos
no corpo (para H3.04), não é alvo de caused_by (para H3.05) e tem espaço livre
de event_id logo depois (para H3.06). Regra fixada aqui, antes de rodar.
"""
import psycopg
from psycopg.types.json import Jsonb

from tg import ledger
from tg.canonico import sha256
from tg.ledger import conteudo_para_hash, ENVELOPE


def copiar(admin_dsn, origem, destino):
    with psycopg.connect(admin_dsn, autocommit=True) as a:
        a.execute(f"DROP DATABASE IF EXISTS {destino}")
        a.execute(f"CREATE DATABASE {destino} TEMPLATE {origem}")


def apagar(admin_dsn, nome):
    with psycopg.connect(admin_dsn, autocommit=True) as a:
        a.execute(f"DROP DATABASE IF EXISTS {nome}")


def _eventos(cur, run_id):
    cur.execute("SELECT event_id FROM event WHERE run_id = %s ORDER BY event_id", (run_id,))
    return [r[0] for r in cur.fetchall()]


def escolher_k(conn, run_id):
    with conn.cursor() as cur:
        ids = _eventos(cur, run_id)
        cur.execute("SELECT DISTINCT caused_by FROM event WHERE caused_by IS NOT NULL")
        alvos = {r[0] for r in cur.fetchall()}
        cur.execute("SELECT DISTINCT event_id FROM event_field WHERE run_id = %s", (run_id,))
        com_campos = {r[0] for r in cur.fetchall()}
    for i in range(len(ids) // 2, len(ids) - 1):
        k = ids[i]
        if k in com_campos and k not in alvos and ids[i + 1] - k > 1:
            return k, ids[i + 1], ids[-1]
    raise RuntimeError("nenhum k satisfaz a regra")


def _rehash(cur, eid):
    cur.execute(f"SELECT {', '.join(ENVELOPE)} FROM event WHERE event_id = %s", (eid,))
    env = dict(zip(ENVELOPE, cur.fetchone()))
    cur.execute("SELECT path, op, next FROM event_field WHERE event_id = %s", (eid,))
    campos = [{"path": p, "op": o, "next": n} for p, o, n in cur.fetchall()]
    h = sha256(conteudo_para_hash(env, campos))
    cur.execute("UPDATE event SET hash = %s WHERE event_id = %s", (h, eid))
    return h


def _mexer_no_corpo(cur, eid):
    cur.execute("SELECT path FROM event_field WHERE event_id = %s ORDER BY path LIMIT 1", (eid,))
    path = cur.fetchone()[0]
    cur.execute("UPDATE event_field SET next = %s, op = 'set' WHERE event_id = %s AND path = %s",
                (Jsonb("adulterado"), eid, path))


ATAQUES = {
    "H3.01": "UPDATE em event_field.next do evento k, sem recalcular hash",
    "H3.02": "UPDATE no corpo de k recalculando o hash de k",
    "H3.03": "UPDATE em asserted_by de k, sem recalcular hash",
    "H3.04": "DELETE de uma linha de event_field de k",
    "H3.05": "DELETE do evento k",
    "H3.06": "INSERT entre k e k+1 com hash próprio correto e prev_hash = hash(k)",
    "H3.07": "UPDATE no corpo da cabeça recalculando o hash da cabeça",
    "H3.08": "DELETE da cabeça (truncamento)",
    "H3.09": "reescrita de k até a cabeça recalculando todos os hashes",
}


def atacar(conn, run_id, vid, k, cabeca):
    with conn.cursor() as cur:
        if vid == "H3.01":
            _mexer_no_corpo(cur, k)
        elif vid == "H3.02":
            _mexer_no_corpo(cur, k); _rehash(cur, k)
        elif vid == "H3.03":
            cur.execute("UPDATE event SET asserted_by = 'intruso' WHERE event_id = %s", (k,))
        elif vid == "H3.04":
            cur.execute("""DELETE FROM event_field WHERE (event_id, path) IN
                           (SELECT event_id, path FROM event_field WHERE event_id = %s ORDER BY path LIMIT 1)""", (k,))
        elif vid == "H3.05":
            cur.execute("DELETE FROM event_field WHERE event_id = %s", (k,))
            cur.execute("DELETE FROM event WHERE event_id = %s", (k,))
        elif vid == "H3.06":
            cur.execute("SELECT hash FROM event WHERE event_id = %s", (k,))
            prev = cur.fetchone()[0]
            novo = k + 1
            env = {"event_id": novo, "run_id": run_id, "feature_id": "SBSJ-FALSO", "feature_type": "incident",
                   "event_type": "BASELINE", "asserted_by": "intruso", "owner_ref": None, "reason": None,
                   "caused_by": None, "prev_hash": prev}
            campos = [{"path": "texto", "op": "set", "next": "evento inserido"}]
            h = sha256(conteudo_para_hash(env, campos))
            cur.execute("""INSERT INTO event (event_id, run_id, feature_id, feature_type, event_type, asserted_by,
                           owner_ref, reason, caused_by, prev_hash, hash) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                        (novo, run_id, "SBSJ-FALSO", "incident", "BASELINE", "intruso", None, None, None, prev, h))
            cur.execute("INSERT INTO event_field VALUES (%s,%s,%s,%s,%s,%s)",
                        (novo, run_id, "SBSJ-FALSO", "texto", "set", Jsonb("evento inserido")))
        elif vid == "H3.07":
            _mexer_no_corpo(cur, cabeca); _rehash(cur, cabeca)
        elif vid == "H3.08":
            cur.execute("DELETE FROM event_field WHERE event_id = %s", (cabeca,))
            cur.execute("DELETE FROM event WHERE event_id = %s", (cabeca,))
        elif vid == "H3.09":
            _mexer_no_corpo(cur, k)
            ids = [i for i in _eventos(cur, run_id) if i >= k]
            cur.execute("SELECT hash FROM event WHERE run_id = %s AND event_id < %s ORDER BY event_id DESC LIMIT 1",
                        (run_id, k))
            ant = cur.fetchone()[0]
            for i in ids:
                cur.execute("UPDATE event SET prev_hash = %s WHERE event_id = %s", (ant, i))
                ant = _rehash(cur, i)
        else:
            raise ValueError(vid)
    conn.commit()


def detectar(conn, run_id, ancora):
    """(resultado de verify_chain, detectado com âncora)."""
    vc = ledger.verify_chain(conn, run_id)
    cab = ledger.cabeca(conn, run_id)
    com_ancora = bool(vc) or tuple(cab) != tuple(ancora)
    return vc, com_ancora
