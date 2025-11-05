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

# File: src/central_controller.py (CORREÇÃO DE CAMINHO E DIAGNÓSTICO)
# Author: Gabriel Moraes
# Date: 12 de Outubro de 2025

import logging
import configparser
import time
import sys
import os
import json
from multiprocessing import Queue
from multiprocessing.connection import Connection
from typing import TYPE_CHECKING

# --- MUDANÇA 1: Corrigir o cálculo do caminho raiz do projeto ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

if TYPE_CHECKING:
    from utils.locale_manager_backend import LocaleManagerBackend

from controller.connection_manager import SumoConnectionManager
from traci.exceptions import TraCIException
from controller.health_monitor import AIHealthMonitor
from controller.request_processor import RequestProcessor
from controller.override_manager import OverrideManager

class CentralController:
    """O orquestrador que gerencia os componentes do controle central."""

    def __init__(self, settings: configparser.ConfigParser, ai_pipe_conn: Connection,
                 watchdog_queue: Queue, sds_data_queue: Queue, sas_data_queue: Queue,
                 ui_command_queue: Queue, locale_manager: 'LocaleManagerBackend'):
        self.settings = settings
        self.ai_pipe_conn = ai_pipe_conn
        self.locale_manager = locale_manager
        
        self.current_operation_mode = "AUTOMATIC"
        self.global_state_file_path: str | None = None
        
        self.override_manager = OverrideManager(locale_manager=self.locale_manager)
        
        self.connection_manager = SumoConnectionManager(
            traci_port=settings.getint('SUMO', 'traci_port'),
            locale_manager=self.locale_manager
        )
        
        heartbeat_timeout = settings.getfloat('WATCHDOG', 'heartbeat_timeout_seconds', fallback=15.0)
        
        self.health_monitor = AIHealthMonitor(
            heartbeat_timeout=heartbeat_timeout,
            locale_manager=self.locale_manager
        )
        
        self.request_processor = RequestProcessor(
            settings=settings,
            ai_pipe_conn=ai_pipe_conn,
            watchdog_q=watchdog_queue,
            health_monitor=self.health_monitor,
            sds_data_queue=sds_data_queue,
            sas_data_queue=sas_data_queue,
            ui_command_queue=ui_command_queue,
            locale_manager=self.locale_manager,
            override_manager=self.override_manager,
            controller_instance=self 
        )
        
        self.grace_period_seconds = settings.getint('WATCHDOG', 'initial_grace_period_seconds', fallback=15)
        self.sumo_conn = None

    def _load_global_state_from_disk(self):
        """Lê o arquivo de estado global, se ele existir."""
        if self.global_state_file_path and os.path.exists(self.global_state_file_path):
            try:
                with open(self.global_state_file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.current_operation_mode = data.get("operation_mode", "AUTOMATIC")
                logging.info(f"Modo de operação global carregado de {self.global_state_file_path}: '{self.current_operation_mode}'.")
            except (IOError, json.JSONDecodeError) as e:
                logging.error(f"Erro ao carregar o estado global: {e}")

    def _save_global_state_to_disk(self):
        """Salva o modo de operação atual no arquivo JSON."""
        if not self.global_state_file_path:
            # --- MUDANÇA 3: Adicionar log de erro explícito para falhas silenciosas ---
            logging.error("[CentralController] Falha ao salvar estado: o caminho do arquivo de estado global não foi definido.")
            return
        try:
            with open(self.global_state_file_path, "w", encoding="utf-8") as f:
                json.dump({"operation_mode": self.current_operation_mode}, f, indent=4)
        except IOError as e:
            logging.error(f"Erro ao salvar o estado global: {e}")

    def run(self):
        """O método principal que executa o ciclo de vida do controlador."""
        lm = self.locale_manager
        
        # --- MUDANÇA 2: Adicionar logs de diagnóstico ---
        logging.info(f"[DIAGNÓSTICO] Caminho raiz do projeto detectado: {project_root}")

        try:
            self.sumo_conn = self.connection_manager.connect()
            
            if self.sumo_conn:
                scenario_path = self.sumo_conn.simulation.getOption('configuration-file')
                scenario_filename = os.path.basename(scenario_path)
                scenario_name, _ = os.path.splitext(scenario_filename)
                
                scenario_dir = os.path.join(project_root, "results", scenario_name)
                logging.info(f"[DIAGNÓSTICO] Diretório do cenário definido como: {scenario_dir}")
                os.makedirs(scenario_dir, exist_ok=True)
                
                self.global_state_file_path = os.path.join(scenario_dir, "global_state.json")
                logging.info(f"[DIAGNÓSTICO] Caminho completo do arquivo de estado global: {self.global_state_file_path}")

                self._load_global_state_from_disk()

                self.override_manager.init_persistence(scenario_name)
                self.override_manager.restore_sumo_state(self.sumo_conn)
                
                self._save_global_state_to_disk()
            
            self._main_loop()

        except (TraCIException, KeyboardInterrupt):
            logging.info(lm.get_string("central_controller.run.simulation_ended"))

        except Exception as e:
            logging.error(lm.get_string("central_controller.run.fatal_error", error=e), exc_info=True)
        finally:
            logging.info(lm.get_string("central_controller.shutdown.sending_signal"))
            try:
                shutdown_signal = ("system", "shutdown", (), {})
                self.ai_pipe_conn.send(shutdown_signal)
            except Exception as e:
                logging.warning(lm.get_string("central_controller.shutdown.signal_error", error=e))

            self.connection_manager.close()
            logging.info(lm.get_string("central_controller.run.process_finished"))

    def _main_loop(self):
        """O loop principal que roteia comandos e avança a simulação."""
        lm = self.locale_manager
        logging.info(lm.get_string("central_controller.main_loop.starting"))
        
        grace_period_end_time = time.time() + self.grace_period_seconds
        
        while True:
            is_ai_healthy = True
            
            if time.time() > grace_period_end_time:
                is_ai_healthy = self.health_monitor.check_health()
            
            self.request_processor.process_queues(self.sumo_conn, is_ai_healthy)

            self.sumo_conn.simulationStep()