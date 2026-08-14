FROM python:3.12-slim

WORKDIR /app

COPY packages/finbot-common /packages/finbot-common
RUN pip install --no-cache-dir /packages/finbot-common

COPY services/fb-mare/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/fb-mare/ .

ENV PYTHONPATH=/app/src

CMD ["python", "-m", "mare_service"]
