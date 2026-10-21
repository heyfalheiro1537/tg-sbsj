"""Verificador independente de um ledger exportado (E5).

Escrito a partir da especificação, sem importar a biblioteca aeroledger, para
mostrar que a prova de integridade é verificável por terceiros. Usa só a
biblioteca padrão e o gabarito geodésico do protocolo (outro código).

Especificação que ele implementa:

  hash(evento) = SHA-256 do JCS (RFC 8785) de
      { event_id, run_id, feature_id, feature_type, event_type, asserted_by,
        owner_ref, reason, caused_by, prev_hash,
        campos: [ {path, op, next} ordenados por path ] }

  cadeia íntegra  ⇔  para cada evento, em ordem de event_id:
      prev_hash = hash do anterior (None no primeiro) e hash recalculado = hash guardado

  ref_id = SHA-256 do JCS do corpo do referencial

Uso: python3 verificador_independente.py <export.json> [elemento linear]
"""
import hashlib
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "protocolo" / "gabarito"))
import geodesia  # noqa: E402   (gabarito independente do protocolo)

ENVELOPE = ("event_id", "run_id", "feature_id", "feature_type", "event_type", "asserted_by",
            "owner_ref", "reason", "caused_by", "prev_hash")


# ---------------------------------------------------------------- JCS, pela especificação

def _numero_ecmascript(x):
    """Number.prototype.toString do ECMAScript (RFC 8785, seção 3.2.2.3)."""
    if isinstance(x, int):
        return str(x)
    if math.isnan(x) or math.isinf(x):
        raise ValueError("número sem forma JCS")
    if x == 0:
        return "0"
    sinal = "-" if x < 0 else ""
    x = abs(x)
    # dígitos mais curtos que reproduzem x (repr do Python é o mesmo critério)
    mant, _, exp = repr(x).partition("e")
    inteiro, _, frac = mant.partition(".")
    digitos = (inteiro + frac).lstrip("0")
    n = len(inteiro.lstrip("0")) + int(exp or 0) if inteiro.lstrip("0") else int(exp or 0) - (len(frac) - len(frac.lstrip("0")))
    digitos = digitos.rstrip("0") or "0"
    k = len(digitos)
    # n: posição do ponto decimal em relação ao primeiro dígito (x = 0.d1d2... × 10^n)
    if k <= n <= 21:
        return sinal + digitos + "0" * (n - k)
    if 0 < n <= 21:
        return sinal + digitos[:n] + "." + digitos[n:]
    if -6 < n <= 0:
        return sinal + "0." + "0" * (-n) + digitos
    e = n - 1
    corpo = digitos[0] + ("." + digitos[1:] if k > 1 else "")
    return sinal + corpo + "e" + ("+" if e > 0 else "-") + str(abs(e))


def jcs(v):
    if v is None:
        return "null"
    if v is True:
        return "true"
    if v is False:
        return "false"
    if isinstance(v, (int, float)):
        return _numero_ecmascript(v)
    if isinstance(v, str):
        return json.dumps(v, ensure_ascii=False)
    if isinstance(v, list):
        return "[" + ",".join(jcs(x) for x in v) + "]"
    if isinstance(v, dict):
        chaves = sorted(v, key=lambda c: c.encode("utf-16-be"))
        return "{" + ",".join(json.dumps(c, ensure_ascii=False) + ":" + jcs(v[c]) for c in chaves) + "}"
    raise TypeError(type(v).__name__)


def sha(v):
    return hashlib.sha256(jcs(v).encode("utf-8")).hexdigest()


# ---------------------------------------------------------------- verificação

def verificar(export):
    """Devolve {'integra', 'primeiro_divergente', 'cabeca', 'refs_invalidos'}."""
    anterior = None
    for e in export["eventos"]:
        conteudo = {k: e[k] for k in ENVELOPE}
        conteudo["campos"] = sorted(({"path": c["path"], "op": c["op"], "next": c["next"]} for c in e["campos"]),
                                    key=lambda c: c["path"])
        if e["prev_hash"] != anterior or sha(conteudo) != e["hash"]:
            return {"integra": False, "primeiro_divergente": e["event_id"], "cabeca": None, "refs_invalidos": []}
        anterior = e["hash"]
    refs = [rid for rid, corpo in export["referenciais"].items() if sha(corpo) != rid]
    cab = (export["eventos"][-1]["event_id"], anterior) if export["eventos"] else None
    return {"integra": not refs, "primeiro_divergente": None, "cabeca": cab, "refs_invalidos": refs}


def ref_id_vigente(export):
    """ref_id do airport ao fim da cadeia (último valor escrito em referencial.ref_id)."""
    ref = None
    for e in export["eventos"]:
        if e["feature_type"] == "airport":
            for c in e["campos"]:
                if c["path"] == "referencial.ref_id" and c["op"] == "set":
                    ref = c["next"]
    return ref


def comprimento(export, elemento="RWY_16_34"):
    """Comprimento geodésico do elemento linear no referencial vigente (Vincenty, GRS80)."""
    corpo = export["referenciais"][ref_id_vigente(export)]
    a, b = corpo["elementos_lineares"][elemento]
    pa, pb = corpo["referentes"][a], corpo["referentes"][b]
    s, _, _ = geodesia.inversa(pa["lat"], pa["lon"], pb["lat"], pb["lon"])
    return s


if __name__ == "__main__":
    dados = json.loads(Path(sys.argv[1]).read_text())
    r = verificar(dados)
    print(json.dumps(r, ensure_ascii=False))
    if r["integra"]:
        print(f"comprimento: {comprimento(dados, *(sys.argv[2:3] or ['RWY_16_34'])):.4f} m")
