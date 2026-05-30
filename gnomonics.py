import math

import numpy as np

from solar_model import day_index_in_year, orbital_model


def contiguous_true_runs(mask):
    """
    Devuelve listas de índices contiguos donde mask es True.
    """
    idx = np.flatnonzero(mask)
    if idx.size == 0:
        return []

    cuts = np.where(np.diff(idx) > 1)[0] + 1
    return np.split(idx, cuts)


def xy_shadow(phi, delta, H, p=1.0, ell=0.0):
    """
    Coordenadas de la punta de la sombra en el plano horizontal.

    D = sin(h)
    x = p cos(delta) sin(H) / D
    y = p [sin(phi) cos(delta) cos(H) - cos(phi) sin(delta)] / D - ell
    """
    D = np.sin(phi) * np.sin(delta) + np.cos(phi) * np.cos(delta) * np.cos(H)
    h = np.arcsin(np.clip(D, -1.0, 1.0))

    with np.errstate(divide="ignore", invalid="ignore"):
        x = p * np.cos(delta) * np.sin(H) / D
        y = p * (
            np.sin(phi) * np.cos(delta) * np.cos(H)
            - np.cos(phi) * np.sin(delta)
        ) / D - ell

    return x, y, D, h


def babilonic_line_params(n, phi, p=1.0, ell=0.0):
    beta = math.radians(7.5 * n)
    cot_beta = 1.0 / math.tan(beta)

    m = cot_beta / math.sin(phi)
    b = -ell + p * (cot_beta**2 - math.cos(2.0 * phi)) / (
        2.0 * math.sin(phi) * math.cos(phi)
    )
    return m, b


def italic_line_params(n, phi, p=1.0, ell=0.0):
    beta = math.radians(7.5 * n)
    cot_beta = 1.0 / math.tan(beta)

    m = -cot_beta / math.sin(phi)
    b = -ell + p * (cot_beta**2 - math.cos(2.0 * phi)) / (
        2.0 * math.sin(phi) * math.cos(phi)
    )
    return m, b


def visible_line_segments(
    phi,
    selected_n,
    p=1.0,
    ell=0.0,
    min_altitude_deg=5.0,
    samples=6000,
    orbital_kwargs=None,
):
    orbital_kwargs = orbital_kwargs or {}

    d = np.linspace(0.0, orbital_kwargs.get("T", 365.2422), samples, endpoint=False)
    delta, _ = orbital_model(d, **orbital_kwargs)

    H0 = np.arccos(np.clip(-np.tan(phi) * np.tan(delta), -1.0, 1.0))
    hmin = math.radians(min_altitude_deg)

    bab = {}
    ita = {}

    for n in selected_n:
        # Babilónicas: H = -H0 + n*15°
        Hb = -H0 + math.radians(15.0 * n)
        xb, yb, Db, hb = xy_shadow(phi, delta, Hb, p=p, ell=ell)

        mask_b = (
            (Hb <= H0)
            & (Db > 0.0)
            & (hb >= hmin)
            & np.isfinite(xb)
            & np.isfinite(yb)
        )
        pts_b = np.column_stack([xb[mask_b], yb[mask_b]])
        if len(pts_b) > 1:
            bab[n] = pts_b

        # Itálicas: H = H0 - n*15°
        Hi = H0 - math.radians(15.0 * n)
        xi, yi, Di, hi = xy_shadow(phi, delta, Hi, p=p, ell=ell)

        mask_i = (
            (-H0 <= Hi)
            & (Di > 0.0)
            & (hi >= hmin)
            & np.isfinite(xi)
            & np.isfinite(yi)
        )
        pts_i = np.column_stack([xi[mask_i], yi[mask_i]])
        if len(pts_i) > 1:
            ita[n] = pts_i

    return bab, ita


def analemma_curves(
    phi,
    hours,
    lon_deg,
    tz_standard=2.0,
    p=1.0,
    ell=0.0,
    min_altitude_deg=0.2,
    samples=5000,
    orbital_kwargs=None,
):
    """
    Analemas a hora civil fija.
    """
    orbital_kwargs = orbital_kwargs or {}
    T = orbital_kwargs.get("T", 365.2422)

    hmin = math.radians(min_altitude_deg)
    curves = {}

    for hour in hours:
        d = np.linspace(0.0, T, samples, endpoint=False)
        d_eval = d + (hour - tz_standard) / 24.0

        delta, Et = orbital_model(d_eval, **orbital_kwargs)
        Et_hours = (12.0 / math.pi) * Et

        tst = hour + lon_deg / 15.0 - tz_standard - Et_hours
        H = np.radians(15.0 * (tst - 12.0))

        x, y, D, h = xy_shadow(phi, delta, H, p=p, ell=ell)

        mask = (
            (D > 0.0)
            & (h >= hmin)
            & np.isfinite(x)
            & np.isfinite(y)
        )

        runs = contiguous_true_runs(mask)
        segments = []

        for run in runs:
            pts = np.column_stack([x[run], y[run]])
            if len(pts) > 1:
                segments.append(pts)

        if segments:
            curves[hour] = segments

    return curves


def true_hour_curves(
    phi,
    true_hours,
    p=1.0,
    ell=0.0,
    min_altitude_deg=0.2,
    samples=5000,
    orbital_kwargs=None,
):
    """
    Familia de horas solares verdaderas H = cte.
    En esta geometría (gnomon vertical), estas curvas no son rectas
    en general; la línea equinoccial horizontal se trata aparte.
    """
    orbital_kwargs = orbital_kwargs or {}
    T = orbital_kwargs.get("T", 365.2422)

    hmin = math.radians(min_altitude_deg)
    curves = {}

    d = np.linspace(0.0, T, samples, endpoint=False)
    delta, _ = orbital_model(d, **orbital_kwargs)

    for hour in true_hours:
        H_const = math.radians(15.0 * (hour - 12.0))
        H = np.full_like(delta, H_const, dtype=float)

        x, y, D, h = xy_shadow(phi, delta, H, p=p, ell=ell)

        mask = (
            (D > 0.0)
            & (h >= hmin)
            & np.isfinite(x)
            & np.isfinite(y)
        )

        runs = contiguous_true_runs(mask)
        segments = []

        for run in runs:
            pts = np.column_stack([x[run], y[run]])
            if len(pts) > 1:
                segments.append(pts)

        if segments:
            curves[hour] = segments

    return curves


def equinoctial_y(phi, p=1.0, ell=0.0):
    """
    En el equinoccio (delta = 0), la curva diaria resulta ser una recta
    horizontal: y = p tan(phi) - ell.
    Se devuelve un segmento recortado por radio máximo y, opcionalmente,
    por |x| <= max_abs_x.
    """
    y = p * math.tan(phi) - ell
    if not np.isfinite(y):
        return None
    return y


def day_curve_for_date(
    phi,
    year,
    month,
    day,
    lon_deg=0.0,
    tz_standard=2.0,
    p=1.0,
    ell=0.0,
    min_altitude_deg=0.2,
    min_civil_hour=None,
    max_civil_hour=None,
    samples=3000,
    orbital_kwargs=None,
):
    """
    Curva diaria para una fecha fija.
    """
    orbital_kwargs = orbital_kwargs or {}
    hmin = math.radians(min_altitude_deg)

    day_index = day_index_in_year(year, month, day)

    d_mid = day_index + (12.0 - tz_standard) / 24.0
    delta_mid, _ = orbital_model(np.array([d_mid]), **orbital_kwargs)
    delta0 = float(delta_mid[0])

    arg = -math.tan(phi) * math.tan(delta0)
    arg = max(-1.0, min(1.0, arg))
    H0 = math.acos(arg)

    Hstart = -H0
    Hend = H0

    if min_civil_hour is not None:
        d_eval = day_index + (min_civil_hour - tz_standard) / 24.0
        _, Et_eval = orbital_model(np.array([d_eval]), **orbital_kwargs)
        Et_hours = (12.0 / math.pi) * float(Et_eval[0])
        tst = min_civil_hour + lon_deg / 15.0 - tz_standard - Et_hours
        Hstart = math.radians(15.0 * (tst - 12.0))
        Hstart = max(-H0, min(H0, Hstart))

    if max_civil_hour is not None:
        d_eval = day_index + (max_civil_hour - tz_standard) / 24.0
        _, Et_eval = orbital_model(np.array([d_eval]), **orbital_kwargs)
        Et_hours = (12.0 / math.pi) * float(Et_eval[0])
        tst = max_civil_hour + lon_deg / 15.0 - tz_standard - Et_hours
        Hend = math.radians(15.0 * (tst - 12.0))
        Hend = max(-H0, min(H0, Hend))

    if Hend <= Hstart:
        return [], delta0

    H = np.linspace(Hstart, Hend, samples)

    x, y, D, h = xy_shadow(phi, delta0, H, p=p, ell=ell)

    mask = (
        (D > 0.0)
        & (h >= hmin)
        & np.isfinite(x)
        & np.isfinite(y)
    )

    runs = contiguous_true_runs(mask)
    segments = []

    for run in runs:
        pts = np.column_stack([x[run], y[run]])
        if len(pts) > 1:
            segments.append(pts)

    return segments, delta0
