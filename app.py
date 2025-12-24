import os
import json
import uuid
from flask import Flask, render_template, request, redirect, url_for, session, flash
from functools import wraps
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "david_final_key_v14_secure"
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024

DB_FILE = "data.json"

DEFAULT_DATA = {
    "settings": {
        "title": "Le Rendez-vous du Dimanche",
        "description": "", 
        "waze_link": "https://ul.waze.com/ul?place=ChIJJZdEM6pqHRURs1uXYBt7fkM&ll=32.32880780%2C34.85794440&navigate=yes&utm_campaign=default&utm_source=waze_website&utm_medium=lm_share_sheet",
        "instagram": "https://www.instagram.com/lerendezvousdudimanche?utm_source=ig_web_button_share_sheet&igsh=ZDNlZDc0MzIxNw==",
        "bg_image": "bg_stage.jpg"
    },
    "events": [],
    "artists": {}
}

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            return redirect(url_for('admin', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def load_data():
    if not os.path.exists(DB_FILE): return DEFAULT_DATA
    try:
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if "artists" not in data: data["artists"] = {}
            if "events" not in data: data["events"] = []
            if "settings" not in data: data["settings"] = DEFAULT_DATA["settings"]
            return data
    except: return DEFAULT_DATA

def save_data(data):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def save_image(file):
    if file and file.filename:
        ext = file.filename.rsplit('.', 1)[1].lower()
        if ext in ['jpg', 'jpeg', 'png', 'webp']:
            filename = f"{uuid.uuid4().hex}.{ext}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            return f"uploads/{filename}"
    return None

# --- ROUTES ---

@app.route('/')
def index(): return render_template('index.html', data=load_data())

@app.route('/artist/<artist_id>')
def artist_profile(artist_id):
    data = load_data()
    artist = data['artists'].get(artist_id)
    if not artist: return redirect(url_for('index'))
    return render_template('artist.html', artist=artist, settings=data['settings'])

@app.route('/guide')
@admin_required
def guide(): return render_template('guide.html')

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        if request.form.get('password') == "pitikon":
            session['is_admin'] = True
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        flash("Mot de passe incorrect", "error")
    return render_template('login.html')

@app.route('/dashboard')
@admin_required
def dashboard(): return render_template('dashboard.html', data=load_data())

@app.route('/save_event', methods=['POST'])
@admin_required
def save_event():
    data = load_data()
    event_id = request.form.get('event_id')
    is_new = not event_id
    
    if is_new:
        event_id = uuid.uuid4().hex
        event = {"id": event_id, "guests": []}
    else:
        event = next((e for e in data['events'] if e['id'] == event_id), None)
        if not event: return redirect(url_for('dashboard'))

    event.update({
        "date_str": request.form.get('date_str'),
        "time_str": request.form.get('time_str'),
        "link": request.form.get('link'),
        "description": request.form.get('description'),
    })

    flyer = request.files.get('flyer_file')
    if flyer: 
        path = save_image(flyer)
        if path: event['flyer'] = path
    elif is_new: event['flyer'] = None

    event['guests'] = [] 
    guest_names = request.form.getlist('guest_name[]')
    guest_descs = request.form.getlist('guest_desc[]')
    guest_photos = request.files.getlist('guest_photo[]')
    existing_photos = request.form.getlist('existing_guest_photo[]')

    for i in range(len(guest_names)):
        if guest_names[i].strip():
            # Cherche si l'artiste existe déjà par son nom
            existing_id = next((aid for aid, a in data['artists'].items() if a['name'].lower() == guest_names[i].strip().lower()), None)
            
            if existing_id: 
                artist_id = existing_id
            else:
                artist_id = uuid.uuid4().hex
                data['artists'][artist_id] = {
                    "id": artist_id, "name": guest_names[i], "bio": "Biographie à venir...", 
                    "main_photo": None, "gallery": []
                }

            # Gestion photo
            photo_path = data['artists'][artist_id]['main_photo']
            if i < len(guest_photos) and guest_photos[i].filename:
                new_photo = save_image(guest_photos[i])
                if new_photo: 
                    photo_path = new_photo
                    data['artists'][artist_id]['main_photo'] = photo_path

            event['guests'].append({
                "id": artist_id, "name": guest_names[i], "desc": guest_descs[i], "photo": photo_path
            })

    if is_new:
        data['events'].insert(0, event)
        flash("🎉 Soirée créée !", "success")
    else:
        flash("✅ Soirée modifiée !", "success")

    save_data(data)
    return redirect(url_for('dashboard'))

@app.route('/delete_event_image/<event_id>')
@admin_required
def delete_event_image(event_id):
    data = load_data()
    event = next((e for e in data['events'] if e['id'] == event_id), None)
    if event:
        event['flyer'] = None
        save_data(data)
        flash("🗑️ Affiche supprimée", "success")
    return redirect(url_for('dashboard'))

@app.route('/delete_artist_photo/<artist_id>')
@admin_required
def delete_artist_photo(artist_id):
    data = load_data()
    if artist_id in data['artists']:
        data['artists'][artist_id]['main_photo'] = None
        save_data(data)
        flash("🗑️ Photo artiste supprimée", "success")
    return redirect(url_for('dashboard') + "#artists")

@app.route('/update_artist_profile', methods=['POST'])
@admin_required
def update_artist_profile():
    data = load_data()
    artist_id = request.form.get('artist_id')
    if artist_id in data['artists']:
        data['artists'][artist_id]['bio'] = request.form.get('bio')
        for f in request.files.getlist('gallery[]'):
            path = save_image(f)
            if path: data['artists'][artist_id]['gallery'].append(path)
        flash("✅ Profil mis à jour !", "success")
    save_data(data)
    return redirect(url_for('dashboard') + "#artists")

@app.route('/delete_artist/<artist_id>')
@admin_required
def delete_artist(artist_id):
    data = load_data()
    if artist_id in data['artists']:
        del data['artists'][artist_id]
        save_data(data)
        flash("🗑️ Artiste supprimé définitivement.", "success")
    return redirect(url_for('dashboard') + "#artists")

@app.route('/delete_event/<event_id>')
@admin_required
def delete_event(event_id):
    data = load_data()
    data['events'] = [e for e in data['events'] if e['id'] != event_id]
    save_data(data)
    flash("🗑️ Soirée supprimée.", "success")
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)