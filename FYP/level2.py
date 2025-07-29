from flask import Blueprint, render_template, request, redirect, url_for, flash
from helpers import get_synonyms, save_new_entry, approve_entry, reject_entry, add_new_index, approve_index_entry_with_thesaurus, reject_index_entry, load_pending_index_entries
from boolean_retrieval import get_related_documents, load_index
from preprocessing import preprocess_query
import os
import json

level2_bp = Blueprint('level2_bp', __name__, template_folder='templates')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PENDING_PATH = os.path.join(BASE_DIR, 'index', 'pending.json')
THESAURUS_PATH = os.path.join(BASE_DIR, 'index', 'thesaurusnarrator.txt')
INDEX_PATH = os.path.join(BASE_DIR, 'index', 'narratorindex.txt')
HADITH_FOLDER = os.path.join(BASE_DIR, 'docs', 'ShahihBukhari')
index_data = load_index(INDEX_PATH)
@level2_bp.route('/level2', methods=['GET', 'POST'])
def level2():
    added_entries = []

    # Load pending entries
    if os.path.exists(PENDING_PATH):
        with open(PENDING_PATH, 'r') as f:
            added_entries = json.load(f)

    # Load pending index entries
    pending_index_entries = load_pending_index_entries()

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
            #call function save_new_entry for add new name
            save_new_entry(name, synonym, index)
            flash("New synonym added and pending approval.", "success")

            # Reload entries after adding new
            if os.path.exists(PENDING_PATH):
                with open(PENDING_PATH, 'r') as f:
                    added_entries = json.load(f)

        elif form_type == 'add_index':
            try:
                narrator_name = request.form['narrator_name']
                index_input = request.form['index_numbers']
                # Parse comma-separated indexes
                indexes = [idx.strip() for idx in index_input.split(',') if idx.strip()]  
                if not indexes:
                    flash("Please enter at least one index number.", "error")
                    return redirect(url_for('level2_bp.level2'))
                # Call the add_new_index function
                result = add_new_index(narrator_name, indexes)
                
                # Generate appropriate message based on result
                if result['is_new_name']:
                    flash("New name and index(es) created. You can add synonyms later. Sent for verification.", "success")
                elif result['duplicate_indexes'] and result['new_indexes']:
                    flash(f"Only index(es) {result['new_indexes']} added under existing name. The rest already exist.", "info")
                elif result['duplicate_indexes'] and not result['new_indexes']:
                    flash("All provided indexes already exist under this name.", "warning")
                else:
                    flash("New index(es) added under existing name. Sent for verification.", "success")
                
                # Reload pending index entries
                pending_index_entries = load_pending_index_entries()
                
                return redirect(url_for('level2_bp.level2'))
                
            except ValueError as e:
                flash(str(e), "error")
                return redirect(url_for('level2_bp.level2'))
            except Exception as e:
                flash(f"An error occurred: {str(e)}", "error")
                return redirect(url_for('level2_bp.level2'))

    return render_template(
        'level2.html',
        added_entries=added_entries,
        pending_index_entries=pending_index_entries,
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





@level2_bp.route('/level2/approve_index', methods=['POST'])
def approve_index_entry_route():
    try:
        name = request.form['name']
        indexes_str = request.form['indexes']
        is_new_name = request.form.get('is_new_name', 'false').lower() == 'true'
        
        # Parse indexes from string
        indexes = [int(idx.strip()) for idx in indexes_str.strip('[]').split(',') if idx.strip().isdigit()]
        
        approve_index_entry_with_thesaurus(name, indexes, is_new_name)
        
        flash("Index entry approved and removed from pending.", "success")
        return redirect(url_for('level2_bp.level2'))
    except Exception as e:
        flash(f"Error processing request: {str(e)}", "error")
        return redirect(url_for('level2_bp.level2'))


        

@level2_bp.route('/level2/reject_index', methods=['POST'])
def reject_index_entry_route():
    try:
        name = request.form['name']
        indexes_str = request.form['indexes']
        
        # Parse indexes from string
        indexes = [int(idx.strip()) for idx in indexes_str.strip('[]').split(',') if idx.strip().isdigit()]
        
        reject_index_entry(name, indexes)
        
        flash("Index entry rejected and removed from pending.", "info")
        return redirect(url_for('level2_bp.level2'))
    except Exception as e:
        flash(f"Error processing request: {str(e)}", "error")
        return redirect(url_for('level2_bp.level2'))
