import os
import requests
import urllib3 
from flask import Flask, request

# --- CONFIGURACIÓN SSL ---
# Esto silencia la advertencia roja en la consola cuando usamos verify=False
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

# --- TUS SECRETOS (Los lee de Render) ---
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
TARGET_URL = os.environ.get('TARGET_URL')

# --- FUNCIÓN: REVISAR LA WEB (MODIFICADA) ---
def check_website():
    if not TARGET_URL:
        return "⚠️ Error: No has configurado la URL en Render."
    
    # 1. Creamos un "Disfraz" para parecer un navegador Chrome real
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        # 2. Añadimos headers=headers (el disfraz)
        # 3. Añadimos verify=False (ignorar error de certificado SSL)
        response = requests.get(TARGET_URL, headers=headers, timeout=10, verify=False)
        
        if response.status_code == 200:
            return f"✅ Todo OK: {TARGET_URL} está ONLINE (Código 200)."
        else:
            return f"⚠️ ALERTA: {TARGET_URL} devuelve error {response.status_code}."
            
    except Exception as e:
        return f"🚨 CRÍTICO: La web {TARGET_URL} no responde. Error: {str(e)}"

# --- FUNCIÓN: ENVIAR A TELEGRAM ---
def send_telegram(chat_id, text, show_button=False):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    
    # Si pedimos botón, lo añadimos al mensaje
    if show_button:
        payload["reply_markup"] = {
            "keyboard": [[{"text": "🔍 Comprobar Ahora"}]],
            "resize_keyboard": True,
            "one_time_keyboard": False
        }
        
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Error enviando a Telegram: {e}")

# --- RUTA 1: AUTOMÁTICA (Para Cron-job.org) ---
@app.route('/monitor')
def monitor():
    resultado = check_website()
    # Solo avisamos si NO sale el check verde
    if "✅" not in resultado:
        send_telegram(TELEGRAM_CHAT_ID, f"🤖 *Monitor Auto:*\n{resultado}")
        return "Alerta enviada", 200
    return "Web OK", 200

# --- RUTA 2: MANUAL (Para el botón de Telegram) ---
@app.route('/webhook', methods=['POST'])
def webhook():
    update = request.get_json()
    if "message" in update and "text" in update["message"]:
        chat_id = update["message"]["chat"]["id"]
        text = update["message"]["text"]
        
        # Si escribe /start o pulsa el botón
        if text == "/start":
            send_telegram(chat_id, "👋 Soy tu Vigilante. Pulsa el botón:", show_button=True)
            
        elif text == "/check" or "Comprobar" in text:
            send_telegram(chat_id, "⏳ Revisando estado...")
            resultado = check_website()
            send_telegram(chat_id, resultado, show_button=True)
            
    return "OK", 200

@app.route('/')
def home():
    return "Bot Activo 🤖"

if __name__ == '__main__':
    app.run()
