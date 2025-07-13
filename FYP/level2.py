from flask import Blueprint, render_template, request, redirect, url_for, flash
from helpers import get_synonyms,save_new_entry, approve_entry, reject_entry
from boolean_retrieval import get_related_documents, load_index
from preprocessing import preprocess_query
import os
import json

level2_bp = Blueprint('level2_bp', __name__, template_folder='templates')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PENDING_PATH = os.path.join('index', 'pending.json')
THESAURUS_PATH = os.path.join('index', 'thesaurusnarrator.txt')
INDEX_PATH = os.path.join('index', 'narratorindex.txt')
HADITH_FOLDER = os.path.join( 'docs', 'ShahihBukhari')
index_data = load_index(INDEX_PATH)
@level2_bp.route('/level2', methods=['GET', 'POST'])
def level2():
    added_entries = []

    # Load pending entries
    if os.path.exists(PENDING_PATH):
        with open(PENDING_PATH, 'r') as f:
            added_entries = json.load(f)

    name = None
    synonyms = []
    documents = []

    if request.method == 'POST':
        form_type = request.form.get('form_type')

        if form_type == 'search':
            name = request.form['narrator_name']
            synonyms = get_synonyms(name)
            documents = get_related_documents(synonyms + [name], index_data, HADITH_FOLDER, synonyms + [name])

        elif form_type == 'add':
            name = request.form['base_name']
            synonym = request.form['new_synonym']
            index = request.form['index']
            save_new_entry(name, synonym, index)

            flash("New synonym added and pending approval.", "success")

            # Reload entries after adding new
            if os.path.exists(PENDING_PATH):
                with open(PENDING_PATH, 'r') as f:
                    added_entries = json.load(f)

    return render_template(
        'level2.html',
        added_entries=added_entries,
        name=name,
        synonyms=synonyms,
        documents=documents
    )

@level2_bp.route('/level2/approve', methods=['POST'])
def approve_entry_route():
    try:
        base_name = preprocess_query(request.form['base_name'])
        new_synonym = preprocess_query(request.form['synonym'])
        index_value = request.form.get('index_value', '') 

        # Call centralized logic and get result
        result = approve_entry(base_name, new_synonym, index_value)
        
        # Check if both base name and synonym already existed
        if result['both_existed']:
            flash("Name already exists in thesaurus, but index has been updated", "info")
        else:
            flash("Name successfully approved!", "success")
        
        return redirect(url_for('level2_bp.level2'))
    except Exception as e:
        flash(f"Error processing request: {str(e)}", "error")
        return redirect(url_for('level2_bp.level2'))


@level2_bp.route('/level2/reject', methods=['POST'])
def reject_entry_route():
    new_name = preprocess_query(request.form['new_name'])  # The synonym to reject

    reject_entry(new_name)
    
    flash("Entry has been rejected.", "info")
    return redirect(url_for('level2_bp.level2'))
