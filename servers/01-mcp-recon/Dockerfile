FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

RUN apt-get update && apt-get install -y --no-install-recommends \
    nmap \
    gobuster \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -s /bin/bash vertex_mcp
WORKDIR /app

COPY servers/01-mcp-recon/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY core_shared/ /app/core_shared/
COPY servers/01-mcp-recon/main.py /app/main.py

RUN chown -R vertex_mcp:vertex_mcp /app
USER vertex_mcp

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
