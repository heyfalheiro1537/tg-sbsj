"""Gabarito geodésico independente do motor.

Implementação em Python puro das fórmulas de Vincenty (1975) sobre o GRS80,
sem importar nada do repositório do TG nem bibliotecas de geodésia. Serve de
oráculo para o ato 4 (troca de referencial), onde o gabarito é "calculado à
mão": a independência vem de ser outro algoritmo, em outro código.

Exatidão declarada das fórmulas: 0,5 mm sobre o elipsoide (Vincenty, 1975).
Esse número é a tolerância numérica do ato 4 no protocolo.

Referência: Vincenty, T. (1975). Direct and inverse solutions of geodesics on
the ellipsoid with application of nested equations. Survey Review 23(176).
"""
from math import atan, atan2, cos, radians, degrees, sin, sqrt, tan, pi

# GRS80 (base do SIRGAS2000)
A = 6378137.0
F = 1 / 298.257222101
B = A * (1 - F)
E2 = F * (2 - F)


def dms(graus: int, minutos: int, segundos: float, hemisferio: str) -> float:
    """Converte GMS para graus decimais; S e W são negativos."""
    v = graus + minutos / 60 + segundos / 3600
    return -v if hemisferio in ("S", "W") else v


def aip(texto: str) -> float:
    """Lê coordenada no formato do AD 2.12: '231310.79S' ou '0455219.08W'."""
    h = texto[-1]
    corpo = texto[:-1]
    inteiro, frac = corpo.split(".")
    gw = 2 if h in "NS" else 3
    g, m, s = int(inteiro[:gw]), int(inteiro[gw:gw + 2]), float(inteiro[gw + 2:] + "." + frac)
    return dms(g, m, s, h)


def inversa(lat1, lon1, lat2, lon2, tol=1e-12, max_iter=200):
    """Distância (m) e azimutes verdadeiros (°) de 1→2 em 1 e de 2→1 em 2."""
    L = radians(lon2 - lon1)
    U1 = atan((1 - F) * tan(radians(lat1)))
    U2 = atan((1 - F) * tan(radians(lat2)))
    sU1, cU1, sU2, cU2 = sin(U1), cos(U1), sin(U2), cos(U2)
    lam = L
    for _ in range(max_iter):
        sl, cl = sin(lam), cos(lam)
        ss = sqrt((cU2 * sl) ** 2 + (cU1 * sU2 - sU1 * cU2 * cl) ** 2)
        cs = sU1 * sU2 + cU1 * cU2 * cl
        sig = atan2(ss, cs)
        sa = cU1 * cU2 * sl / ss
        c2a = 1 - sa * sa
        c2sm = cs - 2 * sU1 * sU2 / c2a if c2a else 0.0
        C = F / 16 * c2a * (4 + F * (4 - 3 * c2a))
        lam_ant = lam
        lam = L + (1 - C) * F * sa * (sig + C * ss * (c2sm + C * cs * (-1 + 2 * c2sm ** 2)))
        if abs(lam - lam_ant) < tol:
            break
    else:
        raise RuntimeError("Vincenty inversa não convergiu")
    u2 = c2a * (A * A - B * B) / (B * B)
    Ak = 1 + u2 / 16384 * (4096 + u2 * (-768 + u2 * (320 - 175 * u2)))
    Bk = u2 / 1024 * (256 + u2 * (-128 + u2 * (74 - 47 * u2)))
    ds = Bk * ss * (c2sm + Bk / 4 * (cs * (-1 + 2 * c2sm ** 2)
                                     - Bk / 6 * c2sm * (-3 + 4 * ss ** 2) * (-3 + 4 * c2sm ** 2)))
    s = B * Ak * (sig - ds)
    a1 = atan2(cU2 * sin(lam), cU1 * sU2 - sU1 * cU2 * cos(lam))
    a2 = atan2(cU1 * sin(lam), -sU1 * cU2 + cU1 * sU2 * cos(lam))
    az12 = degrees(a1) % 360
    az21 = (degrees(a2) + 180) % 360  # azimute de 2 para 1, medido em 2
    return s, az12, az21


def direta(lat1, lon1, az1, s, tol=1e-12, max_iter=200):
    """Ponto a distância s (m) de 1 no azimute az1 (°). Devolve lat, lon, azimute em 2."""
    a1 = radians(az1)
    sa1, ca1 = sin(a1), cos(a1)
    tU1 = (1 - F) * tan(radians(lat1))
    cU1 = 1 / sqrt(1 + tU1 ** 2)
    sU1 = tU1 * cU1
    sig1 = atan2(tU1, ca1)
    sa = cU1 * sa1
    c2a = 1 - sa * sa
    u2 = c2a * (A * A - B * B) / (B * B)
    Ak = 1 + u2 / 16384 * (4096 + u2 * (-768 + u2 * (320 - 175 * u2)))
    Bk = u2 / 1024 * (256 + u2 * (-128 + u2 * (74 - 47 * u2)))
    sig = s / (B * Ak)
    for _ in range(max_iter):
        c2sm = cos(2 * sig1 + sig)
        ss, cs = sin(sig), cos(sig)
        ds = Bk * ss * (c2sm + Bk / 4 * (cs * (-1 + 2 * c2sm ** 2)
                                         - Bk / 6 * c2sm * (-3 + 4 * ss ** 2) * (-3 + 4 * c2sm ** 2)))
        sig_ant = sig
        sig = s / (B * Ak) + ds
        if abs(sig - sig_ant) < tol:
            break
    else:
        raise RuntimeError("Vincenty direta não convergiu")
    ss, cs = sin(sig), cos(sig)
    c2sm = cos(2 * sig1 + sig)
    t = sU1 * ss - cU1 * cs * ca1
    lat2 = atan2(sU1 * cs + cU1 * ss * ca1, (1 - F) * sqrt(sa * sa + t * t))
    lam = atan2(ss * sa1, cU1 * cs - sU1 * ss * ca1)
    C = F / 16 * c2a * (4 + F * (4 - 3 * c2a))
    L = lam - (1 - C) * F * sa * (sig + C * ss * (c2sm + C * cs * (-1 + 2 * c2sm ** 2)))
    a2 = atan2(sa, -t)
    return degrees(lat2), lon1 + degrees(L), degrees(a2) % 360


def raios(lat):
    """Raio meridiano M e grande normal N (m) na latitude dada."""
    s2 = sin(radians(lat)) ** 2
    w = sqrt(1 - E2 * s2)
    return A * (1 - E2) / w ** 3, A / w


def resolver(referente, outro, s, o):
    """Regra de resolução de seed declarada no protocolo (ISO 19148).

    referente, outro: (lat, lon) dos dois Referents do LinearElement.
    s: distância ao longo, a partir do referente, positiva em direção ao outro.
    o: afastamento lateral, positivo à direita de quem anda do referente para o outro.
    """
    _, az, _ = inversa(*referente, *outro)
    if s >= 0:
        lat, lon, az_p = direta(*referente, az, s)
    else:
        lat, lon, az_p = direta(*referente, (az + 180) % 360, -s)
        az_p = (az_p + 180) % 360
    if o == 0:
        return lat, lon
    lat, lon, _ = direta(lat, lon, (az_p + 90) % 360 if o > 0 else (az_p - 90) % 360, abs(o))
    return lat, lon
