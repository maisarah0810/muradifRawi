from flask import Flask, render_template, request, redirect, url_for, flash,send_file
from preprocessing import preprocess_query
from boolean_retrieval import (
    load_index, load_thesaurus,
    get_expanded_terms, get_related_documents
)
from flask_mail import Mail, Message
from authentication import check_credentials
from level1 import level1_bp
from level2 import level2_bp
from admin import admin_bp 
from reset_password import reset_bp 
from werkzeug.security import generate_password_hash
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import os
import json
import mysql.connector
import hashlib
import random
from authentication import get_db_connection
import re

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with a secure secret key
app.register_blueprint(level1_bp)
app.register_blueprint(level2_bp)
app.register_blueprint(admin_bp) 
app.register_blueprint(reset_bp)

mail = Mail(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HADITH_FOLDER = os.path.join(BASE_DIR, 'docs', 'ShahihBukhari')

PENDING_PATH = os.path.join('FYP', 'index', 'pending.json')

# Load once
index_data = load_index(os.path.join('FYP', 'index', 'narratorindex.txt'))
thesaurus_data = load_thesaurus(os.path.join('FYP', 'index', 'thesaurusnarrator.txt'))

def load_pending_entries():
    if os.path.exists(PENDING_PATH):
        with open(PENDING_PATH, 'r') as f:
            return json.load(f)
    return []

def load_random_hadiths(num_hadiths=5):
    """Load random hadiths from ShahihBukhari folder"""
    hadiths = []
    try:
        
        if not os.path.exists(HADITH_FOLDER):
            print(f"ERROR: Hadith folder does not exist at {HADITH_FOLDER}")
            return ["Hadith folder not found"]
        
        # Get list of all hadith files
        hadith_files = [f for f in os.listdir(HADITH_FOLDER) if f.endswith('.txt')]
        print(f"Found {len(hadith_files)} hadith files")
        print(f"First few files: {hadith_files[:5]}")
        
        if not hadith_files:
            print("No hadith files found")
            return ["No hadith files found."]
        
        # Randomly select files
        selected_files = random.sample(hadith_files, min(num_hadiths, len(hadith_files)))
        
        for filename in selected_files:
            file_path = os.path.join(HADITH_FOLDER, filename)
            print(f"Trying to read: {file_path}")
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    content = content.replace('\r', '')
                    # Replace single newlines (not double) with space
                    content = re.sub(r'(?<!\n)\n(?!\n)', ' ', content)
                    # Optionally, collapse multiple spaces
                    content = re.sub(r' +', ' ', content)
                    hadiths.append(content)
            except Exception as e:
                error_msg = f"Error reading {filename}: {str(e)}"
                hadiths.append(error_msg)
                
    except Exception as e:
        error_msg = f"Error loading hadiths: {str(e)}"
        hadiths = [error_msg]
    
    # Ensure we always return a list, even if empty
    if not hadiths:
        hadiths = ["No hadiths available"]
    return hadiths

@app.route('/login', methods=['GET', 'POST'])
def login_route():
    error = None
    next_page = request.args.get('next') or 'verify'

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        level = check_credentials(email, password)

        print(f"Login attempt: user={email}, level={level}, next={next_page}")

        if level is not None:
            if next_page == 'verify':
                if level == 2:
                    return redirect(url_for('level2_bp.level2'))
                elif level == 1:
                    return redirect(url_for('level1_bp.level1'))
                elif level == 0:
                    return redirect(url_for('admin_bp.admin'))

        else:
            error = "Invalid username or password"

    return render_template('login.html', error=error)

@app.route('/verify', methods=['GET'])
def verify():
    return redirect(url_for('login_route', next='verify'))

@app.route('/', methods=['GET', 'POST'])
def index():
    name = None
    synonyms = []
    hadiths = []
    added_entries = load_pending_entries()
    
    # Test hadith loading with fallback
    try:
        random_hadiths = load_random_hadiths(10)  # Load 10 random hadiths
       
    except Exception as e:
        random_hadiths = ["Test hadith 1", "Test hadith 2", "Test hadith 3"]

    if request.method == 'POST':
        if request.form.get('form_type') == 'search':
            name = preprocess_query(request.form['narrator_name'])
            synonyms = get_expanded_terms(name, thesaurus_data)
            synonyms_raw = [s for s in thesaurus_data if preprocess_query(s) in synonyms]
            hadiths = get_related_documents(synonyms, index_data, HADITH_FOLDER, synonyms_raw)

    return render_template('index.html', name=name, synonyms=synonyms,
                           documents=hadiths, added_entries=added_entries, random_hadiths=random_hadiths)

@app.route('/download_thesaurus')
def download_thesaurus():
    # Paths
    thesaurus_path = os.path.join('FYP', 'index', 'thesaurusnarrator.txt')
    pdf_filename = 'thesaurus_narrator.pdf'
    pdf_path = os.path.join(BASE_DIR, pdf_filename)

    # Read and sort thesaurus lines
    with open(thesaurus_path, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f if line.strip()]
    lines.sort()

    # Generate PDF
    c = canvas.Canvas(pdf_path, pagesize=A4)
    width, height = A4

    # Title
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width / 2, height - 50, "THESAURUS OF NARRATOR'S NAME")

    # Content with numbering
    c.setFont("Helvetica", 12)
    y = height - 80
    for idx, line in enumerate(lines, start=1):
        if y < 50:
            c.showPage()
            y = height - 50
            c.setFont("Helvetica", 12)
        c.drawString(50, y, f"{idx}. {line}")
        y -= 20

    c.save()
    return send_file(pdf_path, as_attachment=True, download_name=pdf_filename)


if __name__ == '__main__':
    app.run()
