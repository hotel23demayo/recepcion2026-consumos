"""
Módulo para gestionar reservas express (walk-ins).
Permite registrar huéspedes sin reserva previa con estadía de 1 noche.
"""

from datetime import date, timedelta
import pandas as pd
import os

DB_PASAJEROS = 'data/pasajeros.csv'

def obtener_habitaciones_disponibles():
    """
    Retorna lista de habitaciones NO ocupadas actualmente.
    """
    from core.dashboard import PISOS, obtener_habitaciones_ocupadas
    
    # Todas las habitaciones del hotel
    todas_habitaciones = []
    for piso_habs in PISOS.values():
        todas_habitaciones.extend(piso_habs)
    
    # Habitaciones ocupadas
    ocupadas = obtener_habitaciones_ocupadas()
    
    # Retornar solo las disponibles
    disponibles = [h for h in todas_habitaciones if h not in ocupadas.keys()]
    return sorted(disponibles)


def crear_reserva_express(habitacion, nombre="Huésped sin reserva", pax=1, servicios="DESAYUNO"):
    """
    Crea una reserva mínima para walk-ins (1 noche).
    
    Args:
        habitacion (int): Número de habitación
        nombre (str): Nombre del huésped (opcional)
        pax (int): Cantidad de personas (1-4)
        servicios (str): Tipo de régimen (DESAYUNO, MEDIA PENSION, ALL INCLUSIVE)
    
    Returns:
        tuple: (dict_reserva, str_mensaje) 
               Si falla, retorna (None, str_error)
    """
    
    # Validar que la habitación esté disponible
    disponibles = obtener_habitaciones_disponibles()
    if int(habitacion) not in disponibles:
        return None, f"La habitación {habitacion} no está disponible"
    
    # Fechas: hoy y mañana
    hoy = date.today()
    manana = hoy + timedelta(days=1)
    
    # Crear registro compatible con pasajeros.csv
    nueva_reserva = {
        'Nro. habitación': int(habitacion),
        'Fecha de ingreso': hoy.strftime('%d/%m/%Y'),
        'Fecha de egreso': manana.strftime('%d/%m/%Y'),
        'Plazas ocupadas': int(pax),
        'Tipo documento': 'DNI',
        'Nro. doc.': '00000000',  # Documento genérico
        'Apellido y nombre': nombre,
        'Edad': 0,  # No requerido
        'Voucher': f'WALK-{habitacion}-{hoy.strftime("%d%m%Y")}',
        'Servicios': servicios,
        'Estado': 'Activo',
        'Paquete': 'Walk-in Express',
        'Sede': 'Principal'
    }
    
    try:
        # Agregar al CSV existente
        df_nuevo = pd.DataFrame([nueva_reserva])
        
        if os.path.exists(DB_PASAJEROS):
            df_existente = pd.read_csv(DB_PASAJEROS)
            
            # Verificar que no esté ocupada HOY (solo rechazar si ingreso <= hoy)
            habitaciones_hoy = df_existente[df_existente['Nro. habitación'] == int(habitacion)]
            for _, row in habitaciones_hoy.iterrows():
                from datetime import datetime
                try:
                    fecha_ingreso = datetime.strptime(row['Fecha de ingreso'], '%d/%m/%Y')
                    hoy_dt = datetime.combine(hoy, datetime.min.time())
                    
                    # Solo rechazar si la habitación ya está ocupada (ingreso <= hoy)
                    if fecha_ingreso <= hoy_dt:
                        return None, f"La habitación {habitacion} ya está ocupada hoy"
                except:
                    pass
            
            df_nuevo = pd.concat([df_existente, df_nuevo], ignore_index=True)
        
        # Guardar
        df_nuevo.to_csv(DB_PASAJEROS, index=False)
        
        return nueva_reserva, "Reserva express creada exitosamente"
        
    except Exception as e:
        return None, f"Error al crear reserva: {str(e)}"


def validar_datos_reserva(habitacion, nombre, pax):
    """
    Valida los datos antes de crear la reserva.
    
    Returns:
        tuple: (bool_valido, str_error)
    """
    
    # Validar habitación
    try:
        habitacion = int(habitacion)
    except:
        return False, "Número de habitación inválido"
    
    # Validar pax
    try:
        pax = int(pax)
        if pax < 1 or pax > 4:
            return False, "La cantidad de personas debe ser entre 1 y 4"
    except:
        return False, "Cantidad de personas inválida"
    
    # Validar nombre (opcional pero mínimo 2 caracteres)
    if nombre and len(nombre.strip()) < 2:
        return False, "El nombre debe tener al menos 2 caracteres"
    
    return True, ""