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

# File: src/utils/locale_manager_backend.py (MODIFICADO PARA USAR resource_path)
# Author: Gabriel Moraes
# Date: 22 de Outubro de 2025 # <-- DATA ATUALIZADA

"""
Define o LocaleManagerBackend.

Nesta versão, ele foi refatorado para carregar um único arquivo de tradução
unificado do backend (ex: 'pt_br_backend.json') e usa a função resource_path
para compatibilidade com PyInstaller.
"""

import os
import json
import logging
import configparser
from typing import Dict, Any, List

# --- MUDANÇA 1: Importar a função resource_path ---
from .paths import resource_path
# --- FIM DA MUDANÇA 1 ---

class LocaleManagerBackend:
    """
    Gerencia o carregamento e o acesso às strings de tradução do backend.
    """
    def __init__(self):
        """
        Inicializa o gerenciador de tradução do backend, lendo a configuração
        de idioma diretamente do settings.ini usando resource_path.
        """
        # --- MUDANÇA 2: Usar resource_path para definir o diretório de locales ---
        self.locales_dir = resource_path(os.path.join("src", "locale_backend"))
        # --- FIM DA MUDANÇA 2 ---

        self.fallback_lang_code = "en_us"

        self.current_lang_data: Dict[str, Any] = {}
        self.fallback_lang_data: Dict[str, Any] = {}

        # --- MUDANÇA 3: Usar resource_path para ler o settings.ini ---
        config_path = resource_path(os.path.join("config", "settings.ini"))
        # --- FIM DA MUDANÇA 3 ---

        config = configparser.ConfigParser()
        lang_code = 'pt_br' # Padrão
        try:
            read_files = config.read(config_path, encoding='utf-8')
            if not read_files:
                 logging.warning(f"[LocaleManagerBackend] Falha ao ler settings.ini em '{config_path}', usando idioma padrão.")
            elif config.has_option('UI', 'language'):
                lang_code = config.get('UI', 'language')
        except Exception as e:
            logging.error(f"[LocaleManagerBackend] Falha ao ler settings.ini em '{config_path}', usando idioma padrão. Erro: {e}")

        logging.info(f"[LocaleManagerBackend] Gerenciador de Idiomas do Backend criado. Lendo idioma de settings.ini: '{lang_code}'")
        self.load_language(lang_code)

    def _load_language_file(self, lang_code: str) -> Dict[str, Any]:
        """
        Encontra e lê o arquivo JSON unificado para um idioma específico.
        """
        file_name = f"{lang_code}_backend.json"
        # O self.locales_dir já foi calculado corretamente com resource_path no __init__
        file_path = os.path.join(self.locales_dir, file_name)

        if not os.path.exists(file_path):
            logging.error(f"[LocaleManagerBackend] Arquivo de tradução unificado não encontrado: {file_path}")
            return {}

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logging.error(f"[LocaleManagerBackend] Falha ao carregar ou processar o arquivo '{file_name}': {e}")
            return {}

    def load_language(self, lang_code: str):
        """
        Carrega um novo idioma como o principal e garante que o idioma de fallback (inglês)
        esteja sempre carregado como reserva.
        """
        self.fallback_lang_data = self._load_language_file(self.fallback_lang_code)
        if not self.fallback_lang_data:
            logging.critical("[LocaleManagerBackend] FALHA CRÍTICA: Não foi possível carregar o arquivo de fallback (en_us_backend.json).")

        if lang_code == self.fallback_lang_code:
            self.current_lang_data = self.fallback_lang_data
        else:
            self.current_lang_data = self._load_language_file(lang_code)

        logging.info(f"Arquivo do idioma '{lang_code}' carregado com sucesso para o backend.")

    def _get_nested_value(self, data: Dict, keys: List[str]) -> str | None:
        """
        Navega em um dicionário aninhado usando uma lista de chaves.
        """
        temp_dict = data
        for key in keys:
            if isinstance(temp_dict, dict) and key in temp_dict:
                temp_dict = temp_dict[key]
            else:
                return None
        return str(temp_dict) if isinstance(temp_dict, (str, int, float, bool)) else None

    def get_string(self, key: str, fallback: str = None, **kwargs) -> str:
        """
        Obtém uma string de tradução e formata com os argumentos fornecidos.
        Implementa a lógica de fallback para o inglês.
        """
        keys = key.split('.')

        translation = self._get_nested_value(self.current_lang_data, keys)
        if translation is None:
            fallback_translation = self._get_nested_value(self.fallback_lang_data, keys)
            if fallback_translation is not None:
                translation = fallback_translation
            elif fallback is not None:
                # Se uma fallback string explícita foi passada, use-a
                translation = fallback
            else:
                # Se não há fallback nem no arquivo nem explícito, loga erro e retorna a chave
                logging.error(f"[LocaleManagerBackend] Chave '{key}' não encontrada em nenhum arquivo de tradução.")
                return key

        try:
            return translation.format(**kwargs)
        except KeyError as e:
            logging.error(f"[LocaleManagerBackend] Placeholder '{{{e.args[0]}}}' faltando na chave '{key}' ao formatar.")
            return translation # Retorna a string não formatada ou parcialmente formatada
        except Exception as format_error:
            # Captura outros erros de formatação
            logging.error(f"[LocaleManagerBackend] Erro ao formatar a chave '{key}' com {kwargs}: {format_error}")
            return translation # Retorna a string não formatada