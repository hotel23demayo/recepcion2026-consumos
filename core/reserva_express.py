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


def crear_reserva_express(habitacion, nombre="Huésped sin reserva", pax=1, servicios="DESAYUNO", noches=1):
    """
    Crea una reserva mínima para walk-ins con 1 o más noches.
    
    Args:
        habitacion (int): Número de habitación
        nombre (str): Nombre del huésped (opcional)
        pax (int): Cantidad de personas (1-4)
        servicios (str): Tipo de régimen (DESAYUNO, MEDIA PENSION, ALL INCLUSIVE)
        noches (int): Cantidad de noches (por defecto 1)
    
    Returns:
        tuple: (dict_reserva, str_mensaje) 
               Si falla, retorna (None, str_error)
    """
    from datetime import datetime
    
    # Validar que la habitación esté disponible
    disponibles = obtener_habitaciones_disponibles()
    if int(habitacion) not in disponibles:
        return None, f"La habitación {habitacion} no está disponible"
    
    # Validar cantidad de noches
    try:
        noches = int(noches)
        if noches < 1 or noches > 30:
            return None, "La cantidad de noches debe ser entre 1 y 30"
    except:
        return None, "Cantidad de noches inválida"
    
    # Fechas: hoy y según las noches solicitadas
    hoy = date.today()
    fecha_salida = hoy + timedelta(days=noches)
    
    # Verificar que no haya conflicto con reservas futuras
    if os.path.exists(DB_PASAJEROS):
        df_existente = pd.read_csv(DB_PASAJEROS)
        habitaciones_futuras = df_existente[df_existente['Nro. habitación'] == int(habitacion)]
        
        for _, row in habitaciones_futuras.iterrows():
            try:
                fecha_ingreso_futura = datetime.strptime(row['Fecha de ingreso'], '%d/%m/%Y').date()
                
                # Si hay una reserva futura que ingresa ANTES de nuestra fecha de salida
                if fecha_ingreso_futura < fecha_salida:
                    max_noches = (fecha_ingreso_futura - hoy).days
                    if max_noches <= 0:
                        return None, f"La habitación {habitacion} ya está ocupada"
                    return None, f"La habitación {habitacion} tiene una reserva el {fecha_ingreso_futura.strftime('%d/%m/%Y')}. Máximo {max_noches} noche(s) disponible(s)"
            except:
                pass
    
    # Crear registro compatible con pasajeros.csv
    nueva_reserva = {
        'Nro. habitación': int(habitacion),
        'Fecha de ingreso': hoy.strftime('%d/%m/%Y'),
        'Fecha de egreso': fecha_salida.strftime('%d/%m/%Y'),
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


def calcular_noches_maximas(habitacion):
    """
    Calcula cuántas noches máximo se puede reservar una habitación
    antes de que haya un conflicto con una reserva futura.
    
    Returns:
        int: Cantidad máxima de noches disponibles (0 si no hay límite conocido)
    """
    from datetime import datetime
    
    if not os.path.exists(DB_PASAJEROS):
        return 0  # Sin límite conocido
    
    try:
        df = pd.read_csv(DB_PASAJEROS)
        habitaciones_futuras = df[df['Nro. habitación'] == int(habitacion)]
        
        hoy = date.today()
        min_dias = None
        
        for _, row in habitaciones_futuras.iterrows():
            try:
                fecha_ingreso = datetime.strptime(row['Fecha de ingreso'], '%d/%m/%Y').date()
                if fecha_ingreso > hoy:
                    dias = (fecha_ingreso - hoy).days
                    if min_dias is None or dias < min_dias:
                        min_dias = dias
            except:
                pass
        
        return min_dias if min_dias else 0
    except:
        return 0


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