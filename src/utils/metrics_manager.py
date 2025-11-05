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

# File: src/utils/metrics_manager.py (NOVO ARQUIVO)
# Author: Gabriel Moraes
# Date: 27 de Setembro de 2025

"""
Define o MetricsManager, um componente reutilizável para gerenciar a exposição
de métricas para o Prometheus.
"""

import logging
import threading
from prometheus_client import start_http_server, Gauge, Counter

class MetricsManager:
    """
    Uma caixa de ferramentas para criar, gerenciar e expor métricas do Prometheus
    para um processo específico.
    """
    def __init__(self, process_name: str, port: int):
        """
        Inicializa o gerenciador de métricas para um processo.

        Args:
            process_name (str): O nome do processo (ex: 'AI_Process', 'SDS_Worker').
                                Será usado como uma label nas métricas.
            port (int): A porta TCP onde o servidor de métricas irá escutar.
        """
        self.process_name = process_name
        self.port = port
        self.metrics = {}
        
        # Inicia o servidor HTTP em uma thread daemon para não bloquear o processo
        self.start_server()

    def start_server(self):
        """Inicia o servidor HTTP do Prometheus em uma thread separada."""
        try:
            server_thread = threading.Thread(
                target=lambda: start_http_server(self.port), 
                daemon=True
            )
            server_thread.start()
            logging.info(f"[{self.process_name}-METRICS] Servidor Prometheus iniciado na porta {self.port}")
        except Exception as e:
            logging.error(f"[{self.process_name}-METRICS] Falha ao iniciar o servidor Prometheus: {e}")

    def register_metric(self, name: str, description: str, metric_type: str = 'gauge'):
        """
        Cria e registra uma nova métrica.

        Args:
            name (str): O nome da métrica (ex: 'queue_size').
            description (str): Uma descrição do que a métrica representa.
            metric_type (str): O tipo de métrica ('gauge' ou 'counter').
        """
        if name in self.metrics:
            return

        label_names = ['process_name']
        
        try:
            if metric_type == 'gauge':
                metric = Gauge(name, description, labelnames=label_names)
            elif metric_type == 'counter':
                metric = Counter(name, description, labelnames=label_names)
            else:
                logging.warning(f"[{self.process_name}-METRICS] Tipo de métrica desconhecido: {metric_type}")
                return
            
            self.metrics[name] = metric
            logging.debug(f"[{self.process_name}-METRICS] Métrica '{name}' registrada.")
        except Exception as e:
            logging.error(f"[{self.process_name}-METRICS] Falha ao registrar a métrica '{name}': {e}")

    def update_metric(self, name: str, value: float):
        """
        Atualiza o valor de uma métrica registrada.

        Args:
            name (str): O nome da métrica a ser atualizada.
            value (float): O novo valor para a métrica.
        """
        if name not in self.metrics:
            return

        metric = self.metrics[name]
        
        # O método de atualização depende do tipo de métrica
        if isinstance(metric, Gauge):
            metric.labels(process_name=self.process_name).set(value)
        elif isinstance(metric, Counter):
            # Para contadores, geralmente incrementamos, mas 'inc' com valor permite flexibilidade
            metric.labels(process_name=self.process_name).inc(value)