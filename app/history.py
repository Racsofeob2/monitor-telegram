import matplotlib
# Configuración OBLIGATORIA para servidores sin pantalla (Render)
matplotlib.use('Agg') 
import matplotlib.pyplot as plt
import io
# Importamos el módulo vecino db usando punto (.)
from . import db

def generate_graph_buffer(target_name="Web"):
    """Pide datos a la DB y devuelve una imagen en memoria."""
    
    rows = db.get_recent_logs(limit=15)

    if not rows:
        return None

    rows.reverse() # Ordenamos cronológicamente

    horas = []
    latencias = []
    colores = []

    for row in rows:
        fecha, status, latencia = row
        # Tomamos solo la hora HH:MM
        horas.append(fecha.split(" ")[1][:5])
        
        if status != 200:
            latencias.append(999) # Pico rojo si hay error
            colores.append('red')
        else:
            latencias.append(latencia)
            colores.append('green')

    # Crear gráfico
    plt.figure(figsize=(10, 5))
    plt.plot(horas, latencias, color='gray', linestyle='--', alpha=0.5)
    plt.scatter(horas, latencias, c=colores, s=100, zorder=5)

    plt.title(f"Latencia: {target_name} (ms)")
    plt.ylabel("Milisegundos (999 = Error)")
    plt.xlabel("Hora (UTC)")
    plt.grid(True, linestyle='--', alpha=0.5)
    plt.tight_layout()
    
    # Guardar en memoria RAM
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close() # Liberar memoria
    
    return buf
