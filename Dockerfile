FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src /app/src
WORKDIR /app/src

EXPOSE 8000

CMD ["python", "app.py"]
