import os
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "data")

HIST_PATH = os.path.join(DATA_DIR, "processed_tickets.csv")
KB_PATH   = os.path.join(DATA_DIR, "knowledge_base.csv")

_vectorizer = None
_matrix = None
_history_df = None

def _build_index(limit_rows: int = 15000):
    """
    Lazily build TF-IDF index on first use.
    limit_rows: cap rows for speed; increase later if you want.
    """
    global _vectorizer, _matrix, _history_df
    if not os.path.exists(HIST_PATH):
        print("No historical tickets file found:", HIST_PATH)
        return

    try:
        # Limit rows for faster startup; tune this number to your machine
        df = pd.read_csv(HIST_PATH, nrows=limit_rows)
        _history_df = df.reset_index(drop=True)

        if 'text_clean' in df.columns:
            texts = df['text_clean'].fillna('').astype(str)
        elif 'text' in df.columns:
            texts = df['text'].fillna('').astype(str)
        else:
            texts = _history_df.astype(str).apply(lambda r: " ".join(r.values), axis=1)

        # Faster, lighter TF-IDF config for large corpora
        _vectorizer = TfidfVectorizer(
            max_features=20000,
            ngram_range=(1, 2),
            stop_words='english',
            min_df=2,          # drop singletons
            max_df=0.95        # drop super-common terms
        )
        _matrix = _vectorizer.fit_transform(texts)
        print(f"Built TF-IDF index for {_matrix.shape[0]} historical tickets (limited).")
    except KeyboardInterrupt:
        # If you stop it mid-way, leave things unset
        _vectorizer = None
        _matrix = None
        _history_df = None
        print("TF-IDF build interrupted; index not ready.")
    except Exception as e:
        _vectorizer = None
        _matrix = None
        _history_df = None
        print("Could not build TF-IDF index:", e)


# ------------------ FIND SIMILAR TICKETS ------------------ #

def find_similar_tickets(text, top_k=3):
    global _vectorizer, _matrix, _history_df

    # Lazy build if not ready
    if _vectorizer is None or _matrix is None or _history_df is None:
        _build_index(limit_rows=15000)  # tweak this number if needed

    if _vectorizer is None or _matrix is None or _history_df is None:
        return []

    try:
        vec = _vectorizer.transform([text])
        sims = cosine_similarity(vec, _matrix)[0]
        idxs = sims.argsort()[::-1][:top_k]
        results = []
        for i in idxs:
            if 'text' in _history_df.columns:
                snippet = str(_history_df['text'].iloc[i])[:400]
            elif 'text_clean' in _history_df.columns:
                snippet = str(_history_df['text_clean'].iloc[i])[:400]
            else:
                snippet = " ".join(map(str, _history_df.iloc[i].values))[:400]
            results.append({
                'id': int(i),
                'similarity': float(sims[i]),
                'snippet': snippet
            })
        return results
    except Exception:
        return []


# ------------------ RECOMMEND KNOWLEDGE BASE ARTICLES ------------------ #

def recommend_articles(text, top_k=3):
    if not os.path.exists(KB_PATH):
        return []

    df = pd.read_csv(KB_PATH)
    if df.empty:
        return []

    kb_texts = df['content'].fillna('').astype(str)
    kb_vectorizer = TfidfVectorizer(max_features=20000, ngram_range=(1, 2))
    kb_matrix = kb_vectorizer.fit_transform(kb_texts)

    vec = kb_vectorizer.transform([text])
    sims = cosine_similarity(vec, kb_matrix)[0]
    idxs = sims.argsort()[::-1][:top_k]

    results = []
    for i in idxs:
        results.append({
            "article_id": df['article_id'].iloc[i],
            "title": df['title'].iloc[i],
            "link": df['link'].iloc[i],
            "similarity": float(sims[i]),
            "summary": df['content'].iloc[i][:200]
        })
    return results
