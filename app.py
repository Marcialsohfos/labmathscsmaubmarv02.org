from flask import Flask, request, jsonify, render_template, send_from_directory, url_for
from flask_cors import CORS
import os
import json
from datetime import datetime
from functools import wraps
import uuid

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)

# --- CONFIGURATION ---
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'labmath_secret_key_2024')
app.config['UPLOAD_FOLDER'] = 'static/uploads'

API_KEY = os.environ.get('API_KEY', 'labmath_api_secret_2024')
DATA_FILE = 'data/data.json'

# Créer les dossiers
os.makedirs('data', exist_ok=True)
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# --- FONCTIONS JSON ---
def load_data():
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {
            'activites': [],
            'realisations': [],
            'annonces': [],
            'offres': [],
            'last_update': datetime.now().isoformat()
        }

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

# --- ROUTES PUBLIQUES ---
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

# --- API HEALTH ---
@app.route('/api/health')
def api_health():
    return jsonify({
        'status': 'ok',
        'service': 'labmath-website',
        'timestamp': datetime.now().isoformat()
    })

# --- API ACTIVITÉS ---
@app.route('/api/activites', methods=['GET'])
def get_activites():
    data = load_data()
    activites = [a for a in data.get('activites', []) if a.get('est_publie', True)]
    return jsonify({'success': True, 'data': activites})

@app.route('/api/activites/<sync_id>', methods=['POST'])
@require_api_key
def save_activite(sync_id):
    try:
        data = request.json
        db = load_data()
        
        activite = {
            'sync_id': str(sync_id),
            'titre': data.get('titre'),
            'description': data.get('description', ''),
            'contenu': data.get('contenu', ''),
            'image_url': data.get('image_url', ''),
            'auteur': data.get('auteur', 'Admin'),
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
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/activites/<sync_id>', methods=['DELETE'])
@require_api_key
def delete_activite(sync_id):
    db = load_data()
    db['activites'] = [a for a in db.get('activites', []) if str(a.get('sync_id')) != str(sync_id)]
    save_data(db)
    return jsonify({'success': True})

# --- API RÉALISATIONS ---
@app.route('/api/realisations', methods=['GET'])
def get_realisations():
    data = load_data()
    return jsonify({'success': True, 'data': data.get('realisations', [])})

@app.route('/api/realisations/<sync_id>', methods=['POST'])
@require_api_key
def save_realisation(sync_id):
    try:
        data = request.json
        db = load_data()
        
        realisation = {
            'sync_id': str(sync_id),
            'titre': data.get('titre'),
            'description': data.get('description', ''),
            'image_url': data.get('image_url', ''),
            'categorie': data.get('categorie', ''),
            'date_realisation': data.get('date_realisation'),
            'date_creation': data.get('date_creation', datetime.now().isoformat())
        }
        
        found = False
        for i, r in enumerate(db.get('realisations', [])):
            if str(r.get('sync_id')) == str(sync_id):
                db['realisations'][i] = realisation
                found = True
                break
        
        if not found:
            if 'realisations' not in db:
                db['realisations'] = []
            db['realisations'].append(realisation)
        
        save_data(db)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/realisations/<sync_id>', methods=['DELETE'])
@require_api_key
def delete_realisation(sync_id):
    db = load_data()
    db['realisations'] = [r for r in db.get('realisations', []) if str(r.get('sync_id')) != str(sync_id)]
    save_data(db)
    return jsonify({'success': True})

# --- API ANNONCES ---
@app.route('/api/annonces', methods=['GET'])
def get_annonces():
    data = load_data()
    annonces = [a for a in data.get('annonces', []) if a.get('est_active', True)]
    return jsonify({'success': True, 'data': annonces})

@app.route('/api/annonces/<sync_id>', methods=['POST'])
@require_api_key
def save_annonce(sync_id):
    try:
        data = request.json
        db = load_data()
        
        annonce = {
            'sync_id': str(sync_id),
            'titre': data.get('titre'),
            'contenu': data.get('contenu', ''),
            'type_annonce': data.get('type_annonce', 'info'),
            'date_debut': data.get('date_debut'),
            'date_fin': data.get('date_fin'),
            'date_creation': data.get('date_creation', datetime.now().isoformat()),
            'est_active': data.get('est_active', True)
        }
        
        found = False
        for i, a in enumerate(db.get('annonces', [])):
            if str(a.get('sync_id')) == str(sync_id):
                db['annonces'][i] = annonce
                found = True
                break
        
        if not found:
            if 'annonces' not in db:
                db['annonces'] = []
            db['annonces'].append(annonce)
        
        save_data(db)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/annonces/<sync_id>', methods=['DELETE'])
@require_api_key
def delete_annonce(sync_id):
    db = load_data()
    db['annonces'] = [a for a in db.get('annonces', []) if str(a.get('sync_id')) != str(sync_id)]
    save_data(db)
    return jsonify({'success': True})

# --- API OFFRES ---
@app.route('/api/offres', methods=['GET'])
def get_offres():
    data = load_data()
    offres = [o for o in data.get('offres', []) if o.get('est_active', True)]
    return jsonify({'success': True, 'data': offres})

@app.route('/api/offres/<sync_id>', methods=['POST'])
@require_api_key
def save_offre(sync_id):
    try:
        data = request.json
        db = load_data()
        
        offre = {
            'sync_id': str(sync_id),
            'titre': data.get('titre'),
            'description': data.get('description', ''),
            'type_offre': data.get('type_offre', 'autre'),
            'lieu': data.get('lieu', ''),
            'date_limite': data.get('date_limite'),
            'date_creation': data.get('date_creation', datetime.now().isoformat()),
            'est_active': data.get('est_active', True)
        }
        
        found = False
        for i, o in enumerate(db.get('offres', [])):
            if str(o.get('sync_id')) == str(sync_id):
                db['offres'][i] = offre
                found = True
                break
        
        if not found:
            if 'offres' not in db:
                db['offres'] = []
            db['offres'].append(offre)
        
        save_data(db)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/offres/<sync_id>', methods=['DELETE'])
@require_api_key
def delete_offre(sync_id):
    db = load_data()
    db['offres'] = [o for o in db.get('offres', []) if str(o.get('sync_id')) != str(sync_id)]
    save_data(db)
    return jsonify({'success': True})

# --- UPLOAD IMAGES ---
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/api/upload', methods=['POST'])
@require_api_key
def upload_image():
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': 'Aucun fichier'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'message': 'Nom de fichier vide'}), 400
        
        ext = file.filename.split('.')[-1] if '.' in file.filename else 'jpg'
        filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.{ext}"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        
        return jsonify({
            'success': True,
            'url': url_for('uploaded_file', filename=filename, _external=True)
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# --- GESTION DES ERREURS ---
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500

# --- DÉMARRAGE ---
if __name__ == '__main__':
    if not os.path.exists(DATA_FILE):
        save_data({
            'activites': [],
            'realisations': [],
            'annonces': [],
            'offres': [],
            'last_update': datetime.now().isoformat()
        })
        print("✅ Fichier data.json créé")
    
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)