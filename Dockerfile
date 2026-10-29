FROM python:3.12-slim

# Force Python to print everything to stdout instantly
ENV PYTHONUNBUFFERED=1

WORKDIR /app
COPY requirements.txt .
COPY .env .
RUN pip install --no-cache-dir -r requirements.txt
COPY script.py .
CMD ["python", "script.py"]
