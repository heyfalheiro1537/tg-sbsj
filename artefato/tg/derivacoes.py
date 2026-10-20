"""Conhecimento derivado: nunca armazenado, sempre calculado das premissas.

Comprimento e azimute vêm do referencial (geodésica entre as pontas do
elemento linear). Distâncias declaradas vêm da regra da norma aplicada ao
estado em t. Nada daqui é escrito no ledger.

Regra de distâncias declaradas (premissa normativa; Anexo 14 Vol. I, RBAC 154):
  TORA = comprimento da pista disponível para corrida
  TODA = TORA + CWY da direção
  ASDA = TORA + SWY da direção
  LDA  = comprimento da pista − deslocamento da cabeceira da direção
A regra com barreira de contenção (ato 2) ainda não está fixada no protocolo;
com uma barreira viva, o cálculo recusa em vez de adivinhar.
"""
from pyproj import Geod

from . import ledger
from .referencial import Resolvedor, referencial_vigente

GEOD = Geod(ellps="GRS80")


class RegraPendente(Exception):
    pass


def comprimento(corpo_ref, elemento):
    res = Resolvedor(corpo_ref)
    a, b = res.pontas(elemento)
    pa, pb = res.referente(a), res.referente(b)
    _, _, d = GEOD.inv(pa[1], pa[0], pb[1], pb[0])
    return d


def azimutes(corpo_ref, elemento):
    """{ponta: azimute verdadeiro na ponta, apontando para a outra}."""
    res = Resolvedor(corpo_ref)
    a, b = res.pontas(elemento)
    return {a: res.azimute(elemento, a), b: res.azimute(elemento, b)}


def rumo_magnetico(az_verdadeiro, variacao_leste):
    """Rumo magnético; variação oeste é negativa (22°W → −22)."""
    return (az_verdadeiro - variacao_leste) % 360


def distancia_entre_seeds(corpo_ref, s1, s2):
    res = Resolvedor(corpo_ref)
    p, q = res.seed(s1), res.seed(s2)
    _, _, d = GEOD.inv(p[1], p[0], q[1], q[0])
    return d


def distancias_declaradas(conn, run_id, t=None):
    """{designador: {TORA, TODA, ASDA, LDA}} para cada pista viva em t.

    Pista (feature_type 'runway'): retângulo com inicio e fim nas cabeceiras e
      'direcoes': {'inicio': '16', 'fim': '34'} (a corrida da direção 'inicio'
      parte do início do retângulo).
    SWY/CWY (feature_type 'protect_area', 'papel': 'swy'|'cwy'): retângulo cujo
      comprimento é derivado das seeds; 'aplica_a': {'pista': id, 'direcao': '16'}.
    Cabeceira (feature_type 'runway_direction'): 'designador', 'pista' e,
      quando houver, 'deslocamento_m' (premissa).
    """
    t_lim = ledger._limite(conn, run_id, t)
    _, corpo = referencial_vigente(conn, run_id, t_lim)
    if corpo is None:
        raise ValueError("sem referencial vigente")
    if ledger.features(conn, run_id, t_lim, "arresting_gear"):
        raise RegraPendente("barreira viva: a regra do ato 2 ainda não foi registrada no protocolo")
    estados = {fid: (ft, ledger.reconstruct_state(conn, run_id, fid, t_lim))
               for fid, ft in ledger.features(conn, run_id, t_lim)}
    out = {}
    for fid, (ft, e) in estados.items():
        if ft != "runway":
            continue
        ret = e["geometria"]["primitivos"]["pista"]
        L = distancia_entre_seeds(corpo, ret["inicio"], ret["fim"])
        for lado in ("inicio", "fim"):
            d = e["direcoes"][lado]
            swy = cwy = desloc = 0.0
            for _, (ft2, e2) in estados.items():
                if ft2 == "protect_area" and e2.get("aplica_a", {}).get("pista") == fid \
                        and e2["aplica_a"].get("direcao") == d and e2.get("papel") in ("swy", "cwy"):
                    r2 = next(iter(e2["geometria"]["primitivos"].values()))
                    comp = distancia_entre_seeds(corpo, r2["inicio"], r2["fim"])
                    if e2["papel"] == "swy":
                        swy += comp
                    else:
                        cwy += comp
                if ft2 == "runway_direction" and e2.get("pista") == fid and e2.get("designador") == d:
                    desloc = float(e2.get("deslocamento_m", 0.0))
            out[d] = {"TORA": L, "TODA": L + cwy, "ASDA": L + swy, "LDA": L - desloc}
    return out
