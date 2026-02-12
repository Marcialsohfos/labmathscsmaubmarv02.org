# app.py du SITE PRINCIPAL - Version PUBLIQUE (PAS DE LOGIN)
from flask import Flask, request, jsonify, render_template, send_from_directory, url_for
from flask_cors import CORS
import os
import json
from datetime import datetime
from functools import wraps
import uuid

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'labmath_secret_key_2024')
app.config['UPLOAD_FOLDER'] = 'static/uploads'

API_KEY = os.environ.get('API_KEY', 'labmath_api_secret_2024')
DATA_FILE = 'data/data.json'

os.makedirs('data', exist_ok=True)
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# --- FONCTIONS JSON ---
def load_data():
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {'activites': [], 'realisations': [], 'annonces': [], 'offres': [], 'last_update': datetime.now().isoformat()}

def save_data(data):
    data['last_update'] = datetime.now().isoformat()
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# --- API KEY REQUIRED ---
def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if api_key and api_key == API_KEY:
            return f(*args, **kwargs)
        return jsonify({'success': False, 'message': 'Clé API invalide'}), 401
    return decorated

# --- ROUTES PUBLIQUES (PAS DE LOGIN) ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/activites')
def activites_page():
    return render_template('activites.html')

@app.route('/realisations')
def realisations_page():
    return render_template('realisations.html')

@app.route('/annonces')
def annonces_page():
    return render_template('annonces.html')

@app.route('/offres')
def offres_page():
    return render_template('offres.html')

@app.route('/contact')
def contact_page():
    return render_template('contact.html')

@app.route('/about')
@app.route('/a-propos')
def about_page():
    return render_template('about.html')

# --- API ENDPOINTS ---
@app.route('/api/health')
def api_health():
    return jsonify({'status': 'ok', 'service': 'labmath-website'})

@app.route('/api/activites', methods=['GET'])
def get_activites():
    data = load_data()
    activites = [a for a in data.get('activites', []) if a.get('est_publie', True)]
    return jsonify({'success': True, 'data': activites})

@app.route('/api/activites/<sync_id>', methods=['POST'])
@require_api_key
def save_activite(sync_id):
    data = request.json
    db = load_data()
    
    activite = {
        'sync_id': str(sync_id),
        'titre': data.get('titre'),
        'description': data.get('description', ''),
        'contenu': data.get('contenu', ''),
        'image_url': data.get('image_url', ''),
        'auteur': data.get('auteur', 'Lab_Math'),
        'date_creation': data.get('date_creation', datetime.now().isoformat()),
        'est_publie': data.get('est_publie', True)
    }
    
    found = False
    for i, a in enumerate(db.get('activites', [])):
        if str(a.get('sync_id')) == str(sync_id):
            db['activites'][i] = activite
            found = True
            break
    
    if not found:
        if 'activites' not in db:
            db['activites'] = []
        db['activites'].append(activite)
    
    save_data(db)
    return jsonify({'success': True})

@app.route('/api/activites/<sync_id>', methods=['DELETE'])
@require_api_key
def delete_activite(sync_id):
    db = load_data()
    db['activites'] = [a for a in db.get('activites', []) if str(a.get('sync_id')) != str(sync_id)]
    save_data(db)
    return jsonify({'success': True})

# --- MÊME CHOSE POUR realisations, annonces, offres ---
# (Copiez les endpoints depuis le fichier complet)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/api/upload', methods=['POST'])
@require_api_key
def upload_image():
    file = request.files['file']
    filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.{file.filename.split('.')[-1]}"
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    return jsonify({'success': True, 'url': url_for('uploaded_file', filename=filename, _external=True)})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)