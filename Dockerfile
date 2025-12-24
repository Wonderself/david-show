FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Création du dossier uploads s'il n'est pas copié
RUN mkdir -p static/uploads
CMD ["python", "app.py"]
# FORCE UPDATE : VERSION 3 (Change ce chiffre si ça bug encore)