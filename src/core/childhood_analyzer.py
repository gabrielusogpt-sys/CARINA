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

# File: src/core/childhood_analyzer.py (CORRIGIDO)
# Author: Gabriel Moraes
# Date: 03 de Outubro de 2025

import logging
import os
import json
import numpy as np
import sys
from collections import defaultdict
from typing import TYPE_CHECKING

# Adiciona o diretório 'src' ao path para permitir importações absolutas
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

if TYPE_CHECKING:
    from utils.locale_manager_backend import LocaleManagerBackend

class ChildhoodAnalyzer:
    """
    Analisa o ambiente nos episódios iniciais (infância) para definir
    perfis de tráfego e a linha de base de desempenho.
    """

    def __init__(self, settings: dict, scenario_results_dir: str, locale_manager: 'LocaleManagerBackend'):
        self.locale_manager = locale_manager
        
        # --- CORREÇÃO APLICADA AQUI ---
        # 1. O nome do atributo foi alterado de 'episodes_to_analyze' para 'analysis_episodes'.
        # 2. A chave lida das configurações foi alterada de 'child_phase_episodes' para 'childhood_analysis_episodes'.
        self.analysis_episodes = settings.getint('childhood_analysis_episodes', fallback=1)
        # --- FIM DA CORREÇÃO ---

        self.peak_hours_rules = {}
        if 'peak_hours' in settings:
            try:
                self.peak_hours_rules = json.loads(settings['peak_hours'])
            except json.JSONDecodeError:
                pass
        
        self.cache_path = os.path.join(scenario_results_dir, "analysis_cache", "childhood_cache.json")
        os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)

    def check_cache(self) -> bool:
        """Verifica se o cache da análise de infância existe e é válido."""
        if os.path.exists(self.cache_path):
            logging.info(self.locale_manager.get_string("childhood_analyzer.cache.found", path=self.cache_path))
            return True
        return False

    def load_from_cache(self) -> tuple:
        """Carrega os perfis e a linha de base a partir do arquivo de cache."""
        lm = self.locale_manager
        try:
            logging.info(lm.get_string("childhood_analyzer.cache.loading"))
            with open(self.cache_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data.get('traffic_profiles', {}), data.get('baseline', {})
        except Exception as e:
            logging.error(lm.get_string("childhood_analyzer.cache.load_error", error=e), exc_info=True)
            return {}, {}

    def save_to_cache(self, profiles: dict, baseline: dict):
        """Salva os perfis e a linha de base em um arquivo de cache."""
        lm = self.locale_manager
        try:
            logging.info(lm.get_string("childhood_analyzer.cache.saving"))
            with open(self.cache_path, 'w', encoding='utf-8') as f:
                json.dump({'traffic_profiles': profiles, 'baseline': baseline}, f, indent=4)
        except Exception as e:
            logging.error(lm.get_string("childhood_analyzer.cache.save_error", error=e), exc_info=True)

    def run_analysis(self, episode_metrics: list) -> tuple:
        """
        Executa a análise com base nas métricas dos episódios da infância.
        """
        lm = self.locale_manager
        # Define perfis de tráfego com base nas regras
        traffic_profiles = {}
        if not self.peak_hours_rules:
            logging.info(lm.get_string("childhood_analyzer.run.no_rules_warning"))
            traffic_profiles = {day: {str(h): "low" for h in range(24)} for day in range(7)}
        else:
            for day in range(7):
                traffic_profiles[day] = {}
                for hour in range(24):
                    profile = "low"
                    for rule in self.peak_hours_rules:
                        if day in rule['days'] and rule['start_hour'] <= hour < rule['end_hour']:
                            profile = "peak"
                            break
                    traffic_profiles[day][str(hour)] = profile
        
        # Calcula a linha de base (baseline) de desempenho
        baseline_reward = 0
        if episode_metrics:
            logging.info(lm.get_string("childhood_analyzer.run.start"))
            logging.info(lm.get_string("childhood_analyzer.run.analyzing_episodes", count=len(episode_metrics)))
            
            total_rewards_per_agent = defaultdict(list)
            for single_episode_metrics in episode_metrics:
                for agent_id, metrics in single_episode_metrics.items():
                    total_rewards_per_agent[agent_id].append(metrics['reward'])
            
            mean_rewards = [np.mean(rewards) for rewards in total_rewards_per_agent.values()]
            if mean_rewards:
                baseline_reward = np.mean(mean_rewards)
            
            logging.info(lm.get_string("childhood_analyzer.run.complete", reward=f"{baseline_reward:.2f}"))

        baseline = {'mean_reward': baseline_reward}
        
        return traffic_profiles, baseline