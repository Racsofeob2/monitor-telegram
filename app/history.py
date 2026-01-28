import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
import numpy as np # (Si no tienes numpy instalado, usamos listas nativas para no obligarte a instalar más cosas)

# Estilos
COLOR_RELLENO = '#FF9900'
COLOR_BORDE = '#CC7A00'
COLOR_GRID = '#EEEEEE'

def create_chart(dates_list, values_list, title, is_daily_detail=False):
    if not dates_list: return None

    # Configuración del lienzo
    plt.figure(figsize=(10, 5))
    ax = plt.gca()

    # --- LIMPIEZA DE DATOS ---
    # values_list puede traer 'None' donde hubo errores.
    # Para matplotlib, 'None' crea un hueco en la línea (perfecto para indicar caída).
    
    # 1. Dibujar: Matplotlib maneja los None automáticamente rompiendo la línea
    # Para el relleno (fill_between), necesitamos convertir None a 0 temporalmente o usar where
    # Truco: Usamos una lista limpia solo para el fill, pero la plot usa la original con huecos
    values_for_fill = [v if v is not None else 0 for v in values_list]
    
    # Dibujamos el área (suave)
    plt.fill_between(dates_list, values_for_fill, color=COLOR_RELLENO, alpha=0.5)
    
    # Dibujamos la línea (fuerte) con los huecos donde sea None
    plt.plot(dates_list, values_list, color=COLOR_BORDE, linewidth=2, marker='o', markersize=4)

    # 2. CÁLCULO DE MEDIA Y ESCALA (Solo con datos válidos)
    valid_values = [v for v in values_list if v is not None]
    
    if valid_values:
        # Media real (ignorando errores)
        promedio = sum(valid_values) / len(valid_values)
        plt.axhline(y=promedio, color='gray', linestyle='--', alpha=0.7, label=f'Promedio Real: {int(promedio)}ms')
        plt.legend(frameon=False)
        
        # Escala Inteligente (Auto-Zoom)
        # Ajustamos el techo al máximo valor REAL + 25% de aire
        max_val = max(valid_values)
        # Si la latencia es muy baja (ej: 20ms), forzamos mínimo 100ms para que se vea bien
        plt.ylim(0, max(max_val * 1.25, 100))
    else:
        # Si todo son errores, escala por defecto
        plt.ylim(0, 100)

    # Estética
    plt.title(title, fontsize=12, fontweight='bold', pad=15)
    plt.ylabel("Latencia (ms)")
    plt.grid(axis='y', color=COLOR_GRID, linestyle='-', linewidth=0.5)
    
    # Bordes limpios
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#888888')
    ax.spines['bottom'].set_color('#888888')

    # Ajustes del eje X para el detalle diario
    if is_daily_detail:
        plt.xticks(rotation=45, ha='right')
        # Si hay demasiados datos, ocultamos algunas etiquetas para que no se amontonen
        if len(dates_list) > 10:
            for index, label in enumerate(ax.xaxis.get_ticklabels()):
                if index % (len(dates_list) // 8) != 0:
                    label.set_visible(False)

    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close()
    return buf

# --- PUNTOS DE ENTRADA ---

def generate_global_graph(data_rows):
    """Gráfico Semanal."""
    days = []
    avgs = []
    for row in data_rows:
        # row = ('2023-01-01', 150.5)
        # Convertimos fecha a formato corto "01/01"
        try:
            from datetime import datetime
            dt = datetime.strptime(row[0], "%Y-%m-%d")
            days.append(dt.strftime("%d/%m"))
        except:
            days.append(row[0])
        avgs.append(row[1])
    
    return create_chart(days, avgs, "Latencia Media - Últimos 7 Días")

def generate_day_graph(data_rows, date_str):
    """Gráfico Diario (Detalle)."""
    hours = []
    latencies = []
    
    for row in data_rows:
        # row = ('2023-01-01 14:30:00', status, latency)
        full_date = row[0]
        status = row[1]
        latency = row[2]
        
        # Extraemos hora HH:MM
        time_str = full_date.split(" ")[1][:5] 
        hours.append(time_str)
        
        # FILTRO CLAVE:
        # Solo consideramos latencia válida si el status es bueno (200, 403, 429).
        # Si es error (500, 0, Timeout), pasamos 'None'.
        # Esto hace que el gráfico muestre un hueco en vez de bajar a 0.
        if status in [200, 403, 429]:
            latencies.append(latency)
        else:
            latencies.append(None) # <--- ESTO ARREGLA LA MEDIA Y LA ESCALA

    return create_chart(hours, latencies, f"Detalle del día {date_str}", is_daily_detail=True)
