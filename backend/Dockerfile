FROM python:3.11-slim
WORKDIR /app

# Install Pulumi CLI
RUN apt-get update && apt-get install -y curl && \
    curl -fsSL https://get.pulumi.com | sh && \
    apt-get remove -y curl && apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*
ENV PATH="/root/.pulumi/bin:${PATH}"

# Pre-install GCP plugin to avoid cold-start download
RUN pulumi plugin install resource gcp v8.0.0

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ ./app/
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
