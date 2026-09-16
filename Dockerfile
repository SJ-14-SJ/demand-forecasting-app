FROM node:22-slim AS frontend
WORKDIR /ui
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY forecast/ forecast/
COPY data/ data/
RUN python -m forecast.train --origin 'UCI Online Retail - historical UK sales'
COPY --from=frontend /ui/dist frontend/dist
RUN useradd --create-home appuser
USER appuser
EXPOSE 8000
CMD ["uvicorn", "forecast.api:app", "--host", "0.0.0.0", "--port", "8000"]
