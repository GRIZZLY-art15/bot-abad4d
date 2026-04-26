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

# ============ FUNGSI UNTUK MENYIMPAN KONTAK ============
def save_contact(user_id, username, first_name, last_name, phone_number):
    """Menyimpan kontak user ke file JSON"""
    try:
        contacts = []
        if os.path.exists(CONTACTS_FILE):
            with open(CONTACTS_FILE, "r", encoding="utf-8") as f:
                contacts = json.load(f)
        
        # Cek apakah user sudah pernah share kontak sebelumnya
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
            # Update kontak yang sudah ada
            contacts[existing_index] = new_contact
            print(f"📞 [UPDATE] Kontak user {first_name} ({user_id}) diperbarui")
        else:
            # Tambah kontak baru
            contacts.append(new_contact)
            print(f"📞 [NEW] Kontak baru dari {first_name} ({user_id}) - {phone_number}")
        
        with open(CONTACTS_FILE, "w", encoding="utf-8") as f:
            json.dump(contacts, f, indent=2, ensure_ascii=False)
        
        return True
    except Exception as e:
        print(f"❌ Error saving contact: {e}")
        return False

def get_all_contacts():
    """Mengambil semua kontak yang tersimpan"""
    try:
        if os.path.exists(CONTACTS_FILE):
            with open(CONTACTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except:
        pass
    return []

def get_contact_count():
    """Menghitung jumlah kontak"""
    return len(get_all_contacts())

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

def send_promo_list(chat_id):
    """Kirim daftar promo dengan tombol klik"""
    if not promos:
        send_telegram_message(chat_id, "Belum ada promo tersedia.")
        return
    
    # Buat keyboard dengan tombol untuk setiap promo
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

def send_main_menu(chat_id):
    """Kirim menu utama dengan tombol share kontak"""
    welcome_msg = config.get("welcome_message", "Selamat datang di Abad4D Bot!")
    
    # Buat tombol dengan request_contact (khusus untuk keyboard reply)
    # Tapi karena kita pakai inline keyboard untuk menu, kita buat tombol share kontak terpisah
    keyboard = {
        "inline_keyboard": [
            [{"text": "📞 Share Kontak Saya", "callback_data": "share_contact"}],
            [{"text": "🌐 Kunjungi Website", "url": config.get("website_url")}],
            [{"text": "🎰 Lihat Semua Promo", "callback_data": "list_promos"}],
            [{"text": "ℹ️ Bantuan", "callback_data": "help"}]
        ]
    }
    send_telegram_message(chat_id, welcome_msg, reply_markup=keyboard)

def send_contact_request(chat_id):
    """Mengirim tombol request contact (reply keyboard)"""
    contact_keyboard = {
        "keyboard": [
            [{"text": "📱 Share Nomor Saya", "request_contact": True}]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": True
    }
    
    msg = """📞 *SHARE KONTAK ANDA*

Dengan membagikan nomor telepon, Anda akan:
✅ Mendapatkan update promo terbaru via WhatsApp (opsional)
✅ Mendapatkan bonus special untuk member yang terverifikasi
✅ Memudahkan CS kami untuk menghubungi Anda

🔒 *Data Anda aman dan tidak akan disebarluaskan*

👇 Tekan tombol di bawah untuk share kontak👇
"""
    send_telegram_message(chat_id, msg, reply_markup=contact_keyboard)

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
        <p>📞 <strong>Fitur Share Kontak AKTIF!</strong></p>
        <p>📊 <a href="/api/broadcast_status">Cek Status Broadcast</a></p>
        <p>📋 <a href="/api/promos">Lihat Promo</a></p>
        <p>👥 <a href="/api/users">Lihat User</a></p>
        <p>📞 <a href="/api/contacts">Lihat Kontak</a></p>
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

# ============ API BARU UNTUK KONTAK ============
@app.route('/api/contacts')
def api_get_contacts():
    """Mendapatkan semua kontak yang tersimpan"""
    contacts = get_all_contacts()
    return jsonify({
        'total': len(contacts),
        'contacts': contacts
    })

@app.route('/api/contacts/stats')
def api_contacts_stats():
    """Statistik kontak"""
    contacts = get_all_contacts()
    today = datetime.now().strftime("%Y-%m-%d")
    today_contacts = [c for c in contacts if c.get('shared_at', '').startswith(today)]
    
    return jsonify({
        'total_contacts': len(contacts),
        'today_contacts': len(today_contacts),
        'last_contact': contacts[-1] if contacts else None
    })

@app.route('/api/contacts/export')
def api_export_contacts():
    """Export semua kontak ke CSV"""
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

@app.route('/api/broadcast_status')
def api_broadcast_status():
    return jsonify({
        'is_running': broadcast_status["is_running"],
        'last_broadcast_time': broadcast_status.get("last_broadcast_time", "Belum pernah"),
        'last_broadcast_title': broadcast_status.get("last_broadcast_title", "-"),
        'next_broadcast_in_seconds': broadcast_status.get("next_broadcast_in", 0),
        'next_broadcast_in_minutes': round(broadcast_status.get("next_broadcast_in", 0) / 60, 1),
        'total_broadcasts_sent': broadcast_status.get("total_broadcasts_sent", 0),
        'interval_minutes': promo_settings.get('broadcast_interval_minutes', 20),
        'total_contacts': get_contact_count()
    })

@app.route('/api/stats')
def api_stats():
    return jsonify({
        'total_users': len(load_users()),
        'total_promos': len(promos),
        'total_contacts': get_contact_count(),
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

@app.route('/api/broadcast_to_contacts', methods=['POST'])
def api_broadcast_to_contacts():
    """Broadcast khusus ke user yang sudah share kontak"""
    data = request.json
    contacts = get_all_contacts()
    
    success = 0
    for contact in contacts:
        user_id = contact.get('user_id')
        if user_id:
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
    
    return jsonify({'sent': success, 'total': len(contacts)})

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
            
            # ============ CEK APAKAH ADA KONTAK ============
            contact = data["message"].get("contact")
            
            current_users = load_users()
            if chat_id not in current_users:
                current_users.add(chat_id)
                save_users(current_users)
                print(f"📝 User baru: {username} ({chat_id}) - Total: {len(current_users)}")
            
            # ============ HANDLE SHARE KONTAK ============
            if contact:
                phone_number = contact.get("phone_number")
                first_name = contact.get("first_name", "")
                last_name = contact.get("last_name", "")
                user_id = contact.get("user_id", chat_id)
                
                # Simpan kontak
                save_contact(user_id, username, first_name, last_name, phone_number)
                
                # Kirim konfirmasi ke user
                confirm_msg = f"""✅ *TERIMA KASIH TELAH SHARE KONTAK!*

Halo *{first_name}*, nomor Anda *{phone_number}* telah tersimpan.

🎁 *BONUS UNTUK ANDA:*
Member yang sudah share kontak berhak mendapatkan:
• Bonus New Member 50%
• Bonus Deposit Harian 10%
• Event Giveaway bulanan

💬 Customer Service kami akan menghubungi Anda via WhatsApp untuk info promo terbaru.

🏠 Ketik /start untuk kembali ke menu utama
"""
                send_telegram_message(chat_id, confirm_msg)
                
                # Notifikasi ke admin
                admin_msg = f"""📞 *KONTAK BARU!*

👤 Nama: {first_name} {last_name}
🆔 Username: @{username if username != 'unknown' else '-'}
📱 Nomor: {phone_number}
🕐 Waktu: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
📊 Total Kontak: {get_contact_count()}
"""
                send_telegram_message(ADMIN_ID, admin_msg)
                
                print(f"📞 [WEBHOOK] Kontak tersimpan dari {first_name} - Total kontak: {get_contact_count()}")
                
            # ============ HANDLE TEKS PERINTAH ============
            elif text == "/start":
                send_main_menu(chat_id)
                print(f"📨 Menu sent to {username}")
                
            elif text == "/help":
                help_msg = """
📖 *Panduan Bot Abad4D*

/start - Menu utama
/help - Panduan ini
/promos - Lihat daftar promo
/share - Share kontak Anda

*Fitur Baru:*
✅ Share kontak untuk dapat bonus
✅ Update promo via WhatsApp
✅ Notifikasi event khusus

🔒 *Data Anda aman dan terjaga kerahasiaannya*
"""
                send_telegram_message(chat_id, help_msg)
                
            elif text == "/share":
                send_contact_request(chat_id)
                
            elif text == "/promos":
                send_promo_list(chat_id)
                
            elif text == "/status" and str(chat_id) == str(ADMIN_ID):
                remaining = broadcast_status.get("next_broadcast_in", 0)
                remaining_min = int(remaining // 60)
                remaining_sec = int(remaining % 60)
                total_contacts = get_contact_count()
                
                status_msg = f"""
📊 *STATUS BROADCAST*

🔄 Status: {'✅ AKTIF' if broadcast_status['is_running'] else '❌ BERHENTI'}
📅 Last broadcast: {broadcast_status.get('last_broadcast_time', 'Belum pernah')}
📢 Last promo: {broadcast_status.get('last_broadcast_title', '-')}
⏰ Next broadcast: {remaining_min} menit {remaining_sec} detik
📊 Total broadcast: {broadcast_status.get('total_broadcasts_sent', 0)} kali
👥 Total user: {len(load_users())}
📞 Total kontak: {total_contacts}
🎁 Total promo: {len(promos)}
⏱️ Interval: {promo_settings.get('broadcast_interval_minutes', 20)} menit
"""
                send_telegram_message(chat_id, status_msg)
                print(f"📊 Status sent to admin {username}")
                
            elif text == "/stats" and str(chat_id) == str(ADMIN_ID):
                total_users = len(load_users())
                total_contacts = get_contact_count()
                interval = promo_settings.get('broadcast_interval_minutes', 20)
                send_telegram_message(chat_id, f"📊 *Statistik Bot*\n\n👥 Total user: {total_users}\n📞 Total kontak: {total_contacts}\n🎁 Total promo: {len(promos)}\n⏰ Broadcast: setiap {interval} menit")
                
            elif text == "/contacts" and str(chat_id) == str(ADMIN_ID):
                contacts = get_all_contacts()
                if contacts:
                    msg = "*📞 DAFTAR KONTAK YANG TERSIMPAN*\n\n"
                    for i, c in enumerate(contacts[-10:], 1):  # 10 terakhir
                        msg += f"{i}. {c.get('full_name', '-')} - {c.get('phone_number', '-')}\n"
                    msg += f"\n📊 Total: {len(contacts)} kontak\n\n📌 Gunakan /export_contacts untuk export semua"
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
                        # Kirim per bagian
                        for i in range(0, len(msg), 4000):
                            send_telegram_message(chat_id, msg[i:i+4000])
                    else:
                        send_telegram_message(chat_id, msg)
                else:
                    send_telegram_message(chat_id, "Belum ada kontak.")
                    
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
                # Jika tidak ada perintah, kirim menu utama
                send_main_menu(chat_id)
        
        # ============ HANDLE CALLBACK QUERY (TOMbol INLINE) ============
        elif data and "callback_query" in data:
            callback_data = data["callback_query"]["data"]
            chat_id = data["callback_query"]["message"]["chat"]["id"]
            message_id = data["callback_query"]["message"]["message_id"]
            
            if callback_data == "share_contact":
                # Kirim tombol share kontak
                send_contact_request(chat_id)
                # Answer callback query
                url = f"https://api.telegram.org/bot{TOKEN}/answerCallbackQuery"
                requests.post(url, json={"callback_query_id": data["callback_query"]["id"], "text": "Tekan tombol di bawah untuk share kontak!"})
                return jsonify({"status": "ok"})
            
            elif callback_data == "list_promos":
                send_promo_list(chat_id)
                
            elif callback_data == "back_to_menu":
                send_main_menu(chat_id)
                
            elif callback_data == "help":
                help_msg = """
📖 *Panduan Bot Abad4D*

📌 *Cara Penggunaan:*
• Klik tombol "Lihat Semua Promo" untuk melihat daftar promo
• Klik promo yang ingin dilihat detailnya
• Klik tombol "Kunjungi Website" untuk langsung ke website

🎁 *Bonus Share Kontak:*
• Member yang share kontak dapat bonus 50% new member
• Update promo langsung via WhatsApp
• Event dan giveaway khusus

⏰ *Broadcast Otomatis:*
Bot akan mengirim promo menarik setiap 20 menit!

🔙 Klik tombol kembali untuk ke menu utama
"""
                send_telegram_message(chat_id, help_msg)
                
            elif callback_data.startswith("promo_"):
                try:
                    promo_id = int(callback_data.split("_")[1])
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
                    print(f"Error processing promo callback: {e}")
                    send_telegram_message(chat_id, "Terjadi kesalahan. Silakan coba lagi.")
            
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
        <h3>📞 FITUR SHARE KONTAK AKTIF!</h3>
        <p>Sekarang user bisa share kontak dengan:</p>
        <ul>
            <li>Klik tombol "📞 Share Kontak Saya" di menu utama</li>
            <li>Atau ketik /share</li>
        </ul>
        <hr>
        <h3>📊 API Baru:</h3>
        <ul>
            <li><a href="/api/contacts">/api/contacts</a> - Lihat semua kontak</li>
            <li><a href="/api/contacts/stats">/api/contacts/stats</a> - Statistik kontak</li>
            <li><a href="/api/contacts/export">/api/contacts/export</a> - Export kontak ke CSV</li>
        </ul>
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
    
    # Inisialisasi file kontak jika belum ada
    if not os.path.exists(CONTACTS_FILE):
        with open(CONTACTS_FILE, "w") as f:
            json.dump([], f)
    
    port = int(os.environ.get("PORT", 5000))
    print("=" * 60)
    print("🤖 ABAD4D BOT TELEGRAM - DENGAN FITUR SHARE KONTAK")
    print("=" * 60)
    print(f"🌐 Server running on port {port}")
    print(f"📞 Fitur Share Kontak: AKTIF")
    print(f"📡 Kunjungi /set_webhook untuk mengaktifkan webhook")
    print(f"🔄 Broadcast loop: AKTIF (setiap {promo_settings.get('broadcast_interval_minutes', 20)} menit)")
    print(f"📊 Cek status: /api/broadcast_status")
    print(f"📞 API Kontak: /api/contacts")
    print("=" * 60)
    
    app.run(host="0.0.0.0", port=port)
