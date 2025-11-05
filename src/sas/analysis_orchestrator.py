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

# File: src/sas/analysis_orchestrator.py (MODIFICADO PARA TRADUÇÃO COMPLETA E REGRAS)
# Author: Gabriel Moraes
# Date: 03 de Outubro de 2025

import logging
from multiprocessing import Queue
import configparser
import sys
import os
from typing import TYPE_CHECKING

# Adiciona o diretório 'src' ao path para permitir importações absolutas
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from sas.data_collector import DataCollector
from sas.analyzer_engine import AnalyzerEngine

if TYPE_CHECKING:
    from utils.locale_manager_backend import LocaleManagerBackend

class AnalysisOrchestrator:
    """O maestro que gerencia o fluxo de trabalho do serviço SAS."""

    def __init__(self, sas_data_queue: Queue, settings: configparser.ConfigParser, db_data_queue: Queue, locale_manager: 'LocaleManagerBackend'):
        self.data_queue = sas_data_queue
        self.settings = settings
        self.locale_manager = locale_manager
        lm = self.locale_manager
        
        self.collector = DataCollector(self.locale_manager)
        self.engine = AnalyzerEngine(self.settings, db_data_queue, self.locale_manager)
        
        try:
            section_name = 'INFRASTRUCTURE_ANALYSIS'
            analysis_section = self.settings[section_name]
            
            self.frequency = analysis_section.getint('analysis_frequency_seconds')
            self.initial_delay = analysis_section.getint('initial_analysis_delay_seconds')
            logging.info(lm.get_string("sas_orchestrator.init.analysis_frequency_set", freq=self.frequency))

        except (KeyError, configparser.NoSectionError):
            logging.error(lm.get_string("sas_orchestrator.init.config_error"))
            self.frequency = 86400
            self.initial_delay = 3600
            
        self.last_analysis_time = 0

        logging.info(lm.get_string("sas_orchestrator.init.orchestrator_created"))

    def run(self):
        """
        Inicia o serviço e entra no loop principal de coleta e análise.
        """
        current_run_id = None
        lm = self.locale_manager
        try:
            # --- MUDANÇAS APLICADAS A PARTIR DAQUI ---
            logging.info(lm.get_string("sas_orchestrator.run.main_loop_start"))
            while True:
                raw_sim_data = self.data_queue.get()

                if raw_sim_data is None:
                    break

                if current_run_id is None and isinstance(raw_sim_data.get("run_id"), int):
                    current_run_id = raw_sim_data["run_id"]
                    logging.info(lm.get_string("sas_orchestrator.run.run_id_captured", run_id=current_run_id))

                self.collector.collect(raw_sim_data)

                current_sim_time = raw_sim_data.get('sim_time', 0)
                
                is_past_initial_delay = current_sim_time >= self.initial_delay
                is_time_for_analysis = (current_sim_time - self.last_analysis_time) >= self.frequency

                if is_past_initial_delay and is_time_for_analysis:
                    logging.info(lm.get_string("sas_orchestrator.run.analysis_triggered", time=current_sim_time))

                    accumulated_data = self.collector.get_accumulated_data()
                    
                    if accumulated_data and current_run_id is not None:
                        scenario_name = raw_sim_data.get('scenario_name', 'default_scenario')
                        net_file_path = raw_sim_data.get('net_file')
                        
                        self.engine.run_analysis(
                            accumulated_data=accumulated_data, 
                            sim_duration=current_sim_time, 
                            scenario_name=scenario_name,
                            net_file_path=net_file_path,
                            run_id=current_run_id
                        )
                    elif current_run_id is None:
                        logging.warning(lm.get_string("sas_orchestrator.run.analysis_skipped_no_run_id"))
                    
                    self.last_analysis_time = current_sim_time
                    self.collector.reset()
                    logging.info(lm.get_string("sas_orchestrator.run.analysis_cycle_complete"))

        except KeyboardInterrupt:
            logging.info(lm.get_string("sas_orchestrator.run.interrupt_received"))
        except Exception as e:
            logging.error(lm.get_string("sas_orchestrator.run.fatal_error", error=e), exc_info=True)
        finally:
            logging.info(lm.get_string("sas_orchestrator.run.orchestrator_shutdown"))