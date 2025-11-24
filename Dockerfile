FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY ./app ./app
COPY .env .env

# Set PYTHONPATH so 'app' can be imported
ENV PYTHONPATH=/app

# Explicit full path to uvicorn in case PATH isn’t set up right
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
