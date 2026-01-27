import os
import requests
import urllib3
import time
from flask import Flask, request

# --- IMPORTACIONES RELATIVAS ---
from . import db
from . import history

# Configuración SSL y Flask
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
app = Flask(__name__)

# --- CONFIGURACIÓN ---
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
TARGET_URL = os.environ.get('TARGET_URL')

# Inicializamos la DB al arrancar la app
db.init_db()

# --- FUNCIONES AUXILIARES ---
def send_text(chat_id, text, buttons=False):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    if buttons:
        payload["reply_markup"] = {
            "keyboard": [[{"text": "🔍 Comprobar"}, {"text": "📊 Gráfico"}]],
            "resize_keyboard": True
        }
    try: requests.post(url, json=payload)
    except Exception as e: print(f"Error texto: {e}")

def send_photo(chat_id, photo_buf):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    files = {'photo': ('grafico.png', photo_buf, 'image/png')}
    payload = {'chat_id': chat_id, 'reply_markup': '{"keyboard": [[{"text": "🔍 Comprobar"}, {"text": "📊 Gráfico"}]], "resize_keyboard": true}'}
    try: requests.post(url, data=payload, files=files)
    except Exception as e: print(f"Error foto: {e}")

# --- LÓGICA DE MONITOREO ---
def check_website():
    if not TARGET_URL: return "⚠️ Sin URL Configurada"
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    params = {'nocache': time.time()}
    
    try:
        start = time.time()
        # verify=False para evitar errores SSL locales
        resp = requests.get(TARGET_URL, headers=headers, params=params, timeout=10, verify=False)
        lat = round((time.time() - start) * 1000, 0)
        status = resp.status_code
        
        msg_log = "Online" if status == 200 else f"HTTP {status}"
        res = f"✅ Online: {lat}ms" if status == 200 else f"⚠️ Error HTTP {status}"
        
    except Exception as e:
        status = 500
        lat = 999
        msg_log = str(e)
        res = f"🚨 Caída Crítica: {str(e)}"

    # Guardar en DB
    db.insert_log(status, lat, msg_log)
    return res

# --- RUTAS ---
@app.route('/monitor')
def monitor():
    res = check_website()
    if "✅" not in res:
        send_text(TELEGRAM_CHAT_ID, f"🤖 *Alerta Auto:*\n{res}")
    return "OK", 200

@app.route('/webhook', methods=['POST'])
def webhook():
    update = request.get_json()
    if "message" in update and "text" in update["message"]:
        chat_id = update["message"]["chat"]["id"]
        text = update["message"]["text"]
        
        if "/start" in text:
            send_text(chat_id, "👋 *Panel de Control:*", buttons=True)
        elif "Comprobar" in text or "/check" in text:
            send_text(chat_id, "⏳ Midiendo...")
            send_text(chat_id, check_website(), buttons=True)
        elif "Gráfico" in text or "/history" in text:
            send_text(chat_id, "🎨 Generando gráfico...")
            img = history.generate_graph_buffer(TARGET_URL)
            if img:
                send_photo(chat_id, img)
            else:
                send_text(chat_id, "📭 Aún no hay datos suficientes.")
            
    return "OK", 200

@app.route('/')
def home():
    return "Bot Modular V4 Activo 🚀"
