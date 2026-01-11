"""
Módulo para gestionar el dashboard de habitaciones del hotel.
Calcula estados y colores según ocupación y consumos.
"""

import pandas as pd
import os
from datetime import datetime

# Estructura del hotel
PISOS = {
    1: list(range(101, 122)),  # 101-121 (21 habitaciones)
    2: list(range(222, 243)),  # 222-242 (21 habitaciones)
    3: list(range(343, 354)),  # 343-353 (11 habitaciones)
}

def obtener_habitaciones_ocupadas(archivo_pasajeros='data/pasajeros.csv'):
    """
    Obtiene la lista de habitaciones ocupadas ACTUALMENTE desde el CSV de pasajeros.
    Solo retorna habitaciones donde la fecha de ingreso ya pasó o es hoy.
    Retorna un diccionario con número de habitación como key y datos del pasajero.
    """
    if not os.path.exists(archivo_pasajeros):
        return {}
    
    df = pd.read_csv(archivo_pasajeros)
    habitaciones_ocupadas = {}
    fecha_hoy = datetime.now().strftime('%d/%m/%Y')
    
    for _, row in df.iterrows():
        fecha_ingreso = row['Fecha de ingreso']
        
        # Solo incluir si ya ingresó (fecha ingreso <= hoy)
        try:
            ingreso_dt = datetime.strptime(fecha_ingreso, '%d/%m/%Y')
            hoy_dt = datetime.strptime(fecha_hoy, '%d/%m/%Y')
            
            if ingreso_dt <= hoy_dt:
                habitaciones_ocupadas[int(row['Nro. habitación'])] = {
                    'pasajero': row['Apellido y nombre'],
                    'plazas': int(row['Plazas ocupadas']),
                    'ingreso': row['Fecha de ingreso'],
                    'egreso': row['Fecha de egreso'],
                    'servicios': row['Servicios']
                }
        except:
            # Si hay error en la fecha, incluir por defecto
            habitaciones_ocupadas[int(row['Nro. habitación'])] = {
                'pasajero': row['Apellido y nombre'],
                'plazas': int(row['Plazas ocupadas']),
                'ingreso': row['Fecha de ingreso'],
                'egreso': row['Fecha de egreso'],
                'servicios': row['Servicios']
            }
    
    return habitaciones_ocupadas


def obtener_habitaciones_reservadas_futuras(archivo_pasajeros='data/pasajeros.csv'):
    """
    Obtiene la lista de habitaciones con reservas para ingresos futuros.
    Retorna un diccionario con número de habitación como key y datos de la reserva.
    """
    if not os.path.exists(archivo_pasajeros):
        return {}
    
    df = pd.read_csv(archivo_pasajeros)
    habitaciones_futuras = {}
    fecha_hoy = datetime.now().strftime('%d/%m/%Y')
    
    for _, row in df.iterrows():
        fecha_ingreso = row['Fecha de ingreso']
        
        # Solo incluir si ingresa en el futuro (fecha ingreso > hoy)
        try:
            ingreso_dt = datetime.strptime(fecha_ingreso, '%d/%m/%Y')
            hoy_dt = datetime.strptime(fecha_hoy, '%d/%m/%Y')
            
            if ingreso_dt > hoy_dt:
                habitaciones_futuras[int(row['Nro. habitación'])] = {
                    'pasajero': row['Apellido y nombre'],
                    'plazas': int(row['Plazas ocupadas']),
                    'ingreso': row['Fecha de ingreso'],
                    'egreso': row['Fecha de egreso'],
                    'servicios': row['Servicios']
                }
        except:
            pass
    
    return habitaciones_futuras


def obtener_habitaciones_con_consumos(archivo_consumos='data/consumos_diarios.csv'):
    """
    Obtiene la lista de habitaciones que tienen consumos registrados.
    Retorna un set con los números de habitación.
    """
    if not os.path.exists(archivo_consumos):
        return set()
    
    df = pd.read_csv(archivo_consumos)
    return set(df['habitacion'].astype(int).unique())


def es_checkout_hoy(fecha_egreso):
    """
    Verifica si la fecha de egreso es hoy.
    Formato esperado: DD/MM/YYYY
    """
    try:
        fecha_hoy = datetime.now().strftime('%d/%m/%Y')
        return fecha_egreso == fecha_hoy
    except:
        return False


def obtener_habitaciones_checkout():
    """
    Obtiene las habitaciones con checkout programado para hoy.
    Retorna un set con los números de habitación.
    """
    habitaciones_ocupadas = obtener_habitaciones_ocupadas()
    checkouts_hoy = set()
    
    for num_hab, datos in habitaciones_ocupadas.items():
        if es_checkout_hoy(datos['egreso']):
            checkouts_hoy.add(num_hab)
    
    return checkouts_hoy


def calcular_estado_habitacion(num_habitacion, habitaciones_ocupadas, habitaciones_con_consumos, checkouts_hoy=None, habitaciones_reservadas=None):
    """
    Calcula el estado de una habitación según su ocupación y consumos.
    
    Retorna:
        - 'vacia': habitación no ocupada y sin reserva futura (gris)
        - 'reservada': reserva futura, aún no ingresó (gris con info de reserva)
        - 'ocupada': ocupada sin consumos (verde)
        - 'con_consumos': ocupada con consumos (naranja)
        - 'checkout': checkout programado para hoy (rojo)
    """
    # Prioridad 1: Check-out hoy (de habitaciones ocupadas)
    if checkouts_hoy and num_habitacion in checkouts_hoy:
        return 'checkout'
    
    # Prioridad 2: Habitación ocupada actualmente
    if num_habitacion in habitaciones_ocupadas:
        # Con consumos
        if num_habitacion in habitaciones_con_consumos:
            return 'con_consumos'
        # Sin consumos
        return 'ocupada'
    
    # Prioridad 3: Habitación con reserva futura
    if habitaciones_reservadas and num_habitacion in habitaciones_reservadas:
        return 'reservada'
    
    # Por defecto: vacía
    return 'vacia'


def obtener_datos_dashboard():
    """
    Obtiene todos los datos necesarios para renderizar el dashboard.
    
    Retorna un diccionario con:
        - pisos: estructura de habitaciones por piso
        - estados: estado de cada habitación
        - ocupadas: datos de habitaciones ocupadas
        - reservadas: datos de habitaciones con reserva futura
        - estadisticas: resumen general
        - checkouts_hoy: habitaciones con checkout hoy
    """
    habitaciones_ocupadas = obtener_habitaciones_ocupadas()
    habitaciones_reservadas = obtener_habitaciones_reservadas_futuras()
    habitaciones_con_consumos = obtener_habitaciones_con_consumos()
    checkouts_hoy = obtener_habitaciones_checkout()
    
    # Calcular estados de todas las habitaciones
    estados = {}
    for piso, habitaciones in PISOS.items():
        for num_hab in habitaciones:
            estados[num_hab] = calcular_estado_habitacion(
                num_hab, 
                habitaciones_ocupadas, 
                habitaciones_con_consumos,
                checkouts_hoy,
                habitaciones_reservadas
            )
    
    # Calcular estadísticas
    total_habitaciones = sum(len(habs) for habs in PISOS.values())
    total_ocupadas = len(habitaciones_ocupadas)
    total_reservadas = len(habitaciones_reservadas)
    total_con_consumos = len([h for h, e in estados.items() if e == 'con_consumos'])
    total_checkouts = len(checkouts_hoy)
    
    estadisticas = {
        'total': total_habitaciones,
        'ocupadas': total_ocupadas,
        'vacias': total_habitaciones - total_ocupadas - total_reservadas,
        'reservadas': total_reservadas,
        'con_consumos': total_con_consumos,
        'sin_consumos': total_ocupadas - total_con_consumos,
        'checkouts_hoy': total_checkouts
    }
    
    return {
        'pisos': PISOS,
        'estados': estados,
        'ocupadas': habitaciones_ocupadas,
        'reservadas': habitaciones_reservadas,
        'estadisticas': estadisticas,
        'checkouts_hoy': checkouts_hoy
    }


def obtener_total_consumos_habitacion(num_habitacion, archivo_consumos='data/consumos_diarios.csv'):
    """
    Calcula el total de consumos de una habitación específica.
    """
    if not os.path.exists(archivo_consumos):
        return 0
    
    df = pd.read_csv(archivo_consumos)
    consumos_hab = df[df['habitacion'] == num_habitacion]
    
    if consumos_hab.empty:
        return 0
    
    return consumos_hab['monto'].sum()
