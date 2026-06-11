"""
validacion_modelo.py
====================

Validacion numerica del modelo astronomico del TFG frente a una referencia de
alta precision (algoritmo de Meeus, "Astronomical Algorithms", 1998).

El trazado gnomonico de la aplicacion es exacto por construccion: una vez
conocidas la declinacion solar (delta) y el angulo horario (H), las coordenadas
de la sombra se obtienen mediante proyecciones algebraicas. El unico punto que
puede introducir error en la plantilla es, por tanto, el modelo astronomico que
proporciona delta y la ecuacion del tiempo (E_t) a partir de la fecha, es decir,
el modulo solar_model.py.

Este script calcula delta(d) y E_t(d) con solar_model.py para los 365 dias del
anio y los compara con los valores del algoritmo de Meeus, reproduciendo los
errores recogidos en la memoria del TFG (Tabla 7.1):

    Ecuacion del tiempo : error max ~ 9 s,  RMS ~ 6 s
    Declinacion         : error max ~ 10', RMS ~ 7'

Uso:
    python validacion_modelo.py

Solo necesita numpy y el modulo solar_model.py incluido en este paquete.
"""

import math
from datetime import date

import numpy as np

from solar_model import orbital_model

# Conversion de radianes angulares a minutos de tiempo (2*pi rad = 24 h = 1440 min)
RAD_A_MIN = 1440.0 / (2.0 * math.pi)


def modelo_tfg(n_dia):
    """delta (grados) y E_t (minutos) del modelo del TFG para el dia n_dia
    del anio (0 = 1 de enero), evaluado al mediodia."""
    d = float(n_dia) + 0.5
    delta, Et = orbital_model(np.array([d]))
    return math.degrees(float(delta[0])), float(Et[0]) * RAD_A_MIN


def _dia_juliano(anio, mes, dia, hora=12.0):
    if mes <= 2:
        anio -= 1
        mes += 12
    A = anio // 100
    B = 2 - A + A // 4
    return (math.floor(365.25 * (anio + 4716))
            + math.floor(30.6001 * (mes + 1))
            + dia + B - 1524.5 + hora / 24.0)


def modelo_meeus(anio, mes, dia, hora=12.0):
    """delta (grados) y E_t (minutos) de referencia (Meeus, 1998)."""
    T = (_dia_juliano(anio, mes, dia, hora) - 2451545.0) / 36525.0
    L0 = (280.46646 + 36000.76983 * T + 0.0003032 * T * T) % 360.0
    M = math.radians(357.52911 + 35999.05029 * T - 0.0001537 * T * T)
    C = ((1.914602 - 0.004817 * T - 0.000014 * T * T) * math.sin(M)
         + (0.019993 - 0.000101 * T) * math.sin(2.0 * M)
         + 0.000289 * math.sin(3.0 * M))
    long_verdadera = L0 + C
    Omega = math.radians(125.04 - 1934.136 * T)
    lam = math.radians(long_verdadera - 0.00569 - 0.00478 * math.sin(Omega))
    eps0 = (23.0 + 26.0 / 60.0 + 21.448 / 3600.0
            - (46.8150 * T + 0.00059 * T * T - 0.001813 * T ** 3) / 3600.0)
    eps = math.radians(eps0 + 0.00256 * math.cos(Omega))
    alpha = math.degrees(math.atan2(math.cos(eps) * math.sin(lam),
                                    math.cos(lam))) % 360.0
    delta = math.degrees(math.asin(math.sin(eps) * math.sin(lam)))
    dpsi = -0.00478 * math.sin(Omega)
    E = L0 - 0.0057183 - alpha + dpsi * math.cos(eps)
    E = (E + 180.0) % 360.0 - 180.0
    return delta, E * 4.0   # 1 grado = 4 minutos de tiempo


def main(anio=2026):
    n_dias = 365
    tfg_delta = np.zeros(n_dias)
    tfg_Et = np.zeros(n_dias)
    ref_delta = np.zeros(n_dias)
    ref_Et = np.zeros(n_dias)

    base = date(anio, 1, 1).toordinal()
    for n in range(n_dias):
        d = date.fromordinal(base + n)
        tfg_delta[n], tfg_Et[n] = modelo_tfg(n)
        ref_delta[n], ref_Et[n] = modelo_meeus(d.year, d.month, d.day)

    # Alinear el convenio de signo de la ecuacion del tiempo
    if np.sum(tfg_Et * ref_Et) < 0.0:
        ref_Et = -ref_Et

    err_Et = tfg_Et - ref_Et                      # minutos de tiempo
    err_delta = (tfg_delta - ref_delta) * 60.0    # minutos de arco

    print("=" * 66)
    print("Comprobacion previa de la referencia (Meeus)")
    print("=" * 66)
    for mes, dia in [(2, 11), (5, 14), (7, 26), (11, 3)]:
        _, e = modelo_meeus(anio, mes, dia)
        print(f"  E_t {dia:02d}/{mes:02d} = {e:+6.2f} min   (extremo clasico)")
    for nombre, (mes, dia) in [("solsticio jun", (6, 21)),
                               ("solsticio dic", (12, 21))]:
        dd, _ = modelo_meeus(anio, mes, dia)
        print(f"  delta {nombre} = {dd:+6.2f} grados")

    emax = np.max(np.abs(err_Et))
    erms = np.sqrt(np.mean(err_Et ** 2))
    dmax = np.max(np.abs(err_delta))
    drms = np.sqrt(np.mean(err_delta ** 2))

    print()
    print("=" * 66)
    print(f"Error del modelo del TFG frente a Meeus (anio {anio}, {n_dias} dias)")
    print("=" * 66)
    print(f"  Ecuacion del tiempo : max = {emax * 60:5.1f} s    RMS = {erms * 60:5.1f} s")
    print(f"  Declinacion         : max = {dmax:5.2f}'   RMS = {drms:5.2f}'")
    print()
    print("Valores recogidos en la Tabla 7.1 de la memoria del TFG.")


if __name__ == "__main__":
    main()
