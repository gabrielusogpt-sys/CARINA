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

# File: src/utils/paths.py (NOVO ARQUIVO)
# Author: Gabriel Moraes
# Date: 22 de Outubro de 2025

"""
Define funções utilitárias para lidar com caminhos de arquivos,
garantindo compatibilidade com PyInstaller (--onefile).
"""

import sys
import os

def resource_path(relative_path: str) -> str:
    """
    Retorna o caminho absoluto para um recurso (arquivo de dados),
    funcionando tanto em modo de desenvolvimento quanto no executável
    criado pelo PyInstaller.

    Args:
        relative_path (str): O caminho relativo para o recurso a partir da
                             raiz do projeto (ou do bundle).

    Returns:
        str: O caminho absoluto para o recurso.
    """
    try:
        # PyInstaller cria uma pasta temporária e armazena o caminho em _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # Se _MEIPASS não existe, estamos em modo de desenvolvimento.
        # Usamos abspath(".") para obter a raiz do projeto onde o script/comando é executado.
        # Ajustamos para subir dois níveis a partir de src/utils para chegar na raiz.
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    return os.path.join(base_path, relative_path)

def get_base_output_dir() -> str:
    """
    Retorna o diretório base onde arquivos de saída (logs, results) devem ser escritos.
    Em modo de desenvolvimento, é a raiz do projeto.
    Quando executado como um bundle PyInstaller, é o diretório onde o executável está.

    Returns:
        str: O caminho absoluto para o diretório base de saída.
    """
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # Estamos rodando como um bundle PyInstaller (--onefile ou --onedir)
        # Queremos escrever *ao lado* do executável, não na pasta temporária _MEIPASS.
        return os.path.dirname(sys.executable)
    else:
        # Estamos em modo de desenvolvimento.
        # Define a raiz baseada na localização deste arquivo (src/utils/paths.py)
        return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))