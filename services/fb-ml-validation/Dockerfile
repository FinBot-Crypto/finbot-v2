FROM python:3.12-slim
WORKDIR /app
COPY services/fb-ml-validation/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY services/fb-ml-validation/ .
CMD ["python", "src/main.py"]
