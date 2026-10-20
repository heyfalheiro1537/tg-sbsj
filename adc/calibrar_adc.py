"""Calibra o ADC (fonte F1) contra a gratícula impressa e mede r_cal.

Procedimento registrado no protocolo (H1, oráculo). Não usa o modelo do TG nem
nenhuma feição do aeródromo: só os tiques da gratícula, cujo valor é conhecido
por construção. Por isso rodá-lo não antecipa nenhum resultado de H1.

1. Extrai do PDF vetorial os tiques da moldura: latitude nas bordas esquerda e
   direita, longitude no topo e na base, a cada 6". Os tiques longos são os
   rotulados (00" e 30"); os demais se contam a partir deles.
2. Ajusta por mínimos quadrados, separadamente, φ = a·x + b·y + c e
   λ = d·x + e·y + f, onde (x, y) é a ponta do tique encostada na moldura.
   Linear em lat/lon basta: em 2 km a curvatura da gratícula de uma carta
   conforme fica abaixo de 1 cm.
3. Resíduo de cada tique em metros (norte para latitude, leste para
   longitude). Regra de exclusão, fixada antes de olhar qualquer feição: tique
   com resíduo maior que 5 vezes a mediana dos resíduos é erro de desenho do
   próprio tique; sai do ajuste e é listado.
4. r_cal = raiz(máx|resíduo norte|² + máx|resíduo leste|²) sobre os tiques
   mantidos: limite superior do erro de georreferenciamento de um ponto.

Uso: python3 calibrar_adc.py <adc.pdf>  → imprime o relatório e grava calibracao.json
"""
import json
import statistics
import sys
from math import cos, radians, sqrt
from pathlib import Path

import pymupdf

sys.path.insert(0, str(Path(__file__).parent))
from adc_geo import raios  # noqa: E402

PASSO_S = 6.0                                   # segundos entre tiques
FATOR_EXCLUSAO = 5.0


def segmentos(pdf):
    p = pymupdf.open(pdf)[0]
    out = []
    for d in p.get_drawings():
        if d["type"] != "s" or len(d["items"]) != 1 or d["items"][0][0] != "l":
            continue
        a, b = d["items"][0][1], d["items"][0][2]
        out.append((a.x, a.y, b.x, b.y))
    return out


def tiques(segs):
    """Classifica tiques da moldura: (eixo, borda, x_moldura, y_moldura, comprimento)."""
    X_ESQ, X_DIR, Y_TOPO, Y_BASE = 25.65, 399.6, 78.02, 579.5
    res = []
    for x0, y0, x1, y1 in segs:
        L = sqrt((x1 - x0) ** 2 + (y1 - y0) ** 2)
        if not 5 < L < 12:
            continue
        horiz = abs(y1 - y0) < 0.2
        vert = abs(x1 - x0) < 0.2
        pts = [(x0, y0), (x1, y1)]
        if horiz and min(abs(x - X_ESQ) for x, _ in pts) < 0.5:
            x, y = min(pts, key=lambda q: abs(q[0] - X_ESQ)); res.append(("lat", "esq", x, y, L))
        elif horiz and min(abs(x - X_DIR) for x, _ in pts) < 0.5:
            x, y = min(pts, key=lambda q: abs(q[0] - X_DIR)); res.append(("lat", "dir", x, y, L))
        elif vert and min(abs(y - Y_TOPO) for _, y in pts) < 0.5:
            x, y = min(pts, key=lambda q: abs(q[1] - Y_TOPO)); res.append(("lon", "topo", x, y, L))
        elif vert and max(y for _, y in pts) > Y_BASE - 2.5 and min(y for _, y in pts) > 560:
            x, y = max(pts, key=lambda q: q[1]); res.append(("lon", "base", x, y, L))
    return res


def rotular(ts):
    """Atribui o valor (segundos de arco absolutos dentro do grau) a cada tique."""
    # escala aproximada a partir dos rótulos da borda esquerda e do topo
    lat_esq = sorted((t for t in ts if t[0] == "lat" and t[1] == "esq" and t[4] > 9), key=lambda t: t[3])
    lon_topo = sorted((t for t in ts if t[0] == "lon" and t[1] == "topo" and t[4] > 9), key=lambda t: t[2])
    pt_por_s_lat = (lat_esq[-1][3] - lat_esq[0][3]) / (90.0)          # 13'00" → 14'30"
    pt_por_s_lon = (lon_topo[-1][2] - lon_topo[0][2]) / (60.0)         # 52'00" → 51'00"
    out = []
    for eixo, borda, x, y, L in ts:
        if eixo == "lat":
            longos = sorted((t for t in ts if t[0] == "lat" and t[1] == borda and t[4] > 9), key=lambda t: t[3])
            ref_y, ref_v = longos[0][3], 13 * 60 + 0
            v = ref_v + (y - ref_y) / pt_por_s_lat                     # latitude sul cresce para baixo
        else:
            longos = sorted((t for t in ts if t[0] == "lon" and t[1] == borda and t[4] > 9), key=lambda t: t[2])
            ref_x, ref_v = longos[0][2], 52 * 60 + 0
            v = ref_v - (x - ref_x) / pt_por_s_lon                     # longitude oeste decresce para a direita
        out.append((eixo, borda, x, y, L, round(v / PASSO_S) * PASSO_S))
    return out, pt_por_s_lat, pt_por_s_lon


def mmq(linhas):
    """Mínimos quadrados para v = a·x + b·y + c (3 parâmetros)."""
    import numpy as np
    M = np.array([[x, y, 1.0] for x, y, _ in linhas])
    v = np.array([vv for _, _, vv in linhas])
    coef, *_ = np.linalg.lstsq(M, v, rcond=None)
    return coef, v - M @ coef


def ajustar(rot):
    lat0 = -(23 + 13.75 / 60)
    M, N = raios(lat0)
    m_por_s_lat = M * radians(1 / 3600)
    m_por_s_lon = N * cos(radians(lat0)) * radians(1 / 3600)
    resultado = {}
    for eixo, m_por_s in (("lat", m_por_s_lat), ("lon", m_por_s_lon)):
        ts = [t for t in rot if t[0] == eixo]
        mantidos, excluidos = list(ts), []
        for _ in range(3):                                   # no máximo 3 rodadas de exclusão
            coef, r = mmq([(t[2], t[3], t[5]) for t in mantidos])
            rm = [abs(x) * m_por_s for x in r]
            med = statistics.median(rm)
            pior = max(range(len(rm)), key=lambda i: rm[i])
            if rm[pior] > FATOR_EXCLUSAO * med:
                excluidos.append((mantidos[pior], rm[pior]))
                mantidos.pop(pior)
            else:
                break
        resultado[eixo] = {
            "coef": [float(c) for c in coef],
            "n_tiques": len(ts), "n_mantidos": len(mantidos),
            "residuo_max_m": float(max(rm)), "residuo_mediano_m": float(med),
            "residuo_rms_m": float(sqrt(sum(x * x for x in rm) / len(rm))),
            "excluidos": [{"borda": t[1], "x": round(t[2], 2), "y": round(t[3], 2),
                           "valor_s": t[5], "residuo_m": round(float(e), 2)} for t, e in excluidos],
        }
    r_cal = sqrt(resultado["lat"]["residuo_max_m"] ** 2 + resultado["lon"]["residuo_max_m"] ** 2)
    return resultado, r_cal


if __name__ == "__main__":
    pdf = sys.argv[1]
    ts = tiques(segmentos(pdf))
    rot, sl, so = rotular(ts)
    res, r_cal = ajustar(rot)
    for eixo in ("lat", "lon"):
        r = res[eixo]
        print(f"{eixo}: {r['n_mantidos']}/{r['n_tiques']} tiques; resíduo máx {r['residuo_max_m']:.2f} m, "
              f"mediano {r['residuo_mediano_m']:.2f} m, rms {r['residuo_rms_m']:.2f} m")
        for e in r["excluidos"]:
            print(f"   excluído: {e}")
    print(f"r_cal = {r_cal:.2f} m")
    print(f"tolerância H1b = r_cal + 1,77 = {r_cal + 1.77:.2f} m")
    Path(__file__).with_name("calibracao.json").write_text(json.dumps(
        {"fonte": Path(pdf).name, "r_cal_m": r_cal,
         "convencao": "valor = segundos dentro do grau; lat = -(23 + v/3600), lon = -(45 + v/3600); (x, y) em pontos da página 1",
         "ajuste": res}, indent=2, ensure_ascii=False))
