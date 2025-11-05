# File: ui/handlers/locale_manager.py (CORRIGIDO)
# Author: Gabriel Moraes
# Date: 01 de Outubro de 2025

"""
Define o LocaleManager, o "cérebro" do sistema de tradução da UI.
Nesta versão, o método get_string foi atualizado para aceitar um argumento
'fallback' opcional para maior robustez.
"""

import os
import json
import logging
from typing import Dict, Any, List

from ui.handlers.settings_handler import SettingsHandler

class LocaleManager:
    """
    Gerencia o carregamento e o acesso às strings de tradução da UI.
    """
    def __init__(self):
        """
        Inicializa o gerenciador de tradução, lendo a configuração
        de idioma salva.
        """
        self.locales_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "locales"))
        self.fallback_lang_code = "en_us"
        
        self.current_lang_data: Dict[str, Any] = {}
        self.fallback_lang_data: Dict[str, Any] = {}

        settings_handler = SettingsHandler()
        current_settings = settings_handler.get_current_settings()
        initial_lang_code = current_settings.get('language', 'pt_br')
        
        logging.info(f"[LocaleManager] Idioma inicial definido como '{initial_lang_code}' a partir das configurações.")
        self.load_language(initial_lang_code)

    def _load_file(self, lang_code: str) -> Dict[str, Any]:
        """
        Lê e processa um único arquivo JSON de tradução.
        """
        file_path = os.path.join(self.locales_dir, f"{lang_code}.json")
        if not os.path.exists(file_path):
            logging.error(f"[LocaleManager] Arquivo de tradução não encontrado: {file_path}")
            return {}
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logging.error(f"[LocaleManager] Falha ao carregar ou processar o arquivo '{file_path}': {e}")
            return {}

    def load_language(self, lang_code: str):
        """
        Carrega um novo idioma como o principal e garante que o idioma de fallback (inglês)
        esteja sempre carregado como reserva.
        """
        logging.info(f"[LocaleManager] Carregando idioma: '{lang_code}'...")
        
        self.fallback_lang_data = self._load_file(self.fallback_lang_code)
        if not self.fallback_lang_data:
            logging.critical("[LocaleManager] FALHA CRÍTICA: Não foi possível carregar o idioma de fallback (en_us).")

        if lang_code == self.fallback_lang_code:
            self.current_lang_data = self.fallback_lang_data
        else:
            self.current_lang_data = self._load_file(lang_code)
        
        logging.info(f"'{lang_code}' carregado com sucesso.")

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

    # --- MUDANÇA PRINCIPAL AQUI ---
    def get_string(self, key: str, fallback: str = None) -> str:
        """
        Obtém uma string de tradução usando uma chave aninhada (ex: "main_ui.app_title").
        Implementa a lógica de fallback para o inglês e para um valor padrão.
        """
        keys = key.split('.')
        
        # 1. Tenta a tradução no idioma atual
        translation = self._get_nested_value(self.current_lang_data, keys)
        if translation is not None:
            return translation
            
        # 2. Se falhar, tenta a tradução no idioma de fallback (inglês)
        logging.warning(f"[LocaleManager] Chave '{key}' não encontrada no idioma atual. Tentando fallback para inglês...")
        fallback_translation = self._get_nested_value(self.fallback_lang_data, keys)
        if fallback_translation is not None:
            return fallback_translation
            
        # 3. Se falhar novamente, usa o valor de fallback fornecido na chamada
        if fallback is not None:
            logging.warning(f"[LocaleManager] Chave '{key}' não encontrada no inglês. Usando valor de fallback do código.")
            return fallback

        # 4. Como último recurso, retorna a própria chave
        logging.error(f"[LocaleManager] Chave '{key}' não encontrada em nenhum arquivo de tradução e sem fallback fornecido.")
        return key
    # --- FIM DA MUDANÇA ---