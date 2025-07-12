from flask import Blueprint, render_template, request, redirect, url_for,flash
from helpers import get_synonyms,  save_new_entry
from boolean_retrieval import get_related_documents, load_index
import json
import os

level1_bp = Blueprint('level1_bp', __name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PENDING_PATH = os.path.join(BASE_DIR, 'index', 'pending.json')
HADITH_FOLDER = os.path.join(BASE_DIR, 'docs', 'ShahihBukhari')
INDEX_PATH = os.path.join(BASE_DIR, 'index', 'narratorindex.txt')

index_data = load_index(INDEX_PATH)

@level1_bp.route('/level1', methods=['GET', 'POST'])
def level1():
    name = None
    synonyms = []
    hadiths = []

    # Load existing pending entries
    if os.path.exists(PENDING_PATH):
        with open(PENDING_PATH, 'r') as f:
            added_entries = json.load(f)
    else:
        added_entries = []

    if request.method == 'POST':
        form_type = request.form.get('form_type')

        if form_type == 'add':
            base_name = request.form['base_name']  
            new_synonym = request.form['new_synonym']  
            index_value = request.form['index']
            save_new_entry(base_name, new_synonym, index_value)

            flash("New name and synonym successfully added!", "success")
            
            # Reload updated pending list
            if os.path.exists(PENDING_PATH):
                with open(PENDING_PATH, 'r') as f:
                    added_entries = json.load(f)

            return redirect(url_for('level1_bp.level1'))

        elif form_type == 'search':
            name = request.form['narrator_name']
            synonyms = get_synonyms(name)
            hadiths = get_related_documents(synonyms + [name], index_data, HADITH_FOLDER, synonyms + [name])


    return render_template(
        'level1.html',
        added_entries=added_entries,
        name=name,
        synonyms=synonyms,
        documents=hadiths
    )
