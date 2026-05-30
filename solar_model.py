import math
from datetime import date

import numpy as np

TAU = 2.0 * math.pi


def wrap_to_pi(angle):
    angle = np.asarray(angle, dtype=float)
    return (angle + math.pi) % (2.0 * math.pi) - math.pi


def solve_kepler(M, ecc, tol=1e-12, max_iter=60):
    """
    Resuelve M = u - e sin(u) mediante Newton-Raphson.
    """
    M = np.asarray(M, dtype=float)
    u = M.copy()

    for _ in range(max_iter):
        f = u - ecc * np.sin(u) - M
        fp = 1.0 - ecc * np.cos(u)
        du = -f / fp
        u = u + du
        if np.max(np.abs(du)) < tol:
            break

    return u


def day_index_in_year(year, month, day):
    """
    Número de días transcurridos desde el 1 de enero.
    """
    return (date(year, month, day) - date(year, 1, 1)).days


def orbital_model(
    d_days,
    T=365.2422,
    epsilon_deg=23.44,
    e=0.01671123,
    varpi_deg=102.93768193,
    dperi=2.71875,
):
    """
    Devuelve:
    - delta(d): declinación solar
    - Et(d): ecuación del tiempo en radianes angulares
    """
    d = np.asarray(d_days, dtype=float)

    eps = math.radians(epsilon_deg)
    varpi = math.radians(varpi_deg)

    M = TAU / T * (d - dperi)
    u = solve_kepler(M, e)

    v = 2.0 * np.arctan2(
        np.sqrt(1.0 + e) * np.sin(u / 2.0),
        np.sqrt(1.0 - e) * np.cos(u / 2.0),
    )

    # Longitud eclíptica geocéntrica del Sol
    lam = v + varpi + math.pi

    alpha = np.arctan2(
        np.sin(lam) * np.cos(eps),
        np.cos(lam),
    )

    Et = wrap_to_pi((v - M) - (lam - alpha))
    delta = np.arcsin(np.sin(eps) * np.sin(lam))

    return delta, Et