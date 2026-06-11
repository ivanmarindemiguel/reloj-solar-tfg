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

## Validacion del modelo

El script `validacion_modelo.py` comprueba el modelo astronomico (`solar_model.py`) comparando la ecuacion del tiempo y la declinacion con el algoritmo de referencia de Meeus a lo largo de todo el anio. Reproduce los errores recogidos en la memoria del TFG (Tabla 7.1).

```bash
python validacion_modelo.py
```

## Publicar con enlace

La app original usa Tkinter, por lo que no puede ejecutarse directamente en GitHub Pages. Para tener un enlace publico de la aplicacion, publica este repositorio en GitHub y despliega `streamlit_app.py` en Streamlit Community Cloud.

Pasos recomendados:

1. Crea un repositorio nuevo en GitHub.
2. Sube estos archivos al repositorio.
3. En Streamlit Community Cloud, crea una app nueva desde el repositorio.
4. Usa `streamlit_app.py` como archivo principal.
5. Comparte el enlace publico generado por Streamlit.

Referencias:

- GitHub: https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-new-repository
- Streamlit: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy

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
validacion_modelo.py     Validacion del modelo astronomico frente a Meeus.
excel_export.py          Exportacion de coordenadas a XLSX.
plantillas_uax_chamberi/ Ejemplos generados.
```
