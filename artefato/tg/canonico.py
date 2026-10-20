"""Serialização canônica JSON (JCS, RFC 8785) e hash SHA-256.

O hash da cadeia e o ref_id do referencial dependem de uma única forma de
serializar o mesmo conteúdo. Regras do RFC 8785 aplicadas:
  * chaves ordenadas pela sequência de unidades UTF-16;
  * sem espaços; strings com o escape mínimo do JSON;
  * números no formato do ECMAScript (1.0 → 1, 1e21 → 1e+21, 1e-7 → 1e-7);
  * NaN e infinito são recusados.
"""
import hashlib
import json
import math


def _numero(x):
    if isinstance(x, bool):
        raise TypeError("bool não é número")
    if isinstance(x, int):
        return str(x)
    if math.isnan(x) or math.isinf(x):
        raise ValueError("NaN e infinito não têm forma canônica")
    if x == 0:
        return "0"
    if x.is_integer() and abs(x) < 1e21:
        return str(int(x))
    r = repr(x)
    if "e" in r:
        mant, exp = r.split("e")
        if mant.endswith(".0"):
            mant = mant[:-2]
        sinal = "-" if exp.startswith("-") else "+"
        exp = exp.lstrip("+-").lstrip("0") or "0"
        e = int(exp) * (-1 if sinal == "-" else 1)
        # ECMAScript usa notação decimal entre 1e-7 e 1e21
        if -7 < e < 21:
            return format(x, f".{max(0, -e + len(mant.replace('-', '').replace('.', '')) - 1)}f").rstrip("0").rstrip(".")
        return f"{mant}e{sinal}{exp}"
    return r


def _serializar(v):
    if v is None:
        return "null"
    if v is True:
        return "true"
    if v is False:
        return "false"
    if isinstance(v, (int, float)):
        return _numero(v)
    if isinstance(v, str):
        return json.dumps(v, ensure_ascii=False)
    if isinstance(v, (list, tuple)):
        return "[" + ",".join(_serializar(x) for x in v) + "]"
    if isinstance(v, dict):
        for k in v:
            if not isinstance(k, str):
                raise TypeError("chave de objeto JSON precisa ser string")
        chaves = sorted(v, key=lambda k: k.encode("utf-16-be"))
        return "{" + ",".join(json.dumps(k, ensure_ascii=False) + ":" + _serializar(v[k]) for k in chaves) + "}"
    raise TypeError(f"tipo sem forma JSON: {type(v).__name__}")


def canonico(v) -> bytes:
    return _serializar(v).encode("utf-8")


def sha256(v) -> str:
    return hashlib.sha256(canonico(v)).hexdigest()
