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

PENDING_PATH = os.path.join(BASE_DIR, 'index', 'pending.json')
index_data = load_index(os.path.join(BASE_DIR, 'index', 'narratorindex.txt'))
thesaurus_data = load_thesaurus(os.path.join(BASE_DIR, 'index', 'thesaurusnarrator.txt'))


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
            return ["Hadith folder not found"]
        
        # Get list of all hadith files
        hadith_files = [f for f in os.listdir(HADITH_FOLDER) if f.endswith('.txt')]
        
        if not hadith_files:
            return ["No hadith files found."]
        
        # Randomly select files
        selected_files = random.sample(hadith_files, min(num_hadiths, len(hadith_files)))
        
        for filename in selected_files:
            file_path = os.path.join(HADITH_FOLDER, filename)
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
    thesaurus_path = os.path.join(BASE_DIR, 'index', 'thesaurusnarrator.txt')
    pdf_filename = 'thesaurus_narrator.pdf'
    pdf_path = os.path.join(BASE_DIR, pdf_filename)

    # Read and sort thesaurus lines
    with open(thesaurus_path, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f if line.strip()]
    lines.sort()

    # Generate PDF
    c = canvas.Canvas(pdf_path, pagesize=A4)
    width, height = A4

    # Define margins
    left_margin = 50
    right_margin = 50
    top_margin = 80
    bottom_margin = 50
    available_width = width - left_margin - right_margin

    # Title
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width / 2, height - top_margin, "THESAURUS OF NARRATOR'S NAME")

    # Content with proper word wrapping
    c.setFont("Helvetica", 10)  # Smaller font for better fit
    y = height - top_margin - 30
    line_height = 15

    for idx, line in enumerate(lines, start=1):
        # Check if we need a new page
        if y < bottom_margin + line_height:
            c.showPage()
            y = height - top_margin
            c.setFont("Helvetica", 10)

        # Split long lines into multiple lines
        words = line.split(':')
        if len(words) >= 2:
            primary_name = words[0].strip()
            synonyms = words[1].strip()
            
            # Draw primary name
            c.drawString(left_margin, y, f"{idx}. {primary_name}:")
            y -= line_height
            
            # Split synonyms by comma and wrap long text
            synonym_list = [s.strip() for s in synonyms.split(',')]
            current_line = ""
            
            for synonym in synonym_list:
                test_line = current_line + (", " if current_line else "") + synonym
                if c.stringWidth(test_line, "Helvetica", 10) <= available_width:
                    current_line = test_line
                else:
                    # Draw current line and start new one
                    if current_line:
                        c.drawString(left_margin + 20, y, current_line)
                        y -= line_height
                        if y < bottom_margin + line_height:
                            c.showPage()
                            y = height - top_margin
                            c.setFont("Helvetica", 10)
                    current_line = synonym
            
            # Draw remaining line
            if current_line:
                c.drawString(left_margin + 20, y, current_line)
                y -= line_height * 1.5  # Extra space between entries
        else:
            # Simple line without splitting
            if c.stringWidth(f"{idx}. {line}", "Helvetica", 10) <= available_width:
                c.drawString(left_margin, y, f"{idx}. {line}")
            else:
                # Split long line into multiple lines
                words = line.split()
                current_line = f"{idx}. "
                for word in words:
                    test_line = current_line + word + " "
                    if c.stringWidth(test_line, "Helvetica", 10) <= available_width:
                        current_line = test_line
                    else:
                        c.drawString(left_margin, y, current_line.strip())
                        y -= line_height
                        if y < bottom_margin + line_height:
                            c.showPage()
                            y = height - top_margin
                            c.setFont("Helvetica", 10)
                        current_line = word + " "
                
                if current_line.strip():
                    c.drawString(left_margin, y, current_line.strip())
                y -= line_height * 1.5

    c.save()
    return send_file(pdf_path, as_attachment=True, download_name=pdf_filename)


if __name__ == '__main__':
    app.run()
