# Estágio 1: O Ambiente de Build
# Usamos a mesma base do seu SO (Ubuntu) para garantir compatibilidade de binários
FROM ubuntu:22.04 AS builder

# Evita que o 'apt' faça perguntas interativas
ENV DEBIAN_FRONTEND=noninteractive

# --- CORREÇÃO v6 ---
# Adicionado 'libpython3.11' (a biblioteca compartilhada) e 'binutils' (para objdump)
RUN apt-get update && \
    apt-get install -y software-properties-common wget && \
    add-apt-repository ppa:deadsnakes/ppa -y && \
    apt-get update && \
    apt-get install -y \
    python3.11 \
    libpython3.11 \
    python3.11-venv \
    python3.11-distutils \
    libgl1-mesa-glx \
    libglib2.0-0 \
    binutils \
    && rm -rf /var/lib/apt/lists/*
# --- FIM DA CORREÇÃO ---

# Faz python3 apontar para python3.11
RUN ln -sf /usr/bin/python3.11 /usr/bin/python3

# Usa o 'ensurepip' do próprio python3.11 para instalar o pip
RUN python3.11 -m ensurepip

# Atualiza o pip e instala 'wheel' e 'setuptools', essenciais para builds
RUN python3 -m pip install --upgrade pip setuptools wheel

# Define o diretório de trabalho dentro do container
WORKDIR /app

# Copia todos os arquivos do projeto para o container (respeitando o .dockerignore)
COPY . .

# Usar "python3 -m pip" para garantir a versão correta
# Instala as dependências Python do nosso arquivo limpo
RUN python3 -m pip install --no-cache-dir -r build-requirements.txt

# Instala o sumolib (necessário pelo carina.spec, mas não listado no requirements)
RUN python3 -m pip install sumolib

# Executa o PyInstaller usando o seu arquivo .spec
RUN pyinstaller --noconfirm carina.spec

# O resultado estará em /app/dist/carina