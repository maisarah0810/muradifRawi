import os
import re
from preprocessing import preprocess_query

def load_index(filepath):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    full_path = os.path.join(base_dir, filepath)
    print("Loading file from:", full_path)

    with open(full_path, 'r', encoding='utf-8') as f:
        index = {}
        for line in f:
            key, *values = line.strip().split(':')
            # Strip spaces from each doc ID
            index[key] = [v.strip() for v in values[0].split(',')] if values else []
        return index


def load_thesaurus(filepath):
    synonym_map = {}
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            if ':' in line:
                key, values = line.strip().split(':', 1)
                key = preprocess_query(key)
                synonyms = [preprocess_query(s) for s in values.split(',')]
                all_terms = set([key] + synonyms)
                # map each term in the group to the full group
                for term in all_terms:
                    synonym_map[term] = all_terms
    return synonym_map


def get_expanded_terms(term, thesaurus):
    processed_term = preprocess_query(term)
    return thesaurus.get(processed_term, {processed_term})


def boolean_or_retrieval(expanded_terms, index):
    result_docs = set()
    for term in expanded_terms:
        if term in index:
            result_docs.update(index[term])
    return sorted(result_docs)

def load_hadith_documents(doc_ids, hadith_folder, synonyms_raw=None):
    documents = []
    for doc_id in doc_ids:
        filename = f"ShahihBukhari{doc_id}.txt"
        file_path = os.path.join(hadith_folder, filename)
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # Highlight names if provided
                if synonyms_raw:
                    content = highlight_names_in_text(content, synonyms_raw)
                documents.append({'filename': filename, 'content': content})
    return documents

def get_related_documents(terms, index, hadith_folder, highlight_terms=None):
    if highlight_terms is None:
        highlight_terms = terms
    doc_ids = boolean_or_retrieval(terms, index)
    return load_hadith_documents(doc_ids, hadith_folder, highlight_terms)

def highlight_names_in_text(text, synonyms_raw):
    # Escape special regex characters (like apostrophes) and sort longest names first
    patterns = sorted(synonyms_raw, key=len, reverse=True)
    for name in patterns:
        pattern = re.escape(name)
        # Match whole words only
        text = re.sub(rf'\b({pattern})\b', r'<mark>\1</mark>', text, flags=re.IGNORECASE)
    return text
