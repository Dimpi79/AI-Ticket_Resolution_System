import os
import re
from datasets import load_dataset
import pandas as pd

BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)
OUT_PATH = os.path.join(DATA_DIR, "processed_tickets.csv")

def simple_clean(s):
    s = (s or "").lower()
    s = re.sub(r'http\S+|\S+@\S+', ' ', s)
    s = re.sub(r'\b\d{6,}\b', ' ', s)
    s = re.sub(r'[^a-z0-9\s]', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def prepare():
    ds = load_dataset("Tobi-Bueck/customer-support-tickets", split="train")
    df = ds.to_pandas()
    possible_subjects = ['subject', 'title', 'title_text', 'ticket_subject']
    possible_bodies = ['text', 'body', 'description', 'ticket_body']
    subj = next((c for c in possible_subjects if c in df.columns), None)
    body = next((c for c in possible_bodies if c in df.columns), None)
    if subj and body:
        df['text'] = df[subj].fillna('') + ' ' + df[body].fillna('')
    elif body:
        df['text'] = df[body].fillna('')
    else:
        df['text'] = df.astype(str).apply(lambda r: " ".join(r.values), axis=1)
    df['text_clean'] = df['text'].apply(simple_clean)
    if 'category' in df.columns:
        df['Category'] = df['category']
    elif 'label' in df.columns:
        df['Category'] = df['label']
    else:
        df['Category'] = 'unlabeled'
    df.to_csv(OUT_PATH, index=False)
    print("Saved processed tickets to", OUT_PATH)

if __name__ == '__main__':
    prepare()