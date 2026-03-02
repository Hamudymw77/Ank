# 🪐 Anketa — Největší planeta Sluneční soustavy

Jednoduchá webová anketa postavená na **Pythonu** a **Flasku**. Hlasy se ukládají do JSON souboru na serveru a jsou sdílené pro všechny návštěvníky.

---

## 📁 Struktura projektu

```
mysite/
├── app.py                  # Flask backend
├── data/
│   └── votes.json          # Hlasy (vytvoří se automaticky)
├── templates/
│   ├── vote.html           # Stránka s anketou
│   └── results.html        # Stránka s výsledky
└── static/
    └── style.css           # Styly (dark theme)
```

---

## ⚙️ Funkce

| Funkce | Popis |
|---|---|
| **F1 Hlasování** | Zobrazí otázku se 3 možnostmi, po odeslání uloží hlas |
| **F2 Výsledky** | Zobrazí aktuální výsledky s progress bary |
| **F3 Reset** | Admin může vynulovat všechny hlasy pomocí tokenu |
| **F4 Ochrana** | Cookie zabrání hlasovat dvakrát ze stejného prohlížeče |

---

## 🚀 Instalace a spuštění

### Lokálně

```bash
# 1. Nainstaluj závislosti
pip install flask

# 2. Spusť aplikaci
python app.py

# 3. Otevři v prohlížeči
http://127.0.0.1:5000
```

### PythonAnywhere

1. Nahraj všechny soubory do složky `/home/<tvuj_uzivatel>/mysite/`
2. V záložce **Web** vytvoř novou webovou aplikaci (Manual configuration, Python 3.x)
3. Nastav **Source code** na `/home/<tvuj_uzivatel>/mysite`
4. V WSGI konfiguračním souboru nahraď obsah za:

```python
import sys
sys.path.insert(0, '/home/<tvuj_uzivatel>/mysite')
from app import app as application
```

5. Klikni na **Reload** — hotovo!

---

## 🔐 Admin reset

Na stránce `/results` je dole formulář pro reset hlasování.

Výchozí token (změň před nasazením!):
```
mojetajneheslo
```

Token změníš v `app.py` na řádku:
```python
ADMIN_TOKEN = "mojetajneheslo"
```

Při správném tokenu se všechny hlasy vynulují a cookie se smaže.
Při špatném tokenu server vrátí chybu **403 Forbidden**.

---

## 🍪 Ochrana proti dvojímu hlasování

Aplikace používá **HTTP cookie** s názvem `has_voted`:

- Cookie se nastaví po prvním hlasování a platí **30 dní**
- Pokud cookie existuje, uživatel je přesměrován přímo na výsledky
- Cookie je `httponly` — JavaScript k ní nemá přístup
- Po admin resetu se cookie smaže, takže admin může hned testovat znovu

> **Poznámka:** Cookie lze smazat v nastavení prohlížeče. Pro ankety bez přihlášení je to standardní a očekávané chování.

---

## 🗳️ Otázka a možnosti

Otázka i možnosti jsou definovány v `app.py` a lze je snadno upravit:

```python
QUESTION = "Jaká je největší planeta Sluneční soustavy?"

OPTIONS = {
    "jupiter": "Jupiter",
    "saturn":  "Saturn",
    "mars":    "Mars",
}
```

---

## 🛠️ Technologie

- **Python 3** — backend jazyk
- **Flask** — webový framework
- **JSON** — úložiště hlasů (`data/votes.json`)
- **threading.Lock()** — bezpečný zápis při souběžných požadavcích
- **HTML / CSS** — frontend (žádný JavaScript framework)
- **Google Fonts** — Outfit + JetBrains Mono

---

## 📋 HTTP Endpointy

| Metoda | URL | Popis |
|---|---|---|
| `GET` | `/` | Zobrazí anketu (nebo přesměruje na výsledky) |
| `POST` | `/vote` | Uloží hlas, přesměruje na výsledky |
| `GET` | `/results` | Zobrazí aktuální výsledky |
| `POST` | `/reset` | Vynuluje hlasy (vyžaduje token) |
