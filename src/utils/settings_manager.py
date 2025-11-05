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

# File: src/utils/settings_manager.py (APENAS resource_path ADICIONADO)
# Author: Gabriel Moraes
# Date: 22 de Outubro de 2025 # <-- DATA ATUALIZADA

"""
Define o SettingsManager, uma classe de back-end responsável por ler e
escrever as configurações do sistema no arquivo settings.ini.
"""

import configparser
import os
import logging
from typing import Dict, Any

# --- MUDANÇA 1: Importar resource_path ---
import sys
# Garante que 'src' esteja no path para a importação relativa funcionar
project_root_sm = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
src_path_sm = os.path.join(project_root_sm, 'src')
if src_path_sm not in sys.path:
    sys.path.insert(0, src_path_sm)
from src.utils.paths import resource_path # Importa a função
# --- FIM DA MUDANÇA 1 ---

class SettingsManager:
    """
    Gerencia a leitura e escrita do arquivo de configuração 'settings.ini'.
    """
    _KEY_TO_SECTION_MAP = {
        'theme_dark': 'UI', 'language': 'UI',
        'min_green_time': 'TRAFFIC_RULES', 'yellow_time': 'TRAFFIC_RULES', # Nota: Originalmente tinha yellow_time_seconds, mas o arquivo ui/handlers/settings_handler usa yellow_time. Mantendo yellow_time.
        'heatmap_strategy': 'HEATMAP_SCALING', 'heatmap_saturation': 'HEATMAP_SCALING',
        'log_progress': 'LOGGING', # Nota: Chave original pode ser log_step_progress
        'watchdog_grace': 'WATCHDOG', # Nota: Originalmente tinha initial_grace_period_seconds / heartbeat_timeout_seconds
        'infra_analysis_freq': 'INFRASTRUCTURE_ANALYSIS', # Nota: Originalmente tinha analysis_frequency_seconds / initial_analysis_delay_seconds
        'performance_margin': 'MATURITY', # Nota: Originalmente tinha performance_margin_percent
        'ppo_gamma': 'AI_TRAINING', 'ppo_k_epochs': 'AI_TRAINING', 'ppo_eps_clip': 'AI_TRAINING',
        'dqn_epsilon_decay': 'GUARDIAN_AGENT', 'dqn_batch_size': 'GUARDIAN_AGENT',
        'pbt_frequency': 'PBT', 'pbt_exploitation': 'PBT',
        # --- Adicionar outras chaves/seções que precisam ser salvas se existirem ---
        'weight_waiting_time': 'REWARD_WEIGHTS', 'weight_flow': 'REWARD_WEIGHTS',
        'weight_emergency_brake': 'REWARD_WEIGHTS', 'weight_teleport': 'REWARD_WEIGHTS',
        'update_frequency_seconds': 'GAT_STRATEGIST' # Adicionado GAT
    }

    def __init__(self):
        """
        Inicializa o gerenciador, localizando o arquivo settings.ini usando resource_path.
        """
        # --- MUDANÇA 2: Usar resource_path para self.config_path ---
        self.config_path = resource_path(os.path.join("config", "settings.ini"))
        # --- FIM DA MUDANÇA 2 ---
        logging.info(f"[SettingsManager] Gerenciador de configurações apontando para: {self.config_path}")

    def load_settings(self) -> Dict[str, Any]:
        """
        Lê o arquivo .ini e o converte para um dicionário simples (flat).
        (Lógica original mantida)
        """
        config = configparser.ConfigParser()
        if not os.path.exists(self.config_path):
            logging.error(f"Arquivo de configuração não encontrado em {self.config_path}")
            return {}

        config.read(self.config_path, encoding='utf-8')

        settings_dict = {}
        # Mapeamento pode precisar de ajuste fino baseado no conteúdo real do settings.ini e o que a UI envia
        for key, section in self._KEY_TO_SECTION_MAP.items():
            if config.has_section(section) and config.has_option(section, key):
                settings_dict[key] = config.get(section, key)

        # Adiciona chaves booleanas se necessário (exemplo mantido do original)
        if config.has_section('LOGGING') and config.has_option('LOGGING', 'log_step_progress'):
             # Usa a chave original 'log_step_progress' para ler, mas salva como 'log_progress' se mapeado assim
             settings_dict['log_progress'] = config.getboolean('LOGGING', 'log_step_progress')
        elif config.has_section('UI') and config.has_option('UI', 'theme_dark'): # Adiciona theme_dark
             settings_dict['theme_dark'] = config.getboolean('UI', 'theme_dark')


        return settings_dict

    def save_settings(self, new_settings: Dict[str, Any]):
        """
        Atualiza e salva o arquivo .ini com os novos valores.
        (Lógica original mantida, usa self.config_path que agora é calculado com resource_path)
        """
        config = configparser.ConfigParser()
        if not os.path.exists(self.config_path):
            logging.error(f"Arquivo de configuração não encontrado. Não é possível salvar.")
            return

        config.read(self.config_path, encoding='utf-8')

        for key, value in new_settings.items():
            if key in self._KEY_TO_SECTION_MAP:
                section = self._KEY_TO_SECTION_MAP[key]
                if not config.has_section(section):
                    config.add_section(section)

                # Garante que valores booleanos sejam salvos como strings 'True'/'False'
                if isinstance(value, bool):
                     config.set(section, key, str(value))
                else:
                     config.set(section, key, str(value)) # Converte tudo para string para salvar

        try:
            with open(self.config_path, 'w', encoding='utf-8') as configfile:
                config.write(configfile)
            logging.info(f"Configurações salvas com sucesso em {self.config_path}")
        except IOError as e:
            logging.error(f"Falha ao escrever no arquivo de configuração: {e}")