from typing import List, Dict
from src.core.embedding import embed_single

def build_transcripts(lines: List):
    """
    Build transcript embeddings dictionary.
    
    Args:
        lines: List of transcript sentences
        
    Returns:
        Dictionary mapping sentences to their embeddings
    """
    transcripts_embedded = {}
    print(f"Generating embeddings for {len(lines)} sentences...")
    
    for i, line in enumerate(lines, 1):
        transcripts_embedded[line] = embed_single(line)
        if i % 10 == 0:
            print(f"  Processed {i}/{len(lines)} sentences")
    
    print(f"Generated {len(transcripts_embedded)} embeddings")
    return transcripts_embedded