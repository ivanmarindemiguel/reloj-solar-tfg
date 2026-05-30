import math

import numpy as np

from solar_model import day_index_in_year, orbital_model


def contiguous_true_runs(mask):
    """
    Devuelve listas de indices contiguos donde mask es True.
    """
    idx = np.flatnonzero(mask)
    if idx.size == 0:
        return []

    cuts = np.where(np.diff(idx) > 1)[0] + 1
    return np.split(idx, cuts)


def vertical_shadow(phi, delta, H, gamma=0.0, a=1.0, p=1.0):
    """
    Coordenadas de la sombra del nodus sobre una pared vertical.
    El origen de la plantilla es la proyeccion perpendicular del nodus
    sobre la pared, de modo que el nodus proyectado queda en (0, 0).

    La pared tiene declinacion gamma:
    gamma = 0 mira al Sur, gamma > 0 gira hacia Este.

    B = cos(gamma) [sin(phi) cos(delta) cos(H) - cos(phi) sin(delta)]
        - sin(gamma) cos(delta) sin(H)

    X = a [cos(gamma) cos(delta) sin(H)
           + sin(gamma) (sin(phi) cos(delta) cos(H) - cos(phi) sin(delta))] / B
    Y = - a D / B
    """
    D = np.sin(phi) * np.sin(delta) + np.cos(phi) * np.cos(delta) * np.cos(H)
    h = np.arcsin(np.clip(D, -1.0, 1.0))

    north_shadow_component = (
        np.sin(phi) * np.cos(delta) * np.cos(H)
        - np.cos(phi) * np.sin(delta)
    )

    B = (
        math.cos(gamma) * north_shadow_component
        - math.sin(gamma) * np.cos(delta) * np.sin(H)
    )

    numerator_x = (
        math.cos(gamma) * np.cos(delta) * np.sin(H)
        + math.sin(gamma) * north_shadow_component
    )

    with np.errstate(divide="ignore", invalid="ignore"):
        X = a * numerator_x / B
        Y = -a * D / B

    return X, Y, D, B, h


def vertical_babilonic_line_params(n, phi, gamma=0.0, a=1.0, p=1.0):
    beta = math.radians(7.5 * n)
    cot_beta = 1.0 / math.tan(beta)
    denominator = cot_beta**2 - math.cos(2.0 * phi)

    m = (
        2.0
        * math.cos(phi)
        * (math.cos(gamma) * cot_beta - math.sin(phi) * math.sin(gamma))
        / denominator
    )
    b = -(
        2.0
        * a
        * math.cos(phi)
        * (math.sin(phi) * math.cos(gamma) + math.sin(gamma) * cot_beta)
        / denominator
    )
    return m, b


def vertical_italic_line_params(n, phi, gamma=0.0, a=1.0, p=1.0):
    beta = math.radians(7.5 * n)
    cot_beta = 1.0 / math.tan(beta)
    denominator = cot_beta**2 - math.cos(2.0 * phi)

    m = -(
        2.0
        * math.cos(phi)
        * (math.cos(gamma) * cot_beta + math.sin(phi) * math.sin(gamma))
        / denominator
    )
    b = (
        2.0
        * a
        * math.cos(phi)
        * (-math.sin(phi) * math.cos(gamma) + math.sin(gamma) * cot_beta)
        / denominator
    )
    return m, b


def _visible_segments_from_arrays(X, Y, D, B, h, min_altitude_deg):
    hmin = math.radians(min_altitude_deg)
    bmin = math.sin(hmin)
    mask = (
        (D > 0.0)
        & (B > bmin)
        & (h >= hmin)
        & np.isfinite(X)
        & np.isfinite(Y)
    )

    segments = []
    for run in contiguous_true_runs(mask):
        pts = np.column_stack([X[run], Y[run]])
        if len(pts) > 1:
            segments.append(pts)
    return segments


def vertical_visible_line_segments(
    phi,
    selected_n,
    gamma=0.0,
    a=1.0,
    p=1.0,
    min_altitude_deg=0.2,
    samples=6000,
    orbital_kwargs=None,
):
    orbital_kwargs = orbital_kwargs or {}

    d = np.linspace(0.0, orbital_kwargs.get("T", 365.2422), samples, endpoint=False)
    delta, _ = orbital_model(d, **orbital_kwargs)

    H0 = np.arccos(np.clip(-np.tan(phi) * np.tan(delta), -1.0, 1.0))

    bab = {}
    ita = {}

    for n in selected_n:
        Hb = -H0 + math.radians(15.0 * n)
        Xb, Yb, Db, Bb, hb = vertical_shadow(
            phi, delta, Hb, gamma=gamma, a=a, p=p
        )
        segments_b = _visible_segments_from_arrays(
            Xb, Yb, Db, Bb, hb, min_altitude_deg
        )
        segments_b = [
            segment
            for segment in segments_b
            if len(segment) > 1
        ]
        mask_b_range = Hb <= H0
        if segments_b and np.any(mask_b_range):
            bab[n] = segments_b

        Hi = H0 - math.radians(15.0 * n)
        Xi, Yi, Di, Bi, hi = vertical_shadow(
            phi, delta, Hi, gamma=gamma, a=a, p=p
        )
        segments_i = _visible_segments_from_arrays(
            Xi, Yi, Di, Bi, hi, min_altitude_deg
        )
        segments_i = [
            segment
            for segment in segments_i
            if len(segment) > 1
        ]
        mask_i_range = -H0 <= Hi
        if segments_i and np.any(mask_i_range):
            ita[n] = segments_i

    return bab, ita


def vertical_analemma_curves(
    phi,
    hours,
    lon_deg,
    gamma=0.0,
    tz_standard=2.0,
    a=1.0,
    p=1.0,
    min_altitude_deg=0.2,
    samples=5000,
    orbital_kwargs=None,
):
    orbital_kwargs = orbital_kwargs or {}
    T = orbital_kwargs.get("T", 365.2422)

    curves = {}

    for hour in hours:
        d = np.linspace(0.0, T, samples, endpoint=False)
        d_eval = d + (hour - tz_standard) / 24.0

        delta, Et = orbital_model(d_eval, **orbital_kwargs)
        Et_hours = (12.0 / math.pi) * Et

        true_solar_time = hour + lon_deg / 15.0 - tz_standard - Et_hours
        H = np.radians(15.0 * (true_solar_time - 12.0))

        X, Y, D, B, h = vertical_shadow(phi, delta, H, gamma=gamma, a=a, p=p)
        segments = _visible_segments_from_arrays(X, Y, D, B, h, min_altitude_deg)
        if segments:
            curves[hour] = segments

    return curves


def vertical_true_hour_curves(
    phi,
    true_hours,
    gamma=0.0,
    a=1.0,
    p=1.0,
    min_altitude_deg=0.2,
    samples=5000,
    orbital_kwargs=None,
):
    orbital_kwargs = orbital_kwargs or {}
    T = orbital_kwargs.get("T", 365.2422)

    curves = {}

    d = np.linspace(0.0, T, samples, endpoint=False)
    delta, _ = orbital_model(d, **orbital_kwargs)

    for hour in true_hours:
        H_const = math.radians(15.0 * (hour - 12.0))
        H = np.full_like(delta, H_const, dtype=float)

        X, Y, D, B, h = vertical_shadow(phi, delta, H, gamma=gamma, a=a, p=p)
        segments = _visible_segments_from_arrays(X, Y, D, B, h, min_altitude_deg)
        if segments:
            curves[hour] = segments

    return curves


def vertical_meridian_x(gamma=0.0, a=1.0):
    x = a * math.tan(gamma)
    if not np.isfinite(x):
        return None
    return x


def vertical_equinoctial_line_params(phi, gamma=0.0, a=1.0):
    """
    Recta equinoccial vertical en coordenadas relativas al nodus proyectado.

    Para delta = 0, los rayos solares cumplen dy + tan(phi) dz = 0.
    Al cortar con la pared vertical resulta:

        Y = -cot(phi) * (sin(gamma) * X + a * cos(gamma))
    """
    sin_phi = math.sin(phi)
    if math.isclose(sin_phi, 0.0, abs_tol=1.0e-12):
        return None

    cot_phi = math.cos(phi) / sin_phi
    m = -math.sin(gamma) * cot_phi
    b = -a * math.cos(gamma) * cot_phi
    if not (np.isfinite(m) and np.isfinite(b)):
        return None
    return m, b


def vertical_day_curve_for_date(
    phi,
    year,
    month,
    day,
    lon_deg=0.0,
    gamma=0.0,
    tz_standard=2.0,
    a=1.0,
    p=1.0,
    min_altitude_deg=0.2,
    min_civil_hour=None,
    max_civil_hour=None,
    samples=3000,
    orbital_kwargs=None,
):
    """
    Curva diaria vertical para una fecha fija.
    Si se proporcionan horas civiles limite, se recorta al tramo que
    une los puntos de esa fecha sobre el primer y ultimo analema.
    """
    orbital_kwargs = orbital_kwargs or {}

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
        true_solar_time = min_civil_hour + lon_deg / 15.0 - tz_standard - Et_hours
        Hstart = math.radians(15.0 * (true_solar_time - 12.0))
        Hstart = max(-H0, min(H0, Hstart))

    if max_civil_hour is not None:
        d_eval = day_index + (max_civil_hour - tz_standard) / 24.0
        _, Et_eval = orbital_model(np.array([d_eval]), **orbital_kwargs)
        Et_hours = (12.0 / math.pi) * float(Et_eval[0])
        true_solar_time = max_civil_hour + lon_deg / 15.0 - tz_standard - Et_hours
        Hend = math.radians(15.0 * (true_solar_time - 12.0))
        Hend = max(-H0, min(H0, Hend))

    if Hend <= Hstart:
        return [], delta0

    H = np.linspace(Hstart, Hend, samples)
    delta = np.full_like(H, delta0, dtype=float)

    X, Y, D, B, h = vertical_shadow(phi, delta, H, gamma=gamma, a=a, p=p)
    segments = _visible_segments_from_arrays(X, Y, D, B, h, min_altitude_deg)

    return segments, delta0
