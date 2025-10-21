import os
import re
import json
from datetime import datetime

# OpenAI client (must be installed in venv)
try:
    import openai  # type: ignore
    OPENAI_AVAILABLE = True
except Exception:
    OPENAI_AVAILABLE = False

BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)
LLM_LOG_PATH = os.path.join(DATA_DIR, "llm_logs.jsonl")

# keyword fallback maps
KEYWORDS_MAP = {
    'authentication': ['login', 'password', 'sign in', 'sign up', 'account', 'access'],
    'payment': ['payment', 'transaction', 'billing', 'charge', 'refund', 'card'],
    'technical': ['error', 'bug', 'crash', 'issue', 'broken', 'not working'],
    'refund': ['refund', 'cancel', 'return', 'money back'],
    'feature': ['feature', 'request', 'enhancement', 'improvement', 'suggestion'],
    'general': []
}
TAGS_MAP = {
    'urgent': ['urgent', 'asap', 'immediately', 'priority'],
    'billing': ['invoice', 'billing', 'charge', 'refund', 'payment'],
    'login': ['login', 'password', 'sign in', 'access denied', 'authentication'],
    'bug': ['bug', 'error', 'crash', 'stack trace', 'exception'],
    'feature-request': ['feature', 'request', 'enhancement', 'improvement', 'add'],
    'documentation': ['docs', 'documentation', 'how to', 'guide', 'manual'],
    'security': ['security', 'vulnerability', 'breach', 'attack', 'unauthorized']
}
SOLUTIONS_MAP = {
    'authentication': ('Password reset: use "Forgot Password" on login page and follow email link.', 0.92),
    'payment': ('Payment troubleshooting: check card details and retry or contact bank.', 0.88),
    'technical': ('Try clearing cache, update app, disable extensions, collect logs.', 0.85),
    'refund': ('Submit refund request with order number; allow 5-7 days', 0.87),
    'feature': ('Record feature request with details and use case for product team review.', 0.75),
    'general': ('Support will review this ticket.', 0.7)
}

def _extract_json(text):
    try:
        m = re.search(r'\{.*\}', text, flags=re.DOTALL)
        if not m:
            return None
        return json.loads(m.group(0))
    except Exception:
        return None

def _rule_based(text):
    txt = (text or "").lower()
    best = ('general', 0)
    for cat, kws in KEYWORDS_MAP.items():
        matches = sum(1 for kw in kws if kw in txt)
        if matches > best[1]:
            best = (cat, matches)
    category = best[0]
    tags = []
    for tag, kws in TAGS_MAP.items():
        for kw in kws:
            if kw in txt:
                tags.append(tag)
                break
    sol, conf = SOLUTIONS_MAP.get(category, SOLUTIONS_MAP['general'])
    suggested_priority = 'High' if 'urgent' in tags else 'Medium'
    return {
        'category': category,
        'tags': tags,
        'suggested_priority': suggested_priority,
        'solution': sol,
        'confidence': conf
    }

def _log_llm(input_text, parsed_obj, raw_content, model_name):
    try:
        entry = {
            'timestamp': datetime.now().isoformat(),
            'model': model_name,
            'input_snippet': (input_text or "")[:1000],
            'parsed': parsed_obj,
            'raw_response': (raw_content or "")[:4000]
        }
        with open(LLM_LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    except Exception:
        pass

def classify_text(text, model_name="gpt-3.5-turbo"):
    """
    Returns dict: category, tags, suggested_priority, solution, confidence.
    Uses OpenAI if OPENAI_API_KEY env var present and openai installed; otherwise falls back to rule-based.
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if OPENAI_AVAILABLE and api_key:
        openai.api_key = api_key
        system_prompt = (
            "You are an assistant that MUST return only a single JSON object (no extra text) "
            "with these keys: category (string), tags (array of strings), "
            "suggested_priority (High/Medium/Low), solution (short string), confidence (0.0-1.0). "
            "If uncertain set confidence < 0.5. Use concise values and standard category names. "
            "Do NOT include explanations or extra text."
        )
        user_prompt = f"Ticket text:\n\n'''{text}'''"
        try:
            resp = openai.ChatCompletion.create(
                model=model_name,
                messages=[
                    {"role":"system", "content": system_prompt},
                    {"role":"user", "content": user_prompt}
                ],
                temperature=0.0,
                max_tokens=400
            )
            content = resp['choices'][0]['message']['content']
            parsed = _extract_json(content)
            if parsed and isinstance(parsed, dict):
                parsed.setdefault('category', 'general')
                parsed.setdefault('tags', [])
                parsed.setdefault('suggested_priority', 'Medium')
                parsed.setdefault('solution', '')
                parsed.setdefault('confidence', 0.0)
                try:
                    parsed['confidence'] = float(parsed['confidence'])
                except Exception:
                    parsed['confidence'] = 0.0
                _log_llm(text, parsed, content, model_name)
                return parsed
            parsed_fb = _rule_based(text)
            _log_llm(text, parsed_fb, content, model_name)
            return parsed_fb
        except Exception as e:
            _log_llm(text, {'error': str(e)}, None, model_name)
            return _rule_based(text)
    else:
        return _rule_based(text)