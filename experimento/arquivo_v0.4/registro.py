"""Registro do experimento: protocolo congelado, vereditos e escritas.

Cada execução do notebook ganha um exec_id e um banco próprio, que não é
apagado. Tudo o que acontece vai para resultados/execucoes.jsonl, arquivo em
que só se acrescenta: as verificações (observado, predito, tolerância,
veredito) e cada escrita no ledger. Uma falha corrigida continua visível nas
execuções anteriores, como a regra do protocolo exige.
"""
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent.parent
PROTOCOLO = RAIZ / "protocolo" / "protocolo.yaml"
COMMIT_CONGELAMENTO = "fcfb6a5"
LOG = RAIZ / "resultados" / "execucoes.jsonl"


def sha256_arquivo(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def git(*args):
    return subprocess.run(["git", "-C", str(RAIZ), *args], capture_output=True, text=True, check=True).stdout.strip()


def conferir_congelamento():
    """O protocolo em disco é byte a byte o do commit de congelamento?"""
    no_disco = sha256_arquivo(PROTOCOLO)
    conteudo = subprocess.run(["git", "-C", str(RAIZ), "show", f"{COMMIT_CONGELAMENTO}:protocolo/protocolo.yaml"],
                              capture_output=True, check=True).stdout
    no_commit = hashlib.sha256(conteudo).hexdigest()
    registrado = [l.split()[0] for l in (RAIZ / "protocolo" / "PROTOCOLO.sha256").read_text().splitlines()
                  if l.endswith("protocolo.yaml")][0]
    tags = git("tag", "--points-at", COMMIT_CONGELAMENTO).split()
    return {"sha256_disco": no_disco, "sha256_commit": no_commit, "sha256_registrado": registrado,
            "integro": no_disco == no_commit == registrado, "tag": tags[0] if tags else None}


def _indexar(p):
    idx = {}
    for h in ("H1", "H3", "H4"):
        for v in p[h]["verificacoes"]:
            idx[v["id"]] = {**v, "hipotese": h}
    for ato in ("ato1", "ato4"):
        for v in p["H2"][ato]["verificacoes"]:
            idx[v["id"]] = {**v, "hipotese": "H2"}
    return idx


class Registro:
    def __init__(self):
        c = conferir_congelamento()
        if not c["integro"]:
            raise RuntimeError(f"protocolo diferente do congelado: {c}")
        self.congelamento = c
        self.protocolo = yaml.safe_load(PROTOCOLO.read_text())
        self.idx = _indexar(self.protocolo)
        self.commit = git("rev-parse", "--short", "HEAD")
        sujo = git("status", "--porcelain", "--", "artefato", "experimento")
        self.commit_limpo = sujo == ""
        self.exec_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + self.commit
        self.vereditos = []
        self.n_escritas = {}
        LOG.parent.mkdir(exist_ok=True)
        self._log({"tipo": "inicio", "congelamento": c, "commit_artefato": self.commit,
                   "commit_limpo": self.commit_limpo})

    # -------------------------------------------------------------- log
    def _log(self, d):
        d = {"exec_id": self.exec_id, "quando": datetime.now(timezone.utc).isoformat(), **d}
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(d, ensure_ascii=False, default=str) + "\n")

    def nota(self, texto, **dados):
        self._log({"tipo": "nota", "texto": texto, **dados})

    # -------------------------------------------------------------- escrita no ledger
    def escrever(self, conn, run_id, *args, **kw):
        """append_event com registro: o log conta as escritas (H3.10)."""
        from tg import ledger
        eid, h = ledger.append_event(conn, run_id, *args, **kw)
        self.n_escritas[run_id] = self.n_escritas.get(run_id, 0) + 1
        self._log({"tipo": "escrita", "run_id": run_id, "event_id": eid, "feature_id": args[0],
                   "event_type": args[2], "hash": h})
        return eid, h

    # -------------------------------------------------------------- verificações
    def _fechar(self, vid, observado, predito, tolerancia, passou, nota=None):
        v = {"id": vid, "hipotese": self.idx.get(vid, {}).get("hipotese", "roteiro"),
             "observado": observado, "predito": predito, "tolerancia": tolerancia,
             "veredito": "PASSOU" if passou else "FALHOU", "nota": nota}
        self.vereditos.append(v)
        self._log({"tipo": "verificacao", **v})
        sinal = "✔" if passou else "✘"
        tol = f" ± {tolerancia}" if tolerancia not in (None, 0) else ""
        print(f"{sinal} {vid}: observado {fmt(observado)} | predito {fmt(predito)}{tol} → {v['veredito']}"
              + (f"  ({nota})" if nota else ""))
        return passou

    def numerico(self, vid, observado, angular=False):
        """Compara com 'publicado' e 'tolerancia' do protocolo."""
        v = self.idx[vid]
        pub, tol = v["publicado"], v["tolerancia"]
        dif = abs(observado - pub)
        if angular:
            dif = min(dif, 360 - dif)
        return self._fechar(vid, observado, pub, tol, dif <= tol, f"|Δ| = {dif:.4f}")

    def limite(self, vid, observado, maximo, nota=None):
        return self._fechar(vid, observado, f"≤ {maximo}", None, observado <= maximo, nota)

    def igual(self, vid, observado, esperado, nota=None):
        return self._fechar(vid, observado, esperado, 0, observado == esperado, nota)

    def booleano(self, vid, condicao, descricao):
        return self._fechar(vid, descricao if condicao else "não", descricao, None, bool(condicao))

    def composto(self, vid, observado, predito, passou, nota=None):
        """Verificação com mais de uma condição; observado e predito vão por extenso."""
        return self._fechar(vid, observado, predito, None, bool(passou), nota)

    def roteiro(self, vid, condicao, descricao, observado=None):
        """Verificação do roteiro (fora do protocolo H1–H4): R1, R8, R10..."""
        return self._fechar(vid, observado if observado is not None else ("sim" if condicao else "não"),
                            descricao, None, bool(condicao))

    def nao_executada(self, vid, motivo):
        v = {"id": vid, "hipotese": self.idx.get(vid, {}).get("hipotese", "roteiro"), "veredito": "NÃO EXECUTADA",
             "nota": motivo}
        self.vereditos.append(v)
        self._log({"tipo": "verificacao", **v})
        print(f"– {vid}: não executada ({motivo})")

    # -------------------------------------------------------------- fechamento
    def tabela(self):
        linhas = ["| Verificação | Hipótese | Observado | Predito | Veredito |", "|---|---|---|---|---|"]
        for v in self.vereditos:
            linhas.append(f"| {v['id']} | {v['hipotese']} | {fmt(v.get('observado'))} | {fmt(v.get('predito'))} | {v['veredito']} |")
        return "\n".join(linhas)

    def resumo(self):
        por = {}
        for v in self.vereditos:
            d = por.setdefault(v["hipotese"], {"PASSOU": 0, "FALHOU": 0, "NÃO EXECUTADA": 0})
            d[v["veredito"]] += 1
        self._log({"tipo": "resumo", "por_hipotese": por})
        return por


def fmt(x):
    if isinstance(x, float):
        return f"{x:.4f}" if abs(x) < 1e4 else f"{x:.1f}"
    if isinstance(x, (list, tuple)) and len(x) > 6:
        return f"[{len(x)} itens]"
    return str(x)
