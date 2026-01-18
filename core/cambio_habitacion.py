"""
Módulo para gestionar cambios de habitación por desperfectos o emergencias.
Permite mover un huésped de una habitación a otra manteniendo sus consumos.
"""

import pandas as pd
import os

DB_PASAJEROS = 'data/pasajeros.csv'
DB_CONSUMOS = 'data/consumos_diarios.csv'


def obtener_habitaciones_disponibles_para_cambio(habitacion_origen):
    """
    Obtiene las habitaciones disponibles para hacer un cambio,
    excluyendo la habitación actual del huésped.
    
    Args:
        habitacion_origen (int): Habitación actual del huésped
        
    Returns:
        list: Lista de habitaciones disponibles
    """
    from core.dashboard import PISOS, obtener_habitaciones_ocupadas
    
    # Todas las habitaciones del hotel
    todas_habitaciones = []
    for piso_habs in PISOS.values():
        todas_habitaciones.extend(piso_habs)
    
    # Habitaciones ocupadas
    ocupadas = obtener_habitaciones_ocupadas()
    
    # Retornar disponibles, excluyendo la habitación origen
    disponibles = [h for h in todas_habitaciones 
                   if h not in ocupadas.keys() and h != habitacion_origen]
    return sorted(disponibles)


def cambiar_habitacion(habitacion_origen, habitacion_destino, motivo=""):
    """
    Cambia un huésped de una habitación a otra.
    Actualiza el registro del pasajero y traslada todos sus consumos.
    
    Args:
        habitacion_origen (int): Habitación actual
        habitacion_destino (int): Nueva habitación
        motivo (str): Razón del cambio (opcional)
        
    Returns:
        tuple: (bool_exito, str_mensaje)
    """
    
    if not os.path.exists(DB_PASAJEROS):
        return False, "No existe el archivo de pasajeros"
    
    try:
        habitacion_origen = int(habitacion_origen)
        habitacion_destino = int(habitacion_destino)
    except:
        return False, "Números de habitación inválidos"
    
    if habitacion_origen == habitacion_destino:
        return False, "Las habitaciones origen y destino son iguales"
    
    try:
        # 1. Verificar que la habitación origen esté ocupada
        df_pasajeros = pd.read_csv(DB_PASAJEROS)
        pasajero_origen = df_pasajeros[df_pasajeros['Nro. habitación'] == habitacion_origen]
        
        if pasajero_origen.empty:
            return False, f"La habitación {habitacion_origen} no está ocupada"
        
        # 2. Verificar que la habitación destino esté disponible
        pasajero_destino = df_pasajeros[df_pasajeros['Nro. habitación'] == habitacion_destino]
        if not pasajero_destino.empty:
            return False, f"La habitación {habitacion_destino} ya está ocupada"
        
        # 3. Obtener datos del pasajero
        nombre_pasajero = pasajero_origen.iloc[0]['Apellido y nombre']
        
        # 4. Actualizar habitación en pasajeros.csv
        df_pasajeros.loc[df_pasajeros['Nro. habitación'] == habitacion_origen, 
                         'Nro. habitación'] = habitacion_destino
        
        # 5. Agregar observación si existe el campo
        if 'Observaciones' in df_pasajeros.columns:
            obs_actual = str(df_pasajeros.loc[df_pasajeros['Nro. habitación'] == habitacion_destino, 
                                              'Observaciones'].iloc[0])
            if pd.isna(obs_actual) or obs_actual == 'nan':
                obs_actual = ""
            
            nueva_obs = f"Cambio desde Hab {habitacion_origen}. Motivo: {motivo}" if motivo else f"Cambio desde Hab {habitacion_origen}"
            if obs_actual:
                nueva_obs = f"{obs_actual} | {nueva_obs}"
            
            df_pasajeros.loc[df_pasajeros['Nro. habitación'] == habitacion_destino, 
                            'Observaciones'] = nueva_obs
        
        df_pasajeros.to_csv(DB_PASAJEROS, index=False)
        
        # 6. Actualizar consumos si existen
        consumos_actualizados = 0
        if os.path.exists(DB_CONSUMOS):
            df_consumos = pd.read_csv(DB_CONSUMOS)
            consumos_habitacion = df_consumos[df_consumos['habitacion'] == habitacion_origen]
            
            if not consumos_habitacion.empty:
                df_consumos.loc[df_consumos['habitacion'] == habitacion_origen, 
                               'habitacion'] = habitacion_destino
                df_consumos.to_csv(DB_CONSUMOS, index=False)
                consumos_actualizados = len(consumos_habitacion)
        
        mensaje = f"Cambio exitoso: {nombre_pasajero} movido de habitación {habitacion_origen} → {habitacion_destino}"
        if consumos_actualizados > 0:
            mensaje += f" ({consumos_actualizados} consumo(s) trasladado(s))"
        
        return True, mensaje
        
    except Exception as e:
        return False, f"Error al cambiar habitación: {str(e)}"


def validar_cambio_habitacion(habitacion_origen, habitacion_destino):
    """
    Valida que el cambio de habitación sea posible.
    
    Returns:
        tuple: (bool_valido, str_error)
    """
    
    try:
        habitacion_origen = int(habitacion_origen)
        habitacion_destino = int(habitacion_destino)
    except:
        return False, "Números de habitación inválidos"
    
    if habitacion_origen == habitacion_destino:
        return False, "Debe seleccionar una habitación diferente"
    
    if not os.path.exists(DB_PASAJEROS):
        return False, "No existe el archivo de pasajeros"
    
    df_pasajeros = pd.read_csv(DB_PASAJEROS)
    
    # Verificar origen ocupada
    if df_pasajeros[df_pasajeros['Nro. habitación'] == habitacion_origen].empty:
        return False, f"La habitación {habitacion_origen} no está ocupada"
    
    # Verificar destino disponible
    if not df_pasajeros[df_pasajeros['Nro. habitación'] == habitacion_destino].empty:
        return False, f"La habitación {habitacion_destino} ya está ocupada"
    
    return True, ""
