FROM python:latest
WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY /app /app
CMD ["python", "test-main.py"]
CMD ["python", "main.py"]
