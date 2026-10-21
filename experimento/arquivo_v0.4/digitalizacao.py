"""Do desenho do ADC às seeds: unidades de teste e ajuste de primitivos.

Entrada declarada (plano: "layout de taxiways e pátio digitalizado do ADC
entra como entrada, sem validação"). Três passos:

1. unidades: cada objeto de preenchimento do PDF é uma unidade; um anel contido
   em outro do mesmo objeto é furo (protocolo v0.4, H1.unidade_de_teste);
2. ajuste: retângulos mínimos orientados, divididos ao meio pelo eixo maior
   enquanto o percentil 95 do desvio passar da tolerância e houver orçamento
   (nº de primitivos ≤ nº de trechos do contorno, H1.03). A união dos
   retângulos mínimos contém a peça por construção: a envoltória é conservadora;
3. seeds: cada retângulo vira (inicio, fim, largura), com inicio e fim como
   seeds (THR16, s, o) pela inversa exata da resolução.

Usa a geometria em lat/lon do GeoJSON, não o campo enu_m (plano na altura de
THR16; ver GUIA §4).
"""
import json
from pathlib import Path

import numpy as np
import shapely
from shapely.geometry import LineString, Polygon
from shapely.ops import split

from fontes import ROTULO_PADRAO, ROTULOS
from metricas import desvio_p95

RAIZ = Path(__file__).resolve().parent.parent
CONTORNOS = RAIZ / "protocolo" / "adc" / "contornos_brutos.geojson"


def carregar(plano):
    """Unidades do ADC no plano do motor: [{id, pdf_id, classe, poligono, n_trechos, aneis}]."""
    fc = json.loads(CONTORNOS.read_text())
    por_obj = {}
    for f in fc["features"]:
        p = f["properties"]
        anel = [plano.enu(lat, lon) for lon, lat in f["geometry"]["coordinates"][0][:-1]]
        por_obj.setdefault(p["pdf_id"], []).append({"anel": p["anel"], "classe": p["classe"],
                                                    "n_trechos": p["n_trechos"], "poly": Polygon(anel)})
    unidades = []
    for pdf_id, aneis in sorted(por_obj.items()):
        aneis.sort(key=lambda a: -a["poly"].area)
        usados = set()
        for i, a in enumerate(aneis):
            if i in usados:
                continue
            furos = [j for j, b in enumerate(aneis) if j != i and j not in usados and a["poly"].contains(b["poly"])]
            usados |= {i, *furos}
            poly = Polygon(a["poly"].exterior.coords, [aneis[j]["poly"].exterior.coords for j in furos])
            unidades.append({
                "id": f"{pdf_id}.{a['anel']}", "pdf_id": pdf_id, "classe": a["classe"],
                "poligono": poly, "n_trechos": a["n_trechos"] + sum(aneis[j]["n_trechos"] for j in furos),
                "furos": [f"{pdf_id}.{aneis[j]['anel']}" for j in furos],
            })
    return unidades


def rotulo(unidade):
    if unidade["classe"] == "pista":
        return "runway", "RWY 16/34"
    if unidade["classe"] == "faixa":
        return "protect_area", "STRIP"
    if unidade["classe"] == "quadrilatero_contorno":
        return "protect_area", "SWY"
    return ROTULOS.get(str(unidade["pdf_id"]), ROTULO_PADRAO)


def _retangulo(peca):
    r = peca.minimum_rotated_rectangle
    if r.geom_type != "Polygon":                     # peça degenerada (linha ou ponto)
        r = peca.buffer(1e-3).minimum_rotated_rectangle
    return r


def _dividir(peca):
    """Corta a peça ao meio, perpendicularmente ao eixo maior do seu retângulo mínimo."""
    r = _retangulo(peca)
    c = np.array(r.exterior.coords[:4])
    lados = [c[1] - c[0], c[2] - c[1]]
    maior = max(lados, key=lambda v: np.hypot(*v))
    u = maior / np.hypot(*maior)
    n = np.array([-u[1], u[0]])
    m = np.array(r.centroid.coords[0])
    L = np.hypot(*maior) + 10
    corte = LineString([tuple(m - n * L), tuple(m + n * L)])
    partes = split(peca, corte)
    return [g for g in partes.geoms if g.area > 0] or [peca]


def ajustar(poligono, orcamento, tolerancia):
    """Retângulos cuja união contém o polígono, com p95 do desvio ≤ tolerância.

    Devolve (retangulos, desvio_p95, atingiu). Para quando o desvio cabe na
    tolerância ou quando o próximo corte passaria do orçamento.
    """
    pecas = [poligono]
    while True:
        rets = [_retangulo(p) for p in pecas]
        env = shapely.union_all(rets)
        dev = desvio_p95(env, poligono)
        if dev <= tolerancia:
            return rets, dev, True
        # peça com maior excesso local
        excessos = [desvio_p95(r, p) for r, p in zip(rets, pecas)]
        k = int(np.argmax(excessos))
        novas = _dividir(pecas[k])
        if len(pecas) - 1 + len(novas) > orcamento or len(novas) == 1:
            return rets, dev, False
        pecas = pecas[:k] + novas + pecas[k + 1:]


def retangulo_para_primitivo(r, res, plano, elemento="RWY_16_34", referente="THR16"):
    """Retângulo mínimo → primitivo 'retangulo' com seeds (inicio, fim) exatas."""
    c = np.array(r.exterior.coords[:4])
    l01, l12 = np.hypot(*(c[1] - c[0])), np.hypot(*(c[2] - c[1]))
    if l01 >= l12:      # eixo ao longo de c0→c1; largura = l12
        ini, fim, w = (c[0] + c[3]) / 2, (c[1] + c[2]) / 2, l12
    else:
        ini, fim, w = (c[0] + c[1]) / 2, (c[3] + c[2]) / 2, l01
    seeds = []
    for p in (ini, fim):
        lat, lon = plano.geo(float(p[0]), float(p[1]))
        s, o = res.inverso(elemento, referente, lat, lon)
        seeds.append({"elemento": elemento, "referente": referente, "s": s, "o": o})
    return {"tipo": "retangulo", "inicio": seeds[0], "fim": seeds[1], "largura": float(w)}
