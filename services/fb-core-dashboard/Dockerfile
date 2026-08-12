# Stage 1: Build React Frontend
FROM node:20-slim AS build

WORKDIR /app

COPY services/fb-core-dashboard/package*.json ./
RUN npm install

COPY services/fb-core-dashboard/ .
RUN npm run build

# Stage 2: Serve with Python FastAPI
FROM python:3.10-slim

WORKDIR /app

RUN pip install --no-cache-dir fastapi uvicorn psycopg2-binary nats-py ccxt docker

COPY services/fb-core-dashboard/main.py .
COPY --from=build /app/dist ./dist

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
