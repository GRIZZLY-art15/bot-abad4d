import json
import os
import random
import threading
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
            return data.get("promos", []), data.get("settings", {"broadcast_interval_minutes": 20, "send_image": True})
    except Exception as e:
        print(f"Error loading promos: {e}")
        return [], {"broadcast_interval_minutes": 20, "send_image": True}

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

print(f"✅ Loaded {len(promos)} promos")
print(f"✅ Send image: {promo_settings.get('send_image', True)}")

# ============ FUNGSI KONTAK ============
def save_contact(user_id, username, first_name, last_name, phone_number):
    try:
        contacts = []
        if os.path.exists(CONTACTS_FILE):
            with open(CONTACTS_FILE, "r", encoding="utf-8") as f:
                contacts = json.load(f)
        
        # Cek duplikat
        existing = False
        for i, c in enumerate(contacts):
            if c.get("user_id") == user_id:
                contacts[i] = {
                    "user_id": user_id,
                    "username": username,
                    "first_name": first_name,
                    "last_name": last_name or "",
                    "full_name": f"{first_name} {last_name or ''}".strip(),
                    "phone_number": phone_number,
                    "shared_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                existing = True
                break
        
        if not existing:
            contacts.append({
                "user_id": user_id,
                "username": username,
                "first_name": first_name,
                "last_name": last_name or "",
                "full_name": f"{first_name} {last_name or ''}".strip(),
                "phone_number": phone_number,
                "shared_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
        
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

def get_contact_count():
    return len(get_all_contacts())

# ============ FUNGSI TELEGRAM (DENGAN DUKUNGAN GAMBAR) ============
def send_telegram_photo(chat_id, photo_url, caption, reply_markup=None):
    """Kirim pesan dengan gambar"""
    url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
    payload = {
        "chat_id": chat_id,
        "photo": photo_url,
        "caption": caption,
        "parse_mode": "Markdown"
    }
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        return response.json()
    except Exception as e:
        print(f"Error send photo: {e}")
        return None

def send_telegram_message(chat_id, text, reply_markup=None):
    """Kirim pesan teks biasa"""
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
        print(f"Error send message: {e}")
        return None

def send_promo_with_image(chat_id, promo):
    """Kirim promo lengkap dengan gambar"""
    send_image = promo_settings.get("send_image", True)
    image_url = promo.get("image_url", "")
    
    # Keyboard untuk tombol
    keyboard = {
        "inline_keyboard": [
            [{"text": promo.get("button_text", "🔥 Klaim Bonus"), "url": promo.get("button_url", config.get("website_url"))}],
            [{"text": "🔙 Kembali ke Daftar Promo", "callback_data": "list_promos"}],
            [{"text": "🏠 Menu Utama", "callback_data": "back_to_menu"}]
        ]
    }
    
    # Kirim dengan gambar jika ada dan send_image aktif
    if send_image and image_url and image_url.strip():
        result = send_telegram_photo(chat_id, image_url, promo.get("message", ""), keyboard)
        if result and result.get("ok"):
            print(f"✅ Promo dengan gambar terkirim: {promo['title']}")
            return True
        else:
            # Fallback ke teks biasa jika gambar gagal
            print(f"⚠️ Gagal kirim gambar, fallback ke teks: {promo['title']}")
            return send_telegram_message(chat_id, promo.get("message", ""), keyboard)
    else:
        # Kirim teks biasa tanpa gambar
        return send_telegram_message(chat_id, promo.get("message", ""), keyboard)

def send_main_menu(chat_id):
    """Kirim menu utama"""
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
    """Kirim daftar promo dengan tombol"""
    if not promos:
        send_telegram_message(chat_id, "Belum ada promo tersedia.")
        return
    
    keyboard = {"inline_keyboard": []}
    
    # Buat tombol untuk setiap promo (2 kolom biar rapi)
    row = []
    for promo in promos:
        button_text = f"{promo['title'][:25]}"
        row.append({"text": button_text, "callback_data": f"promo_{promo['id']}"})
        if len(row) == 2:
            keyboard["inline_keyboard"].append(row)
            row = []
    if row:
        keyboard["inline_keyboard"].append(row)
    
    keyboard["inline_keyboard"].append([{"text": "🔙 Kembali ke Menu", "callback_data": "back_to_menu"}])
    
    send_telegram_message(chat_id, "*📋 DAFTAR PROMO ABAD4D*\n\nKlik promo yang ingin kamu lihat:", reply_markup=keyboard)

def send_contact_request(chat_id):
    """Kirim tombol share kontak"""
    contact_keyboard = {
        "keyboard": [[{"text": "📱 Share Nomor Saya", "request_contact": True}]],
        "resize_keyboard": True,
        "one_time_keyboard": True
    }
    
    msg = """📞 *SHARE KONTAK ANDA*

Dengan membagikan nomor telepon, Anda akan:
✅ Mendapatkan update promo terbaru via WhatsApp
✅ Mendapatkan bonus special untuk member terverifikasi
✅ Memudahkan CS kami untuk menghubungi Anda

🔒 *Data Anda aman dan tidak akan disebarluaskan*

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
        print(f"Error send contact request: {e}")

# ============ BROADCAST OTOMATIS ============
def broadcast_promo_auto():
    global last_broadcast_time
    
    if not promos:
        print("❌ Tidak ada promo untuk broadcast")
        return
    
    interval = promo_settings.get("broadcast_interval_minutes", 20)
    interval_seconds = interval * 60
    
    print(f"🔄 Broadcast auto dimulai! Interval: {interval} menit")
    
    while True:
        time.sleep(60)  # Cek setiap menit
        
        now = time.time()
        
        if last_broadcast_time is None:
            last_broadcast_time = now
            print(f"⏰ Broadcast pertama dalam {interval} menit")
            continue
        
        if now - last_broadcast_time >= interval_seconds:
            # Pilih promo acak
            promo = random.choice(promos)
            users_list = list(load_users())
            
            if not users_list:
                print("⚠️ Tidak ada user untuk broadcast")
                last_broadcast_time = now
                continue
            
            print(f"=" * 50)
            print(f"📢 BROADCAST: {promo['title']}")
            print(f"👥 Target: {len(users_list)} user")
            
            success = 0
            fail = 0
            
            for user_id in users_list:
                result = send_promo_with_image(user_id, promo)
                if result:
                    success += 1
                else:
                    fail += 1
                time.sleep(0.1)  # Jeda antar kirim
            
            last_broadcast_time = now
            print(f"✅ Broadcast selesai! Berhasil: {success}, Gagal: {fail}")
            print(f"📅 Waktu: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("=" * 50)

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
            first_name = message["chat"].get("first_name", "")
            
            # Simpan user baru
            current_users = load_users()
            if chat_id not in current_users:
                current_users.add(chat_id)
                save_users(current_users)
                print(f"📝 User baru: {first_name} (@{username}) - ID: {chat_id}")
            
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

🎁 *BONUS UNTUK ANDA:*
Member yang sudah share kontak berhak mendapatkan bonus special!

🏠 Ketik /start untuk kembali ke menu utama"""
                send_telegram_message(chat_id, confirm_msg)
                
                # Notifikasi ke admin
                admin_msg = f"""📞 *KONTAK BARU!*

👤 Nama: {first_name} {last_name}
🆔 Username: @{username if username != 'unknown' else '-'}
📱 Nomor: {phone_number}
🕐 Waktu: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
📊 Total Kontak: {get_contact_count()}"""
                send_telegram_message(ADMIN_ID, admin_msg)
                
                # Hapus keyboard
                remove_keyboard = {"remove_keyboard": True}
                url_remove = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
                requests.post(url_remove, json={
                    "chat_id": chat_id,
                    "text": "✅ Terima kasih! Ketik /start untuk kembali ke menu utama",
                    "reply_markup": json.dumps(remove_keyboard)
                })
                print(f"📞 Kontak tersimpan dari {first_name} - {phone_number}")
            
            # Handle perintah
            elif text == "/start":
                send_main_menu(chat_id)
                print(f"📨 Menu sent to {first_name} (@{username})")
            
            elif text == "/share":
                send_contact_request(chat_id)
                print(f"📨 Share request sent to {first_name}")
            
            elif text == "/promos":
                send_promo_list(chat_id)
                print(f"📨 Promo list sent to {first_name}")
            
            elif text == "/help":
                help_msg = """📖 *Panduan Bot Abad4D*

/start - Menu utama
/help - Panduan ini
/promos - Lihat daftar promo
/share - Share kontak Anda

*Fitur:*
✅ Share kontak untuk dapat bonus
✅ Update promo via WhatsApp
✅ Gambar promo tampil otomatis

🔒 Data Anda aman dan terjaga kerahasiaannya"""
                send_telegram_message(chat_id, help_msg)
            
            elif text == "/status" and str(chat_id) == str(ADMIN_ID):
                status_msg = f"""📊 *STATUS BOT*

🔄 Status: ✅ AKTIF
👥 Total user: {len(load_users())}
📞 Total kontak: {get_contact_count()}
🎁 Total promo: {len(promos)}
⏱️ Interval broadcast: {promo_settings.get('broadcast_interval_minutes', 20)} menit
🖼️ Mode gambar: {'AKTIF' if promo_settings.get('send_image', True) else 'NONAKTIF'}

📅 Last update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
                send_telegram_message(chat_id, status_msg)
                print(f"📊 Status sent to admin")
            
            elif text == "/contacts" and str(chat_id) == str(ADMIN_ID):
                contacts = get_all_contacts()
                if contacts:
                    msg = "*📞 DAFTAR KONTAK*\n\n"
                    for i, c in enumerate(contacts[-10:], 1):
                        msg += f"{i}. {c.get('full_name', '-')} - {c.get('phone_number', '-')}\n"
                    msg += f"\n📊 Total: {len(contacts)} kontak\n\nGunakan /export_contacts untuk export semua"
                    send_telegram_message(chat_id, msg)
                else:
                    send_telegram_message(chat_id, "Belum ada kontak yang tersimpan.")
            
            elif text == "/export_contacts" and str(chat_id) == str(ADMIN_ID):
                contacts = get_all_contacts()
                if contacts:
                    msg = "📞 *EXPORT KONTAK*\n\n"
                    for c in contacts:
                        msg += f"👤 {c.get('full_name', '-')} | 📱 {c.get('phone_number', '-')}\n"
                    
                    if len(msg) > 4000:
                        for i in range(0, len(msg), 4000):
                            send_telegram_message(chat_id, msg[i:i+4000])
                    else:
                        send_telegram_message(chat_id, msg)
                else:
                    send_telegram_message(chat_id, "Belum ada kontak.")
            
            else:
                send_main_menu(chat_id)
        
        # Proses callback query (tombol inline)
        elif "callback_query" in data:
            callback = data["callback_query"]
            chat_id = callback["message"]["chat"]["id"]
            data_callback = callback.get("data", "")
            username = callback["from"].get("username", "unknown")
            
            if data_callback == "share_contact":
                send_contact_request(chat_id)
                print(f"📨 Share contact via callback to @{username}")
            
            elif data_callback == "list_promos":
                send_promo_list(chat_id)
                print(f"📨 Promo list via callback to @{username}")
            
            elif data_callback == "back_to_menu":
                send_main_menu(chat_id)
                print(f"📨 Back to menu via callback to @{username}")
            
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
                        send_promo_with_image(chat_id, promo)
                        print(f"📨 Promo {promo['title']} sent to @{username}")
                    else:
                        send_telegram_message(chat_id, "Promo tidak ditemukan.")
                except Exception as e:
                    print(f"Error promo callback: {e}")
                    send_telegram_message(chat_id, "Terjadi kesalahan. Silakan coba lagi.")
            
            # Answer callback query
            url_answer = f"https://api.telegram.org/bot{TOKEN}/answerCallbackQuery"
            requests.post(url_answer, json={"callback_query_id": callback["id"]})
        
        return jsonify({"status": "ok"})
    except Exception as e:
        print(f"Webhook error: {e}")
        return jsonify({"status": "error"}), 500

# ============ FLASK ROUTES ============
@app.route('/')
def home():
    return """
    <html>
    <head>
        <title>Abad4D Bot</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { font-family: Arial, sans-serif; text-align: center; padding: 50px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; margin: 0; }
            .container { background: white; border-radius: 20px; padding: 40px; max-width: 800px; margin: 0 auto; box-shadow: 0 20px 60px rgba(0,0,0,0.3); }
            h1 { color: #764ba2; }
            .status { color: #28a745; font-size: 20px; font-weight: bold; }
            .info { background: #f8f9fa; padding: 20px; border-radius: 10px; margin: 20px 0; text-align: left; }
            .api-links { display: flex; flex-wrap: wrap; gap: 10px; justify-content: center; margin-top: 20px; }
            .api-link { background: #764ba2; color: white; padding: 10px 20px; border-radius: 8px; text-decoration: none; }
            .api-link:hover { background: #5a3a8a; }
            .footer { margin-top: 30px; color: #666; font-size: 12px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🤖 ABAD4D BOT TELEGRAM</h1>
            <div class="status">✅ BOT AKTIF!</div>
            <p>Mode: <strong>Webhook</strong></p>
            <p>🖼️ Gambar Promo: <strong>AKTIF</strong></p>
            <p>📞 Share Kontak: <strong>AKTIF</strong></p>
            
            <div class="info">
                <h3>📋 Perintah Telegram:</h3>
                <p><code>/start</code> - Menu utama</p>
                <p><code>/share</code> - Share kontak</p>
                <p><code>/promos</code> - Lihat promo</p>
                <p><code>/help</code> - Bantuan</p>
                <hr>
                <h3>🔐 Perintah Admin:</h3>
                <p><code>/status</code> - Status bot</p>
                <p><code>/contacts</code> - Lihat kontak</p>
                <p><code>/export_contacts</code> - Export kontak</p>
            </div>
            
            <div class="api-links">
                <a href="/api/stats" class="api-link">📊 Statistik</a>
                <a href="/api/contacts" class="api-link">📞 Kontak</a>
                <a href="/set_webhook" class="api-link">🔧 Set Webhook</a>
            </div>
            
            <div class="footer">
                <p>📱 Kirim <code>/start</code> ke bot di Telegram untuk mulai!</p>
                <p>© 2024 Abad4D Bot</p>
            </div>
        </div>
    </body>
    </html>
    """

@app.route('/set_webhook')
def set_webhook():
    render_url = os.environ.get('RENDER_EXTERNAL_URL', request.host_url)
    if render_url.endswith('/'):
        render_url = render_url[:-1]
    webhook_url = f"{render_url}/webhook"
    
    # Hapus webhook lama
    requests.post(f"https://api.telegram.org/bot{TOKEN}/deleteWebhook")
    
    # Set webhook baru
    url = f"https://api.telegram.org/bot{TOKEN}/setWebhook"
    response = requests.post(url, json={"url": webhook_url})
    result = response.json()
    
    if result.get("ok"):
        return f"""
        <html>
        <body style="font-family: Arial; text-align: center; padding: 50px;">
            <h1>✅ Webhook Berhasil Diatur!</h1>
            <p>URL: <code>{webhook_url}</code></p>
            <p>🖼️ Sekarang gambar promo akan tampil!</p>
            <p><a href="/">Kembali ke Home</a></p>
        </body>
        </html>
        """
    else:
        return f"❌ Gagal: {result}"

@app.route('/health')
def health():
    return "OK", 200

@app.route('/api/contacts')
def api_contacts():
    return jsonify({
        'total': get_contact_count(),
        'contacts': get_all_contacts()
    })

@app.route('/api/stats')
def api_stats():
    return jsonify({
        'users': len(load_users()),
        'contacts': get_contact_count(),
        'promos': len(promos),
        'send_image': promo_settings.get('send_image', True),
        'interval': promo_settings.get('broadcast_interval_minutes', 20),
        'status': 'active'
    })

@app.route('/api/promos')
def api_promos():
    return jsonify({
        'total': len(promos),
        'promos': promos
    })

# ============ MAIN ============
if __name__ == "__main__":
    print("=" * 60)
    print("🤖 ABAD4D BOT TELEGRAM - DENGAN GAMBAR")
    print("=" * 60)
    
    # Cek koneksi bot
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/getMe"
        response = requests.get(url, timeout=10)
        if response.ok:
            bot_info = response.json().get("result")
            print(f"✅ Bot terhubung: @{bot_info.get('username')}")
        else:
            print("❌ Token tidak valid!")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print(f"✅ Total promo: {len(promos)}")
    print(f"🖼️ Mode gambar: {'AKTIF' if promo_settings.get('send_image', True) else 'NONAKTIF'}")
    print(f"👥 Total user: {len(load_users())}")
    print(f"📞 Total kontak: {get_contact_count()}")
    print("=" * 60)
    
    # Start broadcast thread
    broadcast_thread = threading.Thread(target=broadcast_promo_auto, daemon=True)
    broadcast_thread.start()
    print("✅ Broadcast thread started")
    
    print("\n📱 Buka URL /set_webhook untuk mengaktifkan webhook")
    print("📱 Kirim /start ke bot di Telegram untuk test")
    print("=" * 60)
    
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
