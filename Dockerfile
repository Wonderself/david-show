FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Création du dossier uploads
RUN mkdir -p static/uploads
# COMMANDE DE LANCEMENT
CMD ["python", "app.py"]
# FORCE UPDATE : VERSION 5 (Ce commentaire force la reconstruction)