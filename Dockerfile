# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2025 Gabriel Moraes - Noxfort Labs
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY;
# without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

# File: Dockerfile
# Author: Gabriel Moraes
# Date: 28 de Outubro de 2025
#
# Descrição:
# Este Dockerfile é otimizado para PyInstaller e PyTorch (com CUDA).
# Ele usa um build multi-stage para manter a imagem final leve.
# =====================================================================
# ESTÁGIO 1: BUILDER
# Baseado na imagem oficial do PyTorch com CUDA 11.8 e Python 3.11
# =====================================================================
FROM pytorch/pytorch:2.2.1-cuda11.8-cudnn8-runtime AS builder

# Define o diretório de trabalho
WORKDIR /app

# Define variáveis de ambiente para evitar prompts interativos
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# --- CORREÇÃO 5 ---
# O pacote 'qmapcontrol==0.9.7.5' não suporta Python 3.11.
# Fazendo o downgrade do ambiente de build para Python 3.10.
RUN apt-get update && \
    apt-get install -y \
        python3.10 \
        python3.10-venv \
        python3.10-dev \
        python3-pip \
        build-essential \
        patchelf \
        upx \
        libmpv-dev \
    && rm -rf /var/lib/apt/lists/*
# --- FIM DA CORREÇÃO 5 ---

# Força o link simbólico para libmpv.so.1
RUN ln -sf /usr/lib/x86_64-linux-gnu/libmpv.so.2 /usr/lib/x86_64-linux-gnu/libmpv.so.1

# --- CORREÇÃO 5 ---
# Cria e ativa um ambiente virtual com Python 3.10
RUN python3.10 -m venv /app/venv
# --- FIM DA CORREÇÃO 5 ---
ENV PATH="/app/venv/bin:$PATH"

# Atualiza o pip
RUN pip install --upgrade pip

# Copia o arquivo de requisitos de build (o corrigido, com 'qmapcontrol')
COPY build-requirements.txt .
# Instala os requisitos de Python
RUN pip install --no-cache-dir -r build-requirements.txt

# Copia todo o código-fonte do CARINA para o container
COPY . .

# Executa o PyInstaller
# Assegura que o PyInstaller use o Python do venv
RUN /app/venv/bin/pyinstaller --noconfirm carina.spec

# =====================================================================
# ESTÁGIO 2: FINAL
# Imagem base leve do Ubuntu
# =====================================================================
FROM ubuntu:22.04

WORKDIR /app

# Define variáveis de ambiente para evitar prompts interativos
ENV DEBIAN_FRONTEND=noninteractive

# Instala dependências de sistema (runtime do libmpv)
RUN apt-get update && \
    apt-get install -y \
        libmpv-dev \
        libmpv1 \
    && rm -rf /var/lib/apt/lists/*

# Força o link simbólico para libmpv.so.1
RUN ln -sf /usr/lib/x86_64-linux-gnu/libmpv.so.2 /usr/lib/x86_64-linux-gnu/libmpv.so.1

# Copia o executável construído do estágio anterior
COPY --from=builder /app/dist/carina /app/dist/carina

# O entrypoint é apenas o executável (não é necessário, mas define o padrão)