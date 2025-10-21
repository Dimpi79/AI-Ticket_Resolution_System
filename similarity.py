import os
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "data")
HIST_PATH = os.path.join(DATA_DIR, "processed_tickets.csv")

_vectorizer = None
_matrix = None
_history_df = None

def _build_index():
    global _vectorizer, _matrix, _history_df
    if not os.path.exists(HIST_PATH):
        return
    try:
        df = pd.read_csv(HIST_PATH)
        _history_df = df.reset_index(drop=True)
        if 'text_clean' in df.columns:
            texts = df['text_clean'].fillna('').astype(str)
        elif 'text' in df.columns:
            texts = df['text'].fillna('').astype(str)
        else:
            texts = _history_df.astype(str).apply(lambda r: " ".join(r.values), axis=1)
        _vectorizer = TfidfVectorizer(max_features=20000, ngram_range=(1,2))
        _matrix = _vectorizer.fit_transform(texts)
        print(f"Built TF-IDF index for {_matrix.shape[0]} historical tickets.")
    except Exception as e:
        _vectorizer = None
        _matrix = None
        _history_df = None
        print("Could not build TF-IDF index:", e)

_build_index()

def find_similar_tickets(text, top_k=3):
    global _vectorizer, _matrix, _history_df
    if _vectorizer is None or _matrix is None or _history_df is None:
        return []
    try:
        vec = _vectorizer.transform([text])
        sims = cosine_similarity(vec, _matrix)[0]
        idxs = sims.argsort()[::-1][:top_k]
        results = []
        for i in idxs:
            snippet = ""
            if 'text' in _history_df.columns:
                snippet = str(_history_df['text'].iloc[i])[:400]
            elif 'text_clean' in _history_df.columns:
                snippet = str(_history_df['text_clean'].iloc[i])[:400]
            else:
                snippet = " ".join(map(str, _history_df.iloc[i].values))[:400]
            results.append({
                'id': int(_history_df.index[i]),
                'similarity': float(sims[i]),
                'snippet': snippet
            })
        return results
    except Exception:
        return []