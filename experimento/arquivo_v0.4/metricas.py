"""Métricas de H1, como o protocolo as define."""
import numpy as np
import shapely

PASSO = 0.1      # m; amostragem da borda (protocolo H1.02)


def _pontos_da_borda(geom, passo=PASSO):
    """Pontos a cada 'passo' metros ao longo de todas as bordas, mais os vértices."""
    pts = []
    bordas = geom.boundary
    linhas = list(bordas.geoms) if hasattr(bordas, "geoms") else [bordas]
    for ln in linhas:
        n = max(2, int(np.ceil(ln.length / passo)) + 1)
        d = np.linspace(0, ln.length, n)
        pts.append(shapely.line_interpolate_point(ln, d))
        pts.append(shapely.points(np.array(ln.coords)))
    return np.concatenate(pts)


def contencao(contorno, envoltoria):
    """Hausdorff dirigido contorno → envoltória (0 = contido). H1.01."""
    return float(np.max(shapely.distance(envoltoria, _pontos_da_borda(contorno))))


def desvios(envoltoria, contorno):
    """Distância de cada ponto da borda da envoltória ao contorno (0 se dentro)."""
    return shapely.distance(contorno, _pontos_da_borda(envoltoria))


def desvio_p95(envoltoria, contorno):
    return float(np.percentile(desvios(envoltoria, contorno), 95))


def desvio_max(envoltoria, contorno):
    return float(np.max(desvios(envoltoria, contorno)))


def hausdorff(a, b):
    """Hausdorff simétrico entre as bordas, com amostragem densa. H1.05."""
    pa, pb = _pontos_da_borda(a), _pontos_da_borda(b)
    return float(max(np.max(shapely.distance(b.boundary, pa)), np.max(shapely.distance(a.boundary, pb))))
