import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
import matplotlib.dates as mdates
from datetime import datetime

# Colores estilo "Movistar"
COLOR_RELLENO = '#FF9900' # Naranja intenso
COLOR_BORDE = '#CC7A00'   # Naranja más oscuro
COLOR_GRID = '#E0E0E0'    # Gris muy suave

def create_chart(dates_list, values_list, title, is_daily_detail=False):
    """Genera el gráfico naranja genérico."""
    if not dates_list: return None

    # Configuración del lienzo
    plt.figure(figsize=(10, 5))
    ax = plt.gca()

    # 1. Dibujamos el ÁREA (Relleno)
    # alpha=0.6 le da esa transparencia elegante
    plt.fill_between(dates_list, values_list, color=COLOR_RELLENO, alpha=0.6)
    
    # 2. Dibujamos la LÍNEA superior (Borde)
    plt.plot(dates_list, values_list, color=COLOR_BORDE, linewidth=2)

    # 3. Línea discontinua de promedio (Opcional, como en tu foto)
    promedio = sum(values_list) / len(values_list)
    plt.axhline(y=promedio, color='gray', linestyle='--', alpha=0.7, linewidth=1, label=f'Media: {int(promedio)}ms')

    # Estética
    plt.title(title, fontsize=12, fontweight='bold', pad=15)
    plt.ylabel("Latencia (ms)")
    plt.grid(axis='y', color=COLOR_GRID, linestyle='-', linewidth=0.5)
    
    # Quitar bordes feos de la caja (arriba y derecha)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('gray')
    ax.spines['bottom'].set_color('gray')

    # Limite Y para que se vea bien (si hay error 999, que no aplaste el resto)
    max_val = max(values_list)
    if max_val > 900: 
        plt.ylim(0, 1000) # Si hay errores
    else:
        plt.ylim(0, max_val * 1.2) # Margen del 20% arriba

    plt.legend(frameon=False)
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close()
    return buf

# --- PUNTO DE ENTRADA GLOBAL ---
def generate_global_graph(data_rows):
    """Prepara datos para el gráfico de los últimos 7 días."""
    days = []
    avgs = []
    for row in data_rows:
        # row = ('2023-10-27', 145.5)
        # Convertimos a formato fecha corta "27 Oct"
        dt = datetime.strptime(row[0], "%Y-%m-%d")
        days.append(dt.strftime("%d/%m"))
        avgs.append(row[1])
    
    return create_chart(days, avgs, "Latencia Media - Últimos 7 Días")

# --- PUNTO DE ENTRADA DIARIO ---
def generate_day_graph(data_rows, date_str):
    """Prepara datos para el gráfico detallado de UN día."""
    hours = []
    latencies = []
    for row in data_rows:
        # row = ('2023-10-27 14:30:05', 200, 45.5)
        full_date = row[0]
        status = row[1]
        latency = row[2]
        
        # Extraemos solo la hora HH:MM
        time_str = full_date.split(" ")[1][:5]
        hours.append(time_str)
        
        # Si error, ponemos 999
        if status != 200: latencies.append(999)
        else: latencies.append(latency)

    return create_chart(hours, latencies, f"Detalle del día {date_str}", is_daily_detail=True)
