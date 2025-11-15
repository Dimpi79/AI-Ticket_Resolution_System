import os
from datetime import datetime
from functools import wraps
from time import time
from flask import Flask, request, jsonify, render_template, send_file, Response
from flask_cors import CORS
from similarity import find_similar_tickets, recommend_articles
import pandas as pd
import PyPDF2
import json
import html

from llm_classifier import classify_text
from similarity import find_similar_tickets

app = Flask(__name__, template_folder='templates', static_folder='static')
# or simply: app = Flask(__name__)

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

def generate_kb_article_from_text(text):
    prompt = f"""
    You are a support knowledge-base writer.
    Write a clear support article to solve this issue:

    Issue:
    {text}

    Respond in JSON with fields:
    - title
    - content (full detailed solution)
    """

    try:
        result = classify_text(prompt)  # using your existing LLM wrapper
        return {
            "title": result.get("title", "Support Article"),
            "content": result.get("content", "")
        }
    except:
        return None

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

    # ✅ Always recommend articles (must not be inside if/else)
    articles = recommend_articles(combined_text, top_k=3)

    # ✅ Content Gap Logging
    GAP_LOG = os.path.join(DATA_DIR, "content_gaps.csv")
    if len(articles) == 0:
        gap_entry = pd.DataFrame([{
            "timestamp": datetime.now().isoformat(),
            "ticket_excerpt": combined_text[:200]
        }])
        if not os.path.exists(GAP_LOG):
            gap_entry.to_csv(GAP_LOG, index=False)
        else:
            gap_entry.to_csv(GAP_LOG, mode='a', header=False, index=False)

    # ✅ Final structured response
    response = {
        'uploaded_ticket': combined_text[:1000],
        'analyzed_at': datetime.now().isoformat(),
        'llm_result': llm_result,
        'similar_tickets': similar,
        'recommended_articles': articles
    }

    # ✅ Add convenience top-level fields
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

# Admin Home (Dashboard)
# -------------------------
@app.route('/admin')
@requires_auth
def admin_ui():
    return render_template('admin.html')

@app.route("/admin/gaps")
@requires_auth
def view_gaps():
    GAP_LOG = os.path.join(DATA_DIR, "content_gaps.csv")
    if not os.path.exists(GAP_LOG):
        return "<h3>No content gaps recorded yet.</h3>"

    import pandas as pd
    df = pd.read_csv(GAP_LOG)

    # Add Generate KB button column
    df['action'] = df['ticket_excerpt'].apply(
    lambda t: f"<button onclick=\"generateKB('{html.escape(str(t))}')\">Generate KB</button>"
     )
    
    # Convert table to HTML and allow buttons to render
    table_html = df.to_html(classes="table table-striped", index=False, escape=False)

    return f"""
    <html>
    <head>
        <title>Content Gaps</title>
        <style>
            body {{ font-family: Arial, sans-serif; padding: 20px; }}
            .table {{ border-collapse: collapse; width: 100%; }}
            .table th, .table td {{ border: 1px solid #ddd; padding: 8px; }}
            .table th {{ background-color: #f2f2f2; }}
        </style>
    </head>
    <body>
        <h2>📌 Content Gaps (Tickets With No Matching KB Articles)</h2>
        {table_html}
        <br><br>
        <a href="/admin">⬅ Back to Admin Dashboard</a>

        <!-- ✅ JS to trigger KB generation -->
        <script>
        function generateKB(text) {{
          fetch('/admin/generate_kb', {{
            method: 'POST',
            headers: {{'Content-Type':'application/json'}},
            body: JSON.stringify({{ticket_excerpt: text}})
          }})
          .then(res => res.json())
          .then(data => {{
            alert(data.message || data.error);
            location.reload();
          }});
        }}
        </script>

    </body>
    </html>
    """



@app.route("/admin/generate_kb", methods=['POST'])
@requires_auth
def generate_kb():
    GAP_LOG = os.path.join(DATA_DIR, "content_gaps.csv")
    KB_PATH = os.path.join(DATA_DIR, "knowledge_base.csv")

    ticket_text = request.json.get("ticket_excerpt", "").strip()
    if not ticket_text:
        return jsonify({"error": "Missing ticket text"}), 400

    article = generate_kb_article_from_text(ticket_text)
    if not article:
        return jsonify({"error": "LLM failed"}), 500

    # Append to KB
    df_row = pd.DataFrame([{
        "article_id": f"KB{int(time())}",  # unique ID
        "title": article["title"],
        "content": article["content"],
        "link": "#"
    }])

    if not os.path.exists(KB_PATH):
        df_row.to_csv(KB_PATH, index=False)
    else:
        df_row.to_csv(KB_PATH, mode="a", header=False, index=False)

    return jsonify({"message": "Article created successfully"}), 200


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
        # Replace NaN with None so JSON serialization produces valid JSON (no NaN tokens)
        df_fb = df_fb.where(pd.notnull(df_fb), None)
        records = df_fb.tail(200).to_dict(orient='records')
        return jsonify(records)
    except Exception:
        return jsonify([])



    # Add to your existing Flask app

@app.route('/admin/api/feedback')
@requires_auth
def api_feedback():
    """API endpoint for feedback data"""
    fb_path = os.path.join(DATA_DIR, 'feedback.csv')
    if not os.path.exists(fb_path):
        return jsonify([])
    try:
        df_fb = pd.read_csv(fb_path)
        df_fb = df_fb.where(pd.notnull(df_fb), None)
        records = df_fb.to_dict(orient='records')
        return jsonify(records)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/admin/api/gaps')
@requires_auth
def api_gaps():
    """API endpoint for content gaps data"""
    GAP_LOG = os.path.join(DATA_DIR, "content_gaps.csv")
    if not os.path.exists(GAP_LOG):
        return jsonify([])
    try:
        df = pd.read_csv(GAP_LOG)
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        df = df.where(pd.notnull(df), None)
        records = df.to_dict(orient='records')
        return jsonify(records)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/admin/api/knowledge_base')
@requires_auth
def api_knowledge_base():
    """API endpoint for knowledge base data"""
    KB_PATH = os.path.join(DATA_DIR, "knowledge_base.csv")
    if not os.path.exists(KB_PATH):
        return jsonify([])
    try:
        df = pd.read_csv(KB_PATH)
        df = df.where(pd.notnull(df), None)
        records = df.to_dict(orient='records')
        return jsonify(records)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/admin/api/stats')
@requires_auth
def api_stats():
    """API endpoint for dashboard statistics"""
    try:
        # Load all data
        fb_path = os.path.join(DATA_DIR, 'feedback.csv')
        gaps_path = os.path.join(DATA_DIR, 'content_gaps.csv')
        kb_path = os.path.join(DATA_DIR, 'knowledge_base.csv')
        
        stats = {
            'total_tickets': 0,
            'content_gaps': 0,
            'kb_articles': 0,
            'high_priority_tickets': 0
        }
        
        if os.path.exists(fb_path):
            df_fb = pd.read_csv(fb_path)
            stats['total_tickets'] = len(df_fb)
            if 'final_priority' in df_fb.columns:
                stats['high_priority_tickets'] = len(df_fb[df_fb['final_priority'] == 'High'])
        
        if os.path.exists(gaps_path):
            df_gaps = pd.read_csv(gaps_path)
            stats['content_gaps'] = len(df_gaps)
        
        if os.path.exists(kb_path):
            df_kb = pd.read_csv(kb_path)
            stats['kb_articles'] = len(df_kb)
        
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
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