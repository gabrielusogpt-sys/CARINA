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

# File: src/core/learning_coordinator.py (MODIFICADO PARA TRADUÇÃO COMPLETA)
# Author: Gabriel Moraes
# Date: 03 de Outubro de 2025

import torch
import logging
from typing import TYPE_CHECKING

# --- MUDANÇA 1: Adicionar importações necessárias ---
if TYPE_CHECKING:
    from utils.locale_manager_backend import LocaleManagerBackend

class LearningCoordinator:
    """
    Encapsula a lógica do ciclo de Aprendizado por Reforço.
    """
    # --- MUDANÇA 2: Modificar o construtor ---
    def __init__(self, agents: dict, state_history: dict, locale_manager: 'LocaleManagerBackend'):
        """
        Inicializa o Coordenador de Aprendizado.
        """
        self.agents = agents
        self.state_history = state_history
        self.locale_manager = locale_manager
        # --- MUDANÇA 3 ---
        logging.info(self.locale_manager.get_string("learning_coordinator.init.created"))

    def store_experience(self, last_decision_data: dict, rewards: dict, done: bool):
        """
        Armazena a experiência de cada agente em seu respectivo buffer de memória.
        """
        for tl_id, agent in self.agents.items():
            if tl_id in last_decision_data:
                data = last_decision_data[tl_id]
                
                base_reward = rewards.get(tl_id, 0)
                policy_bonus = agent.current_reward_bonus
                final_reward = base_reward + policy_bonus
                
                agent.push_memory(
                    state_sequence=data['state_sequence'],
                    action=data['action'],
                    log_prob=data['log_prob'],
                    reward=final_reward,
                    done=done,
                    state_value=data['state_val']
                )

    def update_agents(self, last_states: dict, last_done: bool):
        """
        Comanda todos os agentes a aprenderem de suas memórias.
        """
        # --- MUDANÇA 4 ---
        logging.debug(self.locale_manager.get_string("learning_coordinator.update.trigger"))
        for tl_id, agent in self.agents.items():
            if len(agent.memory) > 0:
                agent.learn()