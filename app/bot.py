import os
import requests
import urllib3
import time
import json
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

# Inicializamos la DB
db.init_db()

# --- FUNCIONES DE ENVÍO ---
def send_text(chat_id, text, buttons=False):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    if buttons:
        payload["reply_markup"] = {
            "keyboard": [[{"text": "🔍 Comprobar"}, {"text": "📊 Gráfico"}]],
            "resize_keyboard": True, "one_time_keyboard": False
        }
    try: requests.post(url, json=payload)
    except Exception as e: print(f"Error texto: {e}")

def send_photo_with_buttons(chat_id, photo_buf, caption, buttons_dates=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    reply_markup = {}
    if buttons_dates:
        inline_keyboard = []
        row = []
        for date in buttons_dates:
            btn = {"text": f"📅 {date}", "callback_data": f"ver_{date}"}
            row.append(btn)
            if len(row) == 2:
                inline_keyboard.append(row)
                row = []
        if row: inline_keyboard.append(row)
        reply_markup = {"inline_keyboard": inline_keyboard}

    data = {'chat_id': chat_id, 'caption': caption, 'reply_markup': json.dumps(reply_markup)}
    files = {'photo': ('chart.png', photo_buf, 'image/png')}
    try: requests.post(url, data=data, files=files)
    except Exception as e: print(f"Error foto: {e}")

# --- LÓGICA PRAGMÁTICA (403 = ONLINE) ---
def check_website():
    if not TARGET_URL: return "⚠️ Sin URL Configurada"
    
    # Cabeceras estándar
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Cache-Control': 'no-cache'
    }
    
    params = {'nocache': time.time()}
    status = 0
    lat = 0
    msg_log = ""
    res = ""

    try:
        start = time.time()
        # Timeout corto (10s) para máxima eficiencia
        resp = requests.get(TARGET_URL, headers=headers, params=params, timeout=10, verify=False)
        
        lat = round((time.time() - start) * 1000, 0)
        status = resp.status_code
        
        # --- INTERPRETACIÓN INTELIGENTE ---
        if status == 200:
            msg_log = "Online"
            res = f"✅ Online: {lat}ms"
            
        elif status == 403 or status == 429:
            # MAGIA: El firewall nos bloquea, PERO el servidor responde.
            # Por tanto: LA WEB ESTÁ VIVA.
            msg_log = "Online (WAF)"
            res = f"🛡️ Online (Protegido): {lat}ms"
            
            # TRUCO PARA EL GRÁFICO:
            # Si guardamos un 403, el gráfico se verá rojo? 
            # Si quieres que el gráfico se vea "sano", en la DB el status importa menos que la latencia.
            # El código del gráfico usa la latencia.
            
        elif status >= 500:
            msg_log = f"Server Error {status}"
            res = f"🔥 Error Servidor: {status}"
        else:
            msg_log = f"HTTP {status}"
            res = f"⚠️ Estado: {status}"
            
    except Exception as e:
        status = 500
        lat = 999
        msg_log = str(e)
        res = f"🚨 Caída/Error: {str(e)}"

    # Guardamos en DB
    db.insert_log(status, lat, msg_log)
    return res

# --- RUTAS ---
@app.route('/monitor')
def monitor():
    res = check_website()
    # Solo enviamos alerta automática si NO es Online (ni verde ni escudo)
    if "✅" not in res and "🛡️" not in res:
        send_text(TELEGRAM_CHAT_ID, f"🤖 *Alerta Caída:*\n{res}")
    return "OK", 200

@app.route('/webhook', methods=['POST'])
def webhook():
    update = request.get_json()
    
    if "callback_query" in update:
        cb = update["callback_query"]
        chat_id = cb["message"]["chat"]["id"]
        data = cb["data"]
        try: requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/answerCallbackQuery", json={"callback_query_id": cb["id"]})
        except: pass

        if data.startswith("ver_"):
            date = data.replace("ver_", "")
            rows = db.get_logs_by_day(date)
            if rows:
                img = history.generate_day_graph(rows, date)
                send_photo_with_buttons(chat_id, img, f"🔎 Detalle: {date}")
            else: send_text(chat_id, "⚠️ Sin datos.")

    elif "message" in update and "text" in update["message"]:
        chat_id = update["message"]["chat"]["id"]
        text = update["message"]["text"]
        
        if "/start" in text:
            send_text(chat_id, "👋 *Panel Estable:*", buttons=True)
        elif "Comprobar" in text or "/check" in text:
            send_text(chat_id, "📡 Conectando...")
            send_text(chat_id, check_website(), buttons=True)
        elif "Gráfico" in text or "/history" in text:
             rows = db.get_last_7_days_averages()
             dates = db.get_available_dates()
             if rows:
                img = history.generate_global_graph(rows)
                send_photo_with_buttons(chat_id, img, "📊 Semanal", buttons_dates=dates)
             else: send_text(chat_id, "📭 Sin datos.")

    return "OK", 200

@app.route('/')
def home():
    return "Bot Monitor Estable Activo 🛡️"
