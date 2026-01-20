import re

def clean_transcript_sentence(sentence: str) -> str:
    fillers = [
        r'\bum\b', r'\buh\b', r'\blike\b', r'\byou know\b', 
        r'\bsort of\b', r'\bkind of\b', r'\bi mean\b', 
        r'\bwell\b', r'\byeah\b', r'\bokay\b', r'\balright\b'
    ]
    
    sentence_lower = sentence.lower()

    for filler in fillers:
        sentence_lower = re.sub(filler, '', sentence_lower, flags=re.IGNORECASE)
    sentence_lower = re.sub(r'\s+', ' ', sentence_lower).strip()
    sentence_lower = re.sub(r'^[,\.\-\s]+', '', sentence_lower)
    
    return sentence_lower if sentence_lower else sentence


def process_transcripts(path):
    """
    Args:
        path: Path to transcript file
        
    Returns:
        List of cleaned transcript sentences
    """
    with open(path, "r", encoding='utf-8') as f:
        lines = f.readlines()

    clean_lines = []
    tag = "Automatisch gegenereerde transcriptie"

    for line in lines:
        if len(line) > 5 and tag not in line:
            cleaned = clean_transcript_sentence(line.strip())
            if cleaned and len(cleaned) > 10:  # Skip very short fragments
                clean_lines.append(cleaned)

    return clean_lines