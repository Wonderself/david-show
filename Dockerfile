FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# On s'assure que le dossier uploads existe
RUN mkdir -p static/uploads
CMD ["python", "app.py"]
# RESCUE UPDATE V: 999