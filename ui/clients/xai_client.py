# File: ui/clients/xai_client.py (CORRIGIDO)
# Author: Gabriel Moraes
# Date: 01 de Outubro de 2025

"""
Define o XaiClient.

Nesta versão, o carregamento da lista de agentes foi tornado assíncrono
para evitar o bloqueio da UI na inicialização do widget.
"""

import os
import json
import threading
import time
import logging
from typing import Callable, List

class XaiClient:
    """
    Gerencia a comunicação para iniciar análises XAI e carregar a lista de agentes.
    """
    def __init__(self, on_analysis_complete_callback: Callable[[dict], None]):
        """
        Inicializa o cliente.

        Args:
            on_analysis_complete_callback: A função a ser chamada quando a análise XAI terminar.
        """
        self.on_analysis_complete = on_analysis_complete_callback
        self.project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    def _find_latest_scenario_path(self):
        """Encontra o caminho absoluto para a pasta de cenário mais recente."""
        try:
            results_dir = os.path.join(self.project_root, "results")
            if os.path.exists(results_dir):
                ignored_dirs = {"database"}
                all_scenarios = [
                    d for d in os.listdir(results_dir) 
                    if os.path.isdir(os.path.join(results_dir, d)) and d not in ignored_dirs
                ]
                if all_scenarios:
                    latest_scenario_name = max(all_scenarios, key=lambda d: os.path.getmtime(os.path.join(results_dir, d)))
                    return os.path.join(results_dir, latest_scenario_name)
        except Exception:
            return None
        return None

    # --- MUDANÇA 1: O método síncrono agora é privado ---
    def _get_agent_list_sync(self) -> List[str]:
        """Lê o status.json do cenário mais recente e retorna a lista de agentes."""
        latest_scenario_path = self._find_latest_scenario_path()
        if not latest_scenario_path:
            return []
        try:
            status_file_path = os.path.join(latest_scenario_path, "status.json")
            if os.path.exists(status_file_path):
                with open(status_file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return data.get("agent_ids", [])
        except Exception as e:
            logging.error(f"[XaiClient] Erro ao carregar lista de agentes: {e}")
            return []
        return []
        
    # --- MUDANÇA 2: Novo método alvo da thread para buscar a lista de agentes ---
    def _fetch_agent_list_thread_target(self, on_list_loaded_callback: Callable[[List[str]], None]):
        """
        Executado em segundo plano: busca a lista de agentes e chama o callback.
        """
        agent_ids = self._get_agent_list_sync()
        if on_list_loaded_callback:
            on_list_loaded_callback(agent_ids)

    # --- MUDANÇA 3: Novo método público para iniciar a busca assíncrona da lista ---
    def start_fetching_agent_list(self, on_list_loaded_callback: Callable[[List[str]], None]):
        """
        Inicia a busca pela lista de agentes em uma nova thread.
        """
        logging.info("[XaiClient] Iniciando busca assíncrona pela lista de agentes...")
        thread = threading.Thread(
            target=self._fetch_agent_list_thread_target,
            args=(on_list_loaded_callback,),
            daemon=True
        )
        thread.start()

    # --- A lógica de análise principal permanece a mesma ---
    def start_analysis(self, agent_id: str):
        """
        Inicia a análise XAI em uma nova thread. Retorna imediatamente.
        """
        thread = threading.Thread(
            target=self._analysis_worker_thread_target,
            args=(agent_id,),
            daemon=True
        )
        thread.start()

    def _analysis_worker_thread_target(self, agent_id: str, timeout_seconds: int = 300):
        """
        Este é o método executado pela thread de análise.
        """
        scenario_path = self._find_latest_scenario_path()
        if not scenario_path:
            if self.on_analysis_complete:
                self.on_analysis_complete({"status": "error", "message": "Diretório de cenário 'results' não encontrado."})
            return

        # ... (resto da lógica de análise permanece inalterada)
        try:
            captum_base_dir = os.path.join(scenario_path, "captum")
            requests_dir = os.path.join(captum_base_dir, "requests")
            responses_dir = os.path.join(captum_base_dir, "responses")
            os.makedirs(requests_dir, exist_ok=True)
            os.makedirs(responses_dir, exist_ok=True)

            request_path = os.path.join(requests_dir, f"{agent_id}.request")
            response_path = os.path.join(responses_dir, f"{agent_id}.response")

            if os.path.exists(response_path): os.remove(response_path)
            if os.path.exists(request_path): os.remove(request_path)

            with open(request_path, "w", encoding="utf-8") as f:
                json.dump({"agent_id": agent_id}, f)
        
        except Exception as e:
            if self.on_analysis_complete:
                self.on_analysis_complete({"status": "error", "message": f"Falha ao criar arquivo de pedido: {e}"})
            return

        start_time = time.time()
        response_data = None
        
        while time.time() - start_time < timeout_seconds:
            if os.path.exists(response_path):
                try:
                    time.sleep(0.2) 
                    with open(response_path, "r", encoding="utf-8") as f:
                        response_data = json.load(f)
                    os.remove(response_path)
                    break 
                except Exception as e:
                    response_data = {"status": "error", "message": f"Falha ao ler arquivo de resposta: {e}"}
                    break
            time.sleep(2)

        if response_data is None: 
            response_data = {"status": "error", "message": "Tempo de espera esgotado. O back-end não respondeu."}
        
        if self.on_analysis_complete:
            self.on_analysis_complete(response_data)