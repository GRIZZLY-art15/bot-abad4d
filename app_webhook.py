import json
import os
import requests
from flask import Flask, render_template, request, jsonify
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup

# ========== KONFIGURASI ==========
TOKEN = "8561643849:AABXxn31i0qd-Xz0ZnduL18115YEziEt8g"
ADMIN_ID = 7176181382
# =================================

app = Flask(__name__)

# Load data
DATA_FILE = "users.json"
PROMO_FILE = "promo.json"
CONFIG_FILE = "config.json"

def load_users():
    try:
        with open(DATA_FILE, "r") as f:
            return set(json.load(f))
    except:
        return set()

def save_users(users):
    with open(DATA_FILE, "w") as f:
        json.dump(list(users), f)

users = load_users()

def load_promos():
    try:
        with open(PROMO_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("promos", []), data.get("settings", {})
    except:
        return [], {}

promos, promo_settings = load_promos()

def load_config():
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"welcome_message": "Selamat datang!", "website_url": "https://siteq.link/abad4d"}

# ============ TELEGRAM BOT HANDLER ============
def send_message(chat_id, text, reply_markup=None):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Error: {e}")

def handle_start(chat_id):
    if chat_id not in users:
        users.add(chat_id)
        save_users(users)
        print(f"User baru: {chat_id}")
    
    config = load_config()
    keyboard = {
        "inline_keyboard": [[
            {"text": "🌐 Kunjungi Website", "url": config["website_url"]}
        ]]
    }
    send_message(chat_id, config["welcome_message"], keyboard)

def handle_help(chat_id):
    help_text = """
📖 *Panduan Bot*

/start - Memulai bot
/help - Panduan ini
/promos - Lihat semua promo
"""
    send_message(chat_id, help_text)

def handle_promos(chat_id):
    if not promos:
        send_message(chat_id, "Belum ada promo.")
        return
    
    text = "*📋 DAFTAR PROMO*\n\n"
    for i, promo in enumerate(promos, 1):
        text += f"{i}. {promo['title']}\n"
    send_message(chat_id, text)

# ============ WEBHOOK ENDPOINT ============
@app.route(f'/webhook/{TOKEN}', methods=['POST'])
def webhook():
    try:
        update = Update.de_json(request.get_json(), None)
        message = update.message
        
        if message:
            chat_id = message.chat.id
            text = message.get("text", "")
            
            if text == "/start":
                handle_start(chat_id)
            elif text == "/help":
                handle_help(chat_id)
            elif text == "/promos":
                handle_promos(chat_id)
            elif text.startswith("/"):
                send_message(chat_id, "Perintah tidak dikenal. Ketik /help")
            else:
                send_message(chat_id, "Kirim /start untuk memulai")
        
        return jsonify({"status": "ok"})
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"status": "error"}), 500

# ============ FLASK ADMIN PANEL ============
@app.route('/')
def admin_panel():
    return render_template('admin.html')

@app.route('/api/stats')
def api_stats():
    return jsonify({
        'total_users': len(users),
        'total_promos': len(promos),
        'broadcast_interval': promo_settings.get('broadcast_interval_hours', 1),
        'random_order': promo_settings.get('random_order', True),
        'send_image': promo_settings.get('send_image', True)
    })

@app.route('/api/promos')
def api_get_promos():
    return jsonify(promos)

@app.route('/api/users')
def api_get_users():
    return jsonify(list(users))

@app.route('/health')
def health():
    return "OK", 200

@app.route('/set_webhook')
def set_webhook():
    """Endpoint untuk mengaktifkan webhook"""
    render_url = os.environ.get('RENDER_EXTERNAL_URL', request.host_url)
    webhook_url = f"{render_url}webhook/{TOKEN}"
    
    url = f"https://api.telegram.org/bot{TOKEN}/setWebhook"
    response = requests.post(url, json={"url": webhook_url})
    
    if response.json().get("ok"):
        return f"✅ Webhook berhasil diatur: {webhook_url}"
    else:
        return f"❌ Gagal: {response.text}"

# ============ MAIN ============
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"🤖 Bot Telegram dengan Webhook")
    print(f"🌐 Admin Panel: http://localhost:{port}")
    print(f"📡 Kunjungi /set_webhook untuk mengaktifkan webhook")
    app.run(host="0.0.0.0", port=port)