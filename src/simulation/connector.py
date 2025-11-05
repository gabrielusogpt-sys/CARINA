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

# File: src/simulation/connector.py (MODIFICADO PARA LOGGING E TRADUÇÃO)
# Author: Gabriel Moraes
# Date: 02 de Outubro de 2025

"""
Define o SumoConnector, adaptado para a nova arquitetura baseada em Proxy.

Nesta versão, a classe foi modificada para receber o LocaleManager e usar
o sistema de logging em vez de 'print()', permitindo a tradução de suas mensagens.
"""
import sys
import os
import logging
from typing import TYPE_CHECKING

# A importação do traci aqui será interceptada pelo "monkey patch" no main.py
# e na verdade importará o nosso traci_proxy.
import traci

if TYPE_CHECKING:
    from utils.locale_manager_backend import LocaleManagerBackend

class SumoConnector:
    """Gerencia a "conexão" com o Proxy TraCI."""

    def __init__(self, port: int, locale_manager: 'LocaleManagerBackend'):
        """
        O construtor agora recebe a porta e o gerenciador de traduções.
        """
        self.port = port
        self.conn = None
        self.locale_manager = locale_manager

    def connect(self):
        """
        No mundo do Proxy, "conectar" significa apenas apontar para o proxy.
        """
        lm = self.locale_manager
        logging.info(lm.get_string("connector.connecting"))
        
        # A "conexão" agora é simplesmente a referência ao nosso módulo proxy.
        self.conn = traci
        
        # As chamadas de connect() e setOrder() no proxy são falsas e não fazem
        # nada, mas as chamamos para manter a estrutura do log.
        self.conn.connect(self.port)
        self.conn.setOrder(1)
        
        logging.info(lm.get_string("connector.connection_established"))

    def simulation_step(self):
        """Avança a simulação em um passo através do proxy."""
        if self.conn:
            # Esta chamada será interceptada pelo proxy e enviada para a Central.
            self.conn.simulationStep()

    def close(self):
        """Fecha a "conexão" com o proxy."""
        if self.conn:
            # Esta chamada será interceptada e ignorada pelo proxy.
            self.conn.close()
        self.conn = None