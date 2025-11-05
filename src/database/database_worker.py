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

# File: src/database/database_worker.py (CORRIGIDO PARA INICIALIZAÇÃO CORRETA DO LOGGING)
# Author: Gabriel Moraes
# Date: 05 de Outubro de 2025

import logging
import os
import sys
from multiprocessing import Queue
import threading
import time
import psutil

# Adiciona o diretório 'src' ao path para permitir importações de outros módulos
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from utils.logging_setup import setup_logging
from database.database_manager import DatabaseManager
from utils.metrics_manager import MetricsManager
from utils.locale_manager_backend import LocaleManagerBackend

def run_database_worker(db_queue: Queue):
    """
    Ponto de entrada para o processo do Database Worker.
    """
    # --- CORREÇÃO APLICADA AQUI: A ordem de inicialização foi invertida ---

    # 1. Configura o logging PRIMEIRO.
    log_dir = os.path.join(project_root, "logs", "db_worker")
    os.makedirs(log_dir, exist_ok=True)
    setup_logging(log_dir=log_dir)

    # 2. Com o logging ativo, cria o LocaleManager DEPOIS.
    lm = LocaleManagerBackend()

    # --- FIM DA CORREÇÃO ---

    def monitor_loop(metrics: MetricsManager, process: psutil.Process, queues: dict, interval: int = 5):
        """Coleta e atualiza métricas em um loop."""
        while True:
            metrics.update_metric('process_cpu_usage_percent', process.cpu_percent())
            metrics.update_metric('process_memory_usage_percent', process.memory_percent())
            metrics.update_metric('db_data_queue_size', queues['db_data'].qsize())
            time.sleep(interval)

    metrics_manager = MetricsManager(process_name="DatabaseWorker", port=8005)
    metrics_manager.register_metric('process_cpu_usage_percent', 'Uso de CPU do processo (%)')
    metrics_manager.register_metric('process_memory_usage_percent', 'Uso de Memória do processo (%)')
    metrics_manager.register_metric('db_data_queue_size', 'Tamanho da fila de dados para o DB Worker')

    current_process = psutil.Process()
    monitor_thread = threading.Thread(
        target=monitor_loop,
        args=(metrics_manager, current_process, {'db_data': db_queue}),
        daemon=True
    )
    monitor_thread.start()

    try:
        # O setup_logging já foi movido para o topo
        
        db_manager = DatabaseManager(locale_manager=lm)
        
        logging.info(lm.get_string("db_worker.run.worker_started"))

        while True:
            data_packet = db_queue.get()

            if data_packet is None:
                logging.info(lm.get_string("db_worker.run.shutdown_signal"))
                break

            try:
                log_type = data_packet.get("type")
                payload = data_packet.get("payload")

                if log_type == "log_episode":
                    db_manager.log_episode(**payload)
                elif log_type == "log_report":
                    db_manager.log_analysis_report(**payload)
                else:
                    logging.warning(lm.get_string("db_worker.run.unknown_log_type", type=log_type))

            except Exception as e:
                logging.error(lm.get_string("db_worker.run.processing_error", packet=data_packet), exc_info=e)

    except KeyboardInterrupt:
        logging.info(lm.get_string("db_worker.run.user_interrupt"))
    except Exception as e:
        logging.critical(lm.get_string("db_worker.run.fatal_error", error=e), exc_info=True)
    finally:
        logging.info(lm.get_string("db_worker.run.worker_finished"))