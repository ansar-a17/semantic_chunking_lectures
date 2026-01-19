from sentence_transformers import SentenceTransformer

model = SentenceTransformer('all-MiniLM-L6-v2')

def embed_single(line: str):
    """
    Generate embedding for a single text string.
    
    Args:
        line: Text to embed
        
    Returns:
        Embedding array
    """
    embedding = model.encode(line)
    return embedding
