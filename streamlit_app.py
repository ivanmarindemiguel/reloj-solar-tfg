from datetime import date
from io import BytesIO
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Dict, Iterable, Tuple

import matplotlib

matplotlib.use("Agg")

from matplotlib.figure import Figure
import streamlit as st

from excel_export import write_coordinate_workbook
from plotting import (
    SundialConfig,
    apply_visibility,
    build_coordinate_export_rows,
    build_plot,
    default_visibility,
)
from vertical_plotting import (
    VerticalSundialConfig,
    apply_vertical_visibility,
    build_vertical_coordinate_export_rows,
    build_vertical_plot,
)


M_PER_INCH = 0.0254
CM_PER_INCH = 2.54
DPI_OPTIONS = {
    "150 ppp": 150,
    "300 ppp": 300,
    "600 ppp": 600,
    "1200 ppp": 1200,
}


def parse_int_list(text: str) -> Tuple[int, ...]:
    parts = [part.strip() for part in text.split(",") if part.strip()]
    if not parts:
        return tuple()
    try:
        return tuple(int(part) for part in parts)
    except ValueError as exc:
        raise ValueError("Las listas enteras deben usar numeros separados por comas.") from exc


def parse_float_list(text: str) -> Tuple[float, ...]:
    parts = [part.strip().replace(",", ".") for part in text.split(";") if part.strip()]
    if len(parts) <= 1:
        parts = [part.strip().replace(",", ".") for part in text.split(",") if part.strip()]
    if not parts:
        return tuple()
    try:
        return tuple(float(part) for part in parts)
    except ValueError as exc:
        raise ValueError("Las listas numericas deben usar valores separados por comas.") from exc


def parse_italic_hour_list(text: str) -> Tuple[int, ...]:
    hours = parse_int_list(text)
    invalid = [hour for hour in hours if not (1 <= hour <= 23)]
    if invalid:
        raise ValueError("Las horas italicas deben estar entre 1 y 23.")
    return tuple(sorted(set(24 - hour for hour in hours)))


def parse_dates(text: str, year: int) -> Tuple[Tuple[int, int], ...]:
    items = [item.strip() for item in text.split(",") if item.strip()]
    parsed = []
    for item in items:
        try:
            day_text, month_text = item.split("/")
            day = int(day_text.strip())
            month = int(month_text.strip())
            date(year, month, day)
        except Exception as exc:
            raise ValueError(f"Fecha no valida: {item}. Usa formato dd/mm.") from exc
        parsed.append((day, month))
    return tuple(parsed)


def make_config(values: Dict[str, object]):
    lat = float(values["lat_deg"])
    lon = float(values["lon_deg"])
    wall_declination = float(values["wall_declination_deg"])
    target_width = float(values["target_width_m"])
    target_height = float(values["target_height_m"])
    year = int(values["year"])

    if not (-90.0 <= lat <= 90.0):
        raise ValueError("La latitud debe estar entre -90 y 90 grados.")
    if not (-180.0 <= lon <= 180.0):
        raise ValueError("La longitud debe estar entre -180 y 180 grados.")
    if values["model"] == "Vertical" and not (-180.0 <= wall_declination <= 180.0):
        raise ValueError("La declinacion de pared debe estar entre -180 y 180 grados.")
    if target_width <= 0.0 or target_height <= 0.0:
        raise ValueError("El ancho y el alto objetivo deben ser positivos.")

    common_kwargs = dict(
        lat_deg=lat,
        lon_deg=lon,
        target_width_m=target_width,
        target_height_m=target_height,
        year=year,
        tz_standard=2.0,
        babilonic_indices=parse_int_list(str(values["babilonic_indices"])),
        italic_indices=parse_italic_hour_list(str(values["italic_hours"])),
        analemma_hours=parse_float_list(str(values["analemma_hours"])),
        true_hours=parse_float_list(str(values["true_hours"])),
        special_dates=parse_dates(str(values["special_dates"]), year),
        min_altitude_lines_deg=float(values["min_altitude_lines_deg"]),
        min_altitude_analemmas_deg=float(values["min_altitude_analemmas_deg"]),
        min_altitude_true_hours_deg=float(values["min_altitude_true_hours_deg"]),
        min_altitude_daycurve_deg=float(values["min_altitude_daycurve_deg"]),
    )

    if values["model"] == "Vertical":
        return VerticalSundialConfig(
            **common_kwargs,
            wall_declination_deg=wall_declination,
        )
    return SundialConfig(**common_kwargs)


def make_visibility(values: Dict[str, bool]) -> Dict[str, bool]:
    visibility = default_visibility()
    visibility.update(values)
    return visibility


def render_plot(config, visibility: Dict[str, bool], view_mode: str = "screen"):
    fig = Figure(figsize=(11.5, 7.2), dpi=120, facecolor="white")
    ax = fig.add_subplot(111)
    if isinstance(config, VerticalSundialConfig):
        layers, computed_data = build_vertical_plot(ax, config)
        apply_vertical_visibility(ax, layers, visibility, view_mode=view_mode)
    else:
        layers, computed_data = build_plot(ax, config)
        apply_visibility(ax, layers, visibility, view_mode=view_mode)
    fig.tight_layout()
    return fig, computed_data


def render_export_bytes(config, visibility: Dict[str, bool], file_format: str, dpi: int = 300) -> bytes:
    fig = Figure(
        figsize=(config.target_width_m / M_PER_INCH, config.target_height_m / M_PER_INCH),
        dpi=100,
        facecolor="white",
    )
    ax = fig.add_axes([0, 0, 1, 1])
    if isinstance(config, VerticalSundialConfig):
        layers, _ = build_vertical_plot(ax, config)
        apply_vertical_visibility(ax, layers, visibility, view_mode="print")
    else:
        layers, _ = build_plot(ax, config)
        apply_visibility(ax, layers, visibility, view_mode="print")

    output = BytesIO()
    save_kwargs = dict(format=file_format, bbox_inches=None, pad_inches=0.0, facecolor="white")
    if file_format in {"png", "tiff"}:
        save_kwargs["dpi"] = dpi
    if file_format == "tiff":
        save_kwargs["pil_kwargs"] = {"compression": "tiff_lzw"}
    fig.savefig(output, **save_kwargs)
    return output.getvalue()


def build_excel_bytes(config, visibility: Dict[str, bool]) -> bytes:
    if isinstance(config, VerticalSundialConfig):
        rows, computed_data = build_vertical_coordinate_export_rows(config, visibility=visibility)
    else:
        rows, computed_data = build_coordinate_export_rows(config, visibility=visibility)

    if not rows:
        warnings = computed_data.get("warnings", [])
        detail = "\n".join(warnings)
        raise ValueError("No hay curvas o rectas visibles para exportar coordenadas.\n" + detail)

    temp_path = None
    try:
        with NamedTemporaryFile(suffix=".xlsx", delete=False) as temp_file:
            temp_path = Path(temp_file.name)
        write_coordinate_workbook(temp_path, rows)
        return temp_path.read_bytes()
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def metric_line(label: str, value: str):
    st.metric(label, value)


def format_warnings(warnings: Iterable[str]) -> str:
    return "\n".join(f"- {warning}" for warning in warnings)


st.set_page_config(
    page_title="Reloj solar TFG",
    layout="wide",
)

st.title("Reloj solar horizontal y vertical")

with st.sidebar:
    st.header("Parametros")
    model = st.radio("Modelo", ("Horizontal", "Vertical"), horizontal=True)
    lat_deg = st.number_input(
        "Latitud",
        min_value=-90.0,
        max_value=90.0,
        value=40 + 24 / 60 + 35 / 3600,
        format="%.8f",
    )
    lon_deg = st.number_input(
        "Longitud",
        min_value=-180.0,
        max_value=180.0,
        value=-(3 + 41 / 60 + 11 / 3600),
        format="%.8f",
    )
    wall_declination_deg = st.number_input(
        "Declinacion pared vertical",
        min_value=-180.0,
        max_value=180.0,
        value=0.0,
        format="%.3f",
        disabled=model != "Vertical",
    )
    target_width_m = st.number_input("Ancho objetivo (m)", min_value=0.01, value=1.0, step=0.05)
    target_height_m = st.number_input("Alto objetivo (m)", min_value=0.01, value=0.5, step=0.05)
    year = st.number_input("Anio", min_value=1900, max_value=2200, value=date.today().year, step=1)

    st.header("Elementos")
    babilonic_indices = st.text_input("Lineas babilonicas", value="2,3,4,5,6,7")
    italic_hours = st.text_input("Horas italicas", value="17,18,19,20,21,22")
    analemma_hours = st.text_input("Analemas", value="12,13,14,15,16")
    true_hours = st.text_input("Horas verdaderas", value="9,10,11,12,13,14,15")
    special_dates = st.text_input("Fechas especiales", value="22/08")

    st.header("Filtros")
    min_altitude_lines_deg = st.number_input("Altura minima rectas", value=5.0, step=0.5)
    min_altitude_analemmas_deg = st.number_input("Altura minima analemas", value=5.0, step=0.5)
    min_altitude_true_hours_deg = st.number_input("Altura minima horas verdaderas", value=5.0, step=0.5)
    min_altitude_daycurve_deg = st.number_input("Altura minima curvas diarias", value=15.0, step=0.5)

    st.header("Vista")
    show_bab = st.checkbox("Babilonicas", value=True)
    show_ita = st.checkbox("Italicas", value=True)
    show_analemmas = st.checkbox("Analemas", value=True)
    show_true_hours = st.checkbox("Horas verdaderas", value=True)
    show_daycurves = st.checkbox("Curvas diarias", value=True)
    show_equinox_line = st.checkbox("Recta equinoccial", value=True)
    show_meridian = st.checkbox("Meridiana", value=True)
    show_style_foot = st.checkbox("Pie del estilo / nodus", value=True)
    show_labels_rectas = st.checkbox("Etiquetas rectas", value=True)
    show_labels_analemmas = st.checkbox("Etiquetas analemas", value=True)
    show_labels_true_hours = st.checkbox("Etiquetas horas verdaderas", value=True)
    show_labels_daycurves = st.checkbox("Etiquetas curvas diarias", value=True)
    show_axes = st.checkbox("Ejes", value=True)
    show_grid = st.checkbox("Cuadricula", value=True)
    show_legend = st.checkbox("Leyenda", value=True)
    show_title = st.checkbox("Titulo", value=True)

values = {
    "model": model,
    "lat_deg": lat_deg,
    "lon_deg": lon_deg,
    "wall_declination_deg": wall_declination_deg,
    "target_width_m": target_width_m,
    "target_height_m": target_height_m,
    "year": year,
    "babilonic_indices": babilonic_indices,
    "italic_hours": italic_hours,
    "analemma_hours": analemma_hours,
    "true_hours": true_hours,
    "special_dates": special_dates,
    "min_altitude_lines_deg": min_altitude_lines_deg,
    "min_altitude_analemmas_deg": min_altitude_analemmas_deg,
    "min_altitude_true_hours_deg": min_altitude_true_hours_deg,
    "min_altitude_daycurve_deg": min_altitude_daycurve_deg,
}

visibility_tab, export_tab = st.tabs(["Vista", "Exportar"])

visibility = make_visibility(
    {
        "show_bab": show_bab,
        "show_ita": show_ita,
        "show_analemmas": show_analemmas,
        "show_true_hours": show_true_hours,
        "show_daycurves": show_daycurves,
        "show_equinox_line": show_equinox_line,
        "show_meridian": show_meridian,
        "show_style_foot": show_style_foot,
        "show_labels_rectas": show_labels_rectas,
        "show_labels_analemmas": show_labels_analemmas,
        "show_labels_true_hours": show_labels_true_hours,
        "show_labels_daycurves": show_labels_daycurves,
        "show_axes": show_axes,
        "show_grid": show_grid,
        "show_legend": show_legend,
        "show_title": show_title,
    }
)

try:
    config = make_config(values)
    fig, computed_data = render_plot(config, visibility)
except Exception as exc:
    st.error(str(exc))
    st.stop()

with visibility_tab:
    st.pyplot(fig, clear_figure=True, use_container_width=True)

    summary_columns = st.columns(4)
    with summary_columns[0]:
        if isinstance(config, VerticalSundialConfig):
            metric_line("Escala vertical", f"{computed_data['vertical_scale_m']:.4f} m")
        else:
            metric_line("Altura del estilo", f"{computed_data['style_height_m']:.4f} m")
    with summary_columns[1]:
        metric_line("Geometria ocupada", f"{computed_data['occupied_width_m']:.4f} x {computed_data['occupied_height_m']:.4f} m")
    with summary_columns[2]:
        metric_line("Margen horizontal", f"{computed_data['horizontal_margin_m']:.4f} m")
    with summary_columns[3]:
        metric_line("Margen vertical", f"{computed_data['vertical_margin_m']:.4f} m")

    warnings = computed_data.get("warnings", [])
    if warnings:
        st.warning(format_warnings(warnings))

with export_tab:
    dpi_label = st.selectbox("Resolucion raster", tuple(DPI_OPTIONS.keys()), index=1)
    dpi = DPI_OPTIONS[dpi_label]
    width_px = round((config.target_width_m / M_PER_INCH) * dpi)
    height_px = round((config.target_height_m / M_PER_INCH) * dpi)
    st.caption(
        f"Salida raster estimada: {width_px} x {height_px} px a {dpi} ppp "
        f"({dpi / CM_PER_INCH:.2f} px/cm)."
    )

    export_signature = repr((config, tuple(sorted(visibility.items())), dpi))
    download_columns = st.columns(4)
    with download_columns[0]:
        if st.button("Generar PNG"):
            try:
                st.session_state["png_export"] = {
                    "signature": export_signature,
                    "data": render_export_bytes(config, visibility, "png", dpi=dpi),
                }
            except Exception as exc:
                st.error(str(exc))
        png_export = st.session_state.get("png_export")
        if png_export and png_export["signature"] == export_signature:
            st.download_button(
                "Descargar PNG",
                data=png_export["data"],
                file_name="reloj_solar.png",
                mime="image/png",
            )
    with download_columns[1]:
        if st.button("Generar PDF"):
            try:
                st.session_state["pdf_export"] = {
                    "signature": export_signature,
                    "data": render_export_bytes(config, visibility, "pdf", dpi=dpi),
                }
            except Exception as exc:
                st.error(str(exc))
        pdf_export = st.session_state.get("pdf_export")
        if pdf_export and pdf_export["signature"] == export_signature:
            st.download_button(
                "Descargar PDF",
                data=pdf_export["data"],
                file_name="reloj_solar.pdf",
                mime="application/pdf",
            )
    with download_columns[2]:
        if st.button("Generar TIFF"):
            try:
                st.session_state["tiff_export"] = {
                    "signature": export_signature,
                    "data": render_export_bytes(config, visibility, "tiff", dpi=dpi),
                }
            except Exception as exc:
                st.error(str(exc))
        tiff_export = st.session_state.get("tiff_export")
        if tiff_export and tiff_export["signature"] == export_signature:
            st.download_button(
                "Descargar TIFF",
                data=tiff_export["data"],
                file_name="reloj_solar.tiff",
                mime="image/tiff",
            )
    with download_columns[3]:
        if st.button("Generar Excel"):
            try:
                st.session_state["excel_export"] = {
                    "signature": export_signature,
                    "data": build_excel_bytes(config, visibility),
                }
            except Exception as exc:
                st.error(str(exc))
        excel_export = st.session_state.get("excel_export")
        if excel_export and excel_export["signature"] == export_signature:
            st.download_button(
                "Descargar Excel",
                data=excel_export["data"],
                file_name="reloj_solar_coordenadas.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
