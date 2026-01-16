# GitHub-Discord Bridge Docker Image
FROM python:3.14-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

ENV PORT=5000
EXPOSE 5000

CMD ["python", "/app/main.py"]
