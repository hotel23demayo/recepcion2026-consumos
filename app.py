from flask import Flask, render_template, request, redirect, flash, send_file
import pandas as pd
import os
from datetime import datetime
import sys

app = Flask(__name__)
app.secret_key = 'temporada_2026_recepcion_key_secreta'

# Archivos de datos
DB_PASAJEROS = 'pasajeros.csv'
DB_CONSUMOS = 'consumos_diarios.csv'

def validar_pasajero(habitacion):
    """
    Verifica que la habitación exista en el CSV de pasajeros activos.
    Retorna el nombre del pasajero si existe, None si no.
    """
    if not os.path.exists(DB_PASAJEROS):
        return None
    
    df_pasajeros = pd.read_csv(DB_PASAJEROS)
    pasajero = df_pasajeros[df_pasajeros['Nro. habitación'] == int(habitacion)]
    
    if pasajero.empty:
        return None
    
    return pasajero.iloc[0]['Apellido y nombre']

@app.route('/')
def index():
    """Página principal con el formulario de carga"""
    return render_template('formulario.html')

@app.route('/cargar', methods=['POST'])
def cargar_consumo():
    """Procesar el registro de un consumo"""
    habitacion = request.form.get('habitacion')
    categoria = request.form.get('categoria')
    monto = request.form.get('monto')
    
    # Validación básica
    if not habitacion or not categoria or not monto:
        flash('Todos los campos son obligatorios', 'danger')
        return redirect('/')
    
    # Validar que el pasajero exista
    nombre_pasajero = validar_pasajero(habitacion)
    if not nombre_pasajero:
        flash(f'❌ La habitación {habitacion} no está registrada en el sistema', 'danger')
        return redirect('/')
    
    # Registrar el consumo
    nuevo_registro = {
        'fecha': datetime.now().strftime('%d/%m/%Y %H:%M'),
        'habitacion': habitacion,
        'pasajero': nombre_pasajero,
        'categoria': categoria,
        'monto': float(monto)
    }
    
    # Guardar en el CSV
    df_nuevo = pd.DataFrame([nuevo_registro])
    
    if os.path.exists(DB_CONSUMOS):
        df_nuevo.to_csv(DB_CONSUMOS, mode='a', header=False, index=False)
    else:
        df_nuevo.to_csv(DB_CONSUMOS, mode='w', header=True, index=False)
    
    flash(f'✅ Consumo registrado: {categoria} - ${monto} para {nombre_pasajero} (Hab. {habitacion})', 'success')
    return redirect('/')

@app.route('/cierre-dia')
def cierre_dia():
    """Generar archivo de consulta de consumos agrupados por categoría (CSV)"""
    if not os.path.exists(DB_CONSUMOS):
        flash("No hay consumos registrados para realizar el cierre.", "warning")
        return redirect('/')

    # 1. Leer los consumos registrados
    df = pd.read_csv(DB_CONSUMOS)

    # 2. Pivotear datos: Habitaciones como filas, solo 3 categorías como columnas
    tabla_cierre = df.pivot_table(
        index=['habitacion', 'pasajero'], 
        columns='categoria', 
        values='monto', 
        aggfunc='sum', 
        fill_value=0
    )
    
    # 3. Asegurar que existan las 3 columnas principales
    for col in ['Bebidas', 'Estadía', 'Map']:
        if col not in tabla_cierre.columns:
            tabla_cierre[col] = 0
    
    # 4. Seleccionar solo las columnas que nos interesan
    columnas_orden = ['Bebidas', 'Estadía', 'Map']
    tabla_cierre = tabla_cierre[columnas_orden]

    # 5. Calcular el total acumulado por habitación
    tabla_cierre['TOTAL_GENERAL'] = tabla_cierre.sum(axis=1)

    # 6. Guardar temporalmente para la descarga
    archivo_salida = 'consulta_consumos.csv'
    tabla_cierre.to_csv(archivo_salida)

    return send_file(archivo_salida, as_attachment=True, download_name=f"consulta_consumos_{datetime.now().strftime('%d-%m-%Y')}.csv")

@app.route('/cierre-xlsx')
def cierre_xlsx():
    """Generar archivo de salidas en formato XLSX (Excel) - Cada categoría en su columna"""
    if not os.path.exists(DB_CONSUMOS):
        flash("No hay consumos registrados para generar el archivo de salidas.", "warning")
        return redirect('/')
    
    try:
        # Leer consumos
        df_consumos = pd.read_csv(DB_CONSUMOS)
        
        # Crear tabla pivote: habitaciones en filas, categorías en columnas
        tabla_pivot = df_consumos.pivot_table(
            index=['habitacion', 'pasajero'],
            columns='categoria',
            values='monto',
            aggfunc='sum',
            fill_value=0
        ).reset_index()
        
        # Asegurar que existan todas las columnas (aunque estén vacías)
        for col in ['Estadía', 'Map', 'Bebidas']:
            if col not in tabla_pivot.columns:
                tabla_pivot[col] = 0
        
        # Calcular total por habitación
        tabla_pivot['Total'] = tabla_pivot['Estadía'] + tabla_pivot['Map'] + tabla_pivot['Bebidas']
        
        # Crear estructura del archivo (replica salidas.xlsx)
        max_filas = 30
        data = [[None] * 6 for _ in range(max_filas)]
        
        # Fila 0: Título
        data[0] = ['Pase de caja e información a turno mañana', None, None, None, None, None]
        data[2] = [None, None, 'Turno:   00 A 08 HS', None, None, None]
        data[3] = [None, None, None, None, f'Fecha: {datetime.now().strftime("%Y-%m-%d")}', None]
        data[4] = ['Detalle a cobrar de habitaciones con salida', None, None, None, None, None]
        data[5] = ['HAB', 'Estadía', 'Map', 'Bebidas', 'Forma de pago', 'Total']
        data[6] = [None, None, None, None, None, None]
        
        # Datos de habitaciones - Cada categoría en su columna
        fila_actual = 7
        for idx, row in tabla_pivot.iterrows():
            habitacion = row['habitacion']
            estadia = row['Estadía'] if row['Estadía'] > 0 else None
            map_val = row['Map'] if row['Map'] > 0 else None
            bebidas = row['Bebidas'] if row['Bebidas'] > 0 else None
            total = row['Total']
            
            # Distribuir valores en sus respectivas columnas
            data[fila_actual] = [
                int(habitacion),  # HAB (col 0)
                estadia,          # Estadía (col 1)
                map_val,          # Map (col 2)
                bebidas,          # Bebidas (col 3)
                None,             # Forma de pago (col 4)
                total             # Total (col 5)
            ]
            fila_actual += 1
        
        # Rellenar filas vacías
        for i in range(fila_actual, max_filas):
            data[i] = [None, None, None, None, None, 0.0]
        
        # Guardar como XLSX
        df_salidas = pd.DataFrame(data)
        archivo_salida = f'salidas_{datetime.now().strftime("%d-%m-%Y")}.xlsx'
        df_salidas.to_excel(archivo_salida, engine='openpyxl', index=False, header=False)
        
        return send_file(archivo_salida, as_attachment=True)
        
    except Exception as e:
        flash(f"Error al generar archivo Excel: {str(e)}", "danger")
        return redirect('/')

@app.route('/ver-consumos')
def ver_consumos():
    """Vista de todos los consumos registrados con opción de eliminar"""
    if not os.path.exists(DB_CONSUMOS):
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
            <title>Consumos Registrados</title>
        </head>
        <body>
            <div class="container mt-5">
                <div class="alert alert-info">
                    <h3>No hay consumos registrados aún</h3>
                </div>
                <a href="/" class="btn btn-primary">Volver al Formulario</a>
            </div>
        </body>
        </html>
        """
    
    df = pd.read_csv(DB_CONSUMOS)
    
    # Construir tabla HTML con botón de eliminar
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <title>Consumos Registrados</title>
        <script>
            function confirmarEliminacion(indice) {
                if (confirm('¿Estás seguro de eliminar este consumo?\\nEsta acción no se puede deshacer.')) {
                    window.location.href = '/eliminar-consumo/' + indice;
                }
            }
        </script>
        <style>
            .btn-eliminar { font-size: 0.8rem; padding: 0.25rem 0.5rem; }
        </style>
    </head>
    <body>
        <div class="container mt-5">
            <h2>Historial de Consumos</h2>
            <p class="text-muted">Total de registros: """ + str(len(df)) + """</p>
            
            <div class="table-responsive">
                <table class="table table-striped table-hover">
                    <thead class="table-dark">
                        <tr>
                            <th>#</th>
                            <th>Fecha</th>
                            <th>Habitación</th>
                            <th>Pasajero</th>
                            <th>Categoría</th>
                            <th>Monto</th>
                            <th>Acción</th>
                        </tr>
                    </thead>
                    <tbody>
    """
    
    for idx, row in df.iterrows():
        html += f"""
                        <tr>
                            <td>{idx + 1}</td>
                            <td>{row['fecha']}</td>
                            <td>{row['habitacion']}</td>
                            <td>{row['pasajero']}</td>
                            <td><span class="badge bg-primary">{row['categoria']}</span></td>
                            <td>${row['monto']:.2f}</td>
                            <td>
                                <button onclick="confirmarEliminacion({idx})" class="btn btn-danger btn-sm btn-eliminar">
                                    🗑️ Eliminar
                                </button>
                            </td>
                        </tr>
        """
    
    html += """
                    </tbody>
                </table>
            </div>
            
            <div class="mt-4">
                <a href="/" class="btn btn-primary">Volver al Formulario</a>
                <a href="/cierre-dia" class="btn btn-secondary">Descargar CSV</a>
                <a href="/cierre-xlsx" class="btn btn-success">Descargar Excel</a>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html

@app.route('/eliminar-consumo/<int:indice>')
def eliminar_consumo(indice):
    """Eliminar un consumo específico por su índice"""
    if not os.path.exists(DB_CONSUMOS):
        flash('No hay consumos para eliminar', 'warning')
        return redirect('/ver-consumos')
    
    try:
        # Leer el archivo
        df = pd.read_csv(DB_CONSUMOS)
        
        # Verificar que el índice existe
        if indice < 0 or indice >= len(df):
            flash(f'❌ Índice inválido: {indice}', 'danger')
            return redirect('/ver-consumos')
        
        # Guardar información del consumo eliminado para mostrar
        consumo_eliminado = df.iloc[indice]
        info = f"Hab {consumo_eliminado['habitacion']} - {consumo_eliminado['categoria']} - ${consumo_eliminado['monto']}"
        
        # Eliminar la fila
        df = df.drop(indice)
        
        # Guardar el archivo actualizado
        df.to_csv(DB_CONSUMOS, index=False)
        
        flash(f'✅ Consumo eliminado correctamente: {info}', 'success')
        
    except Exception as e:
        flash(f'❌ Error al eliminar consumo: {str(e)}', 'danger')
    
    return redirect('/ver-consumos')

@app.route('/reiniciar-temporada', methods=['GET', 'POST'])
def reiniciar_temporada():
    """Archivar consumos actuales e iniciar nueva temporada de 5 días"""
    
    if request.method == 'GET':
        # Mostrar página de confirmación
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
            <title>Reiniciar Temporada</title>
        </head>
        <body>
            <div class="container mt-5">
                <div class="card border-warning">
                    <div class="card-header bg-warning text-dark">
                        <h3>⚠️ Reiniciar Temporada</h3>
                    </div>
                    <div class="card-body">
                        <p class="lead">Esta acción archivará todos los consumos actuales y dejará el sistema en cero para una nueva temporada.</p>
                        <hr>
                        <p><strong>¿Qué sucederá?</strong></p>
                        <ul>
                            <li>Se creará un archivo de respaldo: <code>consumos_diarios_BACKUP_DD-MM-YYYY_HH-MM.csv</code></li>
                            <li>El archivo <code>consumos_diarios.csv</code> se reiniciará vacío</li>
                            <li>Las nuevas 40 habitaciones podrán empezar con cuenta en cero</li>
                        </ul>
                        <hr>
                        <form method="POST" action="/reiniciar-temporada">
                            <button type="submit" class="btn btn-danger btn-lg">🔄 Confirmar Reinicio de Temporada</button>
                            <a href="/" class="btn btn-secondary btn-lg">❌ Cancelar</a>
                        </form>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
    
    # POST: Ejecutar el reinicio
    if not os.path.exists(DB_CONSUMOS):
        flash("No hay consumos para archivar. El sistema ya está limpio.", "info")
        return redirect('/')
    
    try:
        # Crear nombre de archivo de backup con timestamp
        timestamp = datetime.now().strftime('%d-%m-%Y_%H-%M')
        archivo_backup = f'consumos_diarios_BACKUP_{timestamp}.csv'
        
        # Copiar el archivo actual al backup
        import shutil
        shutil.copy(DB_CONSUMOS, archivo_backup)
        
        # Reiniciar el archivo de consumos
        with open(DB_CONSUMOS, 'w', encoding='utf-8') as f:
            f.write('fecha,habitacion,pasajero,categoria,monto\n')
        
        flash(f'✅ Temporada reiniciada correctamente. Backup guardado en: {archivo_backup}', 'success')
        return redirect('/')
        
    except Exception as e:
        flash(f'❌ Error al reiniciar temporada: {str(e)}', 'danger')
        return redirect('/')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)