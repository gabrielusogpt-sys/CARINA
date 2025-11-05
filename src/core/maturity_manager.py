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

# File: src/core/maturity_manager.py (MODIFICADO PARA TRADUÇÃO COMPLETA)
# Author: Gabriel Moraes
# Date: 03 de Outubro de 2025

import logging
from collections import deque
import numpy as np
import sys
import os
import json
from typing import TYPE_CHECKING

# Adiciona o diretório 'src' ao path para permitir importações absolutas
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from core.enums import Maturity

if TYPE_CHECKING:
    from utils.locale_manager_backend import LocaleManagerBackend
    from core.maturity_reporter import MaturityReporter


class MaturityManager:
    """
    O "Diretor" da Escola de Pilotagem. Gerencia o estado e a lógica de
    promoção dos agentes, delegando a comunicação para o MaturityReporter.
    """
    
    def __init__(self, settings: dict, baseline: dict, 
                 locale_manager: 'LocaleManagerBackend', reporter: 'MaturityReporter'):
        self.locale_manager = locale_manager
        self.reporter = reporter
        lm = self.locale_manager
        
        self.baseline_performance = baseline.get('mean_reward', -10000)
        performance_margin_percent = settings.getfloat('performance_margin_percent', fallback=5.0)
        self.performance_margin = 1.0 + (performance_margin_percent / 100.0)
        self.baseline_target = self.baseline_performance * self.performance_margin
        self.child_phase_duration = settings.getint('child_phase_episodes', fallback=5)
        self.teen_phase_min_duration = settings.getint('teen_phase_min_episodes', fallback=50)
        self.child_promotion_max_entropy = settings.getfloat('child_promotion_max_entropy', fallback=1.0)
        self.agent_maturity = {}
        self.agent_episodes_in_phase = {}
        rewards_window_size = settings.getint('performance_check_window', fallback=10)
        self.agent_recent_rewards = {}
        self._rewards_window_size = rewards_window_size
        self.teen_entropy_threshold = float('inf')
        self.adult_entropy_threshold = float('inf')
        self.is_calibrated = False
        
        logging.info(lm.get_string("maturity_manager.init.manager_created"))
        logging.info(lm.get_string("maturity_manager.init.performance_target", target=f"{self.baseline_target:.2f}"))

    def get_state(self) -> dict:
        """Coleta o estado interno do manager num dicionário serializável."""
        agent_recent_rewards_list = {
            agent_id: list(rewards)
            for agent_id, rewards in self.agent_recent_rewards.items()
        }
        agent_maturity_names = {
            agent_id: maturity.name
            for agent_id, maturity in self.agent_maturity.items()
        }
        return {
            "agent_maturity": agent_maturity_names,
            "agent_episodes_in_phase": self.agent_episodes_in_phase,
            "agent_recent_rewards": agent_recent_rewards_list,
            "is_calibrated": self.is_calibrated,
            "teen_entropy_threshold": self.teen_entropy_threshold,
            "adult_entropy_threshold": self.adult_entropy_threshold
        }

    def save_state(self, filepath: str):
        """Salva o estado atual do MaturityManager em um arquivo JSON."""
        lm = self.locale_manager
        state = self.get_state()
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=4)
            # --- MUDANÇA 1 ---
            logging.info(lm.get_string("maturity_manager.save.success", path=filepath))
        except IOError as e:
            # --- MUDANÇA 2 ---
            logging.error(lm.get_string("maturity_manager.save.error", error=e))

    def load_state(self, filepath: str):
        """Carrega o estado do manager a partir de um arquivo JSON."""
        lm = self.locale_manager
        if not os.path.exists(filepath):
            # --- MUDANÇA 3 ---
            logging.warning(lm.get_string("maturity_manager.load.not_found", path=filepath))
            return
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                state = json.load(f)
            
            self.agent_maturity = {
                agent_id: Maturity[maturity_name]
                for agent_id, maturity_name in state.get("agent_maturity", {}).items()
            }
            self.agent_episodes_in_phase = state.get("agent_episodes_in_phase", {})
            self.agent_recent_rewards = {
                agent_id: deque(rewards, maxlen=self._rewards_window_size)
                for agent_id, rewards in state.get("agent_recent_rewards", {}).items()
            }
            self.is_calibrated = state.get("is_calibrated", False)
            self.teen_entropy_threshold = state.get("teen_entropy_threshold", float('inf'))
            self.adult_entropy_threshold = state.get("adult_entropy_threshold", float('inf'))
            
            # --- MUDANÇA 4 ---
            logging.info(lm.get_string("maturity_manager.load.success", path=filepath))
            
            self.register_agents(list(self.agent_maturity.keys()))

        except (json.JSONDecodeError, KeyError) as e:
            # --- MUDANÇA 5 ---
            logging.error(lm.get_string("maturity_manager.load.error", error=e), exc_info=True)

    def register_agents(self, agent_ids: list):
        lm = self.locale_manager
        new_agents_registered = 0
        for agent_id in agent_ids:
            if agent_id not in self.agent_maturity:
                self.agent_maturity[agent_id] = Maturity.CHILD
                self.agent_episodes_in_phase[agent_id] = 0
                self.agent_recent_rewards[agent_id] = deque(maxlen=self._rewards_window_size)
                new_agents_registered += 1
        
        if new_agents_registered > 0:
            phase_name = lm.get_string("maturity_manager.phase_child")
            logging.info(lm.get_string("maturity_manager.register.agents_registered", count=new_agents_registered, phase=phase_name.upper()))

    def update_calibration_thresholds(self, teen_threshold: float, adult_threshold: float):
        self.teen_entropy_threshold = teen_threshold
        self.adult_entropy_threshold = adult_threshold
        self.is_calibrated = True
        logging.info(self.locale_manager.get_string("maturity_manager.calibration.thresholds_updated"))

    def check_and_promote_agents(self, agent_metrics: dict) -> bool:
        """
        Verifica e promove agentes. Retorna True se alguma promoção ocorreu.
        """
        lm = self.locale_manager
        promotion_happened = False

        for agent_id, metrics in agent_metrics.items():
            if agent_id not in self.agent_maturity: continue
            
            self.agent_episodes_in_phase[agent_id] += 1
            self.agent_recent_rewards[agent_id].append(metrics.get('reward', 0))
            
            current_phase = self.agent_maturity[agent_id]
            episodes_in_phase = self.agent_episodes_in_phase[agent_id]
            agent_entropy = metrics.get('entropy', float('inf'))

            if current_phase == Maturity.CHILD:
                if episodes_in_phase >= self.child_phase_duration:
                    confidence_ok = agent_entropy < self.child_promotion_max_entropy
                    if confidence_ok:
                        details = { 
                            lm.get_string("maturity_manager.criterion_time"): lm.get_string("maturity_manager.time_details", episodes_in_phase=episodes_in_phase, required_episodes=self.child_phase_duration),
                            lm.get_string("maturity_manager.criterion_confidence"): lm.get_string("maturity_manager.confidence_details", agent_entropy=agent_entropy, entropy_threshold=self.child_promotion_max_entropy)
                        }
                        self._promote_agent(agent_id, Maturity.TEEN)
                        self.reporter.report_promotion(agent_id, Maturity.TEEN, details)
                        promotion_happened = True
                    else:
                        rejection_details = {
                            lm.get_string("maturity_manager.criterion_time"): {"ok": True, "msg": lm.get_string("maturity_manager.time_details", episodes_in_phase=episodes_in_phase, required_episodes=self.child_phase_duration)},
                            lm.get_string("maturity_manager.criterion_confidence"): {"ok": False, "msg": lm.get_string("maturity_manager.confidence_details", agent_entropy=agent_entropy, entropy_threshold=self.child_promotion_max_entropy)}
                        }
                        self.reporter.report_rejection(agent_id, current_phase, Maturity.TEEN, rejection_details)

            elif current_phase == Maturity.TEEN:
                time_ok = episodes_in_phase >= self.teen_phase_min_duration
                if not time_ok: continue

                confidence_ok = not self.is_calibrated or agent_entropy < self.adult_entropy_threshold
                performance_ok = False
                mean_performance = 0
                rewards_buffer = self.agent_recent_rewards[agent_id]
                if len(rewards_buffer) >= self._rewards_window_size:
                    mean_performance = np.mean(list(rewards_buffer))
                    if mean_performance > self.baseline_target:
                        performance_ok = True

                if confidence_ok and performance_ok:
                    details = {
                        lm.get_string("maturity_manager.criterion_time"): lm.get_string("maturity_manager.time_details", episodes_in_phase=episodes_in_phase, required_episodes=self.teen_phase_min_duration),
                        lm.get_string("maturity_manager.criterion_performance"): lm.get_string("maturity_manager.performance_details", mean_performance=mean_performance, baseline_target=self.baseline_target),
                        lm.get_string("maturity_manager.criterion_confidence"): lm.get_string("maturity_manager.confidence_details", agent_entropy=agent_entropy, entropy_threshold=self.adult_entropy_threshold)
                    }
                    self._promote_agent(agent_id, Maturity.ADULT)
                    self.reporter.report_promotion(agent_id, Maturity.ADULT, details)
                    promotion_happened = True
                elif episodes_in_phase % self.teen_phase_min_duration == 0:
                    rejection_details = {
                        lm.get_string("maturity_manager.criterion_time"): {"ok": True, "msg": lm.get_string("maturity_manager.time_details", episodes_in_phase=episodes_in_phase, required_episodes=self.teen_phase_min_duration)},
                        lm.get_string("maturity_manager.criterion_performance"): {"ok": performance_ok, "msg": lm.get_string("maturity_manager.performance_details", mean_performance=mean_performance, baseline_target=self.baseline_target)},
                        lm.get_string("maturity_manager.criterion_confidence"): {"ok": confidence_ok, "msg": lm.get_string("maturity_manager.confidence_details", agent_entropy=agent_entropy, entropy_threshold=self.adult_entropy_threshold)}
                    }
                    self.reporter.report_rejection(agent_id, current_phase, Maturity.ADULT, rejection_details)
        
        return promotion_happened

    def _promote_agent(self, agent_id: str, new_phase: Maturity):
        """Atualiza o estado interno de um agente para a sua nova fase."""
        self.agent_maturity[agent_id] = new_phase
        self.agent_episodes_in_phase[agent_id] = 0