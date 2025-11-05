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

# File: src/memory/replay_memory.py (NOVO FICHEIRO)
# Author: Gabriel Moraes
# Date: 19 de Agosto de 2025

"""
Define a classe ReplayMemory e a sua estrutura de dados Transition.

Este módulo, extraído de 'guardian_agent.py', implementa um buffer de
memória de replay, uma estrutura de dados crucial para algoritmos de
aprendizagem por reforço "off-policy" como o DQN. Ele armazena as
experiências do agente e permite a amostragem de lotes aleatórios para
quebrar a correlação temporal entre as amostras, estabilizando o
processo de treino.
"""
import random
from collections import namedtuple, deque

# Define a estrutura de uma única transição (uma experiência)
# Facilita o acesso aos campos por nome, ex: transition.state
Transition = namedtuple('Transition', ('state', 'action', 'next_state', 'reward'))

class ReplayMemory:
    """Buffer de memória para armazenar e amostrar transições de forma eficiente."""
    def __init__(self, capacity: int):
        """
        Inicializa o buffer de memória com uma capacidade máxima.

        Args:
            capacity (int): O número máximo de transições a serem armazenadas.
        """
        # Usar um deque é eficiente, pois ele descarta automaticamente
        # os itens mais antigos quando a capacidade máxima é atingida.
        self.memory = deque([], maxlen=capacity)

    def push(self, *args):
        """
        Salva uma nova transição na memória.

        Args:
            *args: Os dados da transição, na ordem definida pela namedtuple Transition
                   (state, action, next_state, reward).
        """
        self.memory.append(Transition(*args))

    def sample(self, batch_size: int) -> list:
        """
        Seleciona um lote aleatório de transições da memória.

        Args:
            batch_size (int): O número de transições a serem amostradas.

        Returns:
            list: Uma lista de transições amostradas aleatoriamente.
        """
        return random.sample(self.memory, batch_size)

    def __len__(self) -> int:
        """Retorna o número atual de transições armazenadas na memória."""
        return len(self.memory)