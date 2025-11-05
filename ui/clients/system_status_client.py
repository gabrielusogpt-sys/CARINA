# File: ui/clients/system_status_client.py (CORRIGIDO)
# Author: Gabriel Moraes
# Date: 01 de Outubro de 2025

"""
Define o SystemStatusClient.

Nesta versão, foi adicionado um loop de repetição (polling) na thread de
busca, garantindo que ele continue a procurar pelo arquivo status.json por
um período antes de desistir.
"""

import os
import json
import logging
import threading
import time
from typing import Callable, Dict, Any
from datetime import datetime

class SystemStatusClient:
    """
    Busca o status.json mais recente em uma thread separada.
    """
    def __init__(self, on_complete_callback: Callable[[Dict[str, Any]], None]):
        """
        Inicializa o cliente.

        Args:
            on_complete_callback: A função que será chamada quando a busca terminar.
        """
        self.project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        self.on_complete = on_complete_callback

    def _find_and_read_status_file(self) -> Dict[str, Any]:
        """
        Encontra o arquivo status.json mais recente, lê e retorna seu conteúdo.
        Se ocorrer um erro, retorna um dicionário de erro.
        """
        try:
            results_dir = os.path.join(self.project_root, "results")
            if not os.path.exists(results_dir) or not os.path.isdir(results_dir):
                return {"status": "error", "message_key": "system_status_view.status_file_not_found"}

            ignored_dirs = {"database"}
            all_scenarios = [
                d for d in os.listdir(results_dir)
                if os.path.isdir(os.path.join(results_dir, d)) and d not in ignored_dirs
            ]
            if not all_scenarios:
                return {"status": "error", "message_key": "system_status_view.status_file_not_found"}

            latest_scenario_name = max(all_scenarios, key=lambda d: os.path.getmtime(os.path.join(results_dir, d)))
            status_file_path = os.path.join(results_dir, latest_scenario_name, "status.json")
            
            if not os.path.exists(status_file_path):
                # Este não é mais um erro final, apenas uma tentativa falhada.
                return {"status": "pending"}
            
            with open(status_file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            timestamp = data.get("last_updated", "N/A")
            if timestamp != "N/A":
                dt_object = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                data["last_updated_formatted"] = dt_object.strftime("%d/%m/%Y %H:%M:%S")

            return {"status": "complete", "data": data}

        except Exception as e:
            logging.error(f"[SystemStatusClient] Erro ao buscar/ler status.json: {e}", exc_info=True)
            return {"status": "error", "message_key": "system_status_view.status_file_error", "error_details": str(e)}

    # --- MUDANÇA PRINCIPAL AQUI ---
    def _fetch_thread_target(self):
        """
        Método alvo da thread: procura repetidamente pelo arquivo e chama o callback.
        """
        logging.info("[SystemStatusClient] Iniciando busca em loop pelo status.json...")
        final_result = None
        # Tenta por 60 segundos (20 tentativas com 3 segundos de intervalo)
        for i in range(20):
            result = self._find_and_read_status_file()
            final_result = result
            
            # Se encontrou o arquivo, para de procurar
            if result.get("status") == "complete":
                logging.info(f"[SystemStatusClient] status.json encontrado na tentativa {i+1}.")
                break
            
            # Se o status não for 'complete', espera e tenta novamente
            time.sleep(3)
        
        if final_result.get("status") != "complete":
             logging.warning("[SystemStatusClient] Tempo de busca esgotado. status.json não foi encontrado.")
             # Garante que o resultado final seja o de erro correto
             final_result = {"status": "error", "message_key": "system_status_view.status_file_not_found"}

        if self.on_complete:
            self.on_complete(final_result)
    # --- FIM DA MUDANÇA ---

    def start_fetching_status(self):
        """
        Inicia a busca pelo arquivo de status em uma nova thread.
        Retorna imediatamente, sem bloquear a UI.
        """
        thread = threading.Thread(target=self._fetch_thread_target, daemon=True)
        thread.start()