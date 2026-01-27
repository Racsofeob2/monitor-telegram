import sqlite3
import os
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
DB_PATH = os.path.join(DATA_DIR, 'monitor_logs.db')

if not os.path.exists(DATA_DIR): os.makedirs(DATA_DIR)

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS history
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, status INTEGER, latency REAL, message TEXT)''')
    conn.commit()
    conn.close()

def insert_log(status, latency, message):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO history (date, status, latency, message) VALUES (?, ?, ?, ?)", (now, status, latency, message))
    
    # Limpieza: Borrar datos de más de 7 días
    limit = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
    c.execute("DELETE FROM history WHERE date < ?", (limit,))
    conn.commit()
    conn.close()

# --- NUEVAS FUNCIONES PARA EL GRÁFICO ---

def get_last_7_days_averages():
    """Devuelve la media por día para el gráfico Global."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Agrupamos por día (substr fecha, 1, 10)
    query = '''SELECT substr(date, 1, 10) as day, AVG(latency) FROM history 
               GROUP BY day ORDER BY day ASC LIMIT 7'''
    c.execute(query)
    rows = c.fetchall()
    conn.close()
    return rows

def get_logs_by_day(date_str):
    """Devuelve TODOS los datos de un día específico (ej: '2023-10-27')."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Buscamos fechas que empiecen por ese día
    c.execute("SELECT date, status, latency FROM history WHERE date LIKE ? ORDER BY date ASC", (f"{date_str}%",))
    rows = c.fetchall()
    conn.close()
    return rows

def get_available_dates():
    """Devuelve la lista de días únicos disponibles para los botones."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT DISTINCT substr(date, 1, 10) FROM history ORDER BY date ASC")
    rows = c.fetchall()
    conn.close()
    return [row[0] for row in rows] # Devuelve lista limpia ['2023-10-26', '2023-10-27']
