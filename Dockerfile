FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Création du dossier pour les images
RUN mkdir -p static/uploads
# COMMANDE DE LANCEMENT
CMD ["python", "app.py"]
# FORCE REBUILD : VERSION 10 (Change ce chiffre si ça bloque encore !)