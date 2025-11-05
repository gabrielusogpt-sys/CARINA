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

# File: src/engine/initialization_orchestrator.py (CORRIGIDO PARA RECEBER LOCALE_MANAGER)
# Author: Gabriel Moraes
# Date: 05 de Outubro de 2025

import logging
import torch
import json
import os
from datetime import datetime, timezone
import sys
from typing import TYPE_CHECKING

# Adiciona o diretório 'src' ao path para permitir importações absolutas
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

if TYPE_CHECKING:
    from utils.locale_manager_backend import LocaleManagerBackend

from engine.environment import SumoEnvironment
from core.lifecycle_manager import LifecycleManager
from core.childhood_analyzer import ChildhoodAnalyzer
from engine.asset_manager import AssetManager
from utils.network_parser import build_structural_neighborhood_map

class InitializationOrchestrator:
    """
    Orquestra a sequência de SETUP do sistema, incluindo a geração dos ativos de mapa.
    """

    # --- CORREÇÃO 1: O construtor agora recebe e armazena o locale_manager ---
    def __init__(self, settings, log_dir: str, gpu_info: str, locale_manager: 'LocaleManagerBackend'):
        self.settings = settings
        self.log_dir = log_dir
        self.gpu_info = gpu_info
        self.locale_manager = locale_manager # Armazena a instância recebida
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logging.info("[INIT_ORCHESTRATOR] Setup Engineer created.")

    def _write_system_summary(self, scenario_results_dir: str, agent_count: dict, network_topology: dict, agent_ids: list):
        """Escreve o arquivo status.json com o sumário do sistema."""
        lm = self.locale_manager # Usa a instância armazenada
        summary_data = {
            "gpu_info": self.gpu_info,
            "agent_count": agent_count,
            "network_topology": network_topology,
            "agent_ids": sorted(agent_ids),
            "last_updated": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        }
        status_path = os.path.join(scenario_results_dir, "status.json")
        try:
            os.makedirs(scenario_results_dir, exist_ok=True)
            with open(status_path, "w", encoding="utf-8") as f:
                json.dump(summary_data, f, indent=4)
            logging.info(lm.get_string("init_orchestrator.summary.success", path=status_path))
        except Exception as e:
            logging.error(lm.get_string("init_orchestrator.summary.critical_error", error=e), exc_info=True)

    def initialize_system(self) -> dict:
        """
        Executa a fase de setup e retorna os componentes essenciais para o Trainer.
        """
        # --- CORREÇÃO 2: Usa o locale_manager da instância (self.locale_manager) ---
        lm = self.locale_manager
        
        # A linha "lm = LocaleManagerBackend()" foi REMOVIDA daqui.
        logging.info(lm.get_string("init_orchestrator.run.start"))
        
        env = SumoEnvironment(settings=self.settings, locale_manager=lm)
        env.connect()

        scenario_path = env.scenario_path
        if not scenario_path or "Desconhecido" in scenario_path or "Unknown" in scenario_path:
            error_message = lm.get_string("init_orchestrator.run.scenario_path_error")
            raise RuntimeError(error_message)

        scenario_filename = os.path.basename(scenario_path)
        scenario_name, _ = os.path.splitext(scenario_filename)
        project_root_local = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        scenario_results_dir = os.path.join(project_root_local, "results", scenario_name)
        
        os.makedirs(scenario_results_dir, exist_ok=True)

        asset_manager = AssetManager(lm)
        
        net_file_path = env.conn.simulation.getOption("net-file")
        traffic_light_ids = env.get_traffic_light_ids()
        
        logging.info(lm.get_string("init_orchestrator.run.assets_dashboard"))
        
        _, map_data_tuple = asset_manager.create_map_with_icons(
            net_file_path=net_file_path,
            scenario_results_dir=scenario_results_dir,
            icon_requests={},
            output_filename="map_dashboard_base.png"
        )
        
        if map_data_tuple:
            nodes, edges = map_data_tuple
            asset_manager.generate_coordinates_file(
                map_data=(nodes, edges),
                traffic_light_ids=traffic_light_ids,
                scenario_results_dir=scenario_results_dir
            )
        else:
            logging.warning(lm.get_string("init_orchestrator.run.coords_file_error"))
        
        logging.info(lm.get_string("init_orchestrator.run.assets_planning"))
        initial_planning_map_icons = {tl_id: "existing" for tl_id in traffic_light_ids}
        
        asset_manager.create_map_with_icons(
            net_file_path=net_file_path,
            scenario_results_dir=scenario_results_dir,
            icon_requests=initial_planning_map_icons,
            output_filename="map_planning.png"
        )
        
        logging.info(lm.get_string("init_orchestrator.run.collecting_summary"))
        
        neighborhoods = build_structural_neighborhood_map(net_file_path, traffic_light_ids, lm)
        num_traffic_light_connections = sum(len(neighbors) for neighbors in neighborhoods.values())

        agent_count = {
            "local_agents": len(traffic_light_ids),
            "guardian_agents": len(traffic_light_ids)
        }
        network_topology = {
            "nodes": len(traffic_light_ids),
            "edges": num_traffic_light_connections
        }
        
        self._write_system_summary(
            scenario_results_dir=scenario_results_dir,
            agent_count=agent_count,
            network_topology=network_topology,
            agent_ids=traffic_light_ids
        )

        lifecycle_manager = LifecycleManager(self.settings, self.log_dir, scenario_results_dir, lm)
        
        analyzer = ChildhoodAnalyzer(settings=self.settings['ANALYSIS'], scenario_results_dir=scenario_results_dir, locale_manager=lm)
        
        logging.info(lm.get_string("init_orchestrator.run.complete"))
        
        # --- CORREÇÃO 3: Não precisamos mais retornar o 'lm', pois o chamador já o tem ---
        return {
            "env": env, 
            "lifecycle_manager": lifecycle_manager,
            "childhood_analyzer": analyzer,
            "device": self.device,
            "scenario_results_dir": scenario_results_dir,
            "map_data": map_data_tuple
        }