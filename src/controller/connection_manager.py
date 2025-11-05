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

# File: src/controller/connection_manager.py (Corrigido tipo de retorno para Pylance)
# Author: Gabriel Moraes
# Date: 26 de Outubro de 2025

import sys
import logging
import os
from typing import TYPE_CHECKING, Any # Importar Any como alternativa

# Adiciona o diretório 'src' ao path (mantido)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

if TYPE_CHECKING:
    from utils.locale_manager_backend import LocaleManagerBackend

# Instância de emergência para o bloco de importação e logs críticos
from utils.locale_manager_backend import LocaleManagerBackend
lm_emergency = LocaleManagerBackend()

# --- Bloco de importação robusto para TraCI (Mantido) ---
try:
    import traci
    from traci.exceptions import TraCIException
    logging.info(lm_emergency.get_string("connection_manager.import.traci_loaded", path=traci.__file__))
except (ImportError, ModuleNotFoundError) as e_traci:
    SUMO_TOOLS_PATH = os.environ.get("SUMO_HOME")
    if SUMO_TOOLS_PATH:
        tools_path = os.path.join(SUMO_TOOLS_PATH, "tools")
        if tools_path not in sys.path:
            sys.path.append(tools_path)
            logging.info(lm_emergency.get_string("connection_manager.import.sumo_tools_path", path=tools_path))
        try:
            import traci
            from traci.exceptions import TraCIException
            logging.info(f"TraCI importado com sucesso via SUMO_HOME: {tools_path}")
        except (ImportError, ModuleNotFoundError) as e_sumohome:
            logging.critical(lm_emergency.get_string("connection_manager.import.traci_critical_fail") + f" (Erro: {e_sumohome})")
            class TraCIException(Exception): pass
            raise e_sumohome
    else:
        logging.critical(lm_emergency.get_string("connection_manager.import.traci_critical_fail") + f" (SUMO_HOME não definido, Erro: {e_traci})")
        class TraCIException(Exception): pass
        raise e_traci
# --- Fim do Bloco ---


class SumoConnectionManager:
    """Gerencia a conexão e o encerramento com o servidor TraCI do SUMO."""

    def __init__(self, traci_port: int, locale_manager: 'LocaleManagerBackend', num_retries: int = 60):
        self.port = traci_port
        self.num_retries = num_retries
        # --- MUDANÇA 1: Anotar self.conn com string literal ou Any ---
        # self.conn: 'traci.connection' | None = None # Opção 1: String literal
        self.conn: Any | None = None                 # Opção 2: Usar Any (mais simples)
        # --- Fim ---
        self.locale_manager = locale_manager
        logging.info(self.locale_manager.get_string("connection_manager.init.manager_created"))

    # --- MUDANÇA 2: Corrigir anotação de retorno da função connect ---
    # def connect(self) -> 'traci.connection': # Opção 1: String literal
    def connect(self) -> Any:                 # Opção 2: Usar Any
    # --- Fim ---
        """
        Estabelece a conexão com SUMO e registra o nome do cenário carregado.
        Retorna a conexão ou lança uma exceção em caso de falha.
        """
        lm = self.locale_manager
        separator = "=" * 60
        logging.info(separator)
        logging.info(lm.get_string("connection_manager.connect.waiting_for_sumo", port=self.port))
        logging.info(lm.get_string("connection_manager.connect.open_sumocfg_prompt"))
        logging.info(separator)

        try:
            self.conn = traci.connect(self.port, numRetries=self.num_retries)
            self.conn.setOrder(0)

            scenario_path = self.conn.simulation.getOption('configuration-file')
            scenario_name = os.path.basename(scenario_path)

            logging.info(separator)
            logging.info(lm.get_string("connection_manager.connect.success"))
            logging.info(lm.get_string("connection_manager.connect.scenario_loaded", scenario=scenario_name))
            logging.info(separator)

            return self.conn

        except TraCIException as e:
            logging.error(lm.get_string("connection_manager.connect.fatal_error"), exc_info=True)
            raise e
        except Exception as e_general:
             logging.error(f"[ConnectionManager] Erro inesperado durante a conexão: {e_general}", exc_info=True)
             raise RuntimeError(f"Erro inesperado na conexão TraCI: {e_general}") from e_general

    def close(self):
        """Encerra a conexão com o SUMO de forma limpa e robusta."""
        lm = self.locale_manager
        if self.conn:
            try:
                logging.info(lm.get_string("connection_manager.close.closing"))
                self.conn.close()
            except TraCIException:
                logging.warning(lm.get_string("connection_manager.close.already_lost"))
                pass
            except Exception as e_general:
                 logging.warning(f"[ConnectionManager] Erro inesperado ao fechar conexão: {e_general}")
            finally:
                self.conn = None
        else:
            logging.info(lm.get_string("connection_manager.close.no_connection"))