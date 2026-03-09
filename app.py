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

# ── Otázka a možnosti ───────────────────────────────────────────────────────
QUESTION = "Jaká je největší planeta Sluneční soustavy?"

OPTIONS = {
    "jupiter": "Jupiter",
    "saturn":  "Saturn",
    "mars":    "Mars",
}

# ── Thread-safe I/O ─────────────────────────────────────────────────────────
_lock = threading.Lock()

def _default_votes():
    return {key: 0 for key in OPTIONS}

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
def build_stats():
    votes = load_votes()
    total = sum(votes.values())
    stats = []
    for key, label in OPTIONS.items():
        count = votes.get(key, 0)
        pct   = round(count / total * 100, 1) if total > 0 else 0
        stats.append({"key": key, "label": label, "count": count, "pct": pct})
    return stats, total

# ── Security headers ────────────────────────────────────────────────────────
@app.after_request
def set_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response

# ── Veřejné routy ───────────────────────────────────────────────────────────
@app.route("/")
def index():
    if request.cookies.get(COOKIE_NAME):
        return redirect(url_for("results"))
    return render_template("vote.html", question=QUESTION, options=OPTIONS)

@app.route("/vote", methods=["POST"])
def vote():
    if request.cookies.get(COOKIE_NAME):
        return redirect(url_for("results"))
    choice = request.form.get("choice")
    if choice not in OPTIONS:
        return "Neplatná volba.", 400
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
    stats, total  = build_stats()
    already_voted = request.cookies.get(COOKIE_NAME)
    return render_template(
        "results.html",
        question=QUESTION,
        stats=stats,
        total=total,
        already_voted=already_voted,
    )

# ── Admin routy (oddělené od veřejných) ────────────────────────────────────
@app.route("/admin", methods=["GET", "POST"])
def admin():
    error = None
    success = None

    if request.method == "POST":
        token = request.form.get("token", "")
        if token == ADMIN_TOKEN:
            session["admin"] = True
            return redirect(url_for("admin_panel"))
        else:
            error = "Nesprávný token. Přístup odepřen."

    return render_template("admin_login.html", error=error)

@app.route("/admin/panel", methods=["GET", "POST"])
def admin_panel():
    if not session.get("admin"):
        return redirect(url_for("admin"))

    success = None
    if request.method == "POST":
        save_votes(_default_votes())
        success = "Hlasy byly úspěšně vynulovány."

    stats, total = build_stats()
    return render_template(
        "admin_panel.html",
        question=QUESTION,
        stats=stats,
        total=total,
        success=success,
    )

@app.route("/admin/logout")
def admin_logout():
    session.pop("admin", None)
    return redirect(url_for("index"))

# ── Spuštění ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True)
