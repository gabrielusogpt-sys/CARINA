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

# File: src/sds/data_processor.py (MODIFICADO PARA CALIBRAÇÃO AO VIVO)
# Author: Gabriel Moraes
# Date: 13 de Outubro de 2025

import logging
import os
import sys
import configparser
import json
import time
from collections import defaultdict
from typing import TYPE_CHECKING

# Adiciona o diretório 'src' ao path para permitir importações absolutas
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

if TYPE_CHECKING:
    from utils.locale_manager_backend import LocaleManagerBackend

from utils.map_generator import generate_map_data_files
from utils.map_data_parser import parse_map_data
from utils.network_parser import build_lane_to_edge_map

class DataProcessor:
    def __init__(self, settings: configparser.ConfigParser, locale_manager: 'LocaleManagerBackend'):
        self.locale_manager = locale_manager
        self.map_data = None 
        self.lane_to_edge_map = None 
        self._last_step_vehicles_per_lane = {}
        self.geometry_sent = False
        self.edge_to_lanes_map = defaultdict(list)
        self.heatmap_weights = {}
        self.aggregation_strategy = 'max'
        
        # --- NOVO: Atributos para a calibração ao vivo ---
        self.live_weights_path = None
        self.last_weights_check_time = 0
        # --- FIM DO NOVO BLOCO ---
        
        try:
            cfg = settings['HEATMAP_SCALING']
            self.heatmap_weights = {
                'weight_occupancy': cfg.getfloat('weight_occupancy', 1.0),
                'weight_waiting_time': cfg.getfloat('weight_waiting_time', 1.5),
                'weight_flow': cfg.getfloat('weight_flow', -0.5)
            }
            self.aggregation_strategy = cfg.get('lane_aggregation_strategy', 'max')
        except (KeyError, configparser.NoSectionError):
            self.heatmap_weights = {'occupancy': 1.0, 'waiting_time': 1.5, 'flow': -0.5}
        
        logging.info(self.locale_manager.get_string("sds_processor.init.processor_created"))
        logging.info(f"[DATA_PROCESSOR] Pesos iniciais do mapa de calor: {self.heatmap_weights}")

    # --- NOVO MÉTODO: Verifica e carrega os pesos calibrados pelo SAS ---
    def _check_for_live_weights(self):
        current_time = time.time()
        if (current_time - self.last_weights_check_time) < 5: # Verifica a cada 5 segundos
            return

        self.last_weights_check_time = current_time

        if not self.live_weights_path: # Se o caminho ainda não foi definido, tenta encontrá-lo
            # Lógica para encontrar o diretório do cenário mais recente
            results_dir = os.path.join(project_root, "results")
            if not os.path.isdir(results_dir): return
            
            all_scenarios = [d for d in os.listdir(results_dir) if os.path.isdir(os.path.join(results_dir, d))]
            if not all_scenarios: return

            latest_scenario_dir = max(all_scenarios, key=lambda d: os.path.getmtime(os.path.join(results_dir, d)))
            self.live_weights_path = os.path.join(results_dir, latest_scenario_dir, "heatmap_weights_live.json")

        if self.live_weights_path and os.path.exists(self.live_weights_path):
            try:
                with open(self.live_weights_path, "r", encoding="utf-8") as f:
                    new_weights = json.load(f)
                
                # Compara se os pesos realmente mudaram para evitar logs desnecessários
                if new_weights != self.heatmap_weights:
                    self.heatmap_weights = new_weights
                    logging.info(f"[DATA_PROCESSOR] Pesos do mapa de calor atualizados em tempo real via calibração: {self.heatmap_weights}")

            except (json.JSONDecodeError, IOError) as e:
                logging.warning(f"[DATA_PROCESSOR] Erro ao ler o ficheiro de pesos ao vivo: {e}")

    def process_for_ui(self, raw_data: dict) -> dict | None:
        # --- NOVO: A primeira coisa a fazer é verificar por pesos atualizados ---
        self._check_for_live_weights()

        if not self.map_data:
            net_file = raw_data.get("net_file")
            scenario = raw_data.get("scenario_name")
            self._lazy_load_map_data(net_file_path=net_file, scenario_name=scenario)
        if not raw_data or not self.map_data or not self.lane_to_edge_map:
            return None
        
        street_data_payload = self._prepare_street_data(raw_data)
        congestion_for_heatmap = { street_id: data.get('congestion', 0.0) for street_id, data in street_data_payload.items() }
        panel_data = self._prepare_panel_data(raw_data)
        maturity_phases_data = raw_data.get("maturity_phases", {})
        
        if not self.geometry_sent:
            nodes, edges, _ = self.map_data
            self.geometry_sent = True
            return {
                "type": "initial_map_geometry", "geometry": {"nodes": nodes, "edges": edges},
                "congestion_update": congestion_for_heatmap, "panel_data": panel_data,
                "street_data": street_data_payload, "maturity_phases": maturity_phases_data
            }
        else:
            return {
                "type": "congestion_update", "payload": congestion_for_heatmap,
                "panel_data": panel_data, "street_data": street_data_payload,
                "maturity_phases": maturity_phases_data
            }

    def _lazy_load_map_data(self, net_file_path: str, scenario_name: str):
        if self.map_data and self.lane_to_edge_map: return
        lm = self.locale_manager
        try:
            results_dir = os.path.join(project_root, "results", scenario_name)
            map_data_prefix = os.path.join(results_dir, "maps", f"{scenario_name}_map")
            if not os.path.exists(map_data_prefix + ".nod.xml"):
                generate_map_data_files(net_file_path=net_file_path, output_dir=results_dir, lm=self.locale_manager)
            self.map_data = parse_map_data(map_data_prefix)
            self.lane_to_edge_map = build_lane_to_edge_map(net_file_path, self.locale_manager)
            if self.lane_to_edge_map:
                for lane_id, edge_id in self.lane_to_edge_map.items(): self.edge_to_lanes_map[edge_id].append(lane_id)
        except Exception as e:
            logging.error(lm.get_string("sds_processor.load_map.error", error=e), exc_info=True)

    def _prepare_panel_data(self, raw_data: dict) -> dict:
        tls_phases = raw_data.get('tls_phases', {})
        tls_lanes_state = raw_data.get('tls_lanes_state', {})
        panel_data = {}
        for tl_id, phase in tls_phases.items():
            lanes_state_string = "".join(tls_lanes_state.get(tl_id, {}).values()).lower()
            if any(c in lanes_state_string for c in ['y', 's']): display_state = "YELLOW"
            elif any(c in lanes_state_string for c in ['g']): display_state = "GREEN"
            else: display_state = "RED"
            panel_data[tl_id] = { "phase": phase, "lanes_state": tls_lanes_state.get(tl_id, {}), "display_state": display_state }
        return panel_data
    
    def _prepare_street_data(self, raw_data: dict) -> dict:
        edge_data = defaultdict(lambda: {'occupancy': [], 'waiting_time': 0, 'flow_per_step': 0})
        step_length = raw_data.get('sim_step_length', 1.0)
        edge_speeds_ms = raw_data.get('edge_mean_speeds', {})
        current_vehicles_per_lane = raw_data.get('lane_vehicle_ids', {})
        flow_conversion_factor = (60 / step_length) if step_length > 0 else 60
        for lane_id, occupancy in raw_data.get('lane_occupancies', {}).items():
            edge_id = self.lane_to_edge_map.get(lane_id)
            if edge_id: edge_data[edge_id]['occupancy'].append(occupancy)
        for lane_id, waiting_time in raw_data.get('lane_waiting_time', {}).items():
            edge_id = self.lane_to_edge_map.get(lane_id)
            if edge_id: edge_data[edge_id]['waiting_time'] += waiting_time
        if self._last_step_vehicles_per_lane:
            for lane_id, vehicles_before in self._last_step_vehicles_per_lane.items():
                edge_id = self.lane_to_edge_map.get(lane_id)
                if edge_id:
                    vehicles_after = set(current_vehicles_per_lane.get(lane_id, []))
                    departed_count = len(set(vehicles_before) - vehicles_after)
                    edge_data[edge_id]['flow_per_step'] += departed_count
        self._last_step_vehicles_per_lane = current_vehicles_per_lane
        street_payload = {}
        for edge_id, data in edge_data.items():
            aggregated_occupancy = 0
            if data['occupancy']:
                if self.aggregation_strategy == 'max': aggregated_occupancy = max(data['occupancy'])
                else: aggregated_occupancy = sum(data['occupancy']) / len(data['occupancy'])
            flow_per_minute = data['flow_per_step'] * flow_conversion_factor
            
            # --- MODIFICADO: Usa os pesos atuais em memória (que podem ser os calibrados) ---
            congestion_index = (
                (aggregated_occupancy * 100 * self.heatmap_weights.get('weight_occupancy', 1.0)) + 
                (data['waiting_time'] * self.heatmap_weights.get('weight_waiting_time', 1.5)) + 
                (data['flow_per_step'] * self.heatmap_weights.get('weight_flow', -0.5))
            )

            lanes_for_this_edge = self.edge_to_lanes_map.get(edge_id, [])
            num_vehicles = sum(len(current_vehicles_per_lane.get(lane, [])) for lane in lanes_for_this_edge)
            speed_ms = edge_speeds_ms.get(edge_id, 0.0)
            speed_kmh = speed_ms * 3.6
            street_payload[edge_id] = { "congestion": congestion_index, "flow": int(round(flow_per_minute)), "vehicles": num_vehicles, "speed": round(speed_kmh, 1) }
        return street_payload