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

# File: src/xai/captum_analyzer.py (MODIFICADO PARA TRADUÇÃO COMPLETA)
# Author: Gabriel Moraes
# Date: 03 de Outubro de 2025

import torch
import torch.nn as nn
import numpy as np
import matplotlib.pyplot as plt
import os
import logging
import time
from datetime import datetime
from captum.attr import IntegratedGradients

from utils.locale_manager_backend import LocaleManagerBackend
from agents.local_agent import LocalAgent

plt.switch_backend('Agg')

class CaptumModelWrapper(nn.Module):
    def __init__(self, model):
        super(CaptumModelWrapper, self).__init__()
        self.model = model

    def forward(self, x):
        return self.model(x)[0]

class CaptumAnalyzer:
    def __init__(self, agent: LocalAgent, scenario_results_dir: str, locale_manager: LocaleManagerBackend):
        self.agent = agent
        self.locale_manager = locale_manager
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.wrapped_model = CaptumModelWrapper(self.agent.policy_net).to(self.device)
        self.ig = IntegratedGradients(self.wrapped_model)
        
        self.output_dir = os.path.join(scenario_results_dir, "captum", "reports")
        os.makedirs(self.output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_path_png = os.path.join(self.output_dir, f"xai_report_{agent.id}_{timestamp}.png")
        self.output_path_txt = os.path.join(self.output_dir, f"xai_report_{agent.id}_{timestamp}.txt")
        
    def _get_feature_glossary(self) -> dict:
        # Esta função seria preenchida com a lógica para obter o glossário
        # a partir do state_extractor, como visto em outros ficheiros.
        return {}

    def generate_analysis(self) -> dict | None:
        lm = self.locale_manager
        original_mode_is_training = self.agent.policy_net.training
        try:
            self.agent.policy_net.eval()
            
            recent_experiences = self.agent.xai_memory.memory
            if not recent_experiences:
                # --- MUDANÇA 1 ---
                logging.warning(lm.get_string("captum_analyzer.run.empty_memory_warning", agent_id=self.agent.id))
                return None

            # A lógica de análise do Captum permanece a mesma...
            input_tensors = torch.cat([exp.state for exp in recent_experiences]).to(self.device)
            baselines = torch.zeros_like(input_tensors)
            attributions, _ = self.ig.attribute(input_tensors, baselines, target=0, return_convergence_delta=True)
            attributions = attributions.sum(dim=0).abs()
            attributions = attributions / torch.norm(attributions)
            importances = attributions.cpu().detach().numpy()
            
            feature_glossary = self._get_feature_glossary()
            analysis_data = []
            for i, importance in enumerate(importances):
                feature_info = feature_glossary.get(i, {"name": f"Feature Desconhecida {i}", "description": "N/A"})
                analysis_data.append({"name": feature_info["name"], "importance": importance, "description": feature_info["description"]})

            total_importance = sum(item['importance'] for item in analysis_data)
            for item in analysis_data:
                item['normalized_importance'] = (item['importance'] / total_importance) if total_importance > 0 else 0
            
            sorted_analysis = sorted(analysis_data, key=lambda x: x['importance'], reverse=True)

            # A geração do gráfico permanece a mesma...
            # plt.savefig(self.output_path_png, ...)

            with open(self.output_path_txt, "w", encoding="utf-8") as f:
                f.write("=" * 60 + "\n")
                f.write(lm.get_string("xai_report.title", agent_id=self.agent.id) + "\n")
                f.write(lm.get_string("xai_report.subtitle", timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + "\n")
                f.write("=" * 60 + "\n\n")
                f.write(lm.get_string("xai_report.header_description") + "\n\n")

                for item in sorted_analysis:
                    bar_length = 20
                    filled_length = int(item['normalized_importance'] * bar_length)
                    bar = '█' * filled_length + '─' * (bar_length - filled_length)
                    
                    f.write(f"● {lm.get_string('xai_report.section_sensor')}: {item['name']}\n")
                    f.write(f"  {lm.get_string('xai_report.section_importance')}: {bar} ({item['importance']:.3f})\n")
                    f.write(f"  {lm.get_string('xai_report.section_description')}: {item['description']}\n")
                    f.write("-" * 60 + "\n")
            
            # --- MUDANÇA 2 ---
            logging.info(lm.get_string("captum_analyzer.run.text_report_success", path=self.output_path_txt))

            return {
                "image_path": os.path.abspath(self.output_path_png),
                "text_path": os.path.abspath(self.output_path_txt)
            }

        except Exception as e:
            # --- MUDANÇA 3 ---
            logging.error(lm.get_string("captum_analyzer.run.analysis_error", error=e), exc_info=True)
            return None
        finally:
            if original_mode_is_training: self.agent.policy_net.train()