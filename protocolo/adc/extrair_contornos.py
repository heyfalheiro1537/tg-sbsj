"""Extrai do ADC (fonte F1) os contornos brutos das feições de área.

Procedimento registrado no protocolo (H1, oráculo). Saída: contornos_brutos.geojson,
um polígono por objeto do PDF, em ENU (metros, origem THR16) e em lat/lon,
com o id do objeto no PDF e o estilo que o identifica.

O que é extraído (pelo estilo, não pela posição):
  - preenchimento preto com 4 vértices e lado maior acima de 100 pt (≈740 m;
    nenhuma edificação da carta chega a isso): pista
  - contorno preto em quadrilátero, traço 0,48 pt, sem tracejado: candidatos a SWY
  - contorno preto tracejado em quadrilátero: faixa de pista
  - preenchimento cinza 0,765: pavimento de taxiways e pátios (sem divisão por
    designação; a divisão é a entrada segmentacao.yaml, feita à parte)

Curvas de Bézier são achatadas em 32 cordas; o erro do achatamento fica abaixo
de 0,01 pt (7 cm no terreno), duas ordens abaixo da precisão do oráculo.

Este script não compara nada com o AIP e não mede dimensões: só converte o
desenho para o terreno. Rodá-lo não antecipa H1.

Uso: python3 extrair_contornos.py <adc.pdf> [calibracao.json]
"""
import json
import sys
from pathlib import Path

import pymupdf

sys.path.insert(0, str(Path(__file__).parent))
from adc_geo import para_enu  # noqa: E402

CORDAS_BEZIER = 32
MOLDURA = pymupdf.Rect(25.65, 78.02, 399.6, 579.5)


def carregar_calibracao(caminho):
    c = json.loads(Path(caminho).read_text())
    a = c["ajuste"]
    lat_c, lon_c = a["lat"]["coef"], a["lon"]["coef"]

    def pagina_para_geo(x, y):
        v_lat = lat_c[0] * x + lat_c[1] * y + lat_c[2]
        v_lon = lon_c[0] * x + lon_c[1] * y + lon_c[2]
        return -(23 + v_lat / 3600), -(45 + v_lon / 3600)
    return pagina_para_geo


def bezier(p0, p1, p2, p3, n=CORDAS_BEZIER):
    pts = []
    for k in range(1, n + 1):
        t = k / n
        u = 1 - t
        pts.append((u ** 3 * p0.x + 3 * u * u * t * p1.x + 3 * u * t * t * p2.x + t ** 3 * p3.x,
                    u ** 3 * p0.y + 3 * u * u * t * p1.y + 3 * u * t * t * p2.y + t ** 3 * p3.y))
    return pts


def aneis(desenho):
    """Converte os itens de um desenho em anéis fechados.

    Devolve [(pontos, trechos)], onde trechos é a lista de itens do PDF que
    formam o anel: ('l', p0, p1) para reta e ('c',) para curva. É dela que H1.03
    conta os trechos do contorno de referência.
    """
    out, atual, trechos, fim = [], [], [], None
    for it in desenho["items"]:
        tipo = it[0]
        if tipo == "re":
            r = it[1]
            pts = [(r.x0, r.y0), (r.x1, r.y0), (r.x1, r.y1), (r.x0, r.y1)]
            out.append((pts, [("l", pts[j], pts[(j + 1) % 4]) for j in range(4)]))
            continue
        if tipo == "qu":
            q = it[1]
            pts = [(q.ul.x, q.ul.y), (q.ur.x, q.ur.y), (q.lr.x, q.lr.y), (q.ll.x, q.ll.y)]
            out.append((pts, [("l", pts[j], pts[(j + 1) % 4]) for j in range(4)]))
            continue
        ini = it[1]
        if fim is None or abs(ini.x - fim[0]) > 1e-3 or abs(ini.y - fim[1]) > 1e-3:
            if len(atual) >= 3:
                out.append((atual, trechos))
            atual, trechos = [(ini.x, ini.y)], []
        if tipo == "l":
            trechos.append(("l", (ini.x, ini.y), (it[2].x, it[2].y)))
            atual.append((it[2].x, it[2].y))
        elif tipo == "c":
            trechos.append(("c",))
            atual.extend(bezier(it[1], it[2], it[3], it[4]))
        fim = atual[-1]
    if len(atual) >= 3:
        out.append((atual, trechos))
    return out


def fechar(pts, trechos):
    """Acrescenta o lado de fechamento implícito (o PDF fecha o caminho sem desenhá-lo)."""
    if trechos and trechos[-1][0] == "l":
        ult = trechos[-1][2]
    else:
        ult = pts[-1]
    if abs(ult[0] - pts[0][0]) > 1e-3 or abs(ult[1] - pts[0][1]) > 1e-3:
        trechos = trechos + [("l", ult, pts[0])]
    return trechos


def contar_trechos(trechos, tol_pt=0.01):
    """Nº de trechos do contorno: retas consecutivas colineares contam como uma.

    Colinear = o vértice do meio dista menos de 0,01 pt (7 cm no terreno) da reta
    que liga as pontas; mesma ordem do erro de achatamento das curvas.
    """
    n, ant = 0, None
    for t in trechos:
        if t[0] == "c":
            n += 1; ant = None; continue
        if ant is not None:
            (ax, ay), (bx, by), (cx, cy) = ant[1], t[1], t[2]
            L = ((cx - ax) ** 2 + (cy - ay) ** 2) ** 0.5
            d = abs((cx - ax) * (ay - by) - (ax - bx) * (cy - ay)) / L if L else 0
            if d < tol_pt:
                ant = ("l", ant[1], t[2]); continue
        n += 1; ant = t
    return n


def classe(d):
    cinza = lambda c: c and all(abs(v - 0.765) < 0.01 for v in c)
    preto = lambda c: c and all(abs(v) < 0.01 for v in c)
    tracejado = bool(d.get("dashes")) and d["dashes"] not in ("[] 0", "[] 0.0")
    so_quad = all(it[0] == "qu" for it in d["items"])
    if d["type"] == "f" and cinza(d.get("fill")):
        return "pavimento"
    if d["type"] == "f" and preto(d.get("fill")) and len(d["items"]) == 3 and all(it[0] == "l" for it in d["items"]):
        return "pista"
    if d["type"] == "s" and preto(d.get("color")) and so_quad and tracejado:
        return "faixa"
    if d["type"] == "s" and preto(d.get("color")) and so_quad and not tracejado and abs((d.get("width") or 0) - 0.48) < 0.01:
        return "quadrilatero_contorno"     # candidato a SWY; a rotulagem decide
    return None


def extrair(pdf, calibracao):
    g = carregar_calibracao(calibracao)
    pag = pymupdf.open(pdf)[0]
    feats = []
    for i, d in enumerate(pag.get_drawings()):
        if not MOLDURA.contains(d["rect"]):
            continue
        c = classe(d)
        if c is None:
            continue
        for k, (anel, trechos) in enumerate(aneis(d)):
            if c == "pista":
                lados = [((anel[j][0] - anel[j - 1][0]) ** 2 + (anel[j][1] - anel[j - 1][1]) ** 2) ** 0.5
                         for j in range(len(anel))]
                if len(anel) not in (4, 5) or max(lados) < 100:
                    continue
            geo = [g(x, y) for x, y in anel]
            enu = [para_enu(la, lo) for la, lo in geo]
            feats.append({
                "type": "Feature",
                "properties": {"pdf_id": i, "anel": k, "classe": c, "n_vertices": len(anel),
                               "n_trechos": contar_trechos(fechar(anel, trechos)),
                               "enu_m": [[round(e, 3), round(n, 3)] for e, n in enu],
                               "pagina_pt": [[round(x, 3), round(y, 3)] for x, y in anel]},
                "geometry": {"type": "Polygon",
                             "coordinates": [[[lo, la] for la, lo in geo] + [[geo[0][1], geo[0][0]]]]},
            })
    return {"type": "FeatureCollection",
            "properties": {"fonte": Path(pdf).name, "calibracao": Path(calibracao).name,
                           "plano_local": "ENU tangente em THR16 (AD 2.12)"},
            "features": feats}


if __name__ == "__main__":
    pdf = sys.argv[1]
    cal = sys.argv[2] if len(sys.argv) > 2 else str(Path(__file__).with_name("calibracao.json"))
    fc = extrair(pdf, cal)
    Path(__file__).with_name("contornos_brutos.geojson").write_text(json.dumps(fc, ensure_ascii=False))
    from collections import Counter
    print(Counter(f["properties"]["classe"] for f in fc["features"]))
    for f in fc["features"]:
        p = f["properties"]
        if p["classe"] != "pavimento":
            print(p["pdf_id"], p["classe"], p["n_vertices"], "vértices")
