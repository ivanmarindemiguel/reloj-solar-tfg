import tkinter as tk
from datetime import date
from tkinter import filedialog, messagebox, ttk

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

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
PIXEL_WARNING_THRESHOLD = 120_000_000
RESOLUTION_PRESETS = {
    "150 ppp (borrador)": 150,
    "300 ppp (estandar)": 300,
    "600 ppp (alta calidad)": 600,
    "1200 ppp (arte final)": 1200,
    "Personalizada": None,
}


class SundialApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Aplicacion de reloj solar horizontal y vertical")
        self.geometry("1500x900")
        self.minsize(1300, 800)
        try:
            self.state("zoomed")
        except tk.TclError:
            pass

        self.layers = None
        self.computed_data = None
        self.current_config = None

        self._create_variables()
        self._create_layout()
        self._populate_default_dates()
        self.bind("<Return>", lambda _event: self.generate_plot())
        self.generate_plot()

    # =========================================================
    # VARIABLES
    # =========================================================

    def _create_variables(self):
        current_year = date.today().year

        # Parametros
        self.model_var = tk.StringVar(value="Horizontal")
        self.lat_var = tk.StringVar(value=str(40 + 24 / 60 + 35 / 3600))
        self.lon_var = tk.StringVar(value=str(-(3 + 41 / 60 + 11 / 3600)))
        self.wall_declination_var = tk.StringVar(value="0.0")
        self.target_width_var = tk.StringVar(value="1.0")
        self.target_height_var = tk.StringVar(value="0.5")
        self.year_var = tk.StringVar(value=str(current_year))

        self.bab_idx_var = tk.StringVar(value="2,3,4,5,6,7")
        self.ita_idx_var = tk.StringVar(value="17,18,19,20,21,22")
        self.analemma_hours_var = tk.StringVar(value="12,13,14,15,16")
        self.true_hours_var = tk.StringVar(value="9,10,11,12,13,14,15")

        self.min_alt_lines_var = tk.StringVar(value="5.0")
        self.min_alt_analemmas_var = tk.StringVar(value="5.0")
        self.min_alt_daycurve_var = tk.StringVar(value="15.0")

        self.day_var = tk.StringVar(value="22")
        self.month_var = tk.StringVar(value="8")

        self.view_mode_var = tk.StringVar(value="screen")

        self.resolution_preset_var = tk.StringVar(value="300 ppp (estandar)")
        self.custom_dpi_var = tk.StringVar(value="300")

        self.summary_style_var = tk.StringVar(value="Altura del estilo calculada: -")
        self.summary_occupied_var = tk.StringVar(value="Geometria ocupada: -")
        self.summary_margin_var = tk.StringVar(value="Margen restante: -")
        self.summary_warning_var = tk.StringVar(value="Avisos de visibilidad: ninguno")
        self.export_info_var = tk.StringVar(value="Salida raster estimada: -")

        vis = default_visibility()
        self.show_bab_var = tk.BooleanVar(value=vis["show_bab"])
        self.show_ita_var = tk.BooleanVar(value=vis["show_ita"])
        self.show_analemmas_var = tk.BooleanVar(value=vis["show_analemmas"])
        self.show_true_hours_var = tk.BooleanVar(value=vis["show_true_hours"])
        self.show_daycurves_var = tk.BooleanVar(value=vis["show_daycurves"])
        self.show_equinox_line_var = tk.BooleanVar(value=vis["show_equinox_line"])
        self.show_meridian_var = tk.BooleanVar(value=vis["show_meridian"])
        self.show_style_foot_var = tk.BooleanVar(value=vis["show_style_foot"])

        self.show_labels_rectas_var = tk.BooleanVar(value=vis["show_labels_rectas"])
        self.show_labels_analemmas_var = tk.BooleanVar(value=vis["show_labels_analemmas"])
        self.show_labels_true_hours_var = tk.BooleanVar(value=vis["show_labels_true_hours"])
        self.show_labels_daycurves_var = tk.BooleanVar(value=vis["show_labels_daycurves"])

        self.show_axes_var = tk.BooleanVar(value=vis["show_axes"])
        self.show_grid_var = tk.BooleanVar(value=vis["show_grid"])
        self.show_legend_var = tk.BooleanVar(value=vis["show_legend"])
        self.show_title_var = tk.BooleanVar(value=vis["show_title"])

    # =========================================================
    # LAYOUT
    # =========================================================

    def _create_layout(self):
        paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        left = ttk.Frame(paned, padding=8)
        right = ttk.Frame(paned, padding=8)
        left.configure(width=560)

        paned.add(left, weight=0)
        paned.add(right, weight=1)

        actions = ttk.Frame(left, padding=(0, 8, 0, 0))
        actions.pack(fill=tk.X, pady=(0, 8))

        ttk.Button(actions, text="Generar / recalcular", command=self.generate_plot).pack(
            fill=tk.X, pady=3
        )
        ttk.Button(actions, text="Restaurar valores por defecto", command=self.restore_defaults).pack(
            fill=tk.X, pady=3
        )

        notebook = ttk.Notebook(left)
        notebook.pack(fill=tk.BOTH, expand=True)

        tab_params_container = ttk.Frame(notebook)
        tab_view = ttk.Frame(notebook, padding=8)
        tab_export = ttk.Frame(notebook, padding=8)

        notebook.add(tab_params_container, text="Parametros")
        notebook.add(tab_view, text="Vista")
        notebook.add(tab_export, text="Exportar")

        tab_params = self._create_scrollable_tab(tab_params_container)
        self._build_params_tab(tab_params)
        self._build_view_tab(tab_view)
        self._build_export_tab(tab_export)
        self.after_idle(lambda: paned.sashpos(0, 560))

        self.fig = Figure(figsize=(9, 7), dpi=100, facecolor="white")
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor("white")

        self.canvas = FigureCanvasTkAgg(self.fig, master=right)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(fill=tk.BOTH, expand=True)

        toolbar = NavigationToolbar2Tk(self.canvas, right, pack_toolbar=False)
        toolbar.update()
        toolbar.pack(fill=tk.X)

    def _create_scrollable_tab(self, parent):
        canvas = tk.Canvas(parent, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=canvas.yview)
        scroll_frame = ttk.Frame(canvas, padding=8)

        scroll_frame.bind(
            "<Configure>",
            lambda _event: canvas.configure(scrollregion=canvas.bbox("all")),
        )

        canvas_window = canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        def _resize_inner(_event):
            canvas.itemconfigure(canvas_window, width=_event.width)

        canvas.bind("<Configure>", _resize_inner)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        return scroll_frame

    def _build_params_tab(self, parent):
        frame_geo = ttk.LabelFrame(parent, text="Localizacion y geometria", padding=8)
        frame_geo.pack(fill=tk.X, pady=4)

        self._labeled_entry(frame_geo, "Latitud (°)", self.lat_var, 0)
        self._labeled_entry(frame_geo, "Longitud (°)", self.lon_var, 1)
        self._labeled_entry(frame_geo, "Declinacion pared vertical (deg)", self.wall_declination_var, 2)
        self._labeled_entry(frame_geo, "Ancho objetivo (m)", self.target_width_var, 3)
        self._labeled_entry(frame_geo, "Alto objetivo (m)", self.target_height_var, 4)
        self._labeled_entry(frame_geo, "Ano", self.year_var, 5)

        ttk.Label(
            frame_geo,
            text="Convencion temporal: UTC+2 fijo (sin cambios automaticos)",
        ).grid(row=6, column=0, columnspan=2, sticky="w", pady=(6, 0))
        ttk.Label(
            frame_geo,
            text=(
                "Longitud oeste negativa. En vertical, gamma=0 mira al Sur; "
                "gamma positiva gira la pared hacia Este."
            ),
            justify="left",
            wraplength=420,
        ).grid(row=7, column=0, columnspan=2, sticky="w", pady=(6, 0))

        ttk.Label(frame_geo, text="Modelo").grid(row=8, column=0, sticky="w", pady=(8, 2), padx=(0, 8))
        model_combo = ttk.Combobox(
            frame_geo,
            state="readonly",
            textvariable=self.model_var,
            values=("Horizontal", "Vertical"),
        )
        model_combo.grid(row=8, column=1, sticky="ew", pady=(8, 2))
        model_combo.bind("<<ComboboxSelected>>", lambda _event: self.generate_plot())

        frame_lists = ttk.LabelFrame(parent, text="Listas de elementos", padding=8)
        frame_lists.pack(fill=tk.X, pady=4)

        self._labeled_entry(frame_lists, "Horas babilonicas", self.bab_idx_var, 0)
        self._labeled_entry(frame_lists, "Horas italicas", self.ita_idx_var, 1)
        self._labeled_entry(frame_lists, "Horas de analemas (h)", self.analemma_hours_var, 2)
        self._labeled_entry(frame_lists, "Horas verdaderas (h)", self.true_hours_var, 3)

        frame_dates = ttk.LabelFrame(parent, text="Fechas especiales", padding=8)
        frame_dates.pack(fill=tk.BOTH, expand=False, pady=4)

        input_dates = ttk.Frame(frame_dates)
        input_dates.pack(fill=tk.X)

        ttk.Label(input_dates, text="Dia").grid(row=0, column=0, sticky="w")
        ttk.Entry(input_dates, textvariable=self.day_var, width=8).grid(row=0, column=1, padx=4)

        ttk.Label(input_dates, text="Mes").grid(row=0, column=2, sticky="w")
        ttk.Entry(input_dates, textvariable=self.month_var, width=8).grid(row=0, column=3, padx=4)

        ttk.Button(input_dates, text="Anadir fecha", command=self.add_date).grid(
            row=0, column=4, padx=4
        )
        ttk.Button(input_dates, text="Eliminar seleccionada", command=self.remove_selected_date).grid(
            row=0, column=5, padx=4
        )
        ttk.Button(input_dates, text="Limpiar fechas", command=self.clear_dates).grid(
            row=0, column=6, padx=4
        )

        self.date_listbox = tk.Listbox(frame_dates, height=3, exportselection=False)
        self.date_listbox.pack(fill=tk.X, pady=(8, 0))

        frame_filters = ttk.LabelFrame(parent, text="Filtros de representacion", padding=8)
        frame_filters.pack(fill=tk.X, pady=4)

        self._labeled_entry(frame_filters, "Altura minima rectas (°)", self.min_alt_lines_var, 0)
        self._labeled_entry(
            frame_filters,
            "Altura minima analemas y horas verdaderas (°)",
            self.min_alt_analemmas_var,
            1,
        )
        self._labeled_entry(
            frame_filters,
            "Altura minima curvas diarias (°)",
            self.min_alt_daycurve_var,
            2,
        )

        ttk.Label(
            frame_filters,
            text="Las alturas minimas recortan tramos con el Sol bajo.",
            justify="left",
            wraplength=420,
        ).grid(row=3, column=0, columnspan=2, sticky="w", pady=(6, 0))

        frame_summary = ttk.LabelFrame(parent, text="Resumen geometrico", padding=8)
        frame_summary.pack(fill=tk.X, pady=4)

        ttk.Label(frame_summary, textvariable=self.summary_style_var, justify="left").pack(
            anchor="w", pady=2
        )
        ttk.Label(frame_summary, textvariable=self.summary_occupied_var, justify="left").pack(
            anchor="w", pady=2
        )
        ttk.Label(frame_summary, textvariable=self.summary_margin_var, justify="left").pack(
            anchor="w", pady=2
        )
        ttk.Label(
            frame_summary,
            textvariable=self.summary_warning_var,
            justify="left",
            foreground="#8a4b00",
            wraplength=420,
        ).pack(anchor="w", pady=(4, 2))

    def _build_view_tab(self, parent):
        frame_layers = ttk.LabelFrame(parent, text="Capas visibles", padding=8)
        frame_layers.pack(fill=tk.X, pady=4)

        layer_checks = [
            ("Ver babilonicas", self.show_bab_var),
            ("Ver italicas", self.show_ita_var),
            ("Ver analemas", self.show_analemmas_var),
            ("Ver horas verdaderas", self.show_true_hours_var),
            ("Ver curvas diarias", self.show_daycurves_var),
            ("Ver recta equinoccial", self.show_equinox_line_var),
            ("Ver meridiana", self.show_meridian_var),
            ("Ver pie del estilo", self.show_style_foot_var),
            ("Ver etiquetas de rectas", self.show_labels_rectas_var),
            ("Ver etiquetas de analemas", self.show_labels_analemmas_var),
            ("Ver etiquetas horas verdaderas", self.show_labels_true_hours_var),
            ("Ver etiquetas de fechas", self.show_labels_daycurves_var),
        ]

        for idx, (text, var) in enumerate(layer_checks):
            row = idx % 6
            column = idx // 6
            ttk.Checkbutton(frame_layers, text=text, variable=var, command=self.update_visibility).grid(
                row=row, column=column, sticky="w", pady=2, padx=(0, 12)
            )
        frame_layers.columnconfigure(0, weight=1)
        frame_layers.columnconfigure(1, weight=1)

        frame_axes = ttk.LabelFrame(parent, text="Vista", padding=8)
        frame_axes.pack(fill=tk.X, pady=4)

        view_checks = [
            ("Mostrar ejes", self.show_axes_var),
            ("Mostrar rejilla", self.show_grid_var),
            ("Mostrar leyenda", self.show_legend_var),
            ("Mostrar titulo", self.show_title_var),
        ]

        for idx, (text, var) in enumerate(view_checks):
            ttk.Checkbutton(frame_axes, text=text, variable=var, command=self.update_visibility).grid(
                row=idx // 2, column=idx % 2, sticky="w", pady=2, padx=(0, 12)
            )
        frame_axes.columnconfigure(0, weight=1)
        frame_axes.columnconfigure(1, weight=1)

        frame_mode = ttk.LabelFrame(parent, text="Modo", padding=8)
        frame_mode.pack(fill=tk.X, pady=4)

        ttk.Radiobutton(
            frame_mode,
            text="Pantalla",
            value="screen",
            variable=self.view_mode_var,
            command=self.update_visibility,
        ).grid(row=0, column=0, sticky="w", pady=2)

        ttk.Radiobutton(
            frame_mode,
            text="Impresion limpia",
            value="print",
            variable=self.view_mode_var,
            command=self.update_visibility,
        ).grid(row=1, column=0, sticky="w", pady=2)

        ttk.Label(
            frame_mode,
            text=(
                "Las casillas de esta pestana se aplican al instante.\n"
                "El modo impresion oculta ejes, rejilla, leyenda y titulo,\n"
                "pero mantiene la geometria sin distorsion."
            ),
        ).grid(row=2, column=0, sticky="w", pady=(6, 0))

    def _build_export_tab(self, parent):
        frame_resolution = ttk.LabelFrame(parent, text="Resolucion de impresora", padding=8)
        frame_resolution.pack(fill=tk.X, pady=4)

        ttk.Label(frame_resolution, text="Perfil").grid(row=0, column=0, sticky="w", pady=2)
        preset_combo = ttk.Combobox(
            frame_resolution,
            state="readonly",
            textvariable=self.resolution_preset_var,
            values=list(RESOLUTION_PRESETS.keys()),
        )
        preset_combo.grid(row=0, column=1, sticky="ew", pady=2)
        preset_combo.bind("<<ComboboxSelected>>", lambda _event: self._refresh_export_info())

        ttk.Label(frame_resolution, text="Resolucion personalizada (ppp)").grid(
            row=1, column=0, sticky="w", pady=2
        )
        custom_entry = ttk.Entry(frame_resolution, textvariable=self.custom_dpi_var, width=16)
        custom_entry.grid(row=1, column=1, sticky="ew", pady=2)
        custom_entry.bind("<KeyRelease>", lambda _event: self._refresh_export_info())
        custom_entry.bind("<FocusOut>", lambda _event: self._refresh_export_info())
        frame_resolution.columnconfigure(1, weight=1)

        ttk.Label(
            frame_resolution,
            text="La resolucion afecta a PNG y TIFF. El PDF mantiene el tamano fisico real.",
            justify="left",
        ).grid(row=2, column=0, columnspan=2, sticky="w", pady=(6, 2))

        ttk.Label(parent, textvariable=self.export_info_var, justify="left").pack(
            anchor="w", pady=(0, 8)
        )

        frame_export = ttk.LabelFrame(parent, text="Exportar a escala real", padding=8)
        frame_export.pack(fill=tk.X, pady=4)

        ttk.Button(frame_export, text="Exportar PNG a escala", command=self.export_png_scale).pack(
            fill=tk.X, pady=4
        )
        ttk.Button(frame_export, text="Exportar PDF a escala", command=self.export_pdf_scale).pack(
            fill=tk.X, pady=4
        )
        ttk.Button(frame_export, text="Exportar TIFF a escala", command=self.export_tiff_scale).pack(
            fill=tk.X, pady=4
        )
        ttk.Button(
            frame_export,
            text="Exportar Excel de coordenadas",
            command=self.export_coordinate_excel,
        ).pack(fill=tk.X, pady=4)

        ttk.Label(
            parent,
            text=(
                "Notas:\n"
                "- La exportacion siempre usa el modo impresion limpia.\n"
                "- El archivo se genera con el tamano fisico exacto indicado en parametros.\n"
                "- Para imprimir, usa siempre 'tamano real' o 100%.\n"
                "- Si la proporcion geometrica no coincide con la plantilla, quedaran margenes."
            ),
            justify="left",
        ).pack(anchor="w", pady=(10, 0))

    def _labeled_entry(self, parent, label, variable, row):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=2, padx=(0, 8))
        ttk.Entry(parent, textvariable=variable, width=24).grid(
            row=row, column=1, sticky="ew", pady=2
        )
        parent.columnconfigure(1, weight=1)

    # =========================================================
    # HELPERS DE PARSEO
    # =========================================================

    def _parse_int_list(self, text):
        text = text.strip()
        if not text:
            return tuple()

        parts = [part.strip() for part in text.split(",") if part.strip()]
        try:
            return tuple(sorted(set(int(part) for part in parts)))
        except ValueError as exc:
            raise ValueError(
                "Las listas enteras deben contener solo numeros enteros separados por comas."
            ) from exc

    def _parse_float_list(self, text):
        text = text.strip()
        if not text:
            return tuple()

        parts = [part.strip() for part in text.split(",") if part.strip()]
        try:
            return tuple(float(part) for part in parts)
        except ValueError as exc:
            raise ValueError(
                "Las listas numericas deben contener solo numeros separados por comas."
            ) from exc

    def _parse_scalar_float(self, text, label):
        normalized = text.strip().replace(",", ".")
        try:
            return float(normalized)
        except ValueError as exc:
            raise ValueError(f"El campo '{label}' debe ser un numero valido.") from exc

    def _is_vertical_model(self):
        return self.model_var.get().strip().lower() == "vertical"

    def _format_int_list(self, values):
        return ",".join(str(value) for value in values)

    def _italic_display_hour(self, internal_index):
        return 24 - int(internal_index)

    def _parse_italic_hour_list(self, text):
        hours = self._parse_int_list(text)
        invalid = [hour for hour in hours if not (1 <= hour <= 23)]
        if invalid:
            raise ValueError("Las horas italicas deben estar entre 1 y 23.")
        return tuple(sorted(set(24 - hour for hour in hours)))

    def _format_italic_hour_list(self, internal_indices):
        display_hours = sorted(self._italic_display_hour(index) for index in internal_indices)
        return ",".join(str(hour) for hour in display_hours)

    def _format_float_list(self, values):
        formatted = []
        for value in values:
            if float(value).is_integer():
                formatted.append(str(int(value)))
            else:
                formatted.append(str(value))
        return ",".join(formatted)

    def _get_dates_from_listbox(self):
        dates = []
        for idx in range(self.date_listbox.size()):
            item = self.date_listbox.get(idx)
            day_str, month_str = item.split("/")
            dates.append((int(day_str), int(month_str)))
        return tuple(dates)

    def _current_visibility(self):
        return {
            "show_bab": self.show_bab_var.get(),
            "show_ita": self.show_ita_var.get(),
            "show_analemmas": self.show_analemmas_var.get(),
            "show_true_hours": self.show_true_hours_var.get(),
            "show_daycurves": self.show_daycurves_var.get(),
            "show_equinox_line": self.show_equinox_line_var.get(),
            "show_meridian": self.show_meridian_var.get(),
            "show_style_foot": self.show_style_foot_var.get(),
            "show_labels_rectas": self.show_labels_rectas_var.get(),
            "show_labels_analemmas": self.show_labels_analemmas_var.get(),
            "show_labels_true_hours": self.show_labels_true_hours_var.get(),
            "show_labels_daycurves": self.show_labels_daycurves_var.get(),
            "show_axes": self.show_axes_var.get(),
            "show_grid": self.show_grid_var.get(),
            "show_legend": self.show_legend_var.get(),
            "show_title": self.show_title_var.get(),
        }

    def _selected_dpi(self):
        preset_value = RESOLUTION_PRESETS.get(self.resolution_preset_var.get())
        if preset_value is not None:
            return float(preset_value)

        dpi = self._parse_scalar_float(self.custom_dpi_var.get(), "Resolucion personalizada")
        if dpi <= 0.0:
            raise ValueError("La resolucion personalizada debe ser positiva.")
        return dpi

    def _sync_selection_fields(self, effective_config):
        self.bab_idx_var.set(self._format_int_list(effective_config.babilonic_indices))
        self.ita_idx_var.set(self._format_italic_hour_list(effective_config.italic_indices))
        self.analemma_hours_var.set(self._format_float_list(effective_config.analemma_hours))
        self.true_hours_var.set(self._format_float_list(effective_config.true_hours))

    def _refresh_summary(self):
        if not self.computed_data:
            self.summary_style_var.set("Altura del estilo calculada: -")
            self.summary_occupied_var.set("Geometria ocupada: -")
            self.summary_margin_var.set("Margen restante: -")
            self.summary_warning_var.set("Avisos de visibilidad: ninguno")
            return

        style_height_m = self.computed_data["style_height_m"]
        occupied_width_m = self.computed_data["occupied_width_m"]
        occupied_height_m = self.computed_data["occupied_height_m"]
        margin_x_m = self.computed_data["horizontal_margin_m"]
        margin_y_m = self.computed_data["vertical_margin_m"]

        if "vertical_scale_m" in self.computed_data:
            self.summary_style_var.set(
                "Modelo vertical calculado: "
                f"a={self.computed_data['nodus_distance_m']:.4f} m; "
                "nodus proyectado en (0,0)"
            )
        else:
            self.summary_style_var.set(f"Altura del estilo calculada: {style_height_m:.4f} m")
        self.summary_occupied_var.set(
            f"Geometria ocupada: {occupied_width_m:.4f} m x {occupied_height_m:.4f} m"
        )
        self.summary_margin_var.set(
            f"Margen restante: {margin_x_m:.4f} m horizontal, {margin_y_m:.4f} m vertical"
        )
        warnings = self.computed_data.get("warnings", [])
        if warnings:
            self.summary_warning_var.set(
                "Avisos de visibilidad:\n- " + "\n- ".join(warnings)
            )
        else:
            self.summary_warning_var.set("Avisos de visibilidad: ninguno")

    def _refresh_export_info(self):
        try:
            config = self.build_config()
            dpi = self._selected_dpi()
            width_px = round((config.target_width_m / M_PER_INCH) * dpi)
            height_px = round((config.target_height_m / M_PER_INCH) * dpi)
            px_per_cm = dpi / CM_PER_INCH
            self.export_info_var.set(
                "Salida raster estimada: "
                f"{width_px} x {height_px} px a {dpi:.0f} ppp "
                f"({px_per_cm:.2f} px/cm)"
            )
        except Exception:
            self.export_info_var.set("Salida raster estimada: revisa dimensiones y resolucion.")

    # =========================================================
    # FECHAS
    # =========================================================

    def _populate_default_dates(self):
        self.date_listbox.delete(0, tk.END)
        self.date_listbox.insert(tk.END, "22/08")

    def add_date(self):
        try:
            day = int(self.day_var.get().strip())
            month = int(self.month_var.get().strip())
            year = int(self.year_var.get().strip())

            date(year, month, day)

            item = f"{day:02d}/{month:02d}"
            existing = [self.date_listbox.get(idx) for idx in range(self.date_listbox.size())]
            if item not in existing:
                self.date_listbox.insert(tk.END, item)
        except Exception as exc:
            messagebox.showerror("Fecha no valida", f"No se pudo anadir la fecha.\n\n{exc}")

    def remove_selected_date(self):
        selection = self.date_listbox.curselection()
        if not selection:
            return
        self.date_listbox.delete(selection[0])

    def clear_dates(self):
        self.date_listbox.delete(0, tk.END)

    # =========================================================
    # CONFIG
    # =========================================================

    def build_config(self):
        lat = self._parse_scalar_float(self.lat_var.get(), "Latitud")
        lon = self._parse_scalar_float(self.lon_var.get(), "Longitud")
        wall_declination = 0.0
        if self._is_vertical_model():
            wall_declination = self._parse_scalar_float(
                self.wall_declination_var.get(), "Declinacion pared vertical"
            )
        target_width_m = self._parse_scalar_float(self.target_width_var.get(), "Ancho objetivo")
        target_height_m = self._parse_scalar_float(self.target_height_var.get(), "Alto objetivo")
        year = int(self.year_var.get().strip())

        if not (-90.0 <= lat <= 90.0):
            raise ValueError("La latitud debe estar entre -90 y 90 grados.")
        if not (-180.0 <= lon <= 180.0):
            raise ValueError("La longitud debe estar entre -180 y 180 grados.")
        if self._is_vertical_model() and not (-180.0 <= wall_declination <= 180.0):
            raise ValueError("La declinacion de pared debe estar entre -180 y 180 grados.")
        if target_width_m <= 0.0 or target_height_m <= 0.0:
            raise ValueError("El ancho y el alto objetivo deben ser positivos.")

        special_dates = self._get_dates_from_listbox()

        common_kwargs = dict(
            lat_deg=lat,
            lon_deg=lon,
            target_width_m=target_width_m,
            target_height_m=target_height_m,
            year=year,
            tz_standard=2.0,
            babilonic_indices=self._parse_int_list(self.bab_idx_var.get()),
            italic_indices=self._parse_italic_hour_list(self.ita_idx_var.get()),
            analemma_hours=self._parse_float_list(self.analemma_hours_var.get()),
            true_hours=self._parse_float_list(self.true_hours_var.get()),
            special_dates=special_dates,
            min_altitude_lines_deg=self._parse_scalar_float(
                self.min_alt_lines_var.get(), "Altura minima rectas"
            ),
            min_altitude_analemmas_deg=self._parse_scalar_float(
                self.min_alt_analemmas_var.get(), "Altura minima analemas"
            ),
            min_altitude_true_hours_deg=self._parse_scalar_float(
                self.min_alt_analemmas_var.get(), "Altura minima horas verdaderas"
            ),
            min_altitude_daycurve_deg=self._parse_scalar_float(
                self.min_alt_daycurve_var.get(), "Altura minima curvas diarias"
            ),
        )

        if self._is_vertical_model():
            return VerticalSundialConfig(
                **common_kwargs,
                wall_declination_deg=wall_declination,
            )

        return SundialConfig(**common_kwargs)

    # =========================================================
    # ACCIONES
    # =========================================================

    def generate_plot(self):
        try:
            config = self.build_config()
            self.current_config = config
            if isinstance(config, VerticalSundialConfig):
                self.layers, self.computed_data = build_vertical_plot(self.ax, config)
            else:
                self.layers, self.computed_data = build_plot(self.ax, config)
            effective_config = self.computed_data.get("effective_config", config)
            self._sync_selection_fields(effective_config)
            if isinstance(config, VerticalSundialConfig):
                apply_vertical_visibility(
                    self.ax,
                    self.layers,
                    self._current_visibility(),
                    view_mode=self.view_mode_var.get(),
                )
            else:
                apply_visibility(
                    self.ax,
                    self.layers,
                    self._current_visibility(),
                    view_mode=self.view_mode_var.get(),
                )
            self.fig.tight_layout()
            self.canvas.draw_idle()
            self._refresh_summary()
            self._refresh_export_info()
            warnings = self.computed_data.get("warnings", [])
            if warnings:
                messagebox.showwarning(
                    "Elementos descartados",
                    "Se han ajustado las selecciones a los elementos fisicamente visibles.\n\n"
                    + "\n".join(f"- {warning}" for warning in warnings),
                )
        except Exception as exc:
            messagebox.showerror("Error al generar", str(exc))

    def update_visibility(self):
        if self.layers is None:
            return

        try:
            if isinstance(self.current_config, VerticalSundialConfig):
                apply_vertical_visibility(
                    self.ax,
                    self.layers,
                    self._current_visibility(),
                    view_mode=self.view_mode_var.get(),
                )
            else:
                apply_visibility(
                    self.ax,
                    self.layers,
                    self._current_visibility(),
                    view_mode=self.view_mode_var.get(),
                )
            self.fig.tight_layout()
            self.canvas.draw_idle()
        except Exception as exc:
            messagebox.showerror("Error de visualizacion", str(exc))

    def restore_defaults(self):
        self.model_var.set("Horizontal")
        self.lat_var.set(str(40 + 24 / 60 + 35 / 3600))
        self.lon_var.set(str(-(3 + 41 / 60 + 11 / 3600)))
        self.wall_declination_var.set("0.0")
        self.target_width_var.set("1.0")
        self.target_height_var.set("0.5")
        self.year_var.set(str(date.today().year))

        self.bab_idx_var.set("2,3,4,5,6,7")
        self.ita_idx_var.set("17,18,19,20,21,22")
        self.analemma_hours_var.set("12,13,14,15,16")
        self.true_hours_var.set("9,10,11,12,13,14,15")

        self.min_alt_lines_var.set("5.0")
        self.min_alt_analemmas_var.set("5.0")
        self.min_alt_daycurve_var.set("15.0")

        self.day_var.set("22")
        self.month_var.set("8")

        self.view_mode_var.set("screen")
        self.resolution_preset_var.set("300 ppp (estandar)")
        self.custom_dpi_var.set("300")

        vis = default_visibility()
        self.show_bab_var.set(vis["show_bab"])
        self.show_ita_var.set(vis["show_ita"])
        self.show_analemmas_var.set(vis["show_analemmas"])
        self.show_true_hours_var.set(vis["show_true_hours"])
        self.show_daycurves_var.set(vis["show_daycurves"])
        self.show_equinox_line_var.set(vis["show_equinox_line"])
        self.show_meridian_var.set(vis["show_meridian"])
        self.show_style_foot_var.set(vis["show_style_foot"])
        self.show_labels_rectas_var.set(vis["show_labels_rectas"])
        self.show_labels_analemmas_var.set(vis["show_labels_analemmas"])
        self.show_labels_true_hours_var.set(vis["show_labels_true_hours"])
        self.show_labels_daycurves_var.set(vis["show_labels_daycurves"])
        self.show_axes_var.set(vis["show_axes"])
        self.show_grid_var.set(vis["show_grid"])
        self.show_legend_var.set(vis["show_legend"])
        self.show_title_var.set(vis["show_title"])

        self._populate_default_dates()
        self.generate_plot()

    # =========================================================
    # EXPORTACION
    # =========================================================

    def _build_export_figure(self, config):
        fig = Figure(
            figsize=(config.target_width_m / M_PER_INCH, config.target_height_m / M_PER_INCH),
            dpi=100,
            facecolor="white",
        )
        ax = fig.add_axes([0, 0, 1, 1])
        if isinstance(config, VerticalSundialConfig):
            layers, _ = build_vertical_plot(ax, config)
            apply_vertical_visibility(ax, layers, self._current_visibility(), view_mode="print")
        else:
            layers, _ = build_plot(ax, config)
            apply_visibility(ax, layers, self._current_visibility(), view_mode="print")
        return fig

    def _confirm_large_raster_export(self, dpi, config):
        width_px = round((config.target_width_m / M_PER_INCH) * dpi)
        height_px = round((config.target_height_m / M_PER_INCH) * dpi)
        total_pixels = width_px * height_px

        if total_pixels <= PIXEL_WARNING_THRESHOLD:
            return True

        return messagebox.askyesno(
            "Archivo raster muy grande",
            (
                f"Se van a generar aproximadamente {width_px} x {height_px} px "
                f"({total_pixels / 1_000_000:.1f} MP).\n\n"
                "El archivo puede tardar bastante en exportarse y ocupar mucho espacio.\n\n"
                "Quieres continuar?"
            ),
        )

    def _export_scale(self, path):
        config = self.build_config()
        dpi = self._selected_dpi()

        lower_path = path.lower()
        raster_export = lower_path.endswith(".png") or lower_path.endswith(".tif") or lower_path.endswith(".tiff")
        if raster_export and not self._confirm_large_raster_export(dpi, config):
            return

        fig = self._build_export_figure(config)
        try:
            if lower_path.endswith(".png"):
                fig.savefig(
                    path,
                    dpi=dpi,
                    bbox_inches=None,
                    pad_inches=0.0,
                    facecolor="white",
                )
            elif lower_path.endswith(".tif") or lower_path.endswith(".tiff"):
                fig.savefig(
                    path,
                    dpi=dpi,
                    bbox_inches=None,
                    pad_inches=0.0,
                    facecolor="white",
                    pil_kwargs={"compression": "tiff_lzw"},
                )
            else:
                fig.savefig(
                    path,
                    bbox_inches=None,
                    pad_inches=0.0,
                    facecolor="white",
                )
        finally:
            plt.close(fig)

    def export_png_scale(self):
        path = filedialog.asksaveasfilename(
            title="Guardar PNG a escala",
            defaultextension=".png",
            filetypes=[("PNG", "*.png")],
        )
        if not path:
            return

        try:
            self._export_scale(path)
            messagebox.showinfo("Exportacion completada", f"PNG guardado en:\n{path}")
        except Exception as exc:
            messagebox.showerror("Error al exportar PNG", str(exc))

    def export_pdf_scale(self):
        path = filedialog.asksaveasfilename(
            title="Guardar PDF a escala",
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
        )
        if not path:
            return

        try:
            self._export_scale(path)
            messagebox.showinfo("Exportacion completada", f"PDF guardado en:\n{path}")
        except Exception as exc:
            messagebox.showerror("Error al exportar PDF", str(exc))

    def export_tiff_scale(self):
        path = filedialog.asksaveasfilename(
            title="Guardar TIFF a escala",
            defaultextension=".tiff",
            filetypes=[("TIFF", "*.tif *.tiff")],
        )
        if not path:
            return

        try:
            self._export_scale(path)
            messagebox.showinfo("Exportacion completada", f"TIFF guardado en:\n{path}")
        except Exception as exc:
            messagebox.showerror("Error al exportar TIFF", str(exc))

    def export_coordinate_excel(self):
        path = filedialog.asksaveasfilename(
            title="Guardar Excel de coordenadas",
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
        )
        if not path:
            return

        try:
            config = self.build_config()
            if isinstance(config, VerticalSundialConfig):
                rows, computed_data = build_vertical_coordinate_export_rows(
                    config,
                    visibility=self._current_visibility(),
                    point_count=10,
                )
            else:
                rows, computed_data = build_coordinate_export_rows(
                    config,
                    visibility=self._current_visibility(),
                    point_count=10,
                )
            if not rows:
                warnings = computed_data.get("warnings", [])
                detail = ""
                if warnings:
                    detail = "\n\n" + "\n".join(f"- {warning}" for warning in warnings)
                raise ValueError(
                    "No hay curvas o rectas visibles para exportar coordenadas." + detail
                )

            write_coordinate_workbook(path, rows)
            messagebox.showinfo("Exportacion completada", f"Excel guardado en:\n{path}")
        except Exception as exc:
            messagebox.showerror("Error al exportar Excel", str(exc))


def launch_app():
    app = SundialApp()
    app.mainloop()
