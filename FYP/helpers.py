import os
import json
from boolean_retrieval import (
    load_index, load_thesaurus,
    get_expanded_terms, boolean_or_retrieval, load_hadith_documents
)
from preprocessing import preprocess_query


# Define correct absolute paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

INDEX_PATH = os.path.join('index', 'narratorindex.txt')
THESAURUS_PATH = os.path.join('index', 'thesaurusnarrator.txt')
PENDING_PATH = os.path.join('index', 'pending.json')
HADITH_FOLDER = os.path.join('docs', 'ShahihBukhari')

# Load index and thesaurus once
index = load_index(INDEX_PATH)
thesaurus = load_thesaurus(THESAURUS_PATH)

def get_synonyms(name):
    return list(get_expanded_terms(name, thesaurus))


def save_new_entry(base_name, synonym, index_value):
    new_entry = {
        "base_name": base_name,
        "synonym": synonym,
        "index_value": index_value
    }

    if os.path.exists(PENDING_PATH):
        with open(PENDING_PATH, 'r') as f:
            entries = json.load(f)
    else:
        entries = []

    entries.append(new_entry)

    with open(PENDING_PATH, 'w') as f:
        json.dump(entries, f, indent=2)

def approve_entry(base_name, new_synonym, index_value):
    # Clean index values
    if isinstance(index_value, str):
        index_list = [i.strip() for i in index_value.split(',') if i.strip().isdigit()]
    else:
        index_list = index_value

    index_list = sorted(set(index_list), key=int)
    formatted_index = ", ".join(index_list)

    # Load existing thesaurus lines
    with open(THESAURUS_PATH, 'r') as f:
        lines = f.readlines()

    base_name_found = None
    updated_lines = []
    base_name_existed = False
    synonym_existed = False

    for line in lines:
        if ':' in line:
            existing_base, synonyms_str = line.strip().split(':', 1)
            synonyms = [s.strip() for s in synonyms_str.split(',')]
            all_names = [existing_base.strip()] + synonyms
            
            # Check if base name already exists
            if preprocess_query(base_name) in [preprocess_query(n) for n in all_names]:
                base_name_existed = True
            
            # Check if synonym already exists
            if preprocess_query(new_synonym) in [preprocess_query(n) for n in all_names]:
                synonym_existed = True
            
            # Check if either name already exists
            if preprocess_query(base_name) in [preprocess_query(n) for n in all_names] or \
               preprocess_query(new_synonym) in [preprocess_query(n) for n in all_names]:
                # Found the right base name line to update
                if preprocess_query(new_synonym) not in [preprocess_query(s) for s in synonyms]:
                    synonyms.append(new_synonym)
                updated_line = f"{existing_base}: {', '.join(sorted(set(synonyms), key=str.lower))}\n"
                updated_lines.append(updated_line)
                base_name_found = existing_base
            else:
                updated_lines.append(line)
        else:
            updated_lines.append(line)
    if not base_name_found:
        # Add new line if no existing synonym group matches
        updated_lines.append(f"{base_name}: {new_synonym}\n")
    # Write updated thesaurus
    with open(THESAURUS_PATH, 'w') as f:
        f.writelines(updated_lines)
    
    # Handle index file - check if synonym already exists
    with open(INDEX_PATH, 'r') as f:
        index_lines = f.readlines()
    
    updated_index_lines = []
    synonym_found_in_index = False
    
    for line in index_lines:
        if ':' in line:
            existing_synonym, existing_index_str = line.strip().split(':', 1)
            if preprocess_query(existing_synonym) == preprocess_query(new_synonym):
                # Found existing synonym in index - merge index values
                existing_index_list = [i.strip() for i in existing_index_str.split(',') if i.strip().isdigit()]
                merged_index = sorted(set(existing_index_list + index_list), key=int)
                merged_formatted = ", ".join(merged_index)
                updated_line = f"{existing_synonym}: {merged_formatted}\n"
                updated_index_lines.append(updated_line)
                synonym_found_in_index = True
            else:
                updated_index_lines.append(line)
        else:
            updated_index_lines.append(line)
    
    # If synonym not found in index, add new entry
    if not synonym_found_in_index:
        updated_index_lines.append(f"{new_synonym}: {formatted_index}\n")
    
    # Write updated index file
    with open(INDEX_PATH, 'w') as f:
        f.writelines(updated_index_lines)

    # Remove from pending.json
    if os.path.exists(PENDING_PATH):
        with open(PENDING_PATH, 'r') as f:
            entries = json.load(f)

        updated_entries = [
            entry for entry in entries if preprocess_query(entry["synonym"]) != preprocess_query(new_synonym)
        ]

        with open(PENDING_PATH, 'w') as f:
            json.dump(updated_entries, f, indent=2)
    
    # Return information about what already existed
    return {
        'base_name_existed': base_name_existed,
        'synonym_existed': synonym_existed,
        'both_existed': base_name_existed and synonym_existed
    }

def reject_entry(new_name):
    # Just remove from pending
    if os.path.exists(PENDING_PATH):
        with open(PENDING_PATH, 'r') as f:
            entries = json.load(f)

        updated_entries = [
            entry for entry in entries 
            if preprocess_query(entry["synonym"]) != preprocess_query(new_name)
        ]

        with open(PENDING_PATH, 'w') as f:
            json.dump(updated_entries, f, indent=2)
