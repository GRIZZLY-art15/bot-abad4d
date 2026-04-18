import json
import os
import random
import threading
import time
from datetime import datetime
from flask import Flask, render_template, request, jsonify
import requests

# ========== KONFIGURASI ==========
TOKEN = "8501043849:AAH8Xm31iGQd-XrGZnduLI9ll5YEzintEOg"  # GANTI DENGAN TOKEN ASLI
ADMIN_ID = 7176181382  # GANTI DENGAN ID TELEGRAM KAMU
# =================================

app = Flask(__name__)
app.secret_key = "s4r4h4n4kunC1k4l1s4j4tuh4n34y4h"

# Load data files
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

def load_promos():
    try:
        with open(PROMO_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("promos", []), data.get("settings", {})
    except:
        return [], {}

def load_config():
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"welcome_message": "Selamat datang!", "website_url": "https://siteq.link/abad4d"}

def save_promos(promos, settings):
    with open(PROMO_FILE, "w", encoding="utf-8") as f:
        json.dump({"promos": promos, "settings": settings}, f, indent=4, ensure_ascii=False)

def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)

users = load_users()
promos, promo_settings = load_promos()
config = load_config()

# ============ TELEGRAM FUNCTIONS ============
def send_telegram_message(chat_id, text, photo_url=None, button_text=None, button_url=None):
    if photo_url and promo_settings.get("send_image", True):
        url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
        payload = {
            "chat_id": chat_id,
            "photo": photo_url,
            "caption": text,
            "parse_mode": "Markdown"
        }
    else:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown"
        }
    
    if button_text and button_url:
        payload["reply_markup"] = json.dumps({
            "inline_keyboard": [[{"text": button_text, "url": button_url}]]
        })
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        return response.json()
    except Exception as e:
        print(f"Error: {e}")
        return None

def broadcast_promo():
    """Kirim promo random ke semua user"""
    if not promos:
        print("Tidak ada promo")
        return
    
    promo = random.choice(promos)
    users_list = load_users()
    
    success = 0
    for user_id in users_list:
        result = send_telegram_message(
            user_id,
            promo.get("message", ""),
            promo.get("image_url"),
            promo.get("button_text", "🔥 Klaim Bonus"),
            promo.get("button_url", config.get("website_url"))
        )
        if result and result.get("ok"):
            success += 1
        time.sleep(0.05)
    
    print(f"[{datetime.now()}] Broadcast: {success} terkirim")

def broadcast_loop():
    """Loop untuk broadcast setiap jam"""
    while True:
        time.sleep(3600)  # 1 jam
        broadcast_promo()

# ============ FLASK ROUTES ============
@app.route('/')
def admin_panel():
    return render_template('admin.html')

@app.route('/api/stats')
def api_stats():
    return jsonify({
        'total_users': len(load_users()),
        'total_promos': len(promos),
        'broadcast_interval': promo_settings.get('broadcast_interval_hours', 1),
        'random_order': promo_settings.get('random_order', True),
        'send_image': promo_settings.get('send_image', True)
    })

@app.route('/api/promos')
def api_get_promos():
    return jsonify(promos)

@app.route('/api/promo', methods=['POST'])
def api_add_promo():
    data = request.json
    new_id = max([p.get('id', 0) for p in promos]) + 1 if promos else 1
    new_promo = {
        'id': new_id,
        'title': data.get('title'),
        'message': data.get('message'),
        'image_url': data.get('image_url', ''),
        'button_text': data.get('button_text', '🔥 Klaim Bonus'),
        'button_url': data.get('button_url', config.get('website_url'))
    }
    promos.append(new_promo)
    save_promos(promos, promo_settings)
    return jsonify({'success': True, 'promo': new_promo})

@app.route('/api/promo/<int:promo_id>', methods=['PUT'])
def api_update_promo(promo_id):
    data = request.json
    for i, promo in enumerate(promos):
        if promo.get('id') == promo_id:
            promos[i] = {**promo, **data}
            save_promos(promos, promo_settings)
            return jsonify({'success': True})
    return jsonify({'error': 'Not found'}), 404

@app.route('/api/promo/<int:promo_id>', methods=['DELETE'])
def api_delete_promo(promo_id):
    for i, promo in enumerate(promos):
        if promo.get('id') == promo_id:
            promos.pop(i)
            save_promos(promos, promo_settings)
            return jsonify({'success': True})
    return jsonify({'error': 'Not found'}), 404

@app.route('/api/settings', methods=['POST'])
def api_update_settings():
    data = request.json
    promo_settings['broadcast_interval_hours'] = data.get('broadcast_interval_hours', 1)
    promo_settings['random_order'] = data.get('random_order', True)
    promo_settings['send_image'] = data.get('send_image', True)
    save_promos(promos, promo_settings)
    
    config['website_url'] = data.get('website_url', config.get('website_url'))
    config['welcome_message'] = data.get('welcome_message', config.get('welcome_message'))
    save_config(config)
    
    return jsonify({'success': True})

@app.route('/api/users')
def api_get_users():
    return jsonify(list(load_users()))

@app.route('/api/broadcast', methods=['POST'])
def api_broadcast():
    data = request.json
    users_list = load_users()
    success = 0
    for user_id in users_list:
        result = send_telegram_message(
            user_id,
            data.get('message'),
            data.get('image_url'),
            data.get('button_text'),
            data.get('button_url')
        )
        if result and result.get('ok'):
            success += 1
        time.sleep(0.05)
    return jsonify({'sent': success, 'total': len(users_list)})

@app.route('/api/broadcast_promo/<int:promo_id>', methods=['POST'])
def api_broadcast_promo(promo_id):
    promo = next((p for p in promos if p.get('id') == promo_id), None)
    if not promo:
        return jsonify({'error': 'Not found'}), 404
    
    users_list = load_users()
    success = 0
    for user_id in users_list:
        result = send_telegram_message(
            user_id,
            promo.get('message'),
            promo.get('image_url'),
            promo.get('button_text'),
            promo.get('button_url')
        )
        if result and result.get('ok'):
            success += 1
        time.sleep(0.05)
    return jsonify({'sent': success, 'total': len(users_list)})

@app.route('/webhook', methods=['POST'])
def webhook():
    """Endpoint untuk webhook Telegram"""
    data = request.get_json()
    if data and "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")
        username = data["message"]["chat"].get("username", "unknown")
        
        # Simpan user baru
        current_users = load_users()
        if chat_id not in current_users:
            current_users.add(chat_id)
            save_users(current_users)
            print(f"User baru: {username} ({chat_id})")
        
        # Handle perintah
        if text == "/start":
            keyboard = {
                "inline_keyboard": [
                    [{"text": "🌐 Kunjungi Website", "url": config.get("website_url")}],
                    [{"text": "🎰 Lihat Semua Promo", "callback_data": "list_promos"}]
                ]
            }
            send_telegram_message(chat_id, config.get("welcome_message"), None, None, None)
            # Kirim keyboard terpisah
            url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": "👇 Pilih menu di bawah:",
                "reply_markup": json.dumps(keyboard)
            }
            requests.post(url, json=payload)
            
        elif text == "/help":
            help_text = """
📖 *Panduan Bot Abad4D*

/start - Memulai bot dan daftar promo
/help - Panduan ini
/promos - Lihat semua promo

*Fitur:*
⏰ Setiap jam akan dikirim promo menarik
🎁 Bonus New Member 50%
💰 Cashback Mingguan 1%
"""
            send_telegram_message(chat_id, help_text)
            
        elif text == "/promos":
            if not promos:
                send_telegram_message(chat_id, "Belum ada promo tersedia.")
            else:
                msg = "*📋 DAFTAR PROMO ABAD4D*\n\n"
                for i, p in enumerate(promos, 1):
                    msg += f"{i}. {p['title']}\n"
                msg += "\nKetik /promo <nomor> untuk detail"
                send_telegram_message(chat_id, msg)
                
        elif text.startswith("/promo"):
            try:
                num = int(text.split()[1]) - 1
                if 0 <= num < len(promos):
                    p = promos[num]
                    send_telegram_message(
                        chat_id,
                        p['message'],
                        p.get('image_url'),
                        p.get('button_text'),
                        p.get('button_url')
                    )
                else:
                    send_telegram_message(chat_id, "Nomor promo tidak ditemukan")
            except:
                send_telegram_message(chat_id, "Gunakan: /promo <nomor>")
                
        elif text == "/stats" and chat_id == ADMIN_ID:
            total_users = len(load_users())
            send_telegram_message(chat_id, f"📊 *Statistik Bot*\n\n👥 Total user: {total_users}\n🎁 Total promo: {len(promos)}")
            
        elif text.startswith("/broadcast") and chat_id == ADMIN_ID:
            msg = text.replace("/broadcast", "").strip()
            if msg:
                send_telegram_message(chat_id, "⏳ Mengirim broadcast...")
                users_list = load_users()
                sent = 0
                for uid in users_list:
                    send_telegram_message(uid, msg)
                    sent += 1
                    time.sleep(0.05)
                send_telegram_message(chat_id, f"✅ Broadcast selesai! Terkirim ke {sent} user")
            else:
                send_telegram_message(chat_id, "Gunakan: /broadcast <pesan>")
        else:
            send_telegram_message(chat_id, "🤖 Kirim /start untuk memulai")
    
    return jsonify({"status": "ok"})

@app.route('/set_webhook')
def set_webhook():
    """Endpoint untuk mengatur webhook"""
    render_url = os.environ.get('RENDER_EXTERNAL_URL', request.host_url)
    webhook_url = f"{render_url}webhook"
    
    url = f"https://api.telegram.org/bot{TOKEN}/setWebhook"
    response = requests.post(url, json={"url": webhook_url})
    
    if response.json().get("ok"):
        return f"✅ Webhook berhasil diatur!<br><br>URL: {webhook_url}"
    else:
        return f"❌ Gagal: {response.text}"

@app.route('/health')
def health():
    return "OK", 200

# ============ MAIN ============
if __name__ == "__main__":
    # Mulai broadcast loop di thread terpisah
    broadcast_thread = threading.Thread(target=broadcast_loop, daemon=True)
    broadcast_thread.start()
    
    port = int(os.environ.get("PORT", 5000))
    print("=" * 50)
    print("🤖 ABAD4D BOT TELEGRAM")
    print("=" * 50)
    print(f"🌐 Admin Panel: http://localhost:{port}")
    print(f"📡 Kunjungi /set_webhook untuk mengaktifkan webhook")
    print("=" * 50)
    
    app.run(host="0.0.0.0", port=port)
