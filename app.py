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

# File untuk menyimpan kontak
CONTACTS_FILE = "contacts.json"
DATA_FILE = "users.json"
PROMO_FILE = "promo.json"
CONFIG_FILE = "config.json"

# Variabel untuk tracking broadcast
broadcast_status = {
    "last_broadcast_time": None,
    "last_broadcast_title": None,
    "next_broadcast_in": 0,
    "total_broadcasts_sent": 0,
    "is_running": True
}

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
            promos = data.get("promos", [])
            settings = data.get("settings", {})
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

# Load data awal
users = load_users()
promos, promo_settings = load_promos()
config = load_config()

# ============ FUNGSI UNTUK MENYIMPAN KONTAK ============
def save_contact(user_id, username, first_name, last_name, phone_number):
    """Menyimpan kontak user ke file JSON"""
    try:
        contacts = []
        if os.path.exists(CONTACTS_FILE):
            with open(CONTACTS_FILE, "r", encoding="utf-8") as f:
                contacts = json.load(f)
        
        existing_index = None
        for i, contact in enumerate(contacts):
            if contact.get("user_id") == user_id:
                existing_index = i
                break
        
        new_contact = {
            "user_id": user_id,
            "username": username,
            "first_name": first_name,
            "last_name": last_name or "",
            "full_name": f"{first_name} {last_name or ''}".strip(),
            "phone_number": phone_number,
            "shared_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "is_verified": True
        }
        
        if existing_index is not None:
            contacts[existing_index] = new_contact
            print(f"📞 [UPDATE] Kontak user {first_name} ({user_id}) diperbarui")
        else:
            contacts.append(new_contact)
            print(f"📞 [NEW] Kontak baru dari {first_name} ({user_id}) - {phone_number}")
        
        with open(CONTACTS_FILE, "w", encoding="utf-8") as f:
            json.dump(contacts, f, indent=2, ensure_ascii=False)
        
        return True
    except Exception as e:
        print(f"❌ Error saving contact: {e}")
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

# ============ TELEGRAM FUNCTIONS ============
def send_telegram_message(chat_id, text, photo_url=None, button_text=None, button_url=None, reply_markup=None):
    """Kirim pesan ke Telegram"""
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
    """Kirim daftar promo"""
    if not promos:
        send_telegram_message(chat_id, "Belum ada promo tersedia.")
        return
    
    keyboard = []
    row = []
    for i, promo in enumerate(promos, 1):
        row.append({"text": f"{i}. {promo['title'][:20]}", "callback_data": f"promo_{promo['id']}"})
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    keyboard.append([{"text": "🔙 Kembali ke Menu", "callback_data": "back_to_menu"}])
    
    reply_markup = {"inline_keyboard": keyboard}
    send_telegram_message(chat_id, "*📋 DAFTAR PROMO ABAD4D*\n\nKlik promo yang ingin kamu lihat:", reply_markup=reply_markup)

def send_contact_request(chat_id):
    """Kirim tombol share kontak"""
    contact_keyboard = {
        "keyboard": [
            [{"text": "📱 Share Nomor Saya", "request_contact": True}]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": True
    }
    
    msg = """📞 *SHARE KONTAK ANDA*

Dengan membagikan nomor telepon, Anda akan mendapatkan update promo terbaru dan bonus special!

🔒 *Data Anda aman dan terjaga kerahasiaannya*

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
    
    broadcast_status["last_broadcast_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    broadcast_status["last_broadcast_title"] = promo['title']
    broadcast_status["total_broadcasts_sent"] += 1
    
    print("=" * 60)
    print(f"✅ [BROADCAST] Selesai! Berhasil: {success}, Gagal: {fail}")
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

# ============ PROSES UPDATE DARI TELEGRAM (POLLING) ============
last_update_id = 0

def process_updates():
    """Proses update dari Telegram dengan metode polling (tanpa webhook)"""
    global last_update_id
    
    print("🔄 Memulai polling ke Telegram API...")
    
    while True:
        try:
            url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
            response = requests.get(url, params={
                "offset": last_update_id + 1,
                "timeout": 30
            }, timeout=35)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("ok"):
                    updates = data.get("result", [])
                    
                    for update in updates:
                        print(f"📨 Update received: {update.get('update_id')}")
                        last_update_id = update.get("update_id", last_update_id)
                        
                        # Proses message
                        if "message" in update:
                            message = update["message"]
                            chat_id = message["chat"]["id"]
                            text = message.get("text", "")
                            username = message["chat"].get("username", "unknown")
                            
                            # Simpan user baru
                            current_users = load_users()
                            if chat_id not in current_users:
                                current_users.add(chat_id)
                                save_users(current_users)
                                print(f"📝 User baru: {username} ({chat_id})")
                            
                            # Cek apakah ada kontak yang dishare
                            contact = message.get("contact")
                            
                            if contact:
                                # User share kontak
                                phone_number = contact.get("phone_number")
                                first_name = contact.get("first_name", "")
                                last_name = contact.get("last_name", "")
                                user_id = contact.get("user_id", chat_id)
                                
                                save_contact(user_id, username, first_name, last_name, phone_number)
                                
                                confirm_msg = f"""✅ *TERIMA KASIH TELAH SHARE KONTAK!*

Halo *{first_name}*, nomor Anda *{phone_number}* telah tersimpan.

🎁 *BONUS UNTUK ANDA:*
Member yang sudah share kontak berhak mendapatkan bonus special!

🏠 Ketik /start untuk kembali ke menu utama
"""
                                send_telegram_message(chat_id, confirm_msg)
                                
                                # Notifikasi ke admin
                                admin_msg = f"""📞 *KONTAK BARU!*

👤 Nama: {first_name} {last_name}
📱 Nomor: {phone_number}
🕐 Waktu: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
📊 Total Kontak: {get_contact_count()}
"""
                                send_telegram_message(ADMIN_ID, admin_msg)
                                
                                # Hapus keyboard
                                remove_keyboard = {"remove_keyboard": True}
                                url_remove = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
                                requests.post(url_remove, json={
                                    "chat_id": chat_id,
                                    "text": "Ketik /start untuk kembali",
                                    "reply_markup": json.dumps(remove_keyboard)
                                })
                            
                            # Handle perintah teks
                            elif text == "/start":
                                send_main_menu(chat_id)
                                print(f"📨 Menu sent to {username}")
                            
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

*Fitur Baru:*
✅ Share kontak untuk dapat bonus
✅ Update promo via WhatsApp
✅ Notifikasi event khusus

🔒 Data Anda aman dan terjaga kerahasiaannya"""
                                send_telegram_message(chat_id, help_msg)
                            
                            elif text == "/status" and str(chat_id) == str(ADMIN_ID):
                                remaining = broadcast_status.get("next_broadcast_in", 0)
                                remaining_min = int(remaining // 60)
                                
                                status_msg = f"""📊 *STATUS BROADCAST*

🔄 Status: ✅ AKTIF
⏰ Next broadcast: {remaining_min} menit lagi
📊 Total broadcast: {broadcast_status.get('total_broadcasts_sent', 0)} kali
👥 Total user: {len(load_users())}
📞 Total kontak: {get_contact_count()}
🎁 Total promo: {len(promos)}
⏱️ Interval: {promo_settings.get('broadcast_interval_minutes', 20)} menit"""
                                send_telegram_message(chat_id, status_msg)
                            
                            elif text == "/contacts" and str(chat_id) == str(ADMIN_ID):
                                contacts = get_all_contacts()
                                if contacts:
                                    msg = "*📞 DAFTAR KONTAK*\n\n"
                                    for i, c in enumerate(contacts[-10:], 1):
                                        msg += f"{i}. {c.get('full_name', '-')} - {c.get('phone_number', '-')}\n"
                                    msg += f"\n📊 Total: {len(contacts)} kontak"
                                    send_telegram_message(chat_id, msg)
                                else:
                                    send_telegram_message(chat_id, "Belum ada kontak.")
                            
                            else:
                                send_main_menu(chat_id)
                        
                        # Proses callback query (tombol inline)
                        elif "callback_query" in update:
                            callback = update["callback_query"]
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
                                        send_telegram_message(
                                            chat_id,
                                            promo.get('message', ''),
                                            promo.get('image_url'),
                                            promo.get('button_text', '🔥 Klaim Bonus'),
                                            promo.get('button_url', config.get('website_url'))
                                        )
                                        time.sleep(0.5)
                                        keyboard = {
                                            "inline_keyboard": [
                                                [{"text": "🔙 Kembali ke Daftar Promo", "callback_data": "list_promos"}],
                                                [{"text": "📞 Share Kontak", "callback_data": "share_contact"}],
                                                [{"text": "🏠 Menu Utama", "callback_data": "back_to_menu"}]
                                            ]
                                        }
                                        send_telegram_message(chat_id, "👇 Pilih aksi selanjutnya:", reply_markup=keyboard)
                                    else:
                                        send_telegram_message(chat_id, "Promo tidak ditemukan.")
                                except Exception as e:
                                    print(f"Error: {e}")
                            
                            # Answer callback query
                            url_answer = f"https://api.telegram.org/bot{TOKEN}/answerCallbackQuery"
                            requests.post(url_answer, json={"callback_query_id": callback["id"]})
            
            time.sleep(1)
        except Exception as e:
            print(f"❌ Polling error: {e}")
            time.sleep(5)

# ============ FLASK ROUTES ============
@app.route('/')
def home():
    return """
    <html>
    <head><title>Abad4D Bot</title></head>
    <body style="font-family: Arial; text-align: center; padding: 50px;">
        <h1>🤖 Abad4D Bot is Running!</h1>
        <p style="color: green; font-size: 20px;">✅ BOT AKTIF!</p>
        <p>Mode: <strong>Polling (tanpa webhook)</strong></p>
        <p>⏰ Broadcast setiap 20 menit</p>
        <p>📞 Fitur Share Kontak: <strong>AKTIF</strong></p>
        <hr>
        <p>📱 Coba kirim <code>/start</code> ke bot di Telegram</p>
        <p>📊 <a href="/api/broadcast_status">Cek Status Broadcast</a></p>
        <p>📞 <a href="/api/contacts">Lihat Kontak</a></p>
    </body>
    </html>
    """

@app.route('/health')
def health():
    return "OK", 200

@app.route('/api/broadcast_status')
def api_broadcast_status():
    return jsonify({
        'is_running': broadcast_status["is_running"],
        'last_broadcast_time': broadcast_status.get("last_broadcast_time", "Belum pernah"),
        'last_broadcast_title': broadcast_status.get("last_broadcast_title", "-"),
        'next_broadcast_in_minutes': round(broadcast_status.get("next_broadcast_in", 0) / 60, 1),
        'total_broadcasts_sent': broadcast_status.get("total_broadcasts_sent", 0),
        'interval_minutes': promo_settings.get('broadcast_interval_minutes', 20),
        'total_users': len(load_users()),
        'total_contacts': get_contact_count()
    })

@app.route('/api/contacts')
def api_get_contacts():
    contacts = get_all_contacts()
    return jsonify({
        'total': len(contacts),
        'contacts': contacts
    })

@app.route('/api/contacts/export')
def api_export_contacts():
    import csv
    from io import StringIO
    
    contacts = get_all_contacts()
    
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['User ID', 'Username', 'Nama Lengkap', 'Nomor Telepon', 'Tanggal Share'])
    
    for c in contacts:
        writer.writerow([
            c.get('user_id', ''),
            c.get('username', ''),
            c.get('full_name', ''),
            c.get('phone_number', ''),
            c.get('shared_at', '')
        ])
    
    return output.getvalue(), 200, {
        'Content-Type': 'text/csv',
        'Content-Disposition': 'attachment; filename=contacts.csv'
    }

@app.route('/api/stats')
def api_stats():
    return jsonify({
        'total_users': len(load_users()),
        'total_promos': len(promos),
        'total_contacts': get_contact_count(),
        'broadcast_interval': promo_settings.get('broadcast_interval_minutes', 20),
        'website_url': config.get('website_url')
    })

@app.route('/api/promos')
def api_get_promos():
    return jsonify(promos)

# ============ MAIN ============
if __name__ == "__main__":
    print("=" * 60)
    print("🤖 ABAD4D BOT TELEGRAM - MODE POLLING")
    print("=" * 60)
    
    # Cek token bot
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/getMe"
        response = requests.get(url, timeout=10)
        if response.status_code == 200 and response.json().get("ok"):
            bot_info = response.json().get("result")
            print(f"✅ Bot terhubung: @{bot_info.get('username')}")
        else:
            print(f"❌ Token tidak valid! Periksa TOKEN Anda.")
            exit(1)
    except Exception as e:
        print(f"❌ Gagal koneksi ke Telegram API: {e}")
        exit(1)
    
    # Hapus webhook jika ada
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/deleteWebhook"
        response = requests.post(url, json={"drop_pending_updates": True}, timeout=10)
        if response.json().get("ok"):
            print("✅ Webhook berhasil dihapus")
    except:
        pass
    
    # Inisialisasi file
    if not os.path.exists(CONTACTS_FILE):
        with open(CONTACTS_FILE, "w") as f:
            json.dump([], f)
    
    # Start broadcast thread
    broadcast_thread = threading.Thread(target=broadcast_loop, daemon=True)
    broadcast_thread.start()
    
    # Start polling thread
    polling_thread = threading.Thread(target=process_updates, daemon=True)
    polling_thread.start()
    
    print(f"\n✅ Bot siap menerima pesan!")
    print(f"📞 Fitur Share Kontak: AKTIF")
    print(f"🔄 Broadcast: setiap {promo_settings.get('broadcast_interval_minutes', 20)} menit")
    print(f"\n📱 Kirim /start ke bot di Telegram untuk test")
    print("=" * 60)
    
    # Jalankan Flask server
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
