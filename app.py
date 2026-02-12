#!/usr/bin/env python3
"""
Lab_Math - Site Principal complet
Déployé sur Render.com
Fichier: app.py (À la racine du projet)
"""

from flask import Flask, request, jsonify, render_template, send_from_directory, url_for
from flask_cors import CORS
import os
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from functools import wraps
import uuid
import re
import psycopg2
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Création de l'application Flask
app = Flask(__name__, 
            static_folder='static',
            template_folder='templates',
            static_url_path='/static')
CORS(app)

# --- CONFIGURATION GÉNÉRALE ---
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'labmath_secret_key_2024')
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

# Créer les dossiers nécessaires
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('data', exist_ok=True)

# --- CONFIGURATION API ---
API_KEY = os.environ.get('API_KEY', 'labmath_api_secret_2024')
DATA_FILE = 'data/data.json'

# --- CONFIGURATION EMAIL (pour le formulaire de contact) ---
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USER = os.environ.get('EMAIL_USER')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD')
ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'contact@labmath.com')

# --- CONFIGURATION BASE DE DONNÉES (pour le formulaire de contact) ---
DATABASE_URL = os.environ.get('DATABASE_URL')

# --- DÉCORATEUR POUR L'API ---
def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if api_key and api_key == API_KEY:
            return f(*args, **kwargs)
        return jsonify({'success': False, 'message': 'Clé API invalide'}), 401
    return decorated_function

# --- FONCTIONS DE GESTION DES DONNÉES JSON ---
def load_data():
    """Charge les données depuis le fichier JSON"""
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # Structure par défaut
        return {
            'activites': [],
            'realisations': [],
            'annonces': [],
            'offres': [],
            'last_update': datetime.now().isoformat()
        }

def save_data(data):
    """Sauvegarde les données dans le fichier JSON"""
    data['last_update'] = datetime.now().isoformat()
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# --- FONCTIONS POUR LA BASE DE DONNÉES CONTACT (PostgreSQL) ---
def init_contact_db():
    """Initialiser la base de données PostgreSQL pour les contacts"""
    if not DATABASE_URL:
        print("⚠️ DATABASE_URL non configurée, les contacts seront sauvegardés dans un fichier JSON")
        return
    
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # Créer la table des contacts
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS contacts (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(100) NOT NULL,
                subject VARCHAR(200) NOT NULL,
                message TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status VARCHAR(20) DEFAULT 'pending'
            )
        ''')
        
        # Créer la table des logs
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS contact_logs (
                id SERIAL PRIMARY KEY,
                contact_id INTEGER REFERENCES contacts(id),
                action VARCHAR(50),
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        cursor.close()
        conn.close()
        print("✅ Base de données contacts initialisée (PostgreSQL)")
    except Exception as e:
        print(f"⚠️ Erreur PostgreSQL, utilisation du fichier JSON: {e}")

def save_contact_to_json(contact_data):
    """Sauvegarde de secours dans un fichier JSON"""
    contact_file = 'data/contacts.json'
    try:
        if os.path.exists(contact_file):
            with open(contact_file, 'r', encoding='utf-8') as f:
                contacts = json.load(f)
        else:
            contacts = []
        
        contact_data['id'] = len(contacts) + 1
        contact_data['created_at'] = datetime.now().isoformat()
        contacts.append(contact_data)
        
        with open(contact_file, 'w', encoding='utf-8') as f:
            json.dump(contacts, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Erreur sauvegarde JSON: {e}")
        return False

def send_email(to_email, subject, body):
    """Envoyer un email"""
    if not EMAIL_USER or not EMAIL_PASSWORD:
        print("⚠️ Configuration email manquante")
        return False
    
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_USER
        msg['To'] = to_email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'html'))
        
        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.send_message(msg)
        
        return True
    except Exception as e:
        print(f"Erreur d'envoi d'email: {e}")
        return False

# --- ROUTES PRINCIPALES DU SITE WEB ---

@app.route('/')
def index():
    """Page d'accueil"""
    return render_template('index.html')

@app.route('/activites')
def activites_page():
    """Page des activités"""
    return render_template('activites.html')

@app.route('/realisations')
def realisations_page():
    """Page des réalisations"""
    return render_template('realisations.html')

@app.route('/annonces')
def annonces_page():
    """Page des annonces"""
    return render_template('annonces.html')

@app.route('/offres')
def offres_page():
    """Page des offres"""
    return render_template('offres.html')

@app.route('/contact')
def contact_page():
    """Page de contact"""
    return render_template('contact.html')

@app.route('/about')
@app.route('/a-propos')
def about_page():
    """Page à propos"""
    return render_template('about.html')

# --- API ENDPOINTS - SANTÉ ET STATUT ---

@app.route('/api/health', methods=['GET'])
def api_health():
    """Vérifier que l'API fonctionne"""
    return jsonify({
        'success': True,
        'status': 'ok',
        'service': 'labmath-website',
        'timestamp': datetime.now().isoformat(),
        'data_file_exists': os.path.exists(DATA_FILE),
        'data_count': len(load_data().get('activites', []))
    })

@app.route('/api/status', methods=['GET'])
def api_status():
    """Statut complet de l'API"""
    data = load_data()
    return jsonify({
        'success': True,
        'timestamp': datetime.now().isoformat(),
        'stats': {
            'activites': len(data.get('activites', [])),
            'realisations': len(data.get('realisations', [])),
            'annonces': len(data.get('annonces', [])),
            'offres': len(data.get('offres', []))
        },
        'last_update': data.get('last_update')
    })

# --- API ENDPOINTS - ACTIVITÉS ---

@app.route('/api/activites', methods=['GET'])
def get_activites():
    """Récupère toutes les activités publiées"""
    data = load_data()
    activites = data.get('activites', [])
    # Filtrer seulement les activités publiées
    activites_publiees = [a for a in activites if a.get('est_publie', True)]
    
    # Trier par date de création (plus récent d'abord)
    activites_publiees.sort(key=lambda x: x.get('date_creation', ''), reverse=True)
    
    return jsonify({
        'success': True,
        'count': len(activites_publiees),
        'data': activites_publiees
    })

@app.route('/api/activites/<sync_id>', methods=['GET'])
def get_activite(sync_id):
    """Récupère une activité spécifique"""
    data = load_data()
    for activite in data.get('activites', []):
        if str(activite.get('sync_id')) == str(sync_id):
            return jsonify({'success': True, 'data': activite})
    return jsonify({'success': False, 'message': 'Activité non trouvée'}), 404

@app.route('/api/activites', methods=['POST'])
@app.route('/api/activites/<sync_id>', methods=['POST'])
@require_api_key
def save_activite(sync_id=None):
    """Crée ou met à jour une activité (depuis l'admin)"""
    try:
        data = request.json
        if not data:
            return jsonify({'success': False, 'message': 'Données manquantes'}), 400
        
        db = load_data()
        item_id = sync_id or data.get('id') or str(uuid.uuid4())
        
        # Préparer l'activité
        activite = {
            'sync_id': str(item_id),
            'titre': data.get('titre', 'Sans titre'),
            'description': data.get('description', ''),
            'contenu': data.get('contenu', ''),
            'image_url': data.get('image_url', ''),
            'auteur': data.get('auteur', 'Lab_Math'),
            'date_creation': data.get('date_creation', datetime.now().isoformat()),
            'date_modification': datetime.now().isoformat(),
            'est_publie': data.get('est_publie', True)
        }
        
        # Chercher et mettre à jour ou ajouter
        found = False
        for i, item in enumerate(db.get('activites', [])):
            if str(item.get('sync_id')) == str(item_id):
                db['activites'][i] = activite
                found = True
                break
        
        if not found:
            if 'activites' not in db:
                db['activites'] = []
            db['activites'].append(activite)
        
        save_data(db)
        
        return jsonify({
            'success': True,
            'id': item_id,
            'message': 'Activité sauvegardée avec succès'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Erreur: {str(e)}'
        }), 500

@app.route('/api/activites/<sync_id>', methods=['DELETE'])
@require_api_key
def delete_activite(sync_id):
    """Supprime une activité"""
    try:
        db = load_data()
        initial_count = len(db.get('activites', []))
        
        db['activites'] = [a for a in db.get('activites', []) 
                          if str(a.get('sync_id')) != str(sync_id)]
        
        if len(db['activites']) < initial_count:
            save_data(db)
            return jsonify({'success': True, 'message': 'Activité supprimée'})
        else:
            return jsonify({'success': False, 'message': 'Activité non trouvée'}), 404
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Erreur: {str(e)}'
        }), 500

# --- API ENDPOINTS - RÉALISATIONS ---

@app.route('/api/realisations', methods=['GET'])
def get_realisations():
    """Récupère toutes les réalisations"""
    data = load_data()
    realisations = data.get('realisations', [])
    realisations.sort(key=lambda x: x.get('date_creation', ''), reverse=True)
    
    return jsonify({
        'success': True,
        'count': len(realisations),
        'data': realisations
    })

@app.route('/api/realisations', methods=['POST'])
@app.route('/api/realisations/<sync_id>', methods=['POST'])
@require_api_key
def save_realisation(sync_id=None):
    """Crée ou met à jour une réalisation"""
    try:
        data = request.json
        db = load_data()
        item_id = sync_id or data.get('id') or str(uuid.uuid4())
        
        realisation = {
            'sync_id': str(item_id),
            'titre': data.get('titre', 'Sans titre'),
            'description': data.get('description', ''),
            'image_url': data.get('image_url', ''),
            'categorie': data.get('categorie', 'Projet'),
            'date_realisation': data.get('date_realisation'),
            'date_creation': data.get('date_creation', datetime.now().isoformat()),
            'date_modification': datetime.now().isoformat()
        }
        
        found = False
        for i, item in enumerate(db.get('realisations', [])):
            if str(item.get('sync_id')) == str(item_id):
                db['realisations'][i] = realisation
                found = True
                break
        
        if not found:
            if 'realisations' not in db:
                db['realisations'] = []
            db['realisations'].append(realisation)
        
        save_data(db)
        return jsonify({'success': True, 'id': item_id, 'message': 'Réalisation sauvegardée'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/realisations/<sync_id>', methods=['DELETE'])
@require_api_key
def delete_realisation(sync_id):
    """Supprime une réalisation"""
    try:
        db = load_data()
        db['realisations'] = [r for r in db.get('realisations', []) 
                            if str(r.get('sync_id')) != str(sync_id)]
        save_data(db)
        return jsonify({'success': True, 'message': 'Réalisation supprimée'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# --- API ENDPOINTS - ANNONCES ---

@app.route('/api/annonces', methods=['GET'])
def get_annonces():
    """Récupère toutes les annonces actives"""
    data = load_data()
    annonces = data.get('annonces', [])
    
    # Filtrer les annonces actives
    annonces_actives = [a for a in annonces if a.get('est_active', True)]
    
    # Vérifier les dates de validité
    maintenant = datetime.now()
    annonces_valides = []
    for annonce in annonces_actives:
        date_debut = annonce.get('date_debut')
        date_fin = annonce.get('date_fin')
        
        if date_debut:
            try:
                debut = datetime.fromisoformat(date_debut.replace('Z', '+00:00'))
                if debut > maintenant:
                    continue
            except:
                pass
        
        if date_fin:
            try:
                fin = datetime.fromisoformat(date_fin.replace('Z', '+00:00'))
                if fin < maintenant:
                    continue
            except:
                pass
        
        annonces_valides.append(annonce)
    
    annonces_valides.sort(key=lambda x: x.get('date_creation', ''), reverse=True)
    
    return jsonify({
        'success': True,
        'count': len(annonces_valides),
        'data': annonces_valides
    })

@app.route('/api/annonces', methods=['POST'])
@app.route('/api/annonces/<sync_id>', methods=['POST'])
@require_api_key
def save_annonce(sync_id=None):
    """Crée ou met à jour une annonce"""
    try:
        data = request.json
        db = load_data()
        item_id = sync_id or data.get('id') or str(uuid.uuid4())
        
        annonce = {
            'sync_id': str(item_id),
            'titre': data.get('titre', 'Sans titre'),
            'contenu': data.get('contenu', ''),
            'type_annonce': data.get('type_annonce', 'info'),
            'date_debut': data.get('date_debut'),
            'date_fin': data.get('date_fin'),
            'date_creation': data.get('date_creation', datetime.now().isoformat()),
            'date_modification': datetime.now().isoformat(),
            'est_active': data.get('est_active', True)
        }
        
        found = False
        for i, item in enumerate(db.get('annonces', [])):
            if str(item.get('sync_id')) == str(item_id):
                db['annonces'][i] = annonce
                found = True
                break
        
        if not found:
            if 'annonces' not in db:
                db['annonces'] = []
            db['annonces'].append(annonce)
        
        save_data(db)
        return jsonify({'success': True, 'id': item_id, 'message': 'Annonce sauvegardée'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/annonces/<sync_id>', methods=['DELETE'])
@require_api_key
def delete_annonce(sync_id):
    """Supprime une annonce"""
    try:
        db = load_data()
        db['annonces'] = [a for a in db.get('annonces', []) 
                        if str(a.get('sync_id')) != str(sync_id)]
        save_data(db)
        return jsonify({'success': True, 'message': 'Annonce supprimée'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# --- API ENDPOINTS - OFFRES ---

@app.route('/api/offres', methods=['GET'])
def get_offres():
    """Récupère toutes les offres actives"""
    data = load_data()
    offres = data.get('offres', [])
    
    # Filtrer les offres actives et non expirées
    maintenant = datetime.now().date()
    offres_actives = []
    
    for offre in offres:
        if not offre.get('est_active', True):
            continue
            
        date_limite = offre.get('date_limite')
        if date_limite:
            try:
                limite = datetime.fromisoformat(date_limite).date()
                if limite < maintenant:
                    continue
            except:
                pass
        
        offres_actives.append(offre)
    
    offres_actives.sort(key=lambda x: x.get('date_creation', ''), reverse=True)
    
    return jsonify({
        'success': True,
        'count': len(offres_actives),
        'data': offres_actives
    })

@app.route('/api/offres', methods=['POST'])
@app.route('/api/offres/<sync_id>', methods=['POST'])
@require_api_key
def save_offre(sync_id=None):
    """Crée ou met à jour une offre"""
    try:
        data = request.json
        db = load_data()
        item_id = sync_id or data.get('id') or str(uuid.uuid4())
        
        offre = {
            'sync_id': str(item_id),
            'titre': data.get('titre', 'Sans titre'),
            'description': data.get('description', ''),
            'type_offre': data.get('type_offre', 'autre'),
            'lieu': data.get('lieu', ''),
            'date_limite': data.get('date_limite'),
            'date_creation': data.get('date_creation', datetime.now().isoformat()),
            'date_modification': datetime.now().isoformat(),
            'est_active': data.get('est_active', True)
        }
        
        found = False
        for i, item in enumerate(db.get('offres', [])):
            if str(item.get('sync_id')) == str(item_id):
                db['offres'][i] = offre
                found = True
                break
        
        if not found:
            if 'offres' not in db:
                db['offres'] = []
            db['offres'].append(offre)
        
        save_data(db)
        return jsonify({'success': True, 'id': item_id, 'message': 'Offre sauvegardée'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/offres/<sync_id>', methods=['DELETE'])
@require_api_key
def delete_offre(sync_id):
    """Supprime une offre"""
    try:
        db = load_data()
        db['offres'] = [o for o in db.get('offres', []) 
                       if str(o.get('sync_id')) != str(sync_id)]
        save_data(db)
        return jsonify({'success': True, 'message': 'Offre supprimée'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# --- API ENDPOINTS - FORMULAIRE DE CONTACT ---

@app.route('/api/contact', methods=['POST'])
def submit_contact():
    """Traiter le formulaire de contact"""
    try:
        data = request.json
        
        # Validation des données
        required_fields = ['name', 'email', 'subject', 'message']
        for field in required_fields:
            if field not in data or not data[field].strip():
                return jsonify({
                    'success': False,
                    'error': f'Le champ {field} est requis'
                }), 400
        
        # Validation de l'email
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, data['email']):
            return jsonify({
                'success': False,
                'error': 'Adresse email invalide'
            }), 400
        
        contact_data = {
            'name': data['name'],
            'email': data['email'],
            'subject': data['subject'],
            'message': data['message']
        }
        
        contact_id = None
        
        # Essayer PostgreSQL d'abord
        if DATABASE_URL:
            try:
                conn = psycopg2.connect(DATABASE_URL)
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO contacts (name, email, subject, message)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                ''', (data['name'], data['email'], data['subject'], data['message']))
                
                contact_id = cursor.fetchone()[0]
                
                cursor.execute('''
                    INSERT INTO contact_logs (contact_id, action, details)
                    VALUES (%s, %s, %s)
                ''', (contact_id, 'submitted', json.dumps(data)))
                
                conn.commit()
                cursor.close()
                conn.close()
                
            except Exception as e:
                print(f"Erreur PostgreSQL: {e}, fallback vers JSON")
                save_contact_to_json(contact_data)
        else:
            # Fallback vers JSON
            save_contact_to_json(contact_data)
        
        # Préparer les emails
        user_email_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ padding: 30px; background: #f9f9f9; border: 1px solid #eee; }}
                .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Lab_Math</h1>
                    <p>Confirmation de réception</p>
                </div>
                <div class="content">
                    <h2>Bonjour {data['name']},</h2>
                    <p>Nous avons bien reçu votre message et nous vous en remercions.</p>
                    <p><strong>Sujet :</strong> {data['subject']}</p>
                    <p><strong>Votre message :</strong></p>
                    <p style="background: white; padding: 15px; border-left: 4px solid #667eea;">{data['message']}</p>
                    <p>Notre équipe va examiner votre demande et vous répondra dans les plus brefs délais.</p>
                    <p>Cordialement,<br>L'équipe Lab_Math</p>
                </div>
                <div class="footer">
                    <p>© {datetime.now().year} Lab_Math. Tous droits réservés.</p>
                    <p>Cet email a été envoyé automatiquement, merci de ne pas y répondre.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        admin_email_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ padding: 30px; background: #f9f9f9; border: 1px solid #eee; }}
                .info-box {{ background: #e3f2fd; padding: 15px; border-left: 4px solid #667eea; margin: 20px 0; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Nouveau contact Lab_Math</h1>
                </div>
                <div class="content">
                    <div class="info-box">
                        <p><strong>De :</strong> {data['name']} ({data['email']})</p>
                        <p><strong>Sujet :</strong> {data['subject']}</p>
                        <p><strong>Date :</strong> {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
                        <p><strong>ID :</strong> {contact_id if contact_id else 'JSON'}</p>
                    </div>
                    <h3>Message :</h3>
                    <p style="background: white; padding: 15px; border-radius: 5px;">{data['message']}</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Envoyer les emails si configurés
        if EMAIL_USER and EMAIL_PASSWORD:
            send_email(data['email'], '✅ Confirmation de réception - Lab_Math', user_email_body)
            send_email(ADMIN_EMAIL, f'📬 Nouveau contact: {data["subject"]}', admin_email_body)
        
        return jsonify({
            'success': True,
            'message': 'Message envoyé avec succès',
            'contact_id': contact_id,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Erreur interne: {str(e)}'
        }), 500

@app.route('/api/contacts', methods=['GET'])
@require_api_key
def get_contacts():
    """Récupérer la liste des contacts (pour l'admin)"""
    try:
        if DATABASE_URL:
            conn = psycopg2.connect(DATABASE_URL)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, name, email, subject, message, created_at, status
                FROM contacts
                ORDER BY created_at DESC
                LIMIT 100
            ''')
            
            columns = [desc[0] for desc in cursor.description]
            contacts = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            cursor.close()
            conn.close()
            
            return jsonify({
                'success': True,
                'contacts': contacts,
                'count': len(contacts)
            })
        else:
            # Lire depuis le fichier JSON
            contact_file = 'data/contacts.json'
            if os.path.exists(contact_file):
                with open(contact_file, 'r', encoding='utf-8') as f:
                    contacts = json.load(f)
                return jsonify({
                    'success': True,
                    'contacts': contacts,
                    'count': len(contacts)
                })
            else:
                return jsonify({
                    'success': True,
                    'contacts': [],
                    'count': 0
                })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# --- ENDPOINT POUR LES IMAGES UPLOADÉES ---

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """Servir les fichiers uploadés"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# --- ADMIN: ENDPOINT POUR UPLOADER DES IMAGES ---

@app.route('/api/upload', methods=['POST'])
@require_api_key
def upload_image():
    """Upload d'image depuis l'admin"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': 'Aucun fichier'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'message': 'Nom de fichier vide'}), 400
        
        # Générer un nom unique
        ext = file.filename.split('.')[-1] if '.' in file.filename else 'jpg'
        filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.{ext}"
        
        # Sauvegarder
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        
        # Retourner l'URL complète
        file_url = url_for('uploaded_file', filename=filename, _external=True)
        
        return jsonify({
            'success': True,
            'url': file_url,
            'filename': filename
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# --- INITIALISATION ---

@app.before_request
def before_request():
    """Exécuté avant chaque requête"""
    # S'assurer que le dossier data existe
    os.makedirs('data', exist_ok=True)

# --- GESTION DES ERREURS ---

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500

# --- DÉMARRAGE ---

if __name__ == '__main__':
    # Initialiser la base de données des contacts
    init_contact_db()
    
    # Créer un fichier data.json vide si nécessaire
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
    
    print("\n" + "="*60)
    print("🚀 Lab_Math - Site Principal (Version Complète)")
    print("="*60)
    print(f"📁 Dossier data: {os.path.abspath('data')}")
    print(f"📁 Dossier uploads: {os.path.abspath(app.config['UPLOAD_FOLDER'])}")
    print(f"🔑 Clé API: {'Configurée' if API_KEY else 'Non configurée'}")
    print(f"📧 Email: {'Configuré' if EMAIL_USER else 'Non configuré'}")
    print(f"🗄️  Base données contacts: {'PostgreSQL' if DATABASE_URL else 'JSON (local)'}")
    print(f"🌐 URL: http://0.0.0.0:{port}")
    print("="*60 + "\n")
    
    app.run(host='0.0.0.0', port=port, debug=False)