import os
from datetime import datetime
from functools import wraps
from flask import Flask, request, jsonify, render_template, send_file, Response
from flask_cors import CORS
import pandas as pd
import PyPDF2
import json

from llm_classifier import classify_text
from similarity import find_similar_tickets

app = Flask(__name__, template_folder='.', static_folder='static')
CORS(app)

BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)
FEEDBACK_CSV = os.path.join(DATA_DIR, "feedback.csv")

ALLOWED_EXTENSIONS = {'txt', 'csv', 'pdf'}

# Admin credentials (override via environment)
ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "changeme")

def _check_auth(username, password):
    return username == ADMIN_USER and password == ADMIN_PASS

def _authenticate():
    return Response('Authentication required', 401, {'WWW-Authenticate': 'Basic realm="Login Required"'})

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not _check_auth(auth.username, auth.password):
            return _authenticate()
        return f(*args, **kwargs)
    return decorated

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text(file):
    ext = file.filename.rsplit('.', 1)[1].lower()
    file.stream.seek(0)
    if ext == 'txt':
        return file.read().decode('utf-8', errors='ignore')
    elif ext == 'csv':
        try:
            df_local = pd.read_csv(file)
            return " ".join(df_local.astype(str).values.flatten())
        except Exception:
            file.stream.seek(0)
            return file.read().decode('utf-8', errors='ignore')
    elif ext == 'pdf':
        try:
            reader = PyPDF2.PdfReader(file)
            texts = []
            for page in reader.pages:
                t = page.extract_text()
                if t:
                    texts.append(t)
            return " ".join(texts)
        except Exception:
            file.stream.seek(0)
            return file.read().decode('utf-8', errors='ignore')
    return None

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    if not allowed_file(file.filename):
        return jsonify({'error': 'Unsupported file type'}), 400

    text = extract_text(file)
    if not text or not text.strip():
        return jsonify({'error': 'Could not read text from file'}), 400

    combined_text = text.strip()
    llm_result = {}
    try:
        llm_result = classify_text(combined_text)
    except Exception as e:
        llm_result = {'error': f'LLM error: {str(e)}'}

    # add similarity if available and not already provided by llm_result
    similar = []
    if not isinstance(llm_result, dict) or 'similar_tickets' not in llm_result:
        similar = find_similar_tickets(combined_text, top_k=3)
    else:
        similar = llm_result.get('similar_tickets', [])

    response = {
        'uploaded_ticket': combined_text[:1000],
        'analyzed_at': datetime.now().isoformat(),
        'llm_result': llm_result,
        'similar_tickets': similar
    }
    # convenience top-level fields
    if isinstance(llm_result, dict):
        for k in ['category', 'tags', 'suggested_priority', 'solution', 'confidence']:
            if k in llm_result:
                response[k] = llm_result[k]
    return jsonify(response)

@app.route('/feedback', methods=['POST'])
def receive_feedback():
    payload = request.get_json()
    if not payload:
        return jsonify({'error': 'Invalid JSON'}), 400

    row = {
        'timestamp': datetime.now().isoformat(),
        'original_text': payload.get('original_text',''),
        'final_category': payload.get('final_category',''),
        'final_tags': ",".join(payload.get('final_tags',[])),
        'final_priority': payload.get('final_priority',''),
        'agent_note': payload.get('agent_note','')
    }
    df_row = pd.DataFrame([row])
    if not os.path.exists(FEEDBACK_CSV):
        df_row.to_csv(FEEDBACK_CSV, index=False)
    else:
        df_row.to_csv(FEEDBACK_CSV, index=False, header=False, mode='a')
    return jsonify({'status':'ok'})

# -------------------------
# Admin endpoints (protected)
# -------------------------
@app.route('/admin')
@requires_auth
def admin_ui():
    return render_template('admin.html')

@app.route('/admin/logs')
@requires_auth
def admin_logs():
    logs_path = os.path.join(DATA_DIR, 'llm_logs.jsonl')
    if not os.path.exists(logs_path):
        return jsonify([])
    out = []
    with open(logs_path, 'r', encoding='utf-8') as fh:
        for line in fh:
            try:
                out.append(json.loads(line))
            except Exception:
                continue
    return jsonify(out[-200:][::-1])

@app.route('/admin/feedback')
@requires_auth
def admin_feedback():
    fb_path = os.path.join(DATA_DIR, 'feedback.csv')
    if not os.path.exists(fb_path):
        return jsonify([])
    try:
        df_fb = pd.read_csv(fb_path)
        return jsonify(df_fb.tail(200).to_dict(orient='records'))
    except Exception:
        return jsonify([])

@app.route('/admin/download/<path:fname>')
@requires_auth
def admin_download(fname):
    safe = fname.replace('..', '')
    path = os.path.join(DATA_DIR, safe)
    if os.path.exists(path):
        return send_file(path, as_attachment=True)
    return jsonify({'error': 'not found'}), 404

if __name__ == '__main__':
    print("🚀 Server running on http://localhost:5000")
    app.run(debug=True)