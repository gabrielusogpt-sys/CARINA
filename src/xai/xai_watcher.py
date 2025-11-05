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

# File: src/xai/xai_watcher.py (Atualizado para lidar com saídas de imagem e texto)
# Author: Gabriel Moraes
# Date: 03 de Setembro de 2025

"""
Define o XaiWatcher.

Nesta versão, ele foi atualizado para receber os caminhos tanto do
gráfico (.png) quanto da análise textual (.txt) do CaptumAnalyzer,
e repassar ambos para a UI no arquivo de resposta.
"""

import logging
import os
import json
import threading
import time
from xai.captum_analyzer import CaptumAnalyzer
from engine.environment import SumoEnvironment
from core.population_manager import PopulationManager
from core.lifecycle_manager import LifecycleManager
from core.strategic_coordinator import StrategicCoordinator

class XaiWatcher:
    """
    Vigia uma pasta por arquivos de pedido, aciona o analisador e cria
    um arquivo de resposta.
    """
    def __init__(self, population_manager: PopulationManager, lifecycle_manager: LifecycleManager, 
                 env: SumoEnvironment, strategic_coordinator: StrategicCoordinator):
        self.population_manager = population_manager
        self.lifecycle_manager = lifecycle_manager
        self.env = env
        self.strategic_coordinator = strategic_coordinator
        self.watcher_thread = None
        self.watcher_running = False

    def start(self):
        self.watcher_running = True
        self.watcher_thread = threading.Thread(target=self._watcher_loop, daemon=True)
        self.watcher_thread.start()

    def stop(self):
        self.watcher_running = False

    def _watcher_loop(self):
        logging.info("[XAI_WATCHER] Vigilante de análise XAI iniciado.")
        while self.watcher_running:
            try:
                if not self.lifecycle_manager or not self.lifecycle_manager.scenario_checkpoint_dir:
                    time.sleep(5)
                    continue
                
                scenario_results_dir = os.path.dirname(self.lifecycle_manager.scenario_checkpoint_dir)
                base_dir = os.path.join(scenario_results_dir, "captum")
                requests_dir = os.path.join(base_dir, "requests")
                responses_dir = os.path.join(base_dir, "responses")
                os.makedirs(requests_dir, exist_ok=True)
                os.makedirs(responses_dir, exist_ok=True)
                
                for request_filename in os.listdir(requests_dir):
                    if not request_filename.endswith(".request"): continue

                    request_path = os.path.join(requests_dir, request_filename)
                    response_filename = request_filename.replace(".request", ".response")
                    response_path = os.path.join(responses_dir, response_filename)
                    response_tmp_path = response_path + ".tmp"
                    response_data = {}

                    try:
                        logging.info(f"[XAI_WATCHER] Pedido '{request_filename}' detectado. Processando...")
                        with open(request_path, "r", encoding="utf-8") as f:
                            request_data = json.load(f)
                        
                        agent_id = request_data.get("agent_id")
                        agent = self.population_manager.agents.get(agent_id)

                        if agent and self.env.state_extractor and self.strategic_coordinator:
                            full_glossary = self.env.state_extractor.get_local_feature_glossary(agent_id)
                            max_local_dim = self.strategic_coordinator.max_state_dim
                            padding_needed = max_local_dim - len(full_glossary)
                            for i in range(padding_needed):
                                full_glossary.append({
                                    "feature_name": f"Padding (Índice {i})",
                                    "description": "Preenchimento para uniformizar o tamanho da entrada. Não é um sensor real."
                                })
                            gat_dim = self.strategic_coordinator.output_dim
                            for i in range(gat_dim):
                                full_glossary.append({
                                    "feature_name": f"Vetor Estratégico (Comp. {i+1})",
                                    "description": f"Componente nº {i+1} da orientação estratégica, resumindo o estado de tráfego vizinho."
                                })
                            
                            analyzer = CaptumAnalyzer(agent, scenario_results_dir)
                            # O método agora precisa do glossário completo
                            analysis_result = analyzer.run_analysis(full_glossary=full_glossary)
                            
                            # --- MUDANÇA PRINCIPAL AQUI ---
                            # Verifica se o resultado é um dicionário (sucesso)
                            if analysis_result:
                                response_data = {
                                    "status": "complete", 
                                    "image_path": analysis_result.get("image_path"),
                                    "text_path": analysis_result.get("text_path") # Adiciona o novo caminho
                                }
                            else:
                                response_data = {"status": "error", "message": "Falha ao gerar arquivos de análise. Verifique os logs do back-end."}
                        else:
                            response_data = {"status": "error", "message": f"Agente '{agent_id}' ou componentes essenciais não foram encontrados."}
                    except Exception as e:
                        logging.error(f"[XAI_WATCHER] Erro ao processar pedido: {e}", exc_info=True)
                        response_data = {"status": "error", "message": str(e)}
                    
                    finally:
                        try:
                            with open(response_tmp_path, "w", encoding="utf-8") as f:
                                json.dump(response_data, f, indent=4)
                            os.rename(response_tmp_path, response_path)
                        except Exception as e:
                            logging.error(f"[XAI_WATCHER] Falha crítica ao escrever arquivo de resposta atômica: {e}")
                        
                        os.remove(request_path)
                        logging.info(f"[XAI_WATCHER] Resposta para '{response_filename}' enviada.")

                time.sleep(2)
            except Exception as e:
                logging.error(f"[XAI_WATCHER] Erro crítico no loop do vigilante: {e}", exc_info=True)
                time.sleep(10)
        
        logging.info("[XAI_WATCHER] Vigilante de análise XAI finalizado.")