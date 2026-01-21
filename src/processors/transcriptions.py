import re

def clean_transcript_sentence(sentence: str) -> str:
    """Clean transcript sentence while preserving important content words."""
    fillers = [
        r'\bum\b', r'\buh\b', r'\byou know\b', 
        r'\bsort of\b', r'\bkind of\b', r'\bi mean\b'
    ]
    
    sentence_lower = sentence.lower()

    # Less aggressive filler removal - only remove the most obvious ones
    for filler in fillers:
        sentence_lower = re.sub(filler, '', sentence_lower, flags=re.IGNORECASE)
    
    # Normalize whitespace
    sentence_lower = re.sub(r'\s+', ' ', sentence_lower).strip()
    sentence_lower = re.sub(r'^[,\.\-\s]+', '', sentence_lower)
    
    return sentence_lower if sentence_lower else sentence


def process_transcripts(path):
    """
    Args:
        path: Path to transcript file or list of paths to transcript files.
              If multiple files are provided, they will be merged in order.
        
    Returns:
        List of cleaned transcript sentences
    """
    # Handle both single path and list of paths
    paths = [path] if isinstance(path, str) else path
    
    clean_lines = []
    tag = "Automatisch gegenereerde transcriptie"
    
    # Process each file and merge the results
    for file_path in paths:
        with open(file_path, "r", encoding='utf-8') as f:
            lines = f.readlines()

        for line in lines:
            if len(line) > 5 and tag not in line:
                cleaned = clean_transcript_sentence(line.strip())
                # Reduced minimum length from 10 to 5 to keep more content
                if cleaned and len(cleaned) > 5:
                    clean_lines.append(cleaned)

    return clean_lines