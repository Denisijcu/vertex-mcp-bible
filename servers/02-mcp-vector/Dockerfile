FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

RUN useradd -m -s /bin/bash vertex_mcp
WORKDIR /app

COPY servers/02-mcp-vector/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY core_shared/ /app/core_shared/
COPY servers/02-mcp-vector/main.py /app/main.py

# CRITICO: Crear la carpeta de persistencia y asignar dueño ANTES de bajar privilegios
RUN mkdir -p /app/chroma_data && chown -R vertex_mcp:vertex_mcp /app

USER vertex_mcp

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
