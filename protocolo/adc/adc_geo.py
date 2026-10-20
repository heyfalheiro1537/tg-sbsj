"""Conversões geodésicas usadas na calibração e na extração do ADC.

Sem dependência do motor do TG. GRS80; plano local ENU (tangente) com origem
em THR16 publicada (AD 2.12). Em 3 km o erro do plano tangente é < 1 mm.
"""
from math import atan2, cos, radians, degrees, sin, sqrt

A = 6378137.0
F = 1 / 298.257222101
E2 = F * (2 - F)

# Origem do plano local: THR16, AD 2.12 (premissa); altura elipsoidal 619,3 − 2,6
ORIGEM = (-(23 + 13 / 60 + 10.79 / 3600), -(45 + 52 / 60 + 19.08 / 3600), 616.7)


def _ecef(lat, lon, h=0.0):
    la, lo = radians(lat), radians(lon)
    n = A / sqrt(1 - E2 * sin(la) ** 2)
    return ((n + h) * cos(la) * cos(lo), (n + h) * cos(la) * sin(lo), (n * (1 - E2) + h) * sin(la))


def para_enu(lat, lon, h=None, origem=ORIGEM):
    """(lat, lon) → (leste, norte) em metros no plano tangente da origem.

    Sem altura, o ponto é posto na altura elipsoidal da origem, o que mantém o
    plano horizontal (uma carta 2D não informa altura).
    """
    h = origem[2] if h is None else h
    x, y, z = _ecef(lat, lon, h)
    x0, y0, z0 = _ecef(*origem)
    dx, dy, dz = x - x0, y - y0, z - z0
    la, lo = radians(origem[0]), radians(origem[1])
    e = -sin(lo) * dx + cos(lo) * dy
    n = -sin(la) * cos(lo) * dx - sin(la) * sin(lo) * dy + cos(la) * dz
    return e, n


def raios(lat):
    s2 = sin(radians(lat)) ** 2
    w = sqrt(1 - E2 * s2)
    return A * (1 - E2) / w ** 3, A / w
