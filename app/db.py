import sqlite3
import os
from datetime import datetime

# Construimos la ruta absoluta para evitar errores de "archivo no encontrado"
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
DB_PATH = os.path.join(DATA_DIR, 'monitor_logs.db')

# Aseguramos que la carpeta data exista
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

def init_db():
    """Inicializa la tabla si no existe."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS history
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  date TEXT, 
                  status INTEGER, 
                  latency REAL, 
                  message TEXT)''')
    conn.commit()
    conn.close()

def insert_log(status_code, latency, message):
    """Guarda un nuevo registro."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO history (date, status, latency, message) VALUES (?, ?, ?, ?)",
              (now, status_code, latency, message))
    conn.commit()
    conn.close()

def get_recent_logs(limit=15):
    """Recupera los últimos registros para el gráfico."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(f"SELECT date, status, latency FROM history ORDER BY id DESC LIMIT {limit}")
    rows = c.fetchall()
    conn.close()
    return rows
