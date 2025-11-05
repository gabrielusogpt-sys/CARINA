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

# File: src/analysis/infrastructure_analyzer.py (MODIFICADO PARA TRADUÇÃO COMPLETA)
# Author: Gabriel Moraes
# Date: 01 de Outubro de 2025

import logging
import configparser
from datetime import datetime
import sys
import os
from typing import TYPE_CHECKING

# Adiciona o diretório 'src' ao path para permitir importações absolutas
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from analysis.warrant_evaluator import WarrantEvaluator
from analysis.report_generator import ReportGenerator

if TYPE_CHECKING:
    from utils.locale_manager_backend import LocaleManagerBackend

class InfrastructureAnalyzer:
    """
    Orquestra a análise de dados de tráfego usando componentes especialistas.
    """
    def __init__(self, settings: configparser.ConfigParser, locale_manager: 'LocaleManagerBackend'):
        self.settings = settings
        self.locale_manager = locale_manager
        lm = self.locale_manager
        
        self.analysis_params = {}
        self._load_analysis_parameters()
        self.scenario_name = lm.get_string("infra_analyzer.unknown_scenario")
        logging.info(lm.get_string("infra_analyzer.analyzer_created"))

    def _load_analysis_parameters(self):
        """Carrega os limiares da análise a partir do settings.ini."""
        try:
            section = self.settings['INFRASTRUCTURE_ANALYSIS']
            self.analysis_params = {
                'min_volume_primary': section.getint('min_volume_primary', 500),
                'min_volume_secondary': section.getint('min_volume_secondary', 150),
                'unacceptable_delay': section.getfloat('unacceptable_delay_seconds', 90.0),
                'conflict_threshold': section.getint('conflict_events_threshold', 10),
                'removal_threshold_percent': section.getfloat('removal_threshold_percent', 60.0),
                'change_threshold_percent': section.getfloat('significant_change_threshold_percent', 5.0)
            }
        except (configparser.NoSectionError, KeyError):
            # --- MUDANÇA APLICADA AQUI ---
            logging.error(self.locale_manager.get_string("infra_analyzer.init.config_error"))
            self.analysis_params = {}

    def analyze_collected_data(self, collected_data: dict, last_analysis_cache: dict, scenario_name: str, true_traffic_light_ids: list) -> dict:
        """
        Orquestra a análise, recebendo e repassando a lista de semáforos.
        """
        self.scenario_name = scenario_name
        lm = self.locale_manager
        
        evaluator = WarrantEvaluator(self.analysis_params, true_traffic_light_ids, lm)
        
        analysis_results = {}
        for j_id, j_data in collected_data.items():
            result = evaluator.evaluate(j_id, j_data)
            if result:
                analysis_results[j_id] = result
        
        last_metrics = last_analysis_cache.get("junction_metrics", {})
        significant_change, summary = self._compare_with_cache(collected_data, last_metrics)
        
        report_generator = ReportGenerator(analysis_results, self.analysis_params, self.scenario_name, lm)
        report_content = report_generator.generate_txt_report()
        
        new_cache_data = {
            "last_analysis_timestamp": datetime.now().isoformat(),
            "analysis_parameters": self.analysis_params,
            "junction_metrics": collected_data
        }

        return {
            "report_content": report_content,
            "significant_change": significant_change,
            "summary": summary,
            "new_cache_data": new_cache_data,
            "analysis_results": analysis_results
        }

    def _compare_with_cache(self, current_metrics: dict, last_metrics: dict) -> tuple[bool, str]:
        """Compara as métricas atuais com as anteriores para detectar mudanças."""
        lm = self.locale_manager
        if not last_metrics:
            return True, lm.get_string("infra_analyzer.summary_first_run")

        change_threshold = self.analysis_params.get('change_threshold_percent', 5.0)
        changed_junctions = []

        for j_id, new_data in current_metrics.items():
            if j_id not in last_metrics:
                changed_junctions.append(lm.get_string("infra_analyzer.change_new_junction", id=j_id))
                continue

            old_data = last_metrics[j_id]
            metrics_to_check = ['volume', 'avg_delay', 'conflict_events']
            for metric in metrics_to_check:
                old_val = old_data.get(metric, 0)
                new_val = new_data.get(metric, 0)
                
                if old_val > 0:
                    percent_change = abs(new_val - old_val) / old_val * 100
                    if percent_change > change_threshold:
                        changed_junctions.append(lm.get_string("infra_analyzer.change_metric", percent=f"{percent_change:.1f}", metric=metric, id=j_id))

        if changed_junctions:
            changes_str = ', '.join(changed_junctions)
            return True, lm.get_string("infra_analyzer.summary_changes_detected", changes=changes_str)
        
        return False, lm.get_string("infra_analyzer.summary_no_changes")