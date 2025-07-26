from flask import Flask, request, session, render_template, redirect, jsonify, send_from_directory
from functools import wraps
import random
import logging
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from datetime import datetime, timedelta
from flask import jsonify

# Blacklist temporaire : {ip: expiration_time}
blacklist = {}
# Tentatives OTP échouées : {ip: count}
failed_attempts = {}
MAX_FAILED_ATTEMPTS = 5
BLACKLIST_DURATION = timedelta(minutes=15)

app = Flask(__name__)
app.secret_key = "ctf-secret"

# Logger
logging.basicConfig(level=logging.INFO)

# Limiter configuration
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100 per minute"]  # limites générales (peu strictes)
)
limiter.init_app(app)

USER_EMAIL = "cisco@dataprotect.ma"
USER_PASSWORD = "password123"

# ------------------ Gestion des erreurs ------------------

@app.errorhandler(429)
def ratelimit_handler(e):
   return (
    "🚫 Alerte de sécurité : Trop de tentatives détectées. "
    "Votre adresse IP a été définitivement bloquée pour comportement suspect. "
    "Si vous pensez qu'il s'agit d'une erreur, veuillez contacter l'administrateur.",
    429
)
# ------------------ Décorateurs de sécurité ------------------

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect("/")
        return f(*args, **kwargs)
    return decorated_function

def otp_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect("/")
        if not session.get("otp_verified"):
            return redirect("/otp")
        return f(*args, **kwargs)
    return decorated_function

# ------------------ Routes principales ------------------

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        if email == USER_EMAIL and password == USER_PASSWORD:
            session.clear()
            session['logged_in'] = True
            return redirect("/otp")
        return "Identifiants invalides", 401
    return render_template("login.html")

@app.route("/otp")
@login_required
def otp():
    return render_template("otp.html")

@app.route("/api/send_otp")
@login_required
def send_otp():
    otp = str(random.randint(10000000, 99999999))  # 🔐 OTP à 8 chiffres
    session['otp'] = otp
    return jsonify({
        "status": "otp_sent",
        "otp": otp  
    })

@app.route("/verify_otp", methods=["POST"])
@login_required
@limiter.limit("5 per minute")  
def verify_otp():
    ip = request.remote_addr

    # 🔒 Vérifie si IP est blacklistée
    if ip in blacklist:
        if datetime.utcnow() < blacklist[ip]:
            logging.warning(f"⛔ Accès refusé : IP {ip} est temporairement bannie.")
            return "⛔ Trop de tentatives. Réessayez plus tard.", 403
        else:
            # ✅ Expiration du ban
            del blacklist[ip]
            failed_attempts[ip] = 0

    submitted = request.form.get("otp")
    if submitted == session.get("otp"):
        session['otp_verified'] = True
        failed_attempts[ip] = 0  # Réinitialiser si succès
        return redirect("/dashboard")

    # ❌ OTP incorrect → incrémenter compteur
    failed_attempts[ip] = failed_attempts.get(ip, 0) + 1
    logging.info(f"❌ OTP invalide tenté depuis {ip} ({failed_attempts[ip]} fois)")

    # Si dépassement : bannir IP
    if failed_attempts[ip] >= MAX_FAILED_ATTEMPTS:
        blacklist[ip] = datetime.utcnow() + BLACKLIST_DURATION
        logging.warning(f"🚫 IP {ip} bannie pour activité suspecte !")

    return "OTP invalide", 403


@app.route("/admin/blacklist")
def show_blacklist():
    # Convertit les datetimes en chaînes lisibles
    readable = {ip: expiry.strftime("%Y-%m-%d %H:%M:%S") for ip, expiry in blacklist.items()}
    return jsonify(readable)

@app.route("/dashboard")
@otp_required
def dashboard():
    return render_template("dashboard.html")

@app.route("/download_rapport")
@otp_required
def download_rapport():
    return send_from_directory(directory="files", path="rapport_de_Stage.pdf", as_attachment=True)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
