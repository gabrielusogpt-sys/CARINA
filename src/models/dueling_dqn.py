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

# File: src/models/dueling_dqn.py (NOVO ARQUIVO)
# Author: Gabriel Moraes
# Date: 19 de Agosto de 2025

"""
Define a arquitetura de rede Dueling Deep Q-Network (DQN).

Esta classe, extraída de 'guardian_agent.py', isola a definição do
modelo de Pytorch. A arquitetura Dueling é uma melhoria do DQN padrão
que separa a estimativa do valor do estado e da vantagem de cada ação,
o que pode levar a um aprendizado mais estável e eficiente.
"""
import torch
import torch.nn as nn

class DuelingDQN(nn.Module):
    """Arquitetura de rede Dueling DQN para o Agente Guardião."""
    def __init__(self, n_observations=2, n_actions=3, hidden_size=64):
        """
        Inicializa a rede Dueling DQN.

        Args:
            n_observations (int): O tamanho do vetor de estado de entrada.
            n_actions (int): O número de ações possíveis de saída.
            hidden_size (int): O número de neurônios nas camadas ocultas.
        """
        super(DuelingDQN, self).__init__()
        
        # Camada comum que extrai características do estado
        self.feature_layer = nn.Sequential(
            nn.Linear(n_observations, hidden_size),
            nn.ReLU()
        )
        
        # Fluxo de Vantagem (Advantage Stream): Estima a vantagem de cada ação
        # em relação à média das ações para o estado atual.
        self.advantage_stream = nn.Sequential(
            nn.Linear(hidden_size, hidden_size),
            nn.ReLU(),
            nn.Linear(hidden_size, n_actions)
        )
        
        # Fluxo de Valor (Value Stream): Estima o valor do estado (V(s)).
        self.value_stream = nn.Sequential(
            nn.Linear(hidden_size, hidden_size),
            nn.ReLU(),
            nn.Linear(hidden_size, 1)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Executa a passagem para frente da rede.

        Args:
            x (torch.Tensor): O tensor de estado de entrada.

        Returns:
            torch.Tensor: Os valores Q (Q-values) para cada ação.
        """
        features = self.feature_layer(x)
        
        advantages = self.advantage_stream(features)
        value = self.value_stream(features)
        
        # Combina os fluxos de valor e vantagem para obter os Q-values finais
        # Q(s, a) = V(s) + (A(s, a) - mean(A(s, a')))
        q_values = value + (advantages - advantages.mean(dim=1, keepdim=True))
        
        return q_values