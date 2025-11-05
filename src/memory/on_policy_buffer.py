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

# File: src/memory/on_policy_buffer.py (NOVO ARQUIVO)
# Author: Gabriel Moraes
# Date: 19 de Agosto de 2025

"""
Define a classe OnPolicyBuffer.

Esta classe, extraída de 'local_agent.py', implementa um buffer de
memória simples, projetado para algoritmos de aprendizado por reforço
"on-policy" como o PPO. Ele coleta um lote de transições e as converte
em tensores do PyTorch para o ciclo de aprendizado.
"""
import torch
import numpy as np

class OnPolicyBuffer:
    """Um buffer que armazena transições (estado, ação, etc.) para uma única coleta de dados."""
    
    def __init__(self):
        """Inicializa as listas que irão armazenar os dados da trajetória."""
        self.actions = []
        self.states = []
        self.log_probs = []
        self.rewards = []
        self.dones = []
        self.state_values = []

    def push(self, state_sequence, action, log_prob, reward, done, state_value):
        """
        Adiciona uma única transição ao buffer.

        Args:
            state_sequence: A sequência de estados que levou à decisão.
            action: A ação tomada pelo agente.
            log_prob: O log da probabilidade da ação tomada.
            reward (float): A recompensa recebida após a ação.
            done (bool): Se o episódio terminou após a ação.
            state_value: O valor do estado estimado pelo Crítico.
        """
        self.states.append(state_sequence)
        self.actions.append(action)
        self.log_probs.append(log_prob)
        self.rewards.append(reward)
        self.dones.append(done)
        self.state_values.append(state_value)

    def get_batch(self) -> tuple:
        """
        Converte os dados armazenados em tensores PyTorch e os retorna.
        Assume que as sequências de estado já têm tamanho uniforme.

        Returns:
            tuple: Uma tupla contendo os tensores de estados, ações, log_probs,
                   recompensas (lista), dones (lista) e valores de estado.
        """
        # A conversão para array numpy primeiro é eficiente
        states_np = np.array(self.states, dtype=np.float32)
        actions_np = np.array(self.actions, dtype=np.float32)
        log_probs_np = np.array(self.log_probs, dtype=np.float32)
        state_values_np = np.array(self.state_values, dtype=np.float32)
        
        # Converte para tensores PyTorch
        states_t = torch.from_numpy(states_np)
        actions_t = torch.from_numpy(actions_np)
        log_probs_t = torch.from_numpy(log_probs_np)
        state_values_t = torch.from_numpy(state_values_np)
        
        # O método squeeze() remove dimensões de tamanho 1, se houver
        return states_t, actions_t.squeeze(), log_probs_t.squeeze(), self.rewards, self.dones, state_values_t.squeeze()

    def clear(self):
        """Limpa o buffer. Deve ser chamado após cada ciclo de aprendizado."""
        del self.actions[:]
        del self.states[:]
        del self.log_probs[:]
        del self.rewards[:]
        del self.dones[:]
        del self.state_values[:]

    def __len__(self) -> int:
        """Retorna o número de transições armazenadas no buffer."""
        return len(self.states)