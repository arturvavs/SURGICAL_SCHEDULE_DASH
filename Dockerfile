# Etapa de Build
FROM python:3.12-slim-bookworm AS builder

# Instala dependências de build
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpcre3 \
    libpcre3-dev \
    tzdata \
    curl && \
    ln -sf /usr/share/zoneinfo/America/Sao_Paulo /etc/localtime && \
    echo "America/Sao_Paulo" > /etc/timezone &&\
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Criação do ambiente virtual
WORKDIR /app
ENV VIRTUAL_ENV=/app/venv
RUN python -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Etapa Final
FROM python:3.12-slim-bookworm

# Instala dependências
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpcre3 \
    libpcre3-dev \
    tzdata \
    curl && \
    ln -sf /usr/share/zoneinfo/America/Sao_Paulo /etc/localtime && \
    echo "America/Sao_Paulo" > /etc/timezone &&\
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Copiar o ambiente virtual criado
COPY --from=builder /app/venv /venv

# Configura o contêiner
ENV PATH="/venv/bin:$PATH"
WORKDIR /app
COPY . .
RUN adduser --disabled-password --gecos '' nonroot && chown -R nonroot:nonroot /app
USER nonroot
EXPOSE 6011
HEALTHCHECK --interval=30s --timeout=10s --retries=3 CMD curl --fail http://localhost:6011/health || exit 1
CMD ["python", "app.py"]
