import os
import requests
from flask import Flask

app = Flask(__name__)

# --- CONFIGURACIÓN ---
# Render leerá estas variables de entorno
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
TARGET_URL = os.environ.get('TARGET_URL')

def send_alert(message):
    """Envía un mensaje al grupo de Telegram."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Error: Faltan credenciales de Telegram")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"  # Para poder usar negritas si quieres
    }
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Error enviando a Telegram: {e}")

@app.route('/')
def home():
    return "El bot está vivo y esperando la orden del CronJob."

@app.route('/monitor')
def monitor():
    """Esta es la URL que visitará el cron-job cada 30 min."""
    if not TARGET_URL:
        return "No se ha configurado una URL objetivo.", 500

    print(f"Comprobando {TARGET_URL}...")
    
    try:
        # Hacemos la petición con un tiempo límite de 10 segundos
        response = requests.get(TARGET_URL, timeout=10)
        
        # Si el código es diferente a 200 (OK), es un problema
        if response.status_code != 200:
            mensaje = f"⚠️ *ALERTA*: La web {TARGET_URL} responde con error.\nEstado: {response.status_code}"
            send_alert(mensaje)
            return "Alerta enviada", 200
            
        return "Web Online. Todo correcto.", 200

    except Exception as e:
        # Si entra aquí es que la web está totalmente caída o no existe
        mensaje = f"🚨 *CRÍTICO*: No se puede conectar con {TARGET_URL}.\nError: {str(e)}"
        send_alert(mensaje)
        return "Error crítico detectado", 200

if __name__ == '__main__':
    app.run()
