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

# File: src/core/system_reporter.py (MODIFICADO PARA LOGGAR O MODO DE OPERAÇÃO)
# Author: Gabriel Moraes
# Date: 11 de Outubro de 2025

import logging
from collections import Counter
from typing import TYPE_CHECKING
import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from core.enums import Maturity

if TYPE_CHECKING:
    from utils.locale_manager_backend import LocaleManagerBackend
    
class SystemReporter:
    """Uma classe com métodos estáticos para gerar logs consistentes e estruturados."""

    # --- MUDANÇA PRINCIPAL AQUI: Adicionar 'operation_mode' ao método ---
    @staticmethod
    def report_step_start(lm: 'LocaleManagerBackend', step: int, sim_time: float, operation_mode: str):
        """Loga um cabeçalho claro para o início de um novo passo de simulação."""
        step_message = lm.get_string("reporter.step_start", step=step, sim_time=f"{sim_time:.1f}")
        header = lm.get_string("reporter.step_header", message=step_message)
        
        # Traduz o nome do modo de operação para uma exibição amigável
        mode_key = f"global_modes.{operation_mode.lower()}"
        translated_mode = lm.get_string(mode_key, fallback=operation_mode)
        mode_message = lm.get_string("reporter.step_mode", mode=translated_mode)
        
        # Junta o cabeçalho com a nova informação de modo
        final_log_message = f"\n{header}\n{mode_message}"
        logging.info(final_log_message)

    @staticmethod
    def report_agent_creation(tl_id: str, amp_enabled: bool, lm: 'LocaleManagerBackend'):
        """Loga a criação bem-sucedida de um agente local e seu guardião."""
        logging.info(lm.get_string("reporter.creation.agent_created", tl_id=tl_id))
        logging.info(lm.get_string("reporter.creation.amp_status", enabled=amp_enabled))

    @staticmethod
    def report_graph_structure(num_nodes: int, num_edges: int, lm: 'LocaleManagerBackend'):
        """Loga a estrutura do grafo da rede após a análise."""
        separator = "-" * 60
        logging.info(separator)
        logging.info(lm.get_string("reporter.graph.title"))
        logging.info(lm.get_string("reporter.graph.nodes", count=num_nodes))
        logging.info(lm.get_string("reporter.graph.edges", count=num_edges))
        logging.info(separator)

    @staticmethod
    def report_agent_decision(lm: 'LocaleManagerBackend', tl_id: str, maturity_level: str, action_str: str, is_authorized: bool, reason: str, override_state: str):
        """Loga a decisão, anexando o estado de override se aplicável."""
        
        agent_suggestion = lm.get_string("reporter.agent_suggestion", tl_id=tl_id, maturity_level=maturity_level, action_str=action_str)
        logging.info(agent_suggestion)

        status = lm.get_string("reporter.status_approved") if is_authorized else lm.get_string("reporter.status_denied")
        system_decision = lm.get_string("reporter.system_decision", status=status, reason=reason)
        
        override_suffix = ""
        if override_state == "ALERT":
            override_suffix = " " + lm.get_string("reporter.override_suffix_alert")
        elif override_state == "OFF":
            override_suffix = " " + lm.get_string("reporter.override_suffix_off")
        
        final_system_decision = f"{system_decision}{override_suffix}"
        
        if is_authorized:
            logging.info(final_system_decision)
        else:
            logging.warning(final_system_decision)

    @staticmethod
    def report_school_bulletin(lm: 'LocaleManagerBackend', episode_count: int, total_reward: float, maturity_counts: Counter, calibration_status: str):
        """Loga o 'Boletim da Escola' ao final de cada episódio."""
        children = maturity_counts[Maturity.CHILD]
        teens = maturity_counts[Maturity.TEEN]
        adults = maturity_counts[Maturity.ADULT]
        
        calib_key = "reporter.calib_status_done" if "Concluída" in calibration_status or "Completed" in calibration_status else "reporter.calib_status_ongoing"
        calib_text = lm.get_string(calib_key)
        
        separator = "-" * 80
        logging.info(separator)
        logging.info(lm.get_string("reporter.bulletin_header", episode_count=episode_count))
        logging.info(lm.get_string("reporter.bulletin_performance", total_reward=f"{total_reward:.2f}"))
        logging.info(lm.get_string("reporter.bulletin_class_status", adults=adults, teens=teens, children=children))
        logging.info(lm.get_string("reporter.bulletin_calibration_status", status=calib_text))
        logging.info(separator)