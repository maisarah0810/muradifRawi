import os
import json
from boolean_retrieval import (
    load_index, load_thesaurus,
    get_expanded_terms, boolean_or_retrieval, load_hadith_documents
)
from preprocessing import preprocess_query


# Define correct absolute paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

INDEX_PATH = os.path.join(BASE_DIR, 'index', 'narratorindex.txt')
THESAURUS_PATH = os.path.join(BASE_DIR, 'index', 'thesaurusnarrator.txt')
PENDING_PATH = os.path.join(BASE_DIR, 'index', 'pending.json')
PENDING_INDEX_PATH = os.path.join(BASE_DIR, 'index', 'pending_index.json')
HADITH_FOLDER = os.path.join(BASE_DIR, 'docs', 'ShahihBukhari')

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

def add_new_index(name, indexes):
    """
    Add new indexes to an existing or new name.
    
    Args:
        name (str): The narrator name
        indexes (list): List of integer index numbers
    
    Returns:
        dict: Result information about what was added/updated
    """
    # Validate indexes are numeric
    try:
        index_list = [int(idx) for idx in indexes if str(idx).strip().isdigit()]
    except ValueError:
        raise ValueError("All indexes must be numeric values")
    
    if not index_list:
        raise ValueError("At least one valid numeric index is required")
    
    # Remove duplicates and sort
    index_list = sorted(set(index_list))
    
    # Check if name exists in index file (for information only)
    name_exists = False
    existing_indexes = []
    
    with open(INDEX_PATH, 'r') as f:
        index_lines = f.readlines()
    
    for line in index_lines:
        if ':' in line:
            existing_name, existing_index_str = line.strip().split(':', 1)
            if preprocess_query(existing_name) == preprocess_query(name):
                name_exists = True
                # Get existing indexes for information
                existing_indexes = [int(i.strip()) for i in existing_index_str.split(',') if i.strip().isdigit()]
                break
    
    # NOTE: We do NOT update the main index file immediately
    # All changes will be applied only after approval
    # This maintains consistency with the existing approval workflow
    
    # Save to pending_index.json for verification
    pending_entry = {
        "name": name,
        "indexes": index_list,
        "is_new_name": not name_exists,
        "new_indexes_only": [idx for idx in index_list if idx not in existing_indexes] if name_exists else index_list,
        "existing_indexes": existing_indexes
    }
    
    if os.path.exists(PENDING_INDEX_PATH):
        with open(PENDING_INDEX_PATH, 'r') as f:
            pending_entries = json.load(f)
    else:
        pending_entries = []
    
    pending_entries.append(pending_entry)
    
    with open(PENDING_INDEX_PATH, 'w') as f:
        json.dump(pending_entries, f, indent=2)
    
    # Return result information
    new_indexes_only = [idx for idx in index_list if idx not in existing_indexes] if name_exists else index_list
    
    return {
        'name_exists': name_exists,
        'new_indexes': new_indexes_only,
        'all_indexes': index_list,
        'existing_indexes': existing_indexes,
        'is_new_name': not name_exists,
        'duplicate_indexes': [idx for idx in index_list if idx in existing_indexes] if name_exists else []
    }

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

def approve_index_entry(name, indexes):
    """
    Approve an index entry by removing it from pending_index.json
    """
    if os.path.exists(PENDING_INDEX_PATH):
        with open(PENDING_INDEX_PATH, 'r') as f:
            entries = json.load(f)

        updated_entries = [
            entry for entry in entries 
            if not (preprocess_query(entry["name"]) == preprocess_query(name) and 
                   set(entry["indexes"]) == set(indexes))
        ]

        with open(PENDING_INDEX_PATH, 'w') as f:
            json.dump(updated_entries, f, indent=2)

def approve_index_entry_with_thesaurus(name, indexes, is_new_name=False):
    # First, remove from pending
    approve_index_entry(name, indexes)
    # Apply changes to the main index file
    with open(INDEX_PATH, 'r') as f:
        index_lines = f.readlines()
    updated_index_lines = []
    name_found = False
    
    for line in index_lines:
        if ':' in line:
            existing_name, existing_index_str = line.strip().split(':', 1)
            if preprocess_query(existing_name) == preprocess_query(name):
                name_found = True
                # Get existing indexes and merge with new ones
                existing_indexes = [int(i.strip()) for i in existing_index_str.split(',') if i.strip().isdigit()]
                all_indexes = sorted(set(existing_indexes + indexes))
                formatted_indexes = ", ".join(map(str, all_indexes))
                updated_line = f"{existing_name}: {formatted_indexes}\n"
                updated_index_lines.append(updated_line)
            else:
                updated_index_lines.append(line)
        else:
            updated_index_lines.append(line)
    
    # If name not found in index, add new entry
    if not name_found:
        formatted_indexes = ", ".join(map(str, indexes))
        updated_index_lines.append(f"{name}: {formatted_indexes}\n")
    
    # Write updated index file
    with open(INDEX_PATH, 'w') as f:
        f.writelines(updated_index_lines)
    
    # If it's a new name, add it to thesaurus
    if is_new_name:
        with open(THESAURUS_PATH, 'r') as f:
            thesaurus_lines = f.readlines()
        
        # Check if name already exists in thesaurus
        name_in_thesaurus = False
        for line in thesaurus_lines:
            if ':' in line:
                existing_base, synonyms_str = line.strip().split(':', 1)
                if preprocess_query(existing_base) == preprocess_query(name):
                    name_in_thesaurus = True
                    break
        
        # If name not in thesaurus, add new entry
        if not name_in_thesaurus:
            thesaurus_lines.append(f"{name}:\n")
            with open(THESAURUS_PATH, 'w') as f:
                f.writelines(thesaurus_lines)

def reject_index_entry(name, indexes):
    """
    Reject an index entry by removing it from pending_index.json
    """
    if os.path.exists(PENDING_INDEX_PATH):
        with open(PENDING_INDEX_PATH, 'r') as f:
            entries = json.load(f)

        updated_entries = [
            entry for entry in entries 
            if not (preprocess_query(entry["name"]) == preprocess_query(name) and 
                   set(entry["indexes"]) == set(indexes))
        ]

        with open(PENDING_INDEX_PATH, 'w') as f:
            json.dump(updated_entries, f, indent=2)

def load_pending_index_entries():
    """
    Load pending index entries from pending_index.json
    """
    if os.path.exists(PENDING_INDEX_PATH):
        with open(PENDING_INDEX_PATH, 'r') as f:
            return json.load(f)
    return []
