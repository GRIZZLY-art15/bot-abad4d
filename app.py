import json
import os
import random
import time
from datetime import datetime
from flask import Flask, request, jsonify
import requests

# ========== KONFIGURASI ==========
TOKEN = "8501043849:AAH8Xm31iGQd-XrGZnduLI9ll5YEzintEOg"
ADMIN_ID = 7176181382
# =================================

app = Flask(__name__)

# File untuk menyimpan data
CONTACTS_FILE = "contacts.json"
DATA_FILE = "users.json"
PROMO_FILE = "promo.json"
CONFIG_FILE = "config.json"

# Variabel untuk tracking broadcast terakhir
last_broadcast_time = None

# ============ FUNGSI LOAD DATA ============
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
            return data.get("promos", []), data.get("settings", {"broadcast_interval_minutes": 20})
    except:
        return [], {"broadcast_interval_minutes": 20}

def load_config():
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"welcome_message": "🌟 SELAMAT DATANG DI ABAD4D OFFICIAL 🌟", "website_url": "https://siteq.link/abad4d"}

# Load data
users = load_users()
promos, promo_settings = load_promos()
config = load_config()

# ============ FUNGSI KONTAK ============
def save_contact(user_id, username, first_name, last_name, phone_number):
    try:
        contacts = []
        if os.path.exists(CONTACTS_FILE):
            with open(CONTACTS_FILE, "r", encoding="utf-8") as f:
                contacts = json.load(f)
        
        new_contact = {
            "user_id": user_id,
            "username": username,
            "first_name": first_name,
            "last_name": last_name or "",
            "full_name": f"{first_name} {last_name or ''}".strip(),
            "phone_number": phone_number,
            "shared_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        contacts.append(new_contact)
        
        with open(CONTACTS_FILE, "w", encoding="utf-8") as f:
            json.dump(contacts, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving contact: {e}")
        return False

def get_all_contacts():
    try:
        if os.path.exists(CONTACTS_FILE):
            with open(CONTACTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except:
        pass
    return []

# ============ TELEGRAM FUNCTIONS ============
def send_telegram_message(chat_id, text, reply_markup=None):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        return response.json()
    except Exception as e:
        print(f"Error send: {e}")
        return None

def send_main_menu(chat_id):
    welcome_msg = config.get("welcome_message", "🌟 SELAMAT DATANG DI ABAD4D OFFICIAL 🌟")
    
    keyboard = {
        "inline_keyboard": [
            [{"text": "📞 Share Kontak Saya", "callback_data": "share_contact"}],
            [{"text": "🌐 Kunjungi Website", "url": config.get("website_url")}],
            [{"text": "🎰 Lihat Semua Promo", "callback_data": "list_promos"}],
            [{"text": "ℹ️ Bantuan", "callback_data": "help"}]
        ]
    }
    send_telegram_message(chat_id, welcome_msg, reply_markup=keyboard)

def send_promo_list(chat_id):
    if not promos:
        send_telegram_message(chat_id, "Belum ada promo tersedia.")
        return
    
    keyboard = {"inline_keyboard": []}
    for promo in promos:
        keyboard["inline_keyboard"].append([{"text": promo['title'][:30], "callback_data": f"promo_{promo['id']}"}])
    
    keyboard["inline_keyboard"].append([{"text": "🔙 Kembali ke Menu", "callback_data": "back_to_menu"}])
    
    send_telegram_message(chat_id, "*📋 DAFTAR PROMO ABAD4D*\n\nKlik promo yang ingin kamu lihat:", reply_markup=keyboard)

def send_contact_request(chat_id):
    contact_keyboard = {
        "keyboard": [[{"text": "📱 Share Nomor Saya", "request_contact": True}]],
        "resize_keyboard": True,
        "one_time_keyboard": True
    }
    
    msg = """📞 *SHARE KONTAK ANDA*

Dengan membagikan nomor telepon, Anda akan mendapatkan update promo terbaru!

👇 Tekan tombol di bawah untuk share kontak👇"""
    
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": msg,
        "parse_mode": "Markdown",
        "reply_markup": json.dumps(contact_keyboard)
    }
    
    try:
        requests.post(url, json=payload, timeout=30)
    except Exception as e:
        print(f"Error: {e}")

# ============ WEBHOOK UTAMA ============
@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"status": "ok"})
        
        # Proses message
        if "message" in data:
            message = data["message"]
            chat_id = message["chat"]["id"]
            text = message.get("text", "")
            username = message["chat"].get("username", "unknown")
            
            # Simpan user baru
            current_users = load_users()
            if chat_id not in current_users:
                current_users.add(chat_id)
                save_users(current_users)
                print(f"📝 User baru: @{username} ({chat_id})")
            
            # Cek kontak yang dishare
            contact = message.get("contact")
            if contact:
                phone_number = contact.get("phone_number")
                first_name = contact.get("first_name", "")
                last_name = contact.get("last_name", "")
                user_id = contact.get("user_id", chat_id)
                
                save_contact(user_id, username, first_name, last_name, phone_number)
                
                confirm_msg = f"""✅ *TERIMA KASIH TELAH SHARE KONTAK!*

Halo *{first_name}*, nomor Anda *{phone_number}* telah tersimpan.

🏠 Ketik /start untuk kembali ke menu utama"""
                send_telegram_message(chat_id, confirm_msg)
                
                # Notifikasi ke admin
                admin_msg = f"📞 KONTAK BARU!\nNama: {first_name}\nNomor: {phone_number}"
                send_telegram_message(ADMIN_ID, admin_msg)
                
                # Hapus keyboard
                remove_keyboard = {"remove_keyboard": True}
                url_remove = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
                requests.post(url_remove, json={
                    "chat_id": chat_id,
                    "text": "Ketik /start untuk kembali",
                    "reply_markup": json.dumps(remove_keyboard)
                })
            
            # Handle perintah
            elif text == "/start":
                send_main_menu(chat_id)
                print(f"📨 Menu sent to @{username}")
            
            elif text == "/share":
                send_contact_request(chat_id)
            
            elif text == "/promos":
                send_promo_list(chat_id)
            
            elif text == "/help":
                help_msg = """📖 *Panduan Bot Abad4D*

/start - Menu utama
/help - Panduan ini
/promos - Lihat daftar promo
/share - Share kontak Anda

🔒 Data Anda aman dan terjaga kerahasiaannya"""
                send_telegram_message(chat_id, help_msg)
            
            elif text == "/status" and str(chat_id) == str(ADMIN_ID):
                status_msg = f"""📊 *STATUS BOT*

👥 Total user: {len(load_users())}
📞 Total kontak: {len(get_all_contacts())}
🎁 Total promo: {len(promos)}
⏱️ Interval: {promo_settings.get('broadcast_interval_minutes', 20)} menit
✅ Status: AKTIF"""
                send_telegram_message(chat_id, status_msg)
            
            else:
                send_main_menu(chat_id)
        
        # Proses callback query
        elif "callback_query" in data:
            callback = data["callback_query"]
            chat_id = callback["message"]["chat"]["id"]
            data_callback = callback.get("data", "")
            
            if data_callback == "share_contact":
                send_contact_request(chat_id)
            elif data_callback == "list_promos":
                send_promo_list(chat_id)
            elif data_callback == "back_to_menu":
                send_main_menu(chat_id)
            elif data_callback == "help":
                help_msg = """📖 *Panduan Bot Abad4D*

📌 *Cara Penggunaan:*
• Klik tombol "Lihat Semua Promo" untuk melihat daftar promo
• Klik promo yang ingin dilihat detailnya
• Klik tombol "Kunjungi Website" untuk langsung ke website

🎁 *Bonus Share Kontak:*
• Member yang share kontak dapat bonus special

⏰ *Broadcast Otomatis:*
Bot akan mengirim promo menarik setiap 20 menit!"""
                send_telegram_message(chat_id, help_msg)
            elif data_callback.startswith("promo_"):
                try:
                    promo_id = int(data_callback.split("_")[1])
                    promo = next((p for p in promos if p.get('id') == promo_id), None)
                    if promo:
                        msg = f"*{promo['title']}*\n\n{promo.get('message', '')}"
                        keyboard = {
                            "inline_keyboard": [
                                [{"text": promo.get('button_text', '🔥 Klaim Bonus'), "url": promo.get('button_url', config.get('website_url'))}],
                                [{"text": "🔙 Kembali ke Daftar Promo", "callback_data": "list_promos"}],
                                [{"text": "🏠 Menu Utama", "callback_data": "back_to_menu"}]
                            ]
                        }
                        send_telegram_message(chat_id, msg, reply_markup=keyboard)
                    else:
                        send_telegram_message(chat_id, "Promo tidak ditemukan.")
                except Exception as e:
                    print(f"Error: {e}")
            
            # Answer callback
            url_answer = f"https://api.telegram.org/bot{TOKEN}/answerCallbackQuery"
            requests.post(url_answer, json={"callback_query_id": callback["id"]})
        
        return jsonify({"status": "ok"})
    except Exception as e:
        print(f"Webhook error: {e}")
        return jsonify({"status": "error"}), 500

# ============ BROADCAST OTOMATIS ============
def broadcast_promo_auto():
    global last_broadcast_time
    
    if not promos:
        return
    
    interval = promo_settings.get("broadcast_interval_minutes", 20)
    interval_seconds = interval * 60
    
    while True:
        time.sleep(60)  # Cek setiap menit
        
        now = time.time()
        
        if last_broadcast_time is None:
            last_broadcast_time = now
            print(f"⏰ Broadcast pertama dalam {interval} menit")
            continue
        
        if now - last_broadcast_time >= interval_seconds:
            # Kirim broadcast
            promo = random.choice(promos)
            users_list = list(load_users())
            
            print(f"📢 Broadcasting: {promo['title']} ke {len(users_list)} user")
            
            for user_id in users_list:
                send_telegram_message(
                    user_id,
                    promo.get('message', ''),
                    {
                        "inline_keyboard": [[{"text": promo.get('button_text', '🔥 Klaim Bonus'), "url": promo.get('button_url', config.get('website_url'))}]]
                    }
                )
                time.sleep(0.1)
            
            last_broadcast_time = now
            print(f"✅ Broadcast selesai!")

# ============ FLASK ROUTES ============
@app.route('/')
def home():
    return """
    <html>
    <head><title>Abad4D Bot</title></head>
    <body style="font-family: Arial; text-align: center; padding: 50px;">
        <h1>🤖 Abad4D Bot is Running!</h1>
        <p style="color: green;">✅ BOT AKTIF!</p>
        <p>Mode: <strong>Webhook</strong></p>
        <p>📞 Fitur Share Kontak: <strong>AKTIF</strong></p>
        <hr>
        <p>📱 Kirim <code>/start</code> ke bot di Telegram</p>
        <p><a href="/set_webhook">Klik untuk set webhook</a></p>
    </body>
    </html>
    """

@app.route('/set_webhook')
def set_webhook():
    render_url = os.environ.get('RENDER_EXTERNAL_URL', request.host_url)
    if render_url.endswith('/'):
        render_url = render_url[:-1]
    webhook_url = f"{render_url}/webhook"
    
    # Hapus webhook lama dulu
    requests.post(f"https://api.telegram.org/bot{TOKEN}/deleteWebhook")
    
    # Set webhook baru
    url = f"https://api.telegram.org/bot{TOKEN}/setWebhook"
    response = requests.post(url, json={"url": webhook_url})
    result = response.json()
    
    if result.get("ok"):
        return f"✅ Webhook berhasil diatur! URL: {webhook_url}"
    else:
        return f"❌ Gagal: {result}"

@app.route('/health')
def health():
    return "OK", 200

@app.route('/api/contacts')
def api_contacts():
    return jsonify(get_all_contacts())

@app.route('/api/stats')
def api_stats():
    return jsonify({
        'users': len(load_users()),
        'contacts': len(get_all_contacts()),
        'promos': len(promos)
    })

# ============ MAIN ============
if __name__ == "__main__":
    import threading
    
    print("=" * 50)
    print("🤖 ABAD4D BOT TELEGRAM")
    print("=" * 50)
    
    # Start broadcast thread
    broadcast_thread = threading.Thread(target=broadcast_promo_auto, daemon=True)
    broadcast_thread.start()
    print("✅ Broadcast thread started")
    
    print(f"✅ Bot siap!")
    print(f"📞 Share Kontak: AKTIF")
    print("=" * 50)
    
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
