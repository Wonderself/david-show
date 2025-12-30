import os
import json
import uuid
import cloudinary
import cloudinary.uploader
from flask import Flask, render_template, request, redirect, url_for, session, flash
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "david_rescue_key_v2024")
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024

# Configuration Cloudinary via variables d'environnement
cloudinary.config(
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
    api_key=os.environ.get("CLOUDINARY_API_KEY"),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET")
)

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
            return data
    except:
        return DEFAULT_DATA

def save_data(data):
    try:
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Erreur sauvegarde: {e}")

def upload_image(file):
    """Upload une image sur Cloudinary et retourne l'URL"""
    if file and file.filename:
        try:
            # Upload vers Cloudinary
            result = cloudinary.uploader.upload(
                file,
                folder="rdv-dimanche",
                resource_type="image",
                transformation=[
                    {"quality": "auto:good"},
                    {"fetch_format": "auto"}
                ]
            )
            return result.get("secure_url")
        except Exception as e:
            print(f"Erreur upload Cloudinary: {e}")
            return None
    return None

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            return redirect(url_for('admin', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# ==================== ROUTES PUBLIQUES ====================

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

# ==================== ROUTES ADMIN ====================

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        if request.form.get('password') == "pitikon":
            session['is_admin'] = True
            return redirect(url_for('dashboard'))
        flash("Mot de passe incorrect", "error")
    return render_template('login.html')

@app.route('/dashboard')
@admin_required
def dashboard():
    return render_template('dashboard.html', data=load_data())

@app.route('/guide')
@admin_required
def guide():
    return render_template('guide.html')

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

    # Upload flyer principal
    flyer = request.files.get('flyer_file')
    if flyer and flyer.filename:
        url = upload_image(flyer)
        if url:
            event['flyer'] = url

    # Upload photos supplémentaires
    event_photos = request.files.getlist('event_photos[]')
    for photo in event_photos:
        if photo and photo.filename:
            url = upload_image(photo)
            if url:
                event['photos'].append(url)

    # Gestion des invités
    event['guests'] = []
    names = request.form.getlist('guest_name[]')
    descs = request.form.getlist('guest_desc[]')
    photos = request.files.getlist('guest_photo[]')
    
    for i, name in enumerate(names):
        if name.strip():
            # Chercher artiste existant
            exist_id = next(
                (aid for aid, a in data['artists'].items() 
                 if a['name'].strip().lower() == name.strip().lower()), 
                None
            )
            artist_id = exist_id if exist_id else uuid.uuid4().hex
            
            # Créer l'artiste s'il n'existe pas
            if artist_id not in data['artists']:
                data['artists'][artist_id] = {
                    "id": artist_id,
                    "name": name.strip(),
                    "bio": "Biographie à venir...",
                    "main_photo": "",
                    "gallery": []
                }
            
            # Upload photo si fournie
            guest_photo = data['artists'][artist_id].get('main_photo', '')
            if i < len(photos) and photos[i] and photos[i].filename:
                url = upload_image(photos[i])
                if url:
                    data['artists'][artist_id]['main_photo'] = url
                    guest_photo = url
            
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
        
        # Photo principale
        main_photo = request.files.get('main_photo_file')
        if main_photo and main_photo.filename:
            url = upload_image(main_photo)
            if url:
                data['artists'][aid]['main_photo'] = url
                # SYNC: Mettre à jour dans tous les événements
                for event in data['events']:
                    for guest in event.get('guests', []):
                        if guest['id'] == aid:
                            guest['photo'] = url
        
        # Galerie
        for f in request.files.getlist('gallery[]'):
            if f and f.filename:
                url = upload_image(f)
                if url:
                    data['artists'][aid]['gallery'].append(url)
        
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
        # SYNC: Supprimer aussi dans les événements
        for event in data['events']:
            for guest in event.get('guests', []):
                if guest['id'] == artist_id:
                    guest['photo'] = ""
        save_data(data)
        flash("Photo supprimée", "success")
    return redirect(url_for('dashboard') + "#artists")

@app.route('/delete_gallery_photo/<artist_id>/<int:photo_index>')
@admin_required
def delete_gallery_photo(artist_id, photo_index):
    data = load_data()
    if artist_id in data['artists']:
        gallery = data['artists'][artist_id].get('gallery', [])
        if 0 <= photo_index < len(gallery):
            gallery.pop(photo_index)
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
