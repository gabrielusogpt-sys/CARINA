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

# File: src/models/actor_critic_lstm.py (NOVO ARQUIVO)
# Author: Gabriel Moraes
# Date: 19 de Agosto de 2025

"""
Define a arquitetura de rede Actor-Critic com uma base LSTM.

Esta classe, extraída de 'local_agent.py', isola a definição do
modelo de Pytorch, permitindo que a lógica do agente e a arquitetura
da rede sejam mantidas e modificadas de forma independente.
"""
import torch
import torch.nn as nn
from torch.distributions import Categorical

class ActorCriticNet(nn.Module):
    """
    Uma rede neural que combina uma base LSTM com duas cabeças:
    uma para o Ator (política) e outra para o Crítico (valor do estado).
    """
    def __init__(self, n_observations, n_actions, hidden_size=128, dropout_p=0.1):
        """
        Inicializa a rede Actor-Critic.

        Args:
            n_observations (int): O tamanho do vetor de observação de entrada.
            n_actions (int): O número de ações possíveis de saída.
            hidden_size (int): O número de neurônios na camada oculta (e na LSTM).
            dropout_p (float): A probabilidade de dropout a ser aplicada.
        """
        super(ActorCriticNet, self).__init__()

        # Base compartilhada que processa a sequência de estados
        self.shared_base = nn.Sequential(
            nn.LSTM(input_size=n_observations, hidden_size=hidden_size, batch_first=True)
        )
        
        # Camada de processamento após a LSTM
        self.post_lstm_layer = nn.Sequential(
            nn.Linear(hidden_size, hidden_size),
            nn.LayerNorm(hidden_size),
            nn.ReLU(),
            nn.Dropout(dropout_p)
        )
        
        # Cabeça do Ator: Determina a probabilidade de cada ação (a política)
        self.actor_head = nn.Sequential(
            nn.Linear(hidden_size, n_actions),
            nn.Softmax(dim=-1)
        )
        
        # Cabeça do Crítico: Estima o valor do estado atual
        self.critic_head = nn.Sequential(
            nn.Linear(hidden_size, 1)
        )

    def forward(self, state_sequence: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        """
        Executa a passagem para frente da rede.

        Args:
            state_sequence (torch.Tensor): Um tensor com o lote de sequências de estado.
                                           Shape: [batch_size, sequence_length, n_observations]

        Returns:
            tuple[torch.Tensor, torch.Tensor]: Uma tupla contendo as probabilidades de ação
                                               e o valor do estado estimado.
        """
        # A LSTM retorna a saída de todos os passos de tempo e o último estado oculto/célula
        lstm_out, _ = self.shared_base(state_sequence)
        
        # Usamos apenas a saída do último passo de tempo da sequência para a decisão
        last_time_step_out = lstm_out[:, -1, :]
        
        # Passa pela camada de processamento
        x = self.post_lstm_layer(last_time_step_out)
        
        # Calcula a saída das duas cabeças
        action_probs = self.actor_head(x)
        state_value = self.critic_head(x)
        
        return action_probs, state_value