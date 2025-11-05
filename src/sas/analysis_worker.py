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

# File: src/sas/analysis_worker.py (CORRIGIDO PARA INICIALIZAÇÃO CORRETA DO LOGGING)
# Author: Gabriel Moraes
# Date: 05 de Outubro de 2025

import logging
import os
import sys
from multiprocessing import Queue
import configparser
import threading
import time
import psutil

# Adiciona o diretório 'src' ao path para permitir importações de outros módulos
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from sas.analysis_orchestrator import AnalysisOrchestrator
from utils.logging_setup import setup_logging
from utils.metrics_manager import MetricsManager
from utils.locale_manager_backend import LocaleManagerBackend

def run_analysis_worker(sas_data_queue: Queue, settings: configparser.ConfigParser, db_data_queue: Queue):
    """
    Ponto de entrada para o processo do Serviço de Análise de Simulação (SAS).
    """
    # --- CORREÇÃO APLICADA AQUI: A ordem de inicialização foi invertida ---
    
    # 1. Configura o logging PRIMEIRO.
    log_dir = os.path.join(project_root, "logs", "sas_worker")
    os.makedirs(log_dir, exist_ok=True)
    setup_logging(log_dir=log_dir)

    # 2. Com o logging ativo, cria o LocaleManager DEPOIS.
    locale_manager = LocaleManagerBackend()
    lm = locale_manager
    
    # --- FIM DA CORREÇÃO ---

    def monitor_loop(metrics: MetricsManager, process: psutil.Process, queues: dict, interval: int = 5):
        while True:
            metrics.update_metric('process_cpu_usage_percent', process.cpu_percent())
            metrics.update_metric('process_memory_usage_percent', process.memory_percent())
            metrics.update_metric('sas_data_queue_size', queues['sas_data'].qsize())
            time.sleep(interval)

    metrics_manager = MetricsManager(process_name="AnalysisService", port=8004)
    metrics_manager.register_metric('process_cpu_usage_percent', 'Uso de CPU do processo (%)')
    metrics_manager.register_metric('process_memory_usage_percent', 'Uso de Memória do processo (%)')
    metrics_manager.register_metric('sas_data_queue_size', 'Tamanho da fila de dados da simulação para o SAS')

    current_process = psutil.Process()
    monitor_thread = threading.Thread(
        target=monitor_loop,
        args=(metrics_manager, current_process, {'sas_data': sas_data_queue}),
        daemon=True
    )
    monitor_thread.start()

    try:
        # O setup_logging já foi movido para o topo
        
        orchestrator = AnalysisOrchestrator(
            sas_data_queue=sas_data_queue,
            settings=settings,
            db_data_queue=db_data_queue,
            locale_manager=locale_manager
        )
        
        orchestrator.run()

    except KeyboardInterrupt:
        logging.info(lm.get_string("sas_worker.run.user_interrupt"))
    except Exception as e:
        logging.critical(lm.get_string("sas_worker.run.fatal_error", error=e), exc_info=True)
    finally:
        logging.info(lm.get_string("sas_worker.run.worker_finished"))