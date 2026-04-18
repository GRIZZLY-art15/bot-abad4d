import requests
import json
import time
import threading
import random
from datetime import datetime

# ========== GANTI DENGAN TOKEN DAN ID KAMU ==========
TOKEN = "8501043849:AAH8Xm31iGQd-XrGZnduLI9ll5YEzintEOg"
ADMIN_ID = 7176181382
# ===================================================

DATA_FILE = "users.json"
PROMO_FILE = "promo.json"
last_update_id = 0
current_promo_index = 0

# Load config
try:
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
except:
    config = {
        "welcome_message": "🌟 SELAMAT DATANG DI ABAD4D TEAM 🌟\n\nDapatkan promo menarik setiap jam!\n\n👇 Klik tombol di bawah untuk mulai bermain",
        "website_url": "https://siteq.link/abad4d"
    }

# Load promo list
def load_promos():
    try:
        with open(PROMO_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("promos", []), data.get("settings", {})
    except Exception as e:
        print(f"Error loading promos: {e}")
        return [], {}

promos, promo_settings = load_promos()
print(f"✅ Loaded {len(promos)} promos")

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

def send_message(chat_id, text, reply_markup=None, photo_url=None):
    """Kirim pesan dengan atau tanpa gambar"""
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
    
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        return response.json()
    except Exception as e:
        print(f"Error sending message: {e}")
        return None

def send_promo_to_user(chat_id, promo):
    """Kirim promo ke user dengan tombol dan gambar"""
    keyboard = {
        "inline_keyboard": [[
            {"text": promo.get("button_text", "🔥 Klaim Bonus"), "url": promo.get("button_url", config["website_url"])}
        ]]
    }
    
    image_url = promo.get("image_url")
    send_message(chat_id, promo["message"], keyboard, image_url)

def broadcast_pesan(pesan):
    """Broadcast teks biasa"""
    success = 0
    fail = 0
    if len(users) == 0:
        print("Belum ada user terdaftar.")
        return
    for user_id in users:
        result = send_message(user_id, pesan)
        if result and result.get("ok"):
            success += 1
        else:
            fail += 1
        time.sleep(0.05)
    print(f"Broadcast: {success} berhasil, {fail} gagal")

def broadcast_promo():
    """Broadcast promo ke semua user"""
    global current_promo_index
    
    if not promos:
        print("Tidak ada promo tersedia!")
        return
    
    if promo_settings.get("random_order", True):
        promo = random.choice(promos)
        print(f"Memilih promo random: {promo['title']}")
    else:
        promo = promos[current_promo_index % len(promos)]
        current_promo_index += 1
        print(f"Memilih promo ke-{current_promo_index}: {promo['title']}")
    
    success = 0
    fail = 0
    
    if len(users) == 0:
        print("Belum ada user terdaftar.")
        return
    
    print(f"Mengirim promo '{promo['title']}' ke {len(users)} user...")
    
    for user_id in users:
        try:
            send_promo_to_user(user_id, promo)
            success += 1
        except Exception as e:
            fail += 1
            print(f"Gagal kirim ke {user_id}: {e}")
        time.sleep(0.05)
    
    print(f"✅ Promo terkirim: {success} berhasil, {fail} gagal")

def handle_start(chat_id, username):
    if chat_id not in users:
        users.add(chat_id)
        save_users(users)
        print(f"User baru: {username} ({chat_id})")
    
    welcome_text = """
🌟 *SELAMAT DATANG DI ABAD4D TEAM* 🌟

🔥 *PROMO SPESIAL UNTUK ANDA!* 🔥

✅ Bonus New Member 50%
✅ Cashback Mingguan Up To 1%
✅ Bonus Deposit Harian 10%
✅ Event Pasukan Petir
✅ Event Slot Gacor Setiap Hari

*Kami akan mengirim promo menarik setiap jam!*

👇 Klik tombol di bawah untuk mulai bermain
"""
    
    keyboard = {
        "inline_keyboard": [
            [{"text": "🌐 Kunjungi Website", "url": config["website_url"]}],
            [{"text": "🎰 Lihat Semua Promo", "callback_data": "list_promos"}]
        ]
    }
    send_message(chat_id, welcome_text, keyboard)

def handle_list_promos(chat_id):
    if not promos:
        send_message(chat_id, "Belum ada promo tersedia.")
        return
    
    text = "*📋 DAFTAR SEMUA PROMO*\n\n"
    for i, promo in enumerate(promos, 1):
        text += f"{i}. {promo['title']}\n"
    text += "\nKetik /promo <nomor> untuk detail promo tertentu.\nContoh: /promo 1"
    send_message(chat_id, text)

def handle_promo_detail(chat_id, promo_num):
    try:
        idx = int(promo_num) - 1
        if 0 <= idx < len(promos):
            send_promo_to_user(chat_id, promos[idx])
        else:
            send_message(chat_id, "Nomor promo tidak ditemukan. Ketik /promos untuk melihat daftar.")
    except:
        send_message(chat_id, "Gunakan: /promo <nomor>")

def handle_broadcast(chat_id, args):
    if chat_id != ADMIN_ID:
        send_message(chat_id, "⛔ Akses ditolak. Hanya admin.")
        return
    if not args:
        send_message(chat_id, "📢 Gunakan: /broadcast <pesan>\n\nAtau:\n/broadcast_promo - Kirim promo random")
        return
    send_message(chat_id, "⏳ Mengirim broadcast...")
    broadcast_pesan(" ".join(args))
    send_message(chat_id, "✅ Broadcast selesai!")

def handle_broadcast_promo(chat_id):
    if chat_id != ADMIN_ID:
        send_message(chat_id, "⛔ Akses ditolak.")
        return
    send_message(chat_id, "⏳ Mengirim promo ke semua user...")
    broadcast_promo()
    send_message(chat_id, "✅ Promo broadcast selesai!")

def handle_stats(chat_id):
    if chat_id != ADMIN_ID:
        send_message(chat_id, "⛔ Akses ditolak.")
        return
    
    stats_text = f"""
📊 *STATISTIK BOT ABAD4D*

👥 Total user terdaftar: *{len(users)}*
🎁 Total promo tersedia: *{len(promos)}*
⏰ Broadcast setiap: *{promo_settings.get('broadcast_interval_hours', 1)} jam*
🔄 Mode promo: *Random* ✅
🖼️ Kirim gambar: *{'Ya' if promo_settings.get('send_image', True) else 'Tidak'}*

📋 Daftar promo:
"""
    for i, promo in enumerate(promos, 1):
        stats_text += f"\n{i}. {promo['title']}"
    
    send_message(chat_id, stats_text)

def handle_help(chat_id):
    help_text = """
📖 *PANDUAN BOT ABAD4D*

*Perintah User:*
/start - Memulai bot
/help - Panduan ini
/promos - Lihat daftar semua promo
/promo <nomor> - Lihat detail promo tertentu

*Perintah Admin:*
/stats - Lihat statistik bot
/broadcast <pesan> - Kirim pesan ke semua user
/broadcast_promo - Kirim promo random ke semua user

*Fitur Otomatis:*
⏰ Setiap 1 jam akan mengirim promo random ke semua user terdaftar
🖼️ Promo dikirim lengkap dengan gambar

*Website:* {config['website_url']}
"""
    send_message(chat_id, help_text)

def process_updates():
    global last_update_id
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
    params = {"offset": last_update_id + 1, "timeout": 30}
    
    try:
        response = requests.get(url, params=params, timeout=35)
        data = response.json()
        
        if data.get("ok"):
            for update in data.get("result", []):
                last_update_id = update["update_id"]
                message = update.get("message")
                callback = update.get("callback_query")
                
                if message:
                    chat_id = message["chat"]["id"]
                    text = message.get("text", "")
                    username = message["chat"].get("username", "unknown")
                    
                    if text == "/start":
                        handle_start(chat_id, username)
                    elif text == "/help":
                        handle_help(chat_id)
                    elif text == "/promos":
                        handle_list_promos(chat_id)
                    elif text.startswith("/promo"):
                        parts = text.split()
                        if len(parts) > 1:
                            handle_promo_detail(chat_id, parts[1])
                        else:
                            send_message(chat_id, "Gunakan: /promo <nomor>")
                    elif text.startswith("/broadcast_promo"):
                        handle_broadcast_promo(chat_id)
                    elif text.startswith("/broadcast"):
                        args = text.split()[1:]
                        handle_broadcast(chat_id, args)
                    elif text == "/stats":
                        handle_stats(chat_id)
                    elif text.startswith("/"):
                        send_message(chat_id, "Perintah tidak dikenal. Ketik /help")
                    else:
                        send_message(chat_id, "🤖 Kirim /start untuk memulai")
                
                elif callback:
                    chat_id = callback["message"]["chat"]["id"]
                    data = callback["data"]
                    
                    if data == "list_promos":
                        handle_list_promos(chat_id)
                    
                    requests.post(f"https://api.telegram.org/bot{TOKEN}/answerCallbackQuery", 
                                 json={"callback_query_id": callback["id"]})
                    
    except Exception as e:
        print(f"Error: {e}")

def broadcast_loop():
    last_broadcast = 0
    interval = promo_settings.get("broadcast_interval_hours", 1) * 3600
    
    while True:
        now = time.time()
        if now - last_broadcast >= interval:
            print(f"\n{'='*50}")
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Mengirim broadcast promo otomatis...")
            print(f"{'='*50}")
            broadcast_promo()
            last_broadcast = now
        time.sleep(60)

def main():
    print("=" * 50)
    print("🎯 BOT PROMO OTOMATIS - ABAD4D TEAM")
    print("=" * 50)
    print(f"👑 Admin ID: {ADMIN_ID}")
    print(f"📁 Total user: {len(users)}")
    print(f"🎁 Total promo: {len(promos)}")
    print(f"⏰ Broadcast setiap: {promo_settings.get('broadcast_interval_hours', 1)} jam")
    print(f"🔄 Mode: {'Random' if promo_settings.get('random_order', True) else 'Urut'}")
    print(f"🖼️ Kirim gambar: {'Ya' if promo_settings.get('send_image', True) else 'Tidak'}")
    print("=" * 50)
    print("✅ Bot berjalan! Tekan Ctrl+C untuk berhenti.\n")
    
    print("📋 DAFTAR PROMO:")
    for i, promo in enumerate(promos, 1):
        print(f"   {i}. {promo['title']}")
    print("=" * 50)
    
    broadcast_thread = threading.Thread(target=broadcast_loop, daemon=True)
    broadcast_thread.start()
    
    while True:
        try:
            process_updates()
        except KeyboardInterrupt:
            print("\n🛑 Bot dihentikan.")
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()