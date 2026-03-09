import json
import os
import threading
from flask import Flask, render_template, request, redirect, url_for, abort, make_response, session

app = Flask(__name__)

# ── Konfigurace ─────────────────────────────────────────────────────────────
ADMIN_TOKEN  = os.environ.get("ADMIN_TOKEN", "mojetajneheslo")
SECRET_KEY   = os.environ.get("SECRET_KEY", "changeme-secret-key-123")
COOKIE_NAME  = "has_voted"
COOKIE_DAYS  = 30
DATA_DIR     = os.path.join(os.path.dirname(__file__), "data")
VOTES_FILE   = os.path.join(DATA_DIR, "votes.json")

app.secret_key = SECRET_KEY

# ── Překlady ────────────────────────────────────────────────────────────────
TRANSLATIONS = {
    "cs": {
        "lang_code":        "cs",
        "lang_switch_label":"English",
        "lang_switch_code": "en",
        "eyebrow_vote":     "🪐 Anketa",
        "eyebrow_results":  "📊 Výsledky",
        "show_results":     "Zobrazit výsledky bez hlasování →",
        "back_to_vote":     "← Zpět na hlasování",
        "submit":           "Hlasovat →",
        "total_votes":      "Celkem hlasů:",
        "voted_banner":     "✅ Tvůj hlas byl zaznamenán",
        "voted_for":        "hlasoval/a jsi pro:",
        "my_vote":          "tvůj hlas",
        "info_note":        "ℹ️ Každý prohlížeč může hlasovat pouze jednou. Po odeslání nelze hlas změnit.",
        "reset_label":      "🔐 Reset ankety (pouze admin)",
        "reset_placeholder":"Admin token",
        "reset_btn":        "Vynulovat hlasy",
        "bug_title":        "🐛 Zpětná vazba a hlášení chyb",
        "bug_desc":         "Objevili jste v aplikaci technický problém nebo chybu v textu? Budeme rádi za upozornění. Technické nedostatky doporučujeme hlásit přímo do GitHub repozitáře.",
        "bug_link":         "Vytvořit issue na GitHubu →",
        "invalid_choice":   "Neplatná volba.",
        "question":         "Jaká je největší planeta Sluneční soustavy?",
        "options": {
            "jupiter": "Jupiter",
            "saturn":  "Saturn",
            "mars":    "Mars",
        },
    },
    "en": {
        "lang_code":        "en",
        "lang_switch_label":"Čeština",
        "lang_switch_code": "cs",
        "eyebrow_vote":     "🪐 Survey",
        "eyebrow_results":  "📊 Results",
        "show_results":     "View results without voting →",
        "back_to_vote":     "← Back to survey",
        "submit":           "Vote →",
        "total_votes":      "Total votes:",
        "voted_banner":     "✅ Your vote has been recorded",
        "voted_for":        "you voted for:",
        "my_vote":          "your vote",
        "info_note":        "ℹ️ Each browser can only vote once. Your vote cannot be changed after submission.",
        "reset_label":      "🔐 Reset survey (admin only)",
        "reset_placeholder":"Admin token",
        "reset_btn":        "Reset all votes",
        "bug_title":        "🐛 Feedback & Bug Reports",
        "bug_desc":         "Did you find a technical issue or a mistake in the text? We appreciate you letting us know. Please report technical problems directly to our GitHub repository.",
        "bug_link":         "Create an issue on GitHub →",
        "invalid_choice":   "Invalid choice.",
        "question":         "What is the largest planet in the Solar System?",
        "options": {
            "jupiter": "Jupiter",
            "saturn":  "Saturn",
            "mars":    "Mars",
        },
    },
}

def get_lang():
    """Get language from cookie, default to Czech."""
    return request.cookies.get("lang", "cs")

def get_t():
    """Return translation dict for current language."""
    return TRANSLATIONS.get(get_lang(), TRANSLATIONS["cs"])

# ── Thread-safe I/O ─────────────────────────────────────────────────────────
_lock = threading.Lock()

def _default_votes():
    return {key: 0 for key in TRANSLATIONS["cs"]["options"]}

def load_votes():
    with _lock:
        if not os.path.exists(VOTES_FILE):
            return _default_votes()
        with open(VOTES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

def save_votes(data):
    with _lock:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(VOTES_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

if not os.path.exists(VOTES_FILE):
    save_votes(_default_votes())

# ── Pomocná funkce ──────────────────────────────────────────────────────────
def build_stats(t):
    votes = load_votes()
    total = sum(votes.values())
    stats = []
    for key, label in t["options"].items():
        count = votes.get(key, 0)
        pct   = round(count / total * 100, 1) if total > 0 else 0
        stats.append({"key": key, "label": label, "count": count, "pct": pct})
    return stats, total

# ── Security headers ────────────────────────────────────────────────────────
@app.after_request
def set_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    return response

# ── Jazyk ────────────────────────────────────────────────────────────────────
@app.route("/lang/<code>")
def set_lang(code):
    if code not in TRANSLATIONS:
        code = "cs"
    next_url = request.args.get("next", url_for("index"))
    resp = make_response(redirect(next_url))
    resp.set_cookie("lang", code, max_age=365 * 24 * 3600, samesite="Lax")
    return resp

# ── Veřejné routy ───────────────────────────────────────────────────────────
@app.route("/")
def index():
    if request.cookies.get(COOKIE_NAME):
        return redirect(url_for("results"))
    t = get_t()
    return render_template("vote.html", t=t)

@app.route("/vote", methods=["POST"])
def vote():
    if request.cookies.get(COOKIE_NAME):
        return redirect(url_for("results"))
    t = get_t()
    choice = request.form.get("choice")
    if choice not in t["options"]:
        return t["invalid_choice"], 400
    votes = load_votes()
    votes[choice] = votes.get(choice, 0) + 1
    save_votes(votes)
    resp = make_response(redirect(url_for("results")))
    resp.set_cookie(
        COOKIE_NAME,
        value=choice,
        max_age=COOKIE_DAYS * 24 * 3600,
        httponly=True,
        samesite="Lax",
    )
    return resp

@app.route("/results")
def results():
    t = get_t()
    stats, total  = build_stats(t)
    already_voted = request.cookies.get(COOKIE_NAME)
    return render_template(
        "results.html",
        t=t,
        stats=stats,
        total=total,
        already_voted=already_voted,
    )

@app.route("/reset", methods=["POST"])
def reset():
    token = request.form.get("token", "")
    if token != ADMIN_TOKEN:
        abort(403)
    save_votes(_default_votes())
    resp = make_response(redirect(url_for("results")))
    resp.delete_cookie(COOKIE_NAME)
    return resp

# ── Spuštění ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True)
