FROM python:3.11-slim
WORKDIR /app
COPY servidor/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY servidor/ ./servidor/
RUN mkdir -p /app/data
CMD ["uvicorn", "servidor.main:app", "--host", "0.0.0.0", "--port", "8000"]
