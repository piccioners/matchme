FROM python:3.12-slim

# libpq5 = contiene libpq.so.5 (quello che ti manca)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=8080
CMD ["gunicorn", "-b", "0.0.0.0:$PORT", "wsgi:app"]
