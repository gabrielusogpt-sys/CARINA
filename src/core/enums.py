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

# File: src/core/enums.py (NOVO ARQUIVO)
# Author: Gabriel Moraes
# Date: 02 de Outubro de 2025

"""
Define enumerações (Enums) compartilhadas para o núcleo do sistema.

Este arquivo foi criado para resolver uma dependência circular, isolando
a definição do Enum 'Maturity' em um módulo simples e sem dependências.
"""

from enum import Enum, auto

class Maturity(Enum):
    """Define as fases de maturidade de um agente."""
    CHILD = auto()
    TEEN = auto()
    ADULT = auto()