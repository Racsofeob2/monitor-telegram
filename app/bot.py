import os
import time
import json
import requests # Para la API de Telegram (no para la web objetivo)
from flask import Flask, request

# MOTOR DE NAVEGACIÓN (Bypass TLS)
from curl_cffi import requests as cffi_requests 

# IMPORTACIONES RELATIVAS
from . import db
from . import history

app = Flask(__name__)

# --- CONFIGURACIÓN ---
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
TARGET_URL = os.environ.get('TARGET_URL')

# VARIABLES DE EVASIÓN (Las que acabas de configurar)
MY_COOKIE = os.environ.get('WEB_COOKIE', '')
MY_AGENT = os.environ.get('USER_AGENT', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

# Inicializamos DB
db.init_db()

# --- FUNCIONES DE TELEGRAM (Sin cambios) ---
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

# --- LÓGICA DE MONITOREO (CLONACIÓN DE SESIÓN) ---
def check_website():
    if not TARGET_URL: return "⚠️ Sin URL Configurada"
    
    print(f"🔍 Entrando como CLON a: {TARGET_URL}")
    
    # Construimos las cabeceras exactas de tu navegador
    headers = {
        'User-Agent': MY_AGENT,      # Tu Chrome 144
        'Cookie': MY_COOKIE,         # Tu llave de acceso (cf_clearance)
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
        'Cache-Control': 'no-cache',
        'Upgrade-Insecure-Requests': '1'
    }
    
    params = {'nocache': time.time()}
    status = 0
    lat = 0
    msg_log = ""
    res = ""

    try:
        start = time.time()
        
        # Petición "Impersonate" + Cookies Inyectadas
        resp = cffi_requests.get(
            TARGET_URL, 
            params=params, 
            headers=headers,         # Aquí va tu identidad
            impersonate="chrome110", # Huella TLS base
            timeout=20,              
            verify=False             # Ignoramos error SSL de Render
        )
        
        lat = round((time.time() - start) * 1000, 0)
        status = resp.status_code
        
        if status == 200:
            msg_log = "Online"
            res = f"✅ Online: {lat}ms (Acceso Correcto)"
        elif status == 403:
            msg_log = "Cookie Expired"
            res = f"⛔ Acceso Denegado (403). La cookie ha caducado o Cloudflare detectó la IP."
        else:
            msg_log = f"HTTP {status}"
            res = f"⚠️ Respuesta: Código {status}"
            
    except Exception as e:
        status = 500
        lat = 999
        msg_log = str(e)
        res = f"🚨 Error Conexión: {str(e)}"

    db.insert_log(status, lat, msg_log)
    print(f"💾 Resultado: {status} - {lat}ms")
    return res

# --- RUTAS ---
@app.route('/monitor')
def monitor():
    res = check_website()
    if "✅" not in res:
        send_text(TELEGRAM_CHAT_ID, f"🤖 *Alerta:*\n{res}")
    return "OK", 200

@app.route('/webhook', methods=['POST'])
def webhook():
    update = request.get_json()
    
    # Callbacks (Botones)
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

    # Mensajes
    elif "message" in update and "text" in update["message"]:
        chat_id = update["message"]["chat"]["id"]
        text = update["message"]["text"]
        
        if "/start" in text:
            send_text(chat_id, "👋 *Panel Clon V7:*", buttons=True)
        elif "Comprobar" in text or "/check" in text:
            send_text(chat_id, "🕵️ Usando identidad robada...")
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
def home(): return "Bot Clon V7 Activo 🧬"
