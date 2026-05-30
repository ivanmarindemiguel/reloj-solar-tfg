import math
from dataclasses import dataclass, replace

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D

from gnomonics import (
    analemma_curves,
    day_curve_for_date,
    equinoctial_y,
    true_hour_curves,
    visible_line_segments,
)


@dataclass
class SundialConfig:
    # Localizacion
    lat_deg: float = 40 + 24 / 60 + 35 / 3600
    lon_deg: float = -(3 + 41 / 60 + 11 / 3600)

    # Tamano objetivo de la plantilla
    target_width_m: float = 1.0
    target_height_m: float = 0.5

    # Tiempo
    year: int = 2026
    tz_standard: float = 2.0  # fijo UTC+2

    # Que se genera
    babilonic_indices: tuple = (2, 3, 4, 5, 6, 7)
    italic_indices: tuple = (2, 3, 4, 5, 6, 7)
    analemma_hours: tuple = (12, 13, 14, 15, 16)
    true_hours: tuple = (9, 10, 11, 12, 13, 14, 15)
    special_dates: tuple = ((22, 8),)

    # Filtros
    min_altitude_lines_deg: float = 5.0
    min_altitude_analemmas_deg: float = 5.0
    min_altitude_true_hours_deg: float = 5.0
    min_altitude_daycurve_deg: float = 15.0

    # Parametros orbitales
    T: float = 365.2422
    epsilon_deg: float = 23.44
    e: float = 0.01671123
    varpi_deg: float = 102.93768193
    dperi: float = 2.71875


def default_visibility():
    return {
        "show_bab": True,
        "show_ita": True,
        "show_analemmas": True,
        "show_true_hours": True,
        "show_daycurves": True,
        "show_equinox_line": True,
        "show_meridian": True,
        "show_style_foot": True,
        "show_labels_rectas": True,
        "show_labels_analemmas": True,
        "show_labels_true_hours": True,
        "show_labels_daycurves": True,
        "show_axes": True,
        "show_grid": True,
        "show_legend": True,
        "show_title": True,
    }


def _format_hour_label(hour):
    if float(hour).is_integer():
        return str(int(hour))
    return str(hour)


def _italic_display_hour(index):
    return 24 - int(index)


def _format_italic_label(index):
    return f"I{_italic_display_hour(index)}"


def _orbital_kwargs(config: SundialConfig):
    return {
        "T": config.T,
        "epsilon_deg": config.epsilon_deg,
        "e": config.e,
        "varpi_deg": config.varpi_deg,
        "dperi": config.dperi,
    }


def _compute_geometry(config: SundialConfig, style_height_m):
    phi = math.radians(config.lat_deg)
    orb = _orbital_kwargs(config)

    geometry = {
        "bab": {},
        "ita": {},
        "analemmas": {},
        "true_hours": {},
        "daycurves": {},
        "equinox_y": None,
    }

    line_indices_union = tuple(sorted(set(config.babilonic_indices) | set(config.italic_indices)))
    if line_indices_union:
        bab_all, ita_all = visible_line_segments(
            phi=phi,
            selected_n=line_indices_union,
            p=style_height_m,
            ell=0.0,
            min_altitude_deg=config.min_altitude_lines_deg,
            samples=6000,
            orbital_kwargs=orb,
        )

        geometry["bab"] = {n: bab_all[n] for n in config.babilonic_indices if n in bab_all}
        geometry["ita"] = {n: ita_all[n] for n in config.italic_indices if n in ita_all}

    if config.analemma_hours:
        geometry["analemmas"] = analemma_curves(
            phi=phi,
            hours=config.analemma_hours,
            lon_deg=config.lon_deg,
            tz_standard=config.tz_standard,
            p=style_height_m,
            ell=0.0,
            min_altitude_deg=config.min_altitude_analemmas_deg,
            samples=5000,
            orbital_kwargs=orb,
        )

    if config.true_hours:
        geometry["true_hours"] = true_hour_curves(
            phi=phi,
            true_hours=config.true_hours,
            p=style_height_m,
            ell=0.0,
            min_altitude_deg=config.min_altitude_true_hours_deg,
            samples=5000,
            orbital_kwargs=orb,
        )
    geometry["equinox_y"] = equinoctial_y(
        phi=phi,
        p=style_height_m,
        ell=0.0,
    )

    min_civil_hour = min(config.analemma_hours) if config.analemma_hours else None
    max_civil_hour = max(config.analemma_hours) if config.analemma_hours else None
    for day, month in config.special_dates:
        segments, delta_day = day_curve_for_date(
            phi=phi,
            year=config.year,
            month=month,
            day=day,
            lon_deg=config.lon_deg,
            tz_standard=config.tz_standard,
            p=style_height_m,
            ell=0.0,
            min_altitude_deg=config.min_altitude_daycurve_deg,
            min_civil_hour=min_civil_hour,
            max_civil_hour=max_civil_hour,
            samples=3000,
            orbital_kwargs=orb,
        )
        if segments:
            geometry["daycurves"][(day, month)] = {
                "segments": segments,
                "delta_deg": math.degrees(delta_day),
            }

    return geometry


def _scale_geometry(base_geometry, scale_factor):
    geometry = {
        "bab": {key: pts * scale_factor for key, pts in base_geometry["bab"].items()},
        "ita": {key: pts * scale_factor for key, pts in base_geometry["ita"].items()},
        "analemmas": {
            key: [segment * scale_factor for segment in segments]
            for key, segments in base_geometry["analemmas"].items()
        },
        "true_hours": {
            key: [segment * scale_factor for segment in segments]
            for key, segments in base_geometry["true_hours"].items()
        },
        "daycurves": {
            key: {
                "segments": [segment * scale_factor for segment in item["segments"]],
                "delta_deg": item["delta_deg"],
            }
            for key, item in base_geometry["daycurves"].items()
        },
        "equinox_y": None,
    }

    if base_geometry["equinox_y"] is not None:
        geometry["equinox_y"] = base_geometry["equinox_y"] * scale_factor

    return geometry


def _validated_line_indices(config: SundialConfig):
    requested = tuple(
        sorted(
            set(
                n
                for n in (*config.babilonic_indices, *config.italic_indices)
                if 1 <= n <= 24
            )
        )
    )
    if not requested:
        return tuple(), tuple()

    phi = math.radians(config.lat_deg)
    bab, ita = visible_line_segments(
        phi=phi,
        selected_n=requested,
        p=1.0,
        ell=0.0,
        min_altitude_deg=config.min_altitude_lines_deg,
        samples=6000,
        orbital_kwargs=_orbital_kwargs(config),
    )

    valid_bab = tuple(n for n in config.babilonic_indices if 1 <= n <= 24 and n in bab)
    valid_ita = tuple(n for n in config.italic_indices if 1 <= n <= 24 and n in ita)
    return valid_bab, valid_ita


def _validated_analemma_hours(config: SundialConfig):
    if not config.analemma_hours:
        return tuple()

    phi = math.radians(config.lat_deg)
    reference_samples = 5000
    reference_analemmas = analemma_curves(
        phi=phi,
        hours=config.analemma_hours,
        lon_deg=config.lon_deg,
        tz_standard=config.tz_standard,
        p=1.0,
        ell=0.0,
        min_altitude_deg=config.min_altitude_analemmas_deg,
        samples=reference_samples,
        orbital_kwargs=_orbital_kwargs(config),
    )

    valid_hours = []
    for hour in config.analemma_hours:
        if not (0.0 <= hour <= 24.0):
            continue
        if hour not in reference_analemmas:
            continue

        segments = reference_analemmas[hour]
        if len(segments) != 1:
            continue
        if len(segments[0]) != reference_samples:
            continue

        valid_hours.append(hour)

    return tuple(valid_hours)


def _validated_true_hours(config: SundialConfig):
    if not config.true_hours:
        return tuple()

    phi = math.radians(config.lat_deg)
    reference_true_hours = true_hour_curves(
        phi=phi,
        true_hours=tuple(hour for hour in config.true_hours if 0.0 <= hour <= 24.0),
        p=1.0,
        ell=0.0,
        min_altitude_deg=config.min_altitude_true_hours_deg,
        samples=5000,
        orbital_kwargs=_orbital_kwargs(config),
    )

    valid_hours = []
    for hour in config.true_hours:
        if not (0.0 <= hour <= 24.0):
            continue
        if hour not in reference_true_hours:
            continue
        valid_hours.append(hour)

    return tuple(valid_hours)


def sanitize_config(config: SundialConfig):
    valid_bab, valid_ita = _validated_line_indices(config)
    valid_analemmas = _validated_analemma_hours(config)
    valid_true_hours = _validated_true_hours(config)

    effective_config = replace(
        config,
        babilonic_indices=valid_bab,
        italic_indices=valid_ita,
        analemma_hours=valid_analemmas,
        true_hours=valid_true_hours,
    )

    warnings = []

    removed_bab = [n for n in config.babilonic_indices if n not in valid_bab]
    if removed_bab:
        warnings.append(
            "Se han descartado babilonicas no validas o no visibles: "
            + ", ".join(f"B{n}" for n in removed_bab)
        )

    removed_ita = [n for n in config.italic_indices if n not in valid_ita]
    if removed_ita:
        warnings.append(
            "Se han descartado italicas no validas o no visibles: "
            + ", ".join(_format_italic_label(n) for n in removed_ita)
        )

    removed_analemmas = [hour for hour in config.analemma_hours if hour not in valid_analemmas]
    if removed_analemmas:
        warnings.append(
            "Se han descartado analemas no validos o no visibles: "
            + ", ".join(_format_hour_label(hour) + " h" for hour in removed_analemmas)
        )

    removed_true_hours = [hour for hour in config.true_hours if hour not in valid_true_hours]
    if removed_true_hours:
        warnings.append(
            "Se han descartado horas verdaderas no validas o no visibles: "
            + ", ".join(_format_hour_label(hour) + " h" for hour in removed_true_hours)
        )

    return effective_config, warnings


def _geometry_point_sets(geometry):
    point_sets = []
    point_sets.extend(geometry["bab"].values())
    point_sets.extend(geometry["ita"].values())

    for segments in geometry["analemmas"].values():
        point_sets.extend(segments)

    for segments in geometry["true_hours"].values():
        point_sets.extend(segments)

    for item in geometry["daycurves"].values():
        point_sets.extend(item["segments"])

    if geometry["equinox_y"] is not None:
        point_sets.append(np.array([[0.0, geometry["equinox_y"]]], dtype=float))

    return point_sets


def _geometry_bounds(geometry):
    point_sets = _geometry_point_sets(geometry)
    if not point_sets:
        return None

    all_pts = np.vstack(point_sets)
    return (
        float(all_pts[:, 0].min()),
        float(all_pts[:, 0].max()),
        float(all_pts[:, 1].min()),
        float(all_pts[:, 1].max()),
    )


def _has_visible_geometry(geometry):
    return _geometry_bounds(geometry) is not None


def _requested_elements_visible(config: SundialConfig, geometry):
    for n in config.babilonic_indices:
        if n not in geometry["bab"]:
            return False

    for n in config.italic_indices:
        if n not in geometry["ita"]:
            return False

    for hour in config.analemma_hours:
        if hour not in geometry["analemmas"]:
            return False

    for hour in config.true_hours:
        if hour not in geometry["true_hours"]:
            return False

    for item in config.special_dates:
        if item not in geometry["daycurves"]:
            return False

    return True


def _resolved_style_height(config: SundialConfig, base_geometry=None):
    base_geometry = base_geometry or _compute_geometry(config, style_height_m=1.0)
    bounds = _geometry_bounds(base_geometry)
    fallback_style = min(config.target_width_m, config.target_height_m)

    if bounds is None:
        return fallback_style

    if not _requested_elements_visible(config, base_geometry):
        return fallback_style

    xmin, xmax, ymin, ymax = bounds
    base_width = xmax - xmin
    base_height = ymax - ymin

    scale_candidates = []
    if base_width > 1.0e-12:
        scale_candidates.append(config.target_width_m / base_width)
    if base_height > 1.0e-12:
        scale_candidates.append(config.target_height_m / base_height)

    if not scale_candidates:
        return fallback_style

    return max(min(scale_candidates), 1.0e-6)


def _target_limits(config: SundialConfig, bounds):
    if bounds is None:
        center_x = 0.0
        center_y = 0.0
    else:
        xmin, xmax, ymin, ymax = bounds
        center_x = 0.5 * (xmin + xmax)
        center_y = 0.5 * (ymin + ymax)

    half_width = 0.5 * config.target_width_m
    half_height = 0.5 * config.target_height_m

    return (
        center_x - half_width,
        center_x + half_width,
        center_y - half_height,
        center_y + half_height,
    )


def _missing_elements_warnings(config: SundialConfig, geometry):
    warnings = []

    missing_bab = [n for n in config.babilonic_indices if n not in geometry["bab"]]
    if missing_bab:
        warnings.append(
            "Babilonicas sin trazado visible: "
            + ", ".join(f"B{n}" for n in missing_bab)
        )

    missing_ita = [n for n in config.italic_indices if n not in geometry["ita"]]
    if missing_ita:
        warnings.append(
            "Italicas sin trazado visible: "
            + ", ".join(_format_italic_label(n) for n in missing_ita)
        )

    missing_analemmas = [hour for hour in config.analemma_hours if hour not in geometry["analemmas"]]
    if missing_analemmas:
        warnings.append(
            "Analemas sin trazado visible: "
            + ", ".join(_format_hour_label(hour) + " h" for hour in missing_analemmas)
        )

    missing_true_hours = [hour for hour in config.true_hours if hour not in geometry["true_hours"]]
    if missing_true_hours:
        warnings.append(
            "Horas verdaderas sin trazado visible: "
            + ", ".join(_format_hour_label(hour) + " h" for hour in missing_true_hours)
        )

    missing_dates = [item for item in config.special_dates if item not in geometry["daycurves"]]
    if missing_dates:
        warnings.append(
            "Curvas diarias sin trazado visible: "
            + ", ".join(f"{day:02d}/{month:02d}" for day, month in missing_dates)
        )

    if not _has_visible_geometry(geometry):
        warnings.insert(
            0,
            "No hay geometria visible con la configuracion actual. "
            "Prueba con horas mas centradas, una altura minima menor o un tamano/filtros menos restrictivos.",
        )

    return warnings


def build_plot_data(config: SundialConfig):
    """
    Calcula la geometria ajustada al tamano objetivo sin dibujarla.
    """
    effective_config, validation_warnings = sanitize_config(config)

    base_geometry = _compute_geometry(effective_config, style_height_m=1.0)
    style_height_m = _resolved_style_height(effective_config, base_geometry=base_geometry)
    geometry = _scale_geometry(base_geometry, style_height_m)
    bounds = _geometry_bounds(geometry)

    if bounds is None:
        occupied_width_m = 0.0
        occupied_height_m = 0.0
    else:
        xmin, xmax, ymin, ymax = bounds
        occupied_width_m = xmax - xmin
        occupied_height_m = ymax - ymin

    x0, x1, y0, y1 = _target_limits(config, bounds)
    equinox_line = None
    if geometry["equinox_y"] is not None:
        equinox_line = np.array(
            [[x0, geometry["equinox_y"]], [x1, geometry["equinox_y"]]],
            dtype=float,
        )

    return {
        **geometry,
        "style_height_m": style_height_m,
        "occupied_width_m": occupied_width_m,
        "occupied_height_m": occupied_height_m,
        "horizontal_margin_m": max(config.target_width_m - occupied_width_m, 0.0),
        "vertical_margin_m": max(config.target_height_m - occupied_height_m, 0.0),
        "target_width_m": config.target_width_m,
        "target_height_m": config.target_height_m,
        "bounds": bounds,
        "target_limits": (x0, x1, y0, y1),
        "equinox_line": equinox_line,
        "warnings": validation_warnings + _missing_elements_warnings(effective_config, geometry),
        "effective_config": effective_config,
    }


def _polyline_cumulative_lengths(points):
    if len(points) <= 1:
        return np.array([0.0], dtype=float)

    deltas = np.diff(points, axis=0)
    lengths = np.linalg.norm(deltas, axis=1)
    return np.concatenate(([0.0], np.cumsum(lengths)))


def _sample_point_on_polyline(points, distance):
    pts = np.asarray(points, dtype=float)
    if len(pts) == 0:
        raise ValueError("No se puede muestrear una polilinea vacia.")
    if len(pts) == 1:
        return pts[0].copy()

    cumulative = _polyline_cumulative_lengths(pts)
    total_length = cumulative[-1]
    if total_length <= 1.0e-12:
        return pts[0].copy()

    clamped_distance = min(max(float(distance), 0.0), float(total_length))
    if math.isclose(clamped_distance, float(total_length), rel_tol=0.0, abs_tol=1.0e-12):
        return pts[-1].copy()

    right_idx = np.searchsorted(cumulative, clamped_distance, side="right")
    left_idx = max(right_idx - 1, 0)
    left_distance = cumulative[left_idx]
    right_distance = cumulative[right_idx]

    if math.isclose(right_distance, left_distance, rel_tol=0.0, abs_tol=1.0e-12):
        return pts[left_idx].copy()

    weight = (clamped_distance - left_distance) / (right_distance - left_distance)
    return pts[left_idx] + weight * (pts[right_idx] - pts[left_idx])


def sample_curve_points(curve_segments, point_count=10):
    valid_segments = [
        np.asarray(segment, dtype=float)
        for segment in curve_segments
        if segment is not None and len(segment) > 0
    ]
    if not valid_segments:
        return np.empty((0, 2), dtype=float)

    if point_count <= 0:
        raise ValueError("El numero de puntos de muestreo debe ser positivo.")

    segment_lengths = []
    for segment in valid_segments:
        cumulative = _polyline_cumulative_lengths(segment)
        segment_lengths.append(float(cumulative[-1]))

    total_length = float(sum(segment_lengths))
    if total_length <= 1.0e-12:
        base_point = valid_segments[0][0]
        return np.repeat(base_point[np.newaxis, :], point_count, axis=0)

    segment_ends = np.cumsum(segment_lengths)
    target_distances = np.linspace(0.0, total_length, point_count)
    sampled = []

    for distance in target_distances:
        if math.isclose(distance, total_length, rel_tol=0.0, abs_tol=1.0e-12):
            segment_idx = len(valid_segments) - 1
            local_distance = segment_lengths[segment_idx]
        else:
            segment_idx = int(np.searchsorted(segment_ends, distance, side="right"))
            segment_start = 0.0 if segment_idx == 0 else float(segment_ends[segment_idx - 1])
            local_distance = float(distance - segment_start)

        sampled.append(_sample_point_on_polyline(valid_segments[segment_idx], local_distance))

    return np.asarray(sampled, dtype=float)


def _ordered_line_points(points):
    pts = np.asarray(points, dtype=float)
    if len(pts) <= 1:
        return pts.copy()

    primary_axis = 0 if np.ptp(pts[:, 0]) >= np.ptp(pts[:, 1]) else 1
    secondary_axis = 1 - primary_axis
    order = np.lexsort((pts[:, secondary_axis], pts[:, primary_axis]))
    ordered = pts[order]

    deduplicated = [ordered[0]]
    for point in ordered[1:]:
        if np.linalg.norm(point - deduplicated[-1]) > 1.0e-9:
            deduplicated.append(point)

    return np.asarray(deduplicated, dtype=float)


def build_coordinate_export_rows(config: SundialConfig, visibility=None, point_count=10):
    computed_data = build_plot_data(config)
    effective_config = computed_data["effective_config"]
    visibility = visibility or default_visibility()
    rows = []

    def add_family(family_name, identified_curve_segments):
        for curve_identifier, segments in identified_curve_segments:
            sampled_points = sample_curve_points(segments, point_count=point_count)
            for point_number, point in enumerate(sampled_points, start=1):
                rows.append(
                    (
                        family_name,
                        curve_identifier,
                        point_number,
                        round(float(point[0]), 3),
                        round(float(point[1]), 3),
                    )
                )

    if visibility.get("show_bab", True):
        add_family(
            "babilonica",
            [
                (n, [_ordered_line_points(computed_data["bab"][n])])
                for n in effective_config.babilonic_indices
                if n in computed_data["bab"]
            ],
        )

    if visibility.get("show_ita", True):
        add_family(
            "italica",
            [
                (_italic_display_hour(n), [_ordered_line_points(computed_data["ita"][n])])
                for n in reversed(effective_config.italic_indices)
                if n in computed_data["ita"]
            ],
        )

    if visibility.get("show_analemmas", True):
        add_family(
            "analema",
            [
                (_format_hour_label(hour), computed_data["analemmas"][hour])
                for hour in effective_config.analemma_hours
                if hour in computed_data["analemmas"]
            ],
        )

    if visibility.get("show_true_hours", True):
        add_family(
            "hora_verdadera",
            [
                (_format_hour_label(hour), computed_data["true_hours"][hour])
                for hour in effective_config.true_hours
                if hour in computed_data["true_hours"]
            ],
        )

    if visibility.get("show_daycurves", True):
        add_family(
            "curva_diaria",
            [
                (f"{item[0]:02d}/{item[1]:02d}", computed_data["daycurves"][item]["segments"])
                for item in effective_config.special_dates
                if item in computed_data["daycurves"]
            ],
        )

    if visibility.get("show_equinox_line", True) and computed_data["equinox_line"] is not None:
        add_family("recta_equinoccial", [("equinoccial", [computed_data["equinox_line"]])])

    if visibility.get("show_meridian", True):
        _, _, y0, y1 = computed_data["target_limits"]
        meridian_line = np.array([[0.0, y0], [0.0, y1]], dtype=float)
        add_family("meridiana", [("meridiana", [meridian_line])])

    return rows, computed_data


def build_plot(ax, config: SundialConfig):
    """
    Construye todas las capas y deja en memoria la geometria ajustada al
    tamano objetivo indicado por el usuario.
    """
    ax.clear()

    computed_data = build_plot_data(config)
    effective_config = computed_data["effective_config"]
    geometry = computed_data
    x0, x1, y0, y1 = computed_data["target_limits"]
    equinox_line = computed_data["equinox_line"]

    layers = {
        "bab_lines": [],
        "ita_lines": [],
        "analemma_lines": [],
        "true_hour_lines": [],
        "daycurve_lines": [],
        "equinox_line": [],
        "meridian": [],
        "style_foot": [],
        "labels_rectas": [],
        "labels_analemmas": [],
        "labels_true_hours": [],
        "labels_daycurves": [],
        "legend": None,
        "title": None,
    }

    color_bab = "tab:blue"
    color_ita = "tab:orange"
    color_analemmas = "darkgreen"
    color_true_hours = "purple"
    color_equinox = "dimgray"

    default_cycle = plt.rcParams["axes.prop_cycle"].by_key().get(
        "color", ["tab:red", "tab:purple", "tab:brown", "tab:pink"]
    )

    for n, pts in geometry["bab"].items():
        (line,) = ax.plot(pts[:, 0], pts[:, 1], color=color_bab, lw=2.3)
        layers["bab_lines"].append(line)

        idx = np.argmax(pts[:, 0] ** 2 + pts[:, 1] ** 2)
        txt = ax.text(pts[idx, 0], pts[idx, 1], f"B{n}", color=color_bab, fontsize=10)
        layers["labels_rectas"].append(txt)

    for n, pts in geometry["ita"].items():
        (line,) = ax.plot(pts[:, 0], pts[:, 1], color=color_ita, lw=2.3)
        layers["ita_lines"].append(line)

        idx = np.argmax(pts[:, 0] ** 2 + pts[:, 1] ** 2)
        txt = ax.text(
            pts[idx, 0],
            pts[idx, 1],
            _format_italic_label(n),
            color=color_ita,
            fontsize=10,
        )
        layers["labels_rectas"].append(txt)

    for hour in effective_config.analemma_hours:
        if hour not in geometry["analemmas"]:
            continue

        current_artists = []
        for segment in geometry["analemmas"][hour]:
            (line,) = ax.plot(segment[:, 0], segment[:, 1], color=color_analemmas, lw=2.0)
            current_artists.append(line)

        layers["analemma_lines"].extend(current_artists)

        pts_all = np.vstack(geometry["analemmas"][hour])
        idx = np.argmax(pts_all[:, 1])
        txt = ax.text(
            pts_all[idx, 0],
            pts_all[idx, 1],
            _format_hour_label(hour),
            color=color_analemmas,
            fontsize=9,
        )
        layers["labels_analemmas"].append(txt)

    for hour in effective_config.true_hours:
        if hour not in geometry["true_hours"]:
            continue

        current_artists = []
        for segment in geometry["true_hours"][hour]:
            (line,) = ax.plot(segment[:, 0], segment[:, 1], color=color_true_hours, lw=2.0)
            current_artists.append(line)

        layers["true_hour_lines"].extend(current_artists)

        pts_all = np.vstack(geometry["true_hours"][hour])
        idx = np.argmax(pts_all[:, 1])
        txt = ax.text(
            pts_all[idx, 0],
            pts_all[idx, 1],
            f"V{_format_hour_label(hour)}",
            color=color_true_hours,
            fontsize=9,
        )
        layers["labels_true_hours"].append(txt)

    for idx, ((day, month), item) in enumerate(geometry["daycurves"].items()):
        color = default_cycle[idx % len(default_cycle)]
        for segment in item["segments"]:
            (line,) = ax.plot(segment[:, 0], segment[:, 1], color=color, lw=2.6)
            layers["daycurve_lines"].append(line)

        pts_day = np.vstack(item["segments"])
        label_idx = np.argmax(pts_day[:, 1])
        txt = ax.text(
            pts_day[label_idx, 0],
            pts_day[label_idx, 1],
            f"{day:02d}/{month:02d}",
            color=color,
            fontsize=10,
        )
        layers["labels_daycurves"].append(txt)

    if equinox_line is not None:
        (line,) = ax.plot(
            equinox_line[:, 0],
            equinox_line[:, 1],
            color=color_equinox,
            lw=2.0,
            ls="--",
        )
        layers["equinox_line"].append(line)

    meridian = ax.axvline(0.0, color="black", lw=1.1)
    layers["meridian"].append(meridian)

    (style_foot,) = ax.plot([0.0], [0.0], "ko", ms=5)
    layers["style_foot"].append(style_foot)

    legend_handles = [
        Line2D([0], [0], color=color_bab, lw=2.3, label="Babilonicas"),
        Line2D([0], [0], color=color_ita, lw=2.3, label="Italicas"),
        Line2D([0], [0], color=color_analemmas, lw=2.0, label="Analemas"),
        Line2D([0], [0], color=color_true_hours, lw=2.0, label="Horas verdaderas"),
        Line2D([0], [0], color=default_cycle[0], lw=2.6, label="Curvas diarias"),
        Line2D([0], [0], color=color_equinox, lw=2.0, ls="--", label="Recta equinoccial"),
        Line2D([0], [0], color="black", lw=1.1, label="Meridiana"),
    ]
    legend = ax.legend(handles=legend_handles, loc="best")
    layers["legend"] = legend

    title = ax.set_title(
        "Plantilla de reloj solar horizontal\n"
        f"lat={config.lat_deg:.6f}°, lon={config.lon_deg:.6f}°, "
        f"objetivo={config.target_width_m:.3f} x {config.target_height_m:.3f} m, "
        f"estilo calculado={computed_data['style_height_m']:.4f} m, UTC+2 fijo"
    )
    layers["title"] = title

    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.set_aspect("equal", adjustable="box")
    ax.grid(True, alpha=0.3)

    return layers, computed_data


def apply_visibility(ax, layers, visibility, view_mode="screen"):
    """
    Muestra u oculta capas ya existentes en memoria.
    """
    print_mode = view_mode == "print"

    for artist in layers["bab_lines"]:
        artist.set_visible(visibility["show_bab"])

    for artist in layers["ita_lines"]:
        artist.set_visible(visibility["show_ita"])

    for artist in layers["analemma_lines"]:
        artist.set_visible(visibility["show_analemmas"])

    for artist in layers["true_hour_lines"]:
        artist.set_visible(visibility["show_true_hours"])

    for artist in layers["daycurve_lines"]:
        artist.set_visible(visibility["show_daycurves"])

    for artist in layers["equinox_line"]:
        artist.set_visible(visibility["show_equinox_line"])

    for artist in layers["meridian"]:
        artist.set_visible(visibility["show_meridian"])

    for artist in layers["style_foot"]:
        artist.set_visible(visibility["show_style_foot"])

    for artist in layers["labels_rectas"]:
        artist.set_visible(visibility["show_labels_rectas"])

    for artist in layers["labels_analemmas"]:
        artist.set_visible(visibility["show_labels_analemmas"])

    for artist in layers["labels_true_hours"]:
        artist.set_visible(visibility["show_labels_true_hours"])

    for artist in layers["labels_daycurves"]:
        artist.set_visible(visibility["show_labels_daycurves"])

    if layers["legend"] is not None:
        layers["legend"].set_visible((not print_mode) and visibility["show_legend"])

    if layers["title"] is not None:
        layers["title"].set_visible((not print_mode) and visibility["show_title"])

    if print_mode or (not visibility["show_axes"]):
        ax.set_xlabel("")
        ax.set_ylabel("")
        ax.tick_params(
            bottom=False,
            left=False,
            labelbottom=False,
            labelleft=False,
        )
        for spine in ax.spines.values():
            spine.set_visible(False)
    else:
        ax.set_xlabel("x (Este, m)")
        ax.set_ylabel("y (Norte, m)")
        ax.tick_params(
            bottom=True,
            left=True,
            labelbottom=True,
            labelleft=True,
        )
        for spine in ax.spines.values():
            spine.set_visible(True)

    if print_mode or (not visibility["show_grid"]):
        ax.grid(False)
    else:
        ax.grid(True, alpha=0.3)
    ax.set_aspect("equal", adjustable="box")
