import os
import json
import uuid
from flask import Flask, render_template, request, redirect, url_for, session, flash
from functools import wraps

app = Flask(__name__)
app.secret_key = "david_rescue_key_v2024"
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024

DB_FILE = "data.json"

DEFAULT_DATA = {
    "settings": {
        "title": "Le Rendez-vous du Dimanche",
        "subtitle": "Présenté par David Smadja",
        "description": "",
        "address": "Highlight Bar, Herzl 31, Netanya",
        "waze_link": "https://ul.waze.com/ul?place=ChIJJZdEM6pqHRURs1uXYBt7fkM&ll=32.32880780%2C34.85794440&navigate=yes",
        "maps_link": "https://maps.google.com/?q=Highlight+Bar+Netanya",
        "instagram": "https://www.instagram.com/lerendezvousdudimanche",
        "bg_image": "bg_stage.jpg"
    },
    "events": [],
    "artists": {}
}

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def normalize_photo(photo_value):
    """Normalise les valeurs de photo - retourne toujours une chaîne vide ou un chemin valide"""
    if photo_value is None or photo_value == "" or photo_value == "None":
        return ""
    return str(photo_value).strip()

def load_data():
    if not os.path.exists(DB_FILE):
        save_data(DEFAULT_DATA)
        return DEFAULT_DATA
    try:
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if "artists" not in data: data["artists"] = {}
            if "events" not in data: data["events"] = []
            if "settings" not in data: data["settings"] = DEFAULT_DATA["settings"]
            
            for artist_id, artist in data.get("artists", {}).items():
                artist["main_photo"] = normalize_photo(artist.get("main_photo"))
                if "gallery" not in artist:
                    artist["gallery"] = []
            
            for event in data.get("events", []):
                event["flyer"] = normalize_photo(event.get("flyer"))
                if "photos" not in event:
                    event["photos"] = []
                for guest in event.get("guests", []):
                    guest["photo"] = normalize_photo(guest.get("photo"))
            
            return data
    except Exception as e:
        print(f"Erreur chargement: {e}")
        return DEFAULT_DATA

def save_data(data):
    try:
        for artist_id, artist in data.get("artists", {}).items():
            artist["main_photo"] = normalize_photo(artist.get("main_photo"))
        for event in data.get("events", []):
            event["flyer"] = normalize_photo(event.get("flyer"))
            if "photos" not in event:
                event["photos"] = []
            for guest in event.get("guests", []):
                guest["photo"] = normalize_photo(guest.get("photo"))
        
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Erreur sauvegarde: {e}")

def save_image(file):
    if file and file.filename:
        filename = file.filename.lower()
        if '.' in filename:
            ext = filename.rsplit('.', 1)[1]
            if ext in ['jpg', 'jpeg', 'png', 'webp', 'gif']:
                new_filename = f"{uuid.uuid4().hex}.{ext}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], new_filename)
                file.save(filepath)
                return f"uploads/{new_filename}"
    return ""

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            return redirect(url_for('admin', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    return render_template('index.html', data=load_data())

@app.route('/artist/<artist_id>')
def artist_profile(artist_id):
    data = load_data()
    artist = data['artists'].get(artist_id)
    if not artist:
        return redirect(url_for('index'))
    return render_template('artist.html', artist=artist, settings=data['settings'])

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        if request.form.get('password') == "pitikon":
            session['is_admin'] = True
            return redirect(request.args.get('next') or url_for('dashboard'))
        flash("Mot de passe incorrect", "error")
    return render_template('login.html')

@app.route('/dashboard')
@admin_required
def dashboard():
    return render_template('dashboard.html', data=load_data())

@app.route('/save_event', methods=['POST'])
@admin_required
def save_event():
    data = load_data()
    event_id = request.form.get('event_id')
    is_new = not event_id
    
    if is_new:
        event_id = uuid.uuid4().hex
        event = {"id": event_id, "guests": [], "photos": []}
    else:
        event = next((e for e in data['events'] if e['id'] == event_id), None)
        if not event:
            return redirect(url_for('dashboard'))
        if "photos" not in event:
            event["photos"] = []

    event.update({
        "date_str": request.form.get('date_str', ''),
        "time_str": request.form.get('time_str', ''),
        "link": request.form.get('link', ''),
        "description": request.form.get('description', '')
    })

    flyer = request.files.get('flyer_file')
    if flyer and flyer.filename:
        path = save_image(flyer)
        if path:
            event['flyer'] = path

    event_photos = request.files.getlist('event_photos[]')
    for photo in event_photos:
        if photo and photo.filename:
            path = save_image(photo)
            if path:
                event['photos'].append(path)

    event['guests'] = []
    names = request.form.getlist('guest_name[]')
    descs = request.form.getlist('guest_desc[]')
    photos = request.files.getlist('guest_photo[]')
    
    for i, name in enumerate(names):
        if name.strip():
            exist_id = next(
                (aid for aid, a in data['artists'].items() 
                 if a['name'].strip().lower() == name.strip().lower()), 
                None
            )
            artist_id = exist_id if exist_id else uuid.uuid4().hex
            
            if artist_id not in data['artists']:
                data['artists'][artist_id] = {
                    "id": artist_id,
                    "name": name.strip(),
                    "bio": "Biographie à venir...",
                    "main_photo": "",
                    "gallery": []
                }
            
            guest_photo = ""
            if i < len(photos) and photos[i] and photos[i].filename:
                path = save_image(photos[i])
                if path:
                    data['artists'][artist_id]['main_photo'] = path
                    guest_photo = path
            else:
                guest_photo = normalize_photo(data['artists'][artist_id].get('main_photo'))
            
            event['guests'].append({
                "id": artist_id,
                "name": name.strip(),
                "desc": descs[i] if i < len(descs) else "",
                "photo": guest_photo
            })

    if is_new:
        data['events'].append(event)
    
    save_data(data)
    flash("✅ Soirée enregistrée", "success")
    return redirect(url_for('dashboard'))

@app.route('/update_artist_profile', methods=['POST'])
@admin_required
def update_artist_profile():
    data = load_data()
    aid = request.form.get('artist_id')
    
    if aid in data['artists']:
        data['artists'][aid]['bio'] = request.form.get('bio', '')
        
        main_photo = request.files.get('main_photo_file')
        if main_photo and main_photo.filename:
            path = save_image(main_photo)
            if path:
                data['artists'][aid]['main_photo'] = path
                for event in data['events']:
                    for guest in event.get('guests', []):
                        if guest['id'] == aid:
                            guest['photo'] = path
        
        for f in request.files.getlist('gallery[]'):
            if f and f.filename:
                path = save_image(f)
                if path:
                    data['artists'][aid]['gallery'].append(path)
        
        flash("✅ Profil mis à jour", "success")
    
    save_data(data)
    return redirect(url_for('dashboard') + "#artists")

@app.route('/delete_event_image/<event_id>')
@admin_required
def delete_event_image(event_id):
    data = load_data()
    event = next((ev for ev in data['events'] if ev['id'] == event_id), None)
    if event:
        event['flyer'] = ""
        save_data(data)
        flash("Image supprimée", "success")
    return redirect(url_for('dashboard'))

@app.route('/delete_event_photo/<event_id>/<int:photo_index>')
@admin_required
def delete_event_photo(event_id, photo_index):
    data = load_data()
    event = next((ev for ev in data['events'] if ev['id'] == event_id), None)
    if event and 'photos' in event and 0 <= photo_index < len(event['photos']):
        event['photos'].pop(photo_index)
        save_data(data)
        flash("Photo supprimée", "success")
    return redirect(url_for('dashboard'))

@app.route('/delete_artist_photo/<artist_id>')
@admin_required
def delete_artist_photo(artist_id):
    data = load_data()
    if artist_id in data['artists']:
        data['artists'][artist_id]['main_photo'] = ""
        for event in data['events']:
            for guest in event.get('guests', []):
                if guest['id'] == artist_id:
                    guest['photo'] = ""
        save_data(data)
        flash("Photo supprimée", "success")
    return redirect(url_for('dashboard') + "#artists")

@app.route('/delete_artist/<artist_id>')
@admin_required
def delete_artist(artist_id):
    data = load_data()
    if artist_id in data['artists']:
        del data['artists'][artist_id]
        save_data(data)
        flash("Artiste supprimé", "success")
    return redirect(url_for('dashboard') + "#artists")

@app.route('/delete_event/<event_id>')
@admin_required
def delete_event(event_id):
    data = load_data()
    data['events'] = [e for e in data['events'] if e['id'] != event_id]
    save_data(data)
    flash("Soirée supprimée", "success")
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
