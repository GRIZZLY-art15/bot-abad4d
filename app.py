import json
import os
import random
import threading
import time
from datetime import datetime
from flask import Flask, render_template, request, jsonify
import requests

# ========== KONFIGURASI ==========
TOKEN = "8501043849:AAH8Xm31iGQd-XrGZnduLI9ll5YEzintEOg"
ADMIN_ID = 7176181382
# =================================

app = Flask(__name__)
app.secret_key = "s4r4h4n4kunC1k4l1s4j4tuh4n34y4h"

# Variabel untuk tracking broadcast
broadcast_status = {
    "last_broadcast_time": None,
    "last_broadcast_title": None,
    "next_broadcast_in": 0,
    "total_broadcasts_sent": 0,
    "is_running": True
}

DATA_FILE = "users.json"
PROMO_FILE = "promo.json"
CONFIG_FILE = "config.json"

def load_users():
    try:
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
            return set(data) if data else set()
    except:
        return set()

def save_users(users):
    with open(DATA_FILE, "w") as f:
        json.dump(list(users), f)

def load_promos():
    try:
        with open(PROMO_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            promos = data.get("promos", [])
            settings = data.get("settings", {})
            # Default interval jika tidak ada
            if not settings.get("broadcast_interval_minutes"):
                settings["broadcast_interval_minutes"] = 20
            return promos, settings
    except Exception as e:
        print(f"Error loading promos: {e}")
        return [], {"broadcast_interval_minutes": 20, "random_order": True, "send_image": True}

def load_config():
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"welcome_message": "🌟 SELAMAT DATANG DI ABAD4D OFFICIAL 🌟\n\n🔥 PROMO SPESIAL UNTUK ANDA! 🔥\n\n👇 Klik tombol di bawah untuk mulai bermain", "website_url": "https://siteq.link/abad4d"}

def save_promos(promos, settings):
    with open(PROMO_FILE, "w", encoding="utf-8") as f:
        json.dump({"promos": promos, "settings": settings}, f, indent=4, ensure_ascii=False)

def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)

users = load_users()
promos, promo_settings = load_promos()
config = load_config()

print(f"✅ Loaded {len(promos)} promos")
print(f"⏰ Broadcast interval: {promo_settings.get('broadcast_interval_minutes', 20)} minutes")
print(f"👥 Total users: {len(users)}")

# ============ TELEGRAM FUNCTIONS ============
def send_telegram_message(chat_id, text, photo_url=None, button_text=None, button_url=None, reply_markup=None):
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
    
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        return response.json()
    except Exception as e:
        print(f"Error send: {e}")
        return None

def broadcast_promo():
    global broadcast_status
    
    if not promos:
        print("❌ Tidak ada promo")
        return
    
    promo = random.choice(promos) if promo_settings.get("random_order", True) else promos[0]
    users_list = list(load_users())
    
    if len(users_list) == 0:
        print("⚠️ Belum ada user yang terdaftar. Broadcast skipped.")
        return
    
    success = 0
    fail = 0
    
    print("=" * 60)
    print(f"📢 [BROADCAST] Memulai pengiriman promo...")
    print(f"📢 Judul: {promo['title']}")
    print(f"📢 Target: {len(users_list)} user")
    print("=" * 60)
    
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
        else:
            fail += 1
        time.sleep(0.05)
    
    # Update status
    broadcast_status["last_broadcast_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    broadcast_status["last_broadcast_title"] = promo['title']
    broadcast_status["total_broadcasts_sent"] += 1
    
    print("=" * 60)
    print(f"✅ [BROADCAST] Selesai!")
    print(f"✅ Berhasil: {success} user")
    print(f"❌ Gagal: {fail} user")
    print(f"📅 Waktu: {broadcast_status['last_broadcast_time']}")
    print("=" * 60)

def broadcast_loop():
    global broadcast_status
    
    print("🔄 [LOOP] Broadcast loop dimulai...")
    last_broadcast = 0
    
    while True:
        now = time.time()
        interval_minutes = promo_settings.get("broadcast_interval_minutes", 20)
        interval_seconds = interval_minutes * 60
        
        if last_broadcast == 0:
            print(f"⏰ [LOOP] Broadcast pertama akan dimulai dalam {interval_minutes} menit")
            broadcast_status["next_broadcast_in"] = interval_seconds
        
        if now - last_broadcast >= interval_seconds:
            print(f"\n🚀 [LOOP] Trigger broadcast pada {datetime.now().strftime('%H:%M:%S')}")
            broadcast_promo()
            last_broadcast = now
            broadcast_status["next_broadcast_in"] = interval_seconds
        else:
            remaining = int(interval_seconds - (now - last_broadcast))
            broadcast_status["next_broadcast_in"] = remaining
        
        time.sleep(30)

# ============ FLASK ROUTES ============
@app.route('/')
def home():
    return """
    <html>
    <head><title>Abad4D Bot</title></head>
    <body style="font-family: Arial; text-align: center; padding: 50px;">
        <h1>🤖 Abad4D Bot is Running!</h1>
        <p>⏰ Broadcast setiap 20 menit</p>
        <p>📊 <a href="/api/broadcast_status">Cek Status Broadcast</a></p>
        <p>📋 <a href="/api/promos">Lihat Promo</a></p>
        <p>👥 <a href="/api/users">Lihat User</a></p>
        <p>📡 <a href="/set_webhook">Set Webhook</a></p>
    </body>
    </html>
    """

@app.route('/admin')
def admin_panel():
    try:
        return render_template('admin.html')
    except Exception as e:
        return f"Error loading admin panel: {e}"

@app.route('/api/broadcast_status')
def api_broadcast_status():
    return jsonify({
        'is_running': broadcast_status["is_running"],
        'last_broadcast_time': broadcast_status.get("last_broadcast_time", "Belum pernah"),
        'last_broadcast_title': broadcast_status.get("last_broadcast_title", "-"),
        'next_broadcast_in_seconds': broadcast_status.get("next_broadcast_in", 0),
        'next_broadcast_in_minutes': round(broadcast_status.get("next_broadcast_in", 0) / 60, 1),
        'total_broadcasts_sent': broadcast_status.get("total_broadcasts_sent", 0),
        'interval_minutes': promo_settings.get('broadcast_interval_minutes', 20)
    })

@app.route('/api/stats')
def api_stats():
    return jsonify({
        'total_users': len(load_users()),
        'total_promos': len(promos),
        'broadcast_interval': promo_settings.get('broadcast_interval_minutes', 20),
        'random_order': promo_settings.get('random_order', True),
        'send_image': promo_settings.get('send_image', True),
        'website_url': config.get('website_url'),
        'welcome_message': config.get('welcome_message')
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
    promo_settings['broadcast_interval_minutes'] = data.get('broadcast_interval', 20)
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
    users_list = list(load_users())
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
    
    users_list = list(load_users())
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
    try:
        data = request.get_json()
        
        if data and "message" in data:
            chat_id = data["message"]["chat"]["id"]
            text = data["message"].get("text", "")
            username = data["message"]["chat"].get("username", "unknown")
            
            current_users = load_users()
            if chat_id not in current_users:
                current_users.add(chat_id)
                save_users(current_users)
                print(f"📝 User baru: {username} ({chat_id}) - Total: {len(current_users)}")
            
            if text == "/start":
                welcome_msg = config.get("welcome_message", "Selamat datang di Abad4D Bot!")
                
                keyboard = {
                    "inline_keyboard": [
                        [{"text": "🌐 Website", "url": config.get("website_url")}],
                        [{"text": "🎰 Lihat Promo", "callback_data": "list_promos"}]
                    ]
                }
                send_telegram_message(chat_id, welcome_msg, reply_markup=keyboard)
                print(f"📨 Welcome sent to {username}")
                
            elif text == "/status" and str(chat_id) == str(ADMIN_ID):
                remaining = broadcast_status.get("next_broadcast_in", 0)
                remaining_min = int(remaining // 60)
                remaining_sec = int(remaining % 60)
                
                status_msg = f"""
📊 *STATUS BROADCAST*

🔄 Status: {'✅ AKTIF' if broadcast_status['is_running'] else '❌ BERHENTI'}
📅 Last broadcast: {broadcast_status.get('last_broadcast_time', 'Belum pernah')}
📢 Last promo: {broadcast_status.get('last_broadcast_title', '-')}
⏰ Next broadcast: {remaining_min} menit {remaining_sec} detik
📊 Total broadcast: {broadcast_status.get('total_broadcasts_sent', 0)} kali
👥 Total user: {len(load_users())}
🎁 Total promo: {len(promos)}
⏱️ Interval: {promo_settings.get('broadcast_interval_minutes', 20)} menit
"""
                send_telegram_message(chat_id, status_msg)
                print(f"📊 Status sent to admin {username}")
                
            elif text == "/help":
                help_msg = """
📖 *Panduan Bot Abad4D*

/start - Memulai bot
/help - Panduan ini
/promos - Lihat semua promo
/status - Cek status broadcast (admin only)

*Fitur:*
⏰ Broadcast promo setiap 20 menit otomatis
🎁 8 Promo menarik dengan gambar
"""
                send_telegram_message(chat_id, help_msg)
                
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
                    parts = text.split()
                    if len(parts) < 2:
                        send_telegram_message(chat_id, "Gunakan: /promo <nomor>")
                        return
                    num = int(parts[1]) - 1
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
                except ValueError:
                    send_telegram_message(chat_id, "Gunakan: /promo <nomor>")
                except Exception as e:
                    send_telegram_message(chat_id, f"Error: {e}")
                    
            elif text == "/stats" and str(chat_id) == str(ADMIN_ID):
                total_users = len(load_users())
                interval = promo_settings.get('broadcast_interval_minutes', 20)
                send_telegram_message(chat_id, f"📊 *Statistik Bot*\n\n👥 Total user: {total_users}\n🎁 Total promo: {len(promos)}\n⏰ Broadcast: setiap {interval} menit")
                
            elif text.startswith("/broadcast") and str(chat_id) == str(ADMIN_ID):
                msg = text.replace("/broadcast", "").strip()
                if msg:
                    send_telegram_message(chat_id, "⏳ Mengirim broadcast...")
                    users_list = list(load_users())
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
        
        elif data and "callback_query" in data:
            chat_id = data["callback_query"]["message"]["chat"]["id"]
            if not promos:
                send_telegram_message(chat_id, "Belum ada promo tersedia.")
            else:
                msg = "*📋 DAFTAR PROMO ABAD4D*\n\n"
                for i, p in enumerate(promos, 1):
                    msg += f"{i}. {p['title']}\n"
                msg += "\nKetik /promo <nomor> untuk detail"
                send_telegram_message(chat_id, msg)
            
            # Answer callback query
            url = f"https://api.telegram.org/bot{TOKEN}/answerCallbackQuery"
            requests.post(url, json={"callback_query_id": data["callback_query"]["id"]})
        
        return jsonify({"status": "ok"})
    except Exception as e:
        print(f"Webhook error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/set_webhook')
def set_webhook():
    render_url = os.environ.get('RENDER_EXTERNAL_URL', request.host_url)
    if render_url.endswith('/'):
        render_url = render_url[:-1]
    webhook_url = f"{render_url}/webhook"
    
    url = f"https://api.telegram.org/bot{TOKEN}/setWebhook"
    response = requests.post(url, json={"url": webhook_url})
    result = response.json()
    
    if result.get("ok"):
        return f"""
        <h2>✅ Webhook Berhasil Diatur!</h2>
        <p>URL Webhook: <code>{webhook_url}</code></p>
        <p>Response: <pre>{json.dumps(result, indent=2)}</pre></p>
        <p>Sekarang coba kirim <code>/start</code> ke bot di Telegram.</p>
        <hr>
        <h3>📊 Cek Status Broadcast:</h3>
        <p><a href="/api/broadcast_status">/api/broadcast_status</a></p>
        """
    else:
        return f"""
        <h2>❌ Gagal Mengatur Webhook</h2>
        <p>Error: {result}</p>
        """

@app.route('/health')
def health():
    return "OK", 200

# ============ MAIN ============
if __name__ == "__main__":
    broadcast_thread = threading.Thread(target=broadcast_loop, daemon=True)
    broadcast_thread.start()
    
    port = int(os.environ.get("PORT", 5000))
    print("=" * 60)
    print("🤖 ABAD4D BOT TELEGRAM")
    print("=" * 60)
    print(f"🌐 Server running on port {port}")
    print(f"📡 Kunjungi /set_webhook untuk mengaktifkan webhook")
    print(f"🔄 Broadcast loop: AKTIF (setiap {promo_settings.get('broadcast_interval_minutes', 20)} menit)")
    print(f"📊 Cek status: /api/broadcast_status")
    print("=" * 60)
    
    app.run(host="0.0.0.0", port=port)
