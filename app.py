import json
import os
import threading
from flask import Flask, render_template, request, redirect, url_for, abort, make_response

app = Flask(__name__)

# ── Konfigurace ─────────────────────────────────────────────────────────────
ADMIN_TOKEN  = "mojetajneheslo"
COOKIE_NAME  = "has_voted"
COOKIE_DAYS  = 30          # jak dlouho platí cookie (dní)
DATA_DIR     = os.path.join(os.path.dirname(__file__), "data")
VOTES_FILE   = os.path.join(DATA_DIR, "votes.json")

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

# Vytvoř soubor při startu, pokud neexistuje
if not os.path.exists(VOTES_FILE):
    save_votes(_default_votes())

# ── Pomocná funkce: sestavení výsledků ─────────────────────────────────────
def build_stats():
    votes = load_votes()
    total = sum(votes.values())
    stats = []
    for key, label in OPTIONS.items():
        count = votes.get(key, 0)
        pct   = round(count / total * 100, 1) if total > 0 else 0
        stats.append({"key": key, "label": label, "count": count, "pct": pct})
    return stats, total

# ── Routes ──────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    already_voted = request.cookies.get(COOKIE_NAME)
    if already_voted:
        # Uživatel už hlasoval – rovnou na výsledky
        return redirect(url_for("results"))
    return render_template("vote.html", question=QUESTION, options=OPTIONS)

@app.route("/vote", methods=["POST"])
def vote():
    # Druhá pojistka: zkontroluj cookie i na serveru
    if request.cookies.get(COOKIE_NAME):
        return redirect(url_for("results"))

    choice = request.form.get("choice")
    if choice not in OPTIONS:
        return "Neplatná volba.", 400

    votes = load_votes()
    votes[choice] = votes.get(choice, 0) + 1
    save_votes(votes)

    # Nastav cookie a přesměruj na výsledky
    resp = make_response(redirect(url_for("results")))
    resp.set_cookie(
        COOKIE_NAME,
        value=choice,                        # uložíme i co hlasoval
        max_age=COOKIE_DAYS * 24 * 3600,
        httponly=True,
        samesite="Lax",
    )
    return resp

@app.route("/results")
def results():
    stats, total    = build_stats()
    already_voted   = request.cookies.get(COOKIE_NAME)   # hodnota hlasu nebo None
    return render_template(
        "results.html",
        question=QUESTION,
        stats=stats,
        total=total,
        already_voted=already_voted,
    )

@app.route("/reset", methods=["POST"])
def reset():
    if request.form.get("token", "") != ADMIN_TOKEN:
        abort(403)
    save_votes(_default_votes())
    # Po resetu smaž i cookie, aby mohl uživatel hlasovat znovu
    resp = make_response(redirect(url_for("results")))
    resp.delete_cookie(COOKIE_NAME)
    return resp

# ── Spuštění (lokálně) ──────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True)
