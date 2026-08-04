FROM python:3.13-slim

WORKDIR /workspace

# Install system dependencies if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x solve.sh

ENTRYPOINT ["/workspace/solve.sh"]
