FROM python:3.11-slim
WORKDIR /app
# iproute2 traz o comando tc, usado no Experimento E (tc netem).
RUN apt-get update \
    && apt-get install -y --no-install-recommends iproute2 \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["sleep", "infinity"]
