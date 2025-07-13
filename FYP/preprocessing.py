def preprocess_query(query):
    """
    Preprocess query by converting to lowercase and removing spaces.
    Also handles common variations in Arabic/Islamic names.
    """
    # Convert to lowercase and remove spaces
    processed = ''.join(query.lower().split())
    
    # Handle common variations in Arabic names
    # Replace common variations that might cause mismatches
    variations = {
        'masud': "mas'ud",  # Common variation without apostrophe
        'ibn': 'ibnu',       # Common prefix variation
        'bin': 'bin',        # Keep as is
    }
    
    # Apply variations if they exist in the processed query
    for variation, standard in variations.items():
        if variation in processed:
            processed = processed.replace(variation, standard)
    
    return processed