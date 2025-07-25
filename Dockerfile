# Utilise une image officielle Python
FROM python:3.11-slim

# Crée un répertoire de travail
WORKDIR /app

# Copie les fichiers nécessaires
COPY . /app

# Installe les dépendances
RUN pip install --no-cache-dir Flask Flask-Limiter

# Expose le port utilisé par Flask
EXPOSE 5000

# Définit la commande pour lancer l'application
CMD ["python3", "flask_app.py"]
