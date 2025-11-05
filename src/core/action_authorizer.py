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

# File: src/core/action_authorizer.py (MODIFICADO PARA REFATORAÇÃO DE CHAVES)
# Author: Gabriel Moraes
# Date: 03 de Outubro de 2025

import sys
import os
from typing import TYPE_CHECKING

# Adiciona o diretório 'src' ao path para permitir importações absolutas
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from core.enums import Maturity
if TYPE_CHECKING:
    from utils.locale_manager_backend import LocaleManagerBackend


class ActionAuthorizer:
    """O "Porteiro" da Escola de Pilotagem, especialista em autorizar ações."""

    def __init__(self, traffic_profiles: dict, locale_manager: 'LocaleManagerBackend'):
        """
        Inicializa o autorizador.
        """
        self.traffic_profiles = traffic_profiles
        self.locale_manager = locale_manager

    def is_action_authorized(self, agent_id: str, maturity: Maturity, sim_time: float) -> tuple[bool, str]:
        """
        Verifica se um agente está autorizado a atuar com base na sua maturidade e no tempo.
        """
        lm = self.locale_manager
        
        # --- MUDANÇAS APLICADAS AQUI ---
        if maturity == Maturity.CHILD: 
            return False, lm.get_string("action_authorizer.reason.child")
        
        if maturity == Maturity.ADULT: 
            return True, lm.get_string("action_authorizer.reason.adult")
        
        if maturity == Maturity.TEEN:
            day_index = int(sim_time // 86400) % 7
            hour_of_day = str(int((sim_time % 86400) // 3600))
            
            profile_for_day = self.traffic_profiles.get(day_index, {})
            traffic_level = profile_for_day.get(hour_of_day, "low")
            
            if traffic_level == "peak": 
                return False, lm.get_string("action_authorizer.reason.teen_peak")
            
            return True, lm.get_string("action_authorizer.reason.teen_offpeak")
            
        return False, lm.get_string("action_authorizer.reason.unknown")