FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Création des dossiers
RUN mkdir -p static/uploads
RUN mkdir -p data
CMD ["python", "app.py"]
# FORCE UPDATE V: 77