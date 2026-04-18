from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import json
import os
import requests

app = Flask(__name__)
CORS(app)

# Konfigurasi
TOKEN = "8501043849:AAH8Xm31iGQd-XrGZnduLI9ll5YEzintEOg"
ADMIN_ID = 7176181382
DATA_FILE = "users.json"
PROMO_FILE = "promo.json"
CONFIG_FILE = "config.json"

def load_users():
    try:
        with open(DATA_FILE, "r") as f:
            return list(json.load(f))
    except:
        return []

def load_promos():
    try:
        with open(PROMO_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("promos", []), data.get("settings", {})
    except:
        return [], {}

def save_promos(promos, settings):
    with open(PROMO_FILE, "w", encoding="utf-8") as f:
        json.dump({"promos": promos, "settings": settings}, f, indent=4, ensure_ascii=False)

def load_config():
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"welcome_message": "Selamat datang!", "website_url": "https://siteq.link/abad4d"}

def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)

def send_telegram_message(chat_id, text, photo_url=None, button_text=None, button_url=None):
    if photo_url:
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

def broadcast_to_all(promo):
    users = load_users()
    success = 0
    fail = 0
    
    for user_id in users:
        result = send_telegram_message(
            user_id,
            promo.get("message", ""),
            promo.get("image_url"),
            promo.get("button_text", "🔥 Klaim Bonus"),
            promo.get("button_url", "https://siteq.link/abad4d")
        )
        if result and result.get("ok"):
            success += 1
        else:
            fail += 1
    return success, fail

@app.route('/')
def admin_panel():
    return render_template('admin.html')

@app.route('/api/stats')
def api_stats():
    users = load_users()
    promos, settings = load_promos()
    config = load_config()
    
    return jsonify({
        'total_users': len(users),
        'total_promos': len(promos),
        'broadcast_interval': settings.get('broadcast_interval_hours', 1),
        'random_order': settings.get('random_order', True),
        'send_image': settings.get('send_image', True),
        'website_url': config.get('website_url', ''),
        'welcome_message': config.get('welcome_message', '')
    })

@app.route('/api/promos')
def api_get_promos():
    promos, _ = load_promos()
    return jsonify(promos)

@app.route('/api/promo/<int:promo_id>')
def api_get_promo(promo_id):
    promos, _ = load_promos()
    for promo in promos:
        if promo.get('id') == promo_id:
            return jsonify(promo)
    return jsonify({'error': 'Promo tidak ditemukan'}), 404

@app.route('/api/promo', methods=['POST'])
def api_add_promo():
    data = request.json
    promos, settings = load_promos()
    
    new_id = max([p.get('id', 0) for p in promos]) + 1 if promos else 1
    
    new_promo = {
        'id': new_id,
        'title': data.get('title', 'Promo Baru'),
        'message': data.get('message', ''),
        'image_url': data.get('image_url', ''),
        'button_text': data.get('button_text', '🔥 Klaim Bonus'),
        'button_url': data.get('button_url', 'https://siteq.link/abad4d')
    }
    
    promos.append(new_promo)
    save_promos(promos, settings)
    
    return jsonify({'success': True, 'promo': new_promo})

@app.route('/api/promo/<int:promo_id>', methods=['PUT'])
def api_update_promo(promo_id):
    data = request.json
    promos, settings = load_promos()
    
    for i, promo in enumerate(promos):
        if promo.get('id') == promo_id:
            promos[i] = {
                'id': promo_id,
                'title': data.get('title', promo.get('title')),
                'message': data.get('message', promo.get('message')),
                'image_url': data.get('image_url', promo.get('image_url')),
                'button_text': data.get('button_text', promo.get('button_text')),
                'button_url': data.get('button_url', promo.get('button_url'))
            }
            save_promos(promos, settings)
            return jsonify({'success': True, 'promo': promos[i]})
    
    return jsonify({'error': 'Promo tidak ditemukan'}), 404

@app.route('/api/promo/<int:promo_id>', methods=['DELETE'])
def api_delete_promo(promo_id):
    promos, settings = load_promos()
    
    for i, promo in enumerate(promos):
        if promo.get('id') == promo_id:
            promos.pop(i)
            save_promos(promos, settings)
            return jsonify({'success': True})
    
    return jsonify({'error': 'Promo tidak ditemukan'}), 404

@app.route('/api/settings', methods=['POST'])
def api_update_settings():
    data = request.json
    promos, settings = load_promos()
    
    settings['broadcast_interval_hours'] = data.get('broadcast_interval_hours', 1)
    settings['random_order'] = data.get('random_order', True)
    settings['send_image'] = data.get('send_image', True)
    
    save_promos(promos, settings)
    
    config = load_config()
    if 'website_url' in data:
        config['website_url'] = data['website_url']
    if 'welcome_message' in data:
        config['welcome_message'] = data['welcome_message']
    save_config(config)
    
    return jsonify({'success': True})

@app.route('/api/broadcast', methods=['POST'])
def api_broadcast():
    data = request.json
    
    promo = {
        'message': data.get('message', ''),
        'image_url': data.get('image_url', ''),
        'button_text': data.get('button_text', '🔥 Klaim Bonus'),
        'button_url': data.get('button_url', 'https://siteq.link/abad4d')
    }
    
    success, fail = broadcast_to_all(promo)
    
    return jsonify({
        'success': True,
        'sent': success,
        'failed': fail,
        'total': success + fail
    })

@app.route('/api/broadcast_promo/<int:promo_id>', methods=['POST'])
def api_broadcast_promo(promo_id):
    promos, _ = load_promos()
    
    promo = None
    for p in promos:
        if p.get('id') == promo_id:
            promo = p
            break
    
    if not promo:
        return jsonify({'error': 'Promo tidak ditemukan'}), 404
    
    success, fail = broadcast_to_all(promo)
    
    return jsonify({
        'success': True,
        'sent': success,
        'failed': fail,
        'total': success + fail,
        'promo_title': promo.get('title')
    })

@app.route('/api/users')
def api_get_users():
    users = load_users()
    return jsonify(users)

if __name__ == '__main__':
    if not os.path.exists('templates'):
        os.makedirs('templates')
    
    print("=" * 50)
    print("🔧 ADMIN PANEL - ABAD4D BOT")
    print("=" * 50)
    print(f"📍 Akses admin panel di: http://localhost:5000")
    print(f"👑 Admin ID Telegram: {ADMIN_ID}")
    print("=" * 50)
    print("⚠️  Jalankan bot Telegram juga di terminal terpisah!")
    print("=" * 50)
    
    app.run(debug=True, host='0.0.0.0', port=5000)