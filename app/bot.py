import os
import requests # Para hablar con Telegram
import urllib3
import time
import json
from flask import Flask, request

# --- NUEVO MOTOR: CURL_CFFI (El "Impostor" de Chrome) ---
from curl_cffi import requests as cffi_requests

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

# --- FUNCIONES DE ENVÍO (Telegram API usa requests normal) ---

def send_text(chat_id, text, buttons=False):
    """Envía mensajes de texto con el menú principal inferior."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    
    if buttons:
        payload["reply_markup"] = {
            "keyboard": [[{"text": "🔍 Comprobar"}, {"text": "📊 Gráfico"}]],
            "resize_keyboard": True,
            "one_time_keyboard": False
        }
    try: requests.post(url, json=payload)
    except Exception as e: print(f"Error texto: {e}")

def send_photo_with_buttons(chat_id, photo_buf, caption, buttons_dates=None):
    """Envía la foto con botones INLINE."""
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

    data = {
        'chat_id': chat_id, 
        'caption': caption, 
        'reply_markup': json.dumps(reply_markup)
    }
    files = {'photo': ('chart.png', photo_buf, 'image/png')}
    
    try: requests.post(url, data=data, files=files)
    except Exception as e: print(f"Error foto: {e}")

# --- LÓGICA DE MONITOREO REAL (Bypass TLS con Curl-CFFI) ---
def check_website():
    if not TARGET_URL: return "⚠️ Sin URL Configurada"
    
    print(f"🔍 Iniciando chequeo REAL de: {TARGET_URL}") # LOG
    
    # Truco anti-caché
    params = {'nocache': time.time()}
    
    status = 0
    lat = 0
    msg_log = ""
    res = ""

    try:
        start = time.time()
        
        # USAMOS EL MOTOR IMPERSONATE (Simula ser Chrome 110)
        # Esto engaña al firewall para que crea que somos un humano
        resp = cffi_requests.get(
            TARGET_URL, 
            params=params, 
            impersonate="chrome110", 
            timeout=15
        )
        
        # Calculamos latencia real
        lat = round((time.time() - start) * 1000, 0)
        status = resp.status_code
        
        # Interpretación de resultados
        if status == 200:
            msg_log = "Online"
            res = f"✅ Online: {lat}ms"
        elif status == 403:
            msg_log = "Blocked 403"
            res = f"⛔ Acceso Denegado (403). La web detectó la IP de Render."
        elif status == 429:
            msg_log = "Rate Limit 429"
            res = f"⚠️ Demasiadas peticiones (429)."
        else:
            msg_log = f"HTTP {status}"
            res = f"⚠️ Error HTTP {status}"
            
    except Exception as e:
        # Captura errores de conexión (DNS, Timeout real, Caída)
        status = 500
        lat = 999
        msg_log = str(e)
        res = f"🚨 Error de Conexión: {str(e)}"

    # Guardar en DB
    db.insert_log(status, lat, msg_log)
    print(f"💾 Guardado: {res}")
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
    
    # --- CASO 1: CLICK EN BOTÓN (Callback) ---
    if "callback_query" in update:
        cb = update["callback_query"]
        chat_id = cb["message"]["chat"]["id"]
        data = cb["data"]
        
        try:
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/answerCallbackQuery", 
                          json={"callback_query_id": cb["id"]})
        except: pass

        if data.startswith("ver_"):
            date_target = data.replace("ver_", "")
            rows = db.get_logs_by_day(date_target)
            if rows:
                img = history.generate_day_graph(rows, date_target)
                send_photo_with_buttons(chat_id, img, f"🔎 Detalle: {date_target}")
            else:
                send_text(chat_id, "⚠️ No hay datos para esa fecha.")

    # --- CASO 2: MENSAJE DE TEXTO ---
    elif "message" in update and "text" in update["message"]:
        chat_id = update["message"]["chat"]["id"]
        text = update["message"]["text"]
        
        if "/start" in text:
            send_text(chat_id, "👋 *Panel de Control V6:*", buttons=True)
            
        elif "Comprobar" in text or "/check" in text:
            send_text(chat_id, "⏳ Accediendo como navegador real...")
            send_text(chat_id, check_website(), buttons=True)
            
        elif "Gráfico" in text or "/history" in text:
            rows = db.get_last_7_days_averages()
            dates = db.get_available_dates()
            
            if rows:
                send_text(chat_id, "🎨 Generando informe...")
                img = history.generate_global_graph(rows)
                send_photo_with_buttons(chat_id, img, "📊 Resumen Semanal", buttons_dates=dates)
            else:
                send_text(chat_id, "📭 Aún no hay datos suficientes.")
            
    return "OK", 200

@app.route('/')
def home():
    return "Bot V6 Activo 🚀"
