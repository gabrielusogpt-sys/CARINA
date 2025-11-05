# File: ui/handlers/settings_handler.py (CORRIGIDO)
# Author: Gabriel Moraes
# Date: 01 de Outubro de 2025

"""
Define o SettingsHandler.

Nesta versão, a responsabilidade de salvar o arquivo .ini foi removida.
O método 'save_settings' agora apenas coleta e valida os dados da UI,
retornando um dicionário pronto para ser enviado ao backend pelo SettingsClient.
"""

import logging
from typing import Dict, Any
import configparser
import os

class SettingsHandler:
    """
    Gerencia a lógica de carregar e validar as configurações da UI.
    """
    # O mapa de chaves para seções ainda é útil para a leitura inicial
    _KEY_TO_SECTION_MAP = {
        'language': 'UI', 'theme_dark': 'UI',
        'min_green_time': 'TRAFFIC_RULES', 'yellow_time_seconds': 'TRAFFIC_RULES',
        'heatmap_strategy': 'HEATMAP_SCALING', 'heatmap_saturation': 'HEATMAP_SCALING',
        'performance_margin': 'MATURITY', 'child_phase_episodes': 'MATURITY',
        'teen_phase_min_episodes': 'MATURITY', 'child_promotion_max_entropy': 'MATURITY',
        'performance_check_window': 'MATURITY',
        'calibration_window_size': 'CALIBRATION',
        'ppo_gamma': 'AI_TRAINING', 'ppo_k_epochs': 'AI_TRAINING', 'ppo_eps_clip': 'AI_TRAINING',
        'dqn_epsilon_decay': 'GUARDIAN_AGENT', 'dqn_batch_size': 'GUARDIAN_AGENT',
        'pbt_frequency': 'PBT', 'pbt_exploitation': 'PBT',
        'watchdog_grace': 'WATCHDOG', 'infra_analysis_freq': 'INFRASTRUCTURE_ANALYSIS',
        'weight_waiting_time': 'REWARD_WEIGHTS', 'weight_flow': 'REWARD_WEIGHTS',
        'weight_emergency_brake': 'REWARD_WEIGHTS', 'weight_teleport': 'REWARD_WEIGHTS'
    }

    def __init__(self):
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        self.config_path = os.path.join(project_root, "config", "settings.ini")
        self.config = configparser.ConfigParser()
        self._defaults = self._get_default_settings_map()
        self._current_settings = self.load_settings()
        logging.info("[SettingsHandler] Handler de Configurações inicializado e configurações carregadas.")

    def load_settings(self) -> Dict[str, Any]:
        """Lê o arquivo .ini e retorna um dicionário com as configurações."""
        try:
            if not os.path.exists(self.config_path):
                logging.warning(f"[SettingsHandler] Arquivo {self.config_path} não encontrado. Usando padrões.")
                return self.get_default_settings()

            self.config.read(self.config_path, encoding='utf-8')
            loaded_settings = {}
            for key, section in self._KEY_TO_SECTION_MAP.items():
                if self.config.has_option(section, key):
                    value = self.config.get(section, key)
                    if value.lower() in ['true', 'false']:
                        loaded_settings[key] = self.config.getboolean(section, key)
                    elif '.' in value:
                        try: loaded_settings[key] = self.config.getfloat(section, key)
                        except ValueError: loaded_settings[key] = value
                    else:
                        try: loaded_settings[key] = self.config.getint(section, key)
                        except ValueError: loaded_settings[key] = value
                else:
                    loaded_settings[key] = self._defaults.get(key)
            
            for key, value in self._defaults.items():
                if key not in loaded_settings:
                    loaded_settings[key] = value

            return loaded_settings
        except Exception as e:
            logging.error(f"[SettingsHandler] Erro ao carregar configurações: {e}. Usando padrões.")
            return self.get_default_settings()

    # --- MUDANÇA PRINCIPAL AQUI ---
    # Este método não escreve mais no arquivo. Ele apenas prepara os dados.
    def prepare_settings_for_save(self, new_settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        Valida e prepara as novas configurações para serem enviadas ao backend.
        Por enquanto, a validação é simples (apenas coleta), mas pode ser expandida aqui.
        """
        # Atualiza as configurações atuais na memória da UI
        self._current_settings.update(new_settings)
        logging.info("[SettingsHandler] Novas configurações preparadas para envio ao backend.")
        # Retorna o payload completo, pronto para ser enviado
        return new_settings

    def get_current_settings(self) -> Dict[str, Any]:
        return self._current_settings.copy()

    def get_default_settings(self) -> Dict[str, Any]:
        return self._defaults.copy()

    def _get_default_settings_map(self) -> Dict[str, Any]:
        """Retorna o dicionário de configurações padrão."""
        return {
            'theme_dark': True, 'language': 'pt_br', 'min_green_time': '10',
            'yellow_time_seconds': '3', 'heatmap_strategy': 'max', 'heatmap_saturation': '100.0',
            'performance_margin': '-100.0', 'child_phase_episodes': '1',
            'teen_phase_min_episodes': '1', 'child_promotion_max_entropy': '2.0',
            'performance_check_window': '1', 'calibration_window_size': '10',
            'ppo_gamma': '0.99', 'ppo_k_epochs': '4', 'ppo_eps_clip': '0.2',
            'dqn_epsilon_decay': '30000', 'dqn_batch_size': '128',
            'pbt_frequency': '10', 'pbt_exploitation': '25',
            'watchdog_grace': '30', 'infra_analysis_freq': '1',
            'weight_waiting_time': '-2.0', 'weight_flow': '2.0',
            'weight_emergency_brake': '-50.0', 'weight_teleport': '-300.0',
        }