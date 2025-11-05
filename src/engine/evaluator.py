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

# File: src/core/evaluator.py (NOVO ARQUIVO)
# Author: [Seu Nome]
# Date: 25 de Julho de 2025

"""
Define a classe ValidationEvaluator, responsável por avaliar a performance
de um agente em um ambiente, sem que o agente aprenda durante a avaliação.
"""
import torch
import logging
from collections import deque
import numpy as np

class ValidationEvaluator:
    """
    Executa episódios de validação para medir a performance de generalização dos agentes.
    """
    def __init__(self, settings):
        """
        Inicializa o Avaliador.
        :param settings: As configurações globais do projeto.
        """
        self.settings = settings
        self.sequence_length = self.settings.getint('AI_TRAINING', 'sequence_length', fallback=4)
        self.state_history = {}
        logging.info("[EVAL] Módulo ValidationEvaluator criado.")

    def _initialize_state_history(self, initial_states):
        """Preenche o histórico com estados zerados para formar a primeira sequência."""
        self.state_history.clear()
        for tl_id, state in initial_states.items():
            if state:
                history = deque(maxlen=self.sequence_length)
                zero_state = np.zeros_like(state)
                for _ in range(self.sequence_length):
                    history.append(zero_state)
                self.state_history[tl_id] = history

    def evaluate(self, agents: dict, env, num_episodes: int) -> float:
        """
        Roda um número de episódios de validação e retorna a recompensa média.
        :param agents: O dicionário de agentes a serem avaliados.
        :param env: A instância do ambiente SUMO a ser usada para a validação.
        :param num_episodes: O número de episódios a serem executados.
        :return: A recompensa total média por episódio.
        """
        logging.info(f"[EVAL] Iniciando ciclo de validação para {num_episodes} episódio(s).")

        # IMPORTANTE: Coloca as redes em modo de avaliação (desliga dropout, etc.)
        for agent in agents.values():
            agent.actor.eval()
            agent.critic.eval()

        cycle_rewards = []

        for i_episode in range(num_episodes):
            env.reset()
            current_states = env.get_global_state()
            self._initialize_state_history(current_states)
            
            episode_reward = 0
            step = 0
            done = False

            while not done:
                if env.conn and env.conn.simulation.getMinExpectedNumber() > 0:
                    actions_to_apply = {}
                    for tl_id, agent in agents.items():
                        state = current_states.get(tl_id, [])
                        if not state: continue
                        
                        if tl_id in self.state_history:
                            self.state_history[tl_id].append(state)
                            state_sequence = list(self.state_history[tl_id])
                            
                            # Agente escolhe a ação sem explorar, usando seu conhecimento atual
                            action, _, _ = agent.choose_action(state_sequence)
                            actions_to_apply[tl_id] = action.item()

                    next_states, rewards, done = env.step(actions=actions_to_apply)
                    
                    # Acumula a recompensa do passo
                    episode_reward += sum(rewards.values())
                    current_states = next_states
                    step += 1
                else:
                    if env.conn and env.conn.simulation.getMinExpectedNumber() <= 0 and step > 0:
                        done = True
            
            cycle_rewards.append(episode_reward)
            logging.info(f"[EVAL] Episódio de validação {i_episode+1}/{num_episodes} finalizado. Recompensa: {episode_reward:.2f}")

        # IMPORTANTE: Coloca as redes de volta em modo de treinamento
        for agent in agents.values():
            agent.actor.train()
            agent.critic.train()

        # Calcula a média das recompensas de todos os episódios do ciclo
        average_reward = np.mean(cycle_rewards) if cycle_rewards else 0
        logging.info(f"[EVAL] Ciclo de validação concluído. Recompensa média: {average_reward:.2f}")

        return average_reward