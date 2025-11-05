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

# File: src/sas/analyzer_engine.py (Lazy Import para Pandas/Sklearn)
# Author: Gabriel Moraes
# Date: 24 de Outubro de 2025 # <-- DATA ATUALIZADA

import logging
import os
import json
import configparser
from collections import defaultdict
from multiprocessing import Queue
import sys
from typing import TYPE_CHECKING, List, Dict

# Adiciona o diretório 'src' ao path para permitir importações absolutas
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Importações que *não* são pesadas ou são essenciais logo de início
from analysis.infrastructure_analyzer import InfrastructureAnalyzer
from rendering.static_map_renderer import StaticMapRenderer
from utils.network_topology_parser import NetworkTopologyParser

if TYPE_CHECKING:
    from utils.locale_manager_backend import LocaleManagerBackend

# --- MUDANÇA 1: Verificar disponibilidade SEM importar no topo ---
# Tenta importar apenas para definir a flag, mas não mantém a importação global
SKLEARN_AVAILABLE = False
try:
    # Apenas verifica se os módulos existem, não os carrega permanentemente aqui
    import importlib
    importlib.import_module('pandas')
    importlib.import_module('sklearn.linear_model')
    SKLEARN_AVAILABLE = True
    logging.debug("[ANALYZER_ENGINE] Pandas e Scikit-learn detectados.")
except ImportError:
    logging.warning("[ANALYZER_ENGINE] Bibliotecas 'pandas' ou 'sklearn' não encontradas. Calibração do heatmap desativada.")
# --- FIM DA MUDANÇA 1 ---

class AnalyzerEngine:
    """Executa a análise de infraestrutura e gera os arquivos de resultado."""

    def __init__(self, settings: configparser.ConfigParser, db_data_queue: Queue, locale_manager: 'LocaleManagerBackend'):
        self.settings = settings
        self.locale_manager = locale_manager
        lm = self.locale_manager

        self.analyzer = InfrastructureAnalyzer(self.settings, self.locale_manager)
        self.map_renderer = StaticMapRenderer(self.locale_manager)
        self.topology_parser = NetworkTopologyParser(self.locale_manager)
        self.db_data_queue = db_data_queue

        self.scenario_dir = None
        self.analysis_dir = None
        self.cache_path = None
        self.ui_status_path = None

        # Mensagem de log sobre sklearn movida para a verificação acima
        logging.info(lm.get_string("sas_engine.init.engine_created"))

    def run_analysis(self, accumulated_data: dict, sim_duration: float, scenario_name: str,
                     net_file_path: str, run_id: int, calibration_data_points: list):
        lm = self.locale_manager

        if sim_duration <= 0 or not net_file_path:
            logging.warning(lm.get_string("sas_engine.run.analysis_skipped_no_data"))
            return

        project_root_local = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        self.scenario_dir = os.path.join(project_root_local, "results", scenario_name)
        self.analysis_dir = os.path.join(self.scenario_dir, "infrastructure_analysis")
        os.makedirs(self.analysis_dir, exist_ok=True)
        self.cache_path = os.path.join(self.analysis_dir, "analysis_cache.json")
        self.ui_status_path = os.path.join(self.analysis_dir, "analysis_status.json")

        processed_data, true_traffic_light_ids = self._process_accumulated_data(accumulated_data, sim_duration, net_file_path)

        last_analysis_cache = self._load_cache()

        analysis_result = self.analyzer.analyze_collected_data(
            collected_data=processed_data,
            last_analysis_cache=last_analysis_cache,
            scenario_name=scenario_name,
            true_traffic_light_ids=true_traffic_light_ids
        )

        try:
            log_payload = { "run_id": run_id, "summary": analysis_result.get("summary", "N/A"), "report_content": analysis_result.get("report_content", "") }
            data_packet = {"type": "log_report", "payload": log_payload}
            self.db_data_queue.put(data_packet)
            logging.info(lm.get_string("sas_engine.run.report_sent_to_db"))
        except Exception as e:
            logging.error(lm.get_string("sas_engine.run.db_queue_error", error=e))

        if "analysis_results" in analysis_result and analysis_result["analysis_results"]:
            self._generate_planning_map(analysis_result["analysis_results"], net_file_path)

        self._save_cache(analysis_result.get("new_cache_data", {}))
        self._notify_ui(analysis_result)

        # Só tenta calibrar se SKLEARN_AVAILABLE for True E houver dados
        if SKLEARN_AVAILABLE and calibration_data_points:
            new_weights = self._calibrate_heatmap_weights(calibration_data_points)
            if new_weights:
                self._save_live_weights(new_weights)

        logging.info(lm.get_string("sas_engine.run.analysis_complete"))

    def _calibrate_heatmap_weights(self, data_points: List[Dict]) -> Dict | None:
        # --- MUDANÇA 2: Importar pandas e sklearn AQUI DENTRO ---
        # Garante que só importamos se SKLEARN_AVAILABLE for True (já verificado antes de chamar)
        try:
            import pandas as pd
            from sklearn.linear_model import LinearRegression
        except ImportError:
             # Isso não deve acontecer se SKLEARN_AVAILABLE for True, mas é uma segurança extra
             logging.error("[ANALYZER_ENGINE] Falha ao importar pandas/sklearn DENTRO da calibração.")
             return None
        # --- FIM DA MUDANÇA 2 ---

        logging.info(f"[ANALYZER_ENGINE] Iniciando calibração do mapa de calor com {len(data_points)} pontos de dados.")
        if len(data_points) < 100: # Mínimo de pontos para uma regressão minimamente estável
            logging.warning(f"[ANALYZER_ENGINE] Dados insuficientes para calibração (< 100 pontos, temos {len(data_points)}). Abortando.")
            return None
        try:
            df = pd.DataFrame(data_points)
            # Limpeza de dados (importante!)
            df.replace([float('inf'), -float('inf')], float('nan'), inplace=True) # Substitui infinitos por NaN
            df.dropna(inplace=True) # Remove linhas com NaN

            if df.empty or len(df) < 2: # Precisa de pelo menos 2 pontos para regressão
                logging.warning("[ANALYZER_ENGINE] Nenhum dado válido restante após a limpeza ou dados insuficientes. Abortando calibração.")
                return None

            features = ['occupancy', 'waiting_time', 'flow']
            target = 'bad_events' # Eventos ruins (teleportes + frenagens)

            # Garante que as colunas existem
            if not all(feat in df.columns for feat in features) or target not in df.columns:
                 logging.error(f"[ANALYZER_ENGINE] Colunas necessárias ({features + [target]}) não encontradas no DataFrame. Colunas presentes: {df.columns.tolist()}. Abortando calibração.")
                 return None

            X = df[features]
            y = df[target]

            # Adiciona validação simples dos dados
            if X.isnull().values.any() or y.isnull().values.any():
                 logging.warning("[ANALYZER_ENGINE] Dados NaN encontrados mesmo após dropna. Abortando calibração.")
                 return None
            if not pd.api.types.is_numeric_dtype(y):
                 logging.warning(f"[ANALYZER_ENGINE] Coluna target '{target}' não é numérica. Abortando calibração.")
                 return None
            if not all(pd.api.types.is_numeric_dtype(X[col]) for col in X.columns):
                 logging.warning(f"[ANALYZER_ENGINE] Uma ou mais colunas de features não são numéricas. Abortando calibração.")
                 return None


            # Regressão Linear com coeficientes não-negativos para ocupancy e waiting_time
            # (Flow pode ser negativo, indicando que mais fluxo reduz "bad_events")
            model = LinearRegression(positive=False) # Permite coeficientes negativos
            model.fit(X, y)

            # Garante que pesos de occupancy e waiting time sejam >= 0
            coef_occupancy = max(0.0, model.coef_[0])
            coef_waiting = max(0.0, model.coef_[1])
            coef_flow = model.coef_[2] # Flow pode ser negativo

            # Normaliza os pesos para que somem (em valor absoluto) aproximadamente 1 ou um valor razoável
            # Isso evita que pesos muito grandes dominem o cálculo
            total_abs_weight = abs(coef_occupancy) + abs(coef_waiting) + abs(coef_flow)
            if total_abs_weight > 1e-6: # Evita divisão por zero
                 norm_factor = 3.0 / total_abs_weight # Escala para que a soma dos valores absolutos seja ~3 (similar aos pesos originais)
                 coef_occupancy *= norm_factor
                 coef_waiting *= norm_factor
                 coef_flow *= norm_factor


            # Monta o dicionário final, garantindo que o peso do fluxo seja negativo
            new_weights = {
                'weight_occupancy': round(coef_occupancy, 4),
                'weight_waiting_time': round(coef_waiting, 4),
                'weight_flow': round(-abs(coef_flow), 4) # Garante que flow seja negativo ou zero
            }

            logging.info(f"[ANALYZER_ENGINE] Calibração concluída. Novos pesos do mapa de calor: {new_weights}")
            return new_weights

        except Exception as e:
            logging.error(f"[ANALYZER_ENGINE] Erro durante a calibração do mapa de calor: {e}", exc_info=True)
            return None

    def _save_live_weights(self, weights: Dict):
        # Garante que o diretório do cenário existe
        if not self.scenario_dir or not os.path.exists(self.scenario_dir):
            logging.error("[ANALYZER_ENGINE] Diretório do cenário não definido ou não existe. Não é possível salvar pesos.")
            return

        live_weights_path = os.path.join(self.scenario_dir, "heatmap_weights_live.json")
        try:
            with open(live_weights_path, "w", encoding="utf-8") as f:
                json.dump(weights, f, indent=4)
            logging.info(f"[ANALYZER_ENGINE] Pesos do mapa de calor ao vivo salvos em: {live_weights_path}")
        except IOError as e:
            logging.error(f"[ANALYZER_ENGINE] Falha ao salvar os pesos do mapa de calor ao vivo: {e}")

    def _process_accumulated_data(self, accumulated_data: dict, sim_duration: float, net_file_path: str) -> tuple[dict, list]:
        lm = self.locale_manager
        logging.info(lm.get_string("sas_engine.run.processing_data"))

        # --- ALTERADO: Agora chama o especialista externo ---
        junction_types, junction_incoming_edges = self.topology_parser.build(net_file_path)

        if not junction_types or not junction_incoming_edges:
            logging.error(lm.get_string("sas_engine.topology.cannot_continue_error"))
            return {}, []

        true_traffic_light_ids = [j_id for j_id, j_type in junction_types.items() if j_type == 'traffic_light']

        processed_data = {}
        sim_duration_hours = sim_duration / 3600.0 if sim_duration > 0 else 1.0

        # Calcula métricas por junção (lógica mantida)
        for j_id, incoming_edges in junction_incoming_edges.items():
            if not incoming_edges: continue
            # Ordena ruas de entrada pelo número de faixas (proxy para principal/secundária)
            sorted_edges = sorted(incoming_edges.items(), key=lambda item: item[1]['num_lanes'], reverse=True)
            max_lanes = sorted_edges[0][1]['num_lanes'] if sorted_edges else 0
            primary_lanes, secondary_lanes = [], []
            for edge_id, edge_data in sorted_edges:
                if edge_data['num_lanes'] == max_lanes: primary_lanes.extend(edge_data['lanes'])
                else: secondary_lanes.extend(edge_data['lanes'])

            # Soma veículos que saíram das faixas primárias e secundárias
            primary_vehicles = sum(accumulated_data.get('total_vehicles_departed_per_lane', {}).get(lane, 0) for lane in primary_lanes)
            secondary_vehicles = sum(accumulated_data.get('total_vehicles_departed_per_lane', {}).get(lane, 0) for lane in secondary_lanes)
            # Soma tempo de espera apenas nas faixas secundárias
            secondary_wait_time = sum(accumulated_data.get('total_waiting_time_per_lane', {}).get(lane, 0) for lane in secondary_lanes)

            # Calcula métricas por hora ou média
            vol_primary = int(primary_vehicles / sim_duration_hours)
            vol_secondary = int(secondary_vehicles / sim_duration_hours)
            avg_delay_secondary = (secondary_wait_time / secondary_vehicles) if secondary_vehicles > 0 else 0

            # Adiciona dados processados ao dicionário
            processed_data[j_id] = {
                "volume": vol_primary, # Volume da via principal (agora chamado 'volume')
                "vol_secondary": vol_secondary, # Volume da via secundária
                "avg_delay": avg_delay_secondary, # Atraso médio apenas na secundária
                "conflict_events": accumulated_data.get('conflict_events_per_junction', {}).get(j_id, 0), # Eventos de conflito na junção
                "type": junction_types.get(j_id, 'unknown') # Tipo da junção
            }

        logging.info(lm.get_string("sas_engine.run.data_processed", count=len(processed_data)))
        return processed_data, true_traffic_light_ids

    def _generate_planning_map(self, analysis_results: dict, net_file_path: str):
        lm = self.locale_manager
        # Garante que temos um diretório de cenário válido
        if not self.scenario_dir or not os.path.exists(self.scenario_dir):
            logging.error("[ANALYZER_ENGINE] Diretório do cenário inválido. Não é possível gerar mapa de planejamento.")
            return

        logging.info(lm.get_string("sas_engine.map.generating"))
        # Mapeia recomendações para tipos de ícone
        rec_add = lm.get_string("warrant_evaluator.rec_add")
        rec_remove = lm.get_string("warrant_evaluator.rec_remove")
        icon_requests = {
            j_id: "add" if rec_add in r.get('recommendation', '') else "remove" if rec_remove in r.get('recommendation', '') else "existing"
            for j_id, r in analysis_results.items()
        }
        if net_file_path:
            self.map_renderer.create_map_with_icons(
                net_file_path=net_file_path,
                scenario_results_dir=self.scenario_dir, # Usa o diretório do cenário
                icon_requests=icon_requests,
                output_filename="map_planning.png" # Nome do arquivo de saída
            )
        else:
             logging.warning("[ANALYZER_ENGINE] Caminho do net_file não disponível. Mapa de planejamento não gerado.")


    def _load_cache(self) -> dict:
        if not self.cache_path or not os.path.exists(self.cache_path): return {}
        try:
            with open(self.cache_path, "r", encoding="utf-8") as f: return json.load(f)
        except (json.JSONDecodeError, IOError): return {}

    def _save_cache(self, cache_data: dict):
        if not cache_data or not self.cache_path: return
        try:
            # Garante que o diretório exista
            os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
            with open(self.cache_path, "w", encoding="utf-8") as f: json.dump(cache_data, f, indent=4)
        except IOError: logging.error(self.locale_manager.get_string("sas_engine.cache.save_error"))

    def _notify_ui(self, analysis_result: dict):
        if not analysis_result or not analysis_result.get("analysis_results") or not self.ui_status_path: return
        try:
            # Garante que o diretório exista
            os.makedirs(os.path.dirname(self.ui_status_path), exist_ok=True)
            with open(self.ui_status_path, "w", encoding="utf-8") as f: json.dump(analysis_result, f, indent=4)
        except IOError: logging.error(self.locale_manager.get_string("sas_engine.ui.status_save_error"))