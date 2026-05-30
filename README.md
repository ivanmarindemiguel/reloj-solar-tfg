# Reloj solar horizontal y vertical

Aplicacion desarrollada para el TFG. Permite generar plantillas de reloj solar horizontal y vertical, visualizar las curvas principales y exportar resultados a escala real.

## Funcionalidades

- Generacion de relojes solares horizontales y verticales.
- Calculo de lineas babilonicas, italicas, analemas, horas verdaderas, curvas diarias, meridiana y recta equinoccial.
- Ajuste al tamano objetivo de plantilla.
- Filtros de altura solar minima.
- Exportacion a PNG, PDF, TIFF y Excel de coordenadas.
- Version de escritorio con Tkinter y version web con Streamlit.

## Ejecutar la app de escritorio

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## Ejecutar la version web

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run streamlit_app.py
```


## Estructura

```text
main.py                  Entrada de la app de escritorio.
gui.py                   Interfaz Tkinter.
streamlit_app.py          Version web desplegable.
plotting.py              Trazado del reloj horizontal.
vertical_plotting.py     Trazado del reloj vertical.
gnomonics.py             Calculos gnomonicos horizontales.
vertical_gnomonics.py    Calculos gnomonicos verticales.
solar_model.py           Modelo orbital.
excel_export.py          Exportacion de coordenadas a XLSX.
plantillas_uax_chamberi/ Ejemplos generados.
```
