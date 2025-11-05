# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2025 Gabriel Moraes - Noxfort Labs
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# File: src/utils/logging_setup.py
# Author: Gabriel Moraes
# Date: 17 de Setembro de 2025

"""
Configura um sistema de logging que escreve para o console e para um arquivo
em tempo real, com suporte a caracteres universais (UTF-8) e níveis de
log diferentes para cada saída.
"""
import logging
import sys
import os

def setup_logging(log_dir: str):
    """
    Configura o logging para o console e para um arquivo usando UTF-8.
    O arquivo de log captura tudo (DEBUG), enquanto o console é mais limpo (INFO).
    """
    log_file_path = os.path.join(log_dir, 'console_output.log')
    
    log_formatter = logging.Formatter('%(asctime)s [%(levelname)s] - %(message)s')
    
    root_logger = logging.getLogger()
    # --- CORREÇÃO (Parte 1): Define o nível mais baixo no logger principal ---
    # Isso permite que ele passe todas as mensagens para os handlers, que farão a filtragem.
    root_logger.setLevel(logging.DEBUG)
    
    # Limpa handlers existentes para evitar duplicação de logs
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    # --- CORREÇÃO (Parte 2): Configura o FileHandler para gravar TUDO ---
    # 1. Handler para salvar os logs em um arquivo, especificando a codificação UTF-8
    file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
    file_handler.setFormatter(log_formatter)
    file_handler.setLevel(logging.DEBUG) # Grava desde DEBUG até CRITICAL no arquivo.
    root_logger.addHandler(file_handler)

    # --- CORREÇÃO (Parte 3): Configura o ConsoleHandler para ser menos verboso ---
    # 2. Handler para mostrar os logs no console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_formatter)
    console_handler.setLevel(logging.INFO) # Mostra apenas de INFO até CRITICAL no console.
    root_logger.addHandler(console_handler)

    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        # A exceção será capturada por ambos os handlers
        root_logger.critical("Exceção não tratada:", exc_info=(exc_type, exc_value, exc_traceback))

    sys.excepthook = handle_exception
    
    # Esta mensagem só aparecerá no console, pois é INFO.
    logging.info("Sistema de Logging (Modo Tempo Real, UTF-8) configurado.")
    # Esta mensagem só aparecerá no arquivo .txt, pois é DEBUG.
    logging.debug("Logger configurado. FileHandler=DEBUG, StreamHandler=INFO.")