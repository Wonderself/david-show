FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Création du dossier uploads s'il n'est pas copié
RUN mkdir -p static/uploads
# Suppression du fichier data pour partir propre
CMD ["python", "app.py"]
# Force Update Final 1