FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN useradd --create-home --uid 1000 bot && mkdir -p /app/data && chown -R bot /app/data
USER bot

VOLUME ["/app/data"]
CMD ["python", "main.py"]
