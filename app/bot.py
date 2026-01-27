import os
import requests
import urllib3
import time
import json
import cloudscraper
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

# --- FUNCIONES DE ENVÍO ---

def send_text(chat_id, text, buttons=False):
    """Envía mensajes de texto con el menú principal inferior."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    
    # Menú fijo inferior (Teclado normal)
    if buttons:
        payload["reply_markup"] = {
            "keyboard": [[{"text": "🔍 Comprobar"}, {"text": "📊 Gráfico"}]],
            "resize_keyboard": True,
            "one_time_keyboard": False
        }
    try: requests.post(url, json=payload)
    except Exception as e: print(f"Error texto: {e}")

def send_photo_with_buttons(chat_id, photo_buf, caption, buttons_dates=None):
    """Envía la foto con botones INLINE (pegados a la imagen) para elegir fecha."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    
    # Construcción del teclado interactivo
    reply_markup = {}
    if buttons_dates:
        inline_keyboard = []
        row = []
        for date in buttons_dates:
            # Callback data es el ID que recibimos cuando hacen click (ej: "ver_2023-10-27")
            btn = {"text": f"📅 {date}", "callback_data": f"ver_{date}"}
            row.append(btn)
            
            # Agrupamos botones de 2 en 2 para que se vea ordenado
            if len(row) == 2:
                inline_keyboard.append(row)
                row = []
        
        if row: inline_keyboard.append(row) # Añadir los que sobren
        reply_markup = {"inline_keyboard": inline_keyboard}

    # Preparamos los datos multipart
    data = {
        'chat_id': chat_id, 
        'caption': caption, 
        'reply_markup': json.dumps(reply_markup) # Convertimos a JSON texto
    }
    files = {'photo': ('chart.png', photo_buf, 'image/png')}
    
    try: requests.post(url, data=data, files=files)
    except Exception as e: print(f"Error foto: {e}")

# --- LÓGICA DE MONITOREO CON CLOUDSCRAPER ---
def check_website():
    if not TARGET_URL: return "⚠️ Sin URL Configurada"
    
    # Cloudscraper se encarga de fingir ser un navegador Chrome real
    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'desktop': True
        }
    )
    
    params = {'nocache': time.time()}
    
    try:
        start = time.time()
        
        # Usamos scraper.get en lugar de requests.get
        resp = scraper.get(TARGET_URL, params=params, timeout=15)
        
        lat = round((time.time() - start) * 1000, 0)
        status = resp.status_code
        
        if status == 200:
            msg_log = "Online"
            res = f"✅ Online: {lat}ms"
        elif status == 403:
             # Si cloudscraper falla, es un bloqueo muy agresivo
            msg_log = "Bloqueo Fuerte (403)"
            res = f"⚠️ ALERTA: Ni Cloudscraper pudo pasar. El firewall es muy estricto."
        else:
            msg_log = f"HTTP {status}"
            res = f"⚠️ Error HTTP {status}"
        
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
        # Usamos send_text simple para alertas automáticas
        send_text(TELEGRAM_CHAT_ID, f"🤖 *Alerta Auto:*\n{res}")
    return "OK", 200

@app.route('/webhook', methods=['POST'])
def webhook():
    update = request.get_json()
    
    # --- CASO 1: CLICK EN UN BOTÓN DE FECHA (Callback Query) ---
    if "callback_query" in update:
        cb = update["callback_query"]
        chat_id = cb["message"]["chat"]["id"]
        data = cb["data"] # Aquí viene ej: "ver_2023-10-27"
        
        # 1. Avisamos a Telegram que recibimos el click (quita el reloj de carga)
        try:
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/answerCallbackQuery", 
                          json={"callback_query_id": cb["id"]})
        except: pass

        # 2. Procesamos la petición de fecha
        if data.startswith("ver_"):
            date_target = data.replace("ver_", "")
            
            # Pedimos a DB los datos específicos de ese día
            rows = db.get_logs_by_day(date_target)
            
            if rows:
                # Generamos gráfico detallado
                img = history.generate_day_graph(rows, date_target)
                send_photo_with_buttons(chat_id, img, f"🔎 Detalle del día: {date_target}")
            else:
                send_text(chat_id, "⚠️ No hay datos registrados para esa fecha.")

    # --- CASO 2: MENSAJE DE TEXTO NORMAL ---
    elif "message" in update and "text" in update["message"]:
        chat_id = update["message"]["chat"]["id"]
        text = update["message"]["text"]
        
        if "/start" in text:
            send_text(chat_id, "👋 *Panel de Control:*", buttons=True)
            
        elif "Comprobar" in text or "/check" in text:
            send_text(chat_id, "⏳ Midiendo...")
            send_text(chat_id, check_website(), buttons=True)
            
        elif "Gráfico" in text or "/history" in text:
            # 1. Pedimos datos globales (Medias de 7 días)
            rows = db.get_last_7_days_averages()
            # 2. Pedimos fechas disponibles para pintar botones
            dates = db.get_available_dates()
            
            if rows:
                send_text(chat_id, "🎨 Generando informe semanal...")
                # Generamos gráfico global
                img = history.generate_global_graph(rows)
                # Enviamos foto + botones de fechas
                send_photo_with_buttons(chat_id, img, "📊 Resumen Semanal (Media Diaria)", buttons_dates=dates)
            else:
                send_text(chat_id, "📭 Aún no hay datos suficientes para generar estadísticas.")
            
    return "OK", 200

@app.route('/')
def home():
    return "Bot Interactivo V5 Activo 🚀"
