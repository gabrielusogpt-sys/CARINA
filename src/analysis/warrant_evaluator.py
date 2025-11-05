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

# File: src/analysis/report_generator.py
# Author: Gabriel Moraes
# Date: 01 de Outubro de 2025

# -*- coding: utf-8 -*-
import logging
import os
import pandas as pd
from datetime import datetime
from utils.settings_manager import SettingsManager
from utils.locale_manager_backend import LocaleManager

# Configuração do Logger
logger = logging.getLogger(__name__)

class ReportGenerator:
    """
    Gera relatórios técnicos detalhados com base nos dados de análise de infraestrutura.
    """
    def __init__(self, settings_manager, locale_manager, data):
        self.settings = settings_manager
        self.lm = locale_manager
        self.analysis_data = data
        self.timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.report_dir = self.settings.get('Paths', 'analysis_reports')
        os.makedirs(self.report_dir, exist_ok=True)
        
        self.parameters = {
            'min_vph': self.settings.getint('AnalysisParameters', 'warrant_min_vph'),
            'min_vph_minor': self.settings.getint('AnalysisParameters', 'warrant_min_vph_minor'),
            'unacceptable_delay': self.settings.getint('AnalysisParameters', 'unacceptable_delay_threshold'),
            'unacceptable_queue': self.settings.getint('AnalysisParameters', 'unacceptable_queue_threshold'),
        }

    def generate_report(self, junction_id):
        """
        Gera um relatório técnico para um cruzamento específico.
        """
        logger.info(self.lm.get_string('report_generator.logging.generating_report', junction_id=junction_id))
        
        data = self.analysis_data.get(junction_id)
        if not data:
            logger.warning(self.lm.get_string('report_generator.logging.no_data', junction_id=junction_id))
            return None

        file_path = os.path.join(self.report_dir, f"report_{junction_id}_{self.timestamp}.txt")
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(self.lm.get_string('report_generator.header.title') + "\n")
                f.write("=" * 80 + "\n")
                f.write(self.lm.get_string('report_generator.header.junction_id', junction_id=junction_id) + "\n")
                f.write(self.lm.get_string('report_generator.header.report_date', timestamp=self.timestamp) + "\n")
                f.write(self.lm.get_string('report_generator.header.analysis_period', hours=data.get('analysis_hours', 'N/A')) + "\n")
                f.write("-" * 80 + "\n\n")

                # 1. Sumário da Recomendação
                f.write(self.lm.get_string('report_generator.recommendation.title') + "\n")
                f.write("-" * 30 + "\n")
                f.write(f"{self.lm.get_string('report_generator.recommendation.status')}: {self.lm.get_string('recommendation.' + data.get('recommendation', 'error'))}\n")
                f.write(f"{self.lm.get_string('report_generator.recommendation.reason')}: {self.lm.get_string(data.get('reason', 'reason.unknown'))}\n")
                f.write("\n")

                # 2. Análise de Métricas de Desempenho
                f.write(self.lm.get_string('report_generator.performance.title') + "\n")
                f.write("-" * 30 + "\n")
                f.write(self._format_metrics(data.get('performance_metrics', {}), self.parameters))
                f.write("\n")

                # 3. Avaliação de 'Warrants' (Critérios Técnicos)
                f.write(self.lm.get_string('report_generator.warrants.title') + "\n")
                f.write("-" * 30 + "\n")
                f.write(self._format_warrants(data.get('warrant_analysis', {}), self.parameters))
                f.write("\n")

                # 4. Dados Brutos (DataFrame)
                f.write(self.lm.get_string('report_generator.raw_data.title') + "\n")
                f.write("-" * 30 + "\n")
                df = pd.DataFrame(data.get('hourly_data', []))
                f.write(df.to_string(index=False))
                f.write("\n\n")

                f.write("=" * 80 + "\n")
                f.write(self.lm.get_string('report_generator.footer.end_of_report') + "\n")
            
            logger.info(self.lm.get_string('report_generator.logging.report_success', junction_id=junction_id, file_path=file_path))
            return file_path

        except IOError as e:
            logger.error(self.lm.get_string('report_generator.logging.report_fail', junction_id=junction_id, error=str(e)))
            return None
        except Exception as e:
            logger.error(self.lm.get_string('report_generator.logging.report_fail_generic', junction_id=junction_id, error=str(e)))
            return None

    def _format_metrics(self, data, params):
        """Formata a seção de métricas de desempenho."""
        p = params
        d = data
        summary = []
        summary.append(self.lm.get_string('report_generator.performance.total_vehicles', value=d.get('total_vehicles', 0)))
        summary.append(self.lm.get_string('report_generator.performance.peak_hour_volume', value=d.get('peak_vph', 0), hour=d.get('peak_hour', 'N/A')))
        
        # --- CORREÇÃO (SyntaxError e NameError) ---
        summary.append(
            (self.lm.get_string('report_generator.junction.avg_queue', value=f'{d.get('avg_queue', 0):.0f}', threshold=p.get('unacceptable_queue', 'N/A'))),
            (self.lm.get_string('report_generator.junction.avg_delay', value=f'{d.get('avg_delay', 0):.0f}', threshold=p.get('unacceptable_delay', 'N/A')))
        )
        # --- FIM DA CORREÇÃO ---
        return "\n".join(summary)

    def _format_warrants(self, data, params):
        """Formata a seção de análise de warrants."""
        p = params
        summary = []

        # Warrant 1: Volume Mínimo
        w1 = data.get('W1_MinVehicularVolume', {})
        summary.append(self.lm.get_string('report_generator.warrants.w1.title'))
        summary.append(self.lm.get_string('report_generator.warrants.w1.met', status=self.lm.get_string(f"boolean.{w1.get('met', False)}")))
        summary.append(self.lm.get_string('report_generator.warrants.w1.hours_met', hours=w1.get('hours_met', 0), required=w1.get('required_hours', 'N/A')))
        summary.append(self.lm.get_string('report_generator.warrants.w1.peak_vph_major', value=w1.get('peak_vph_major', 0), threshold=p.get('min_vph', 'N/A')))
        summary.append(self.lm.get_string('report_generator.warrants.w1.peak_vph_minor', value=w1.get('peak_vph_minor', 0), threshold=p.get('min_vph_minor', 'N/A')))
        summary.append("") # Espaçador

        # Warrant 2: Interrupção de Tráfego
        w2 = data.get('W2_InterruptionOfContinuousTraffic', {})
        summary.append(self.lm.get_string('report_generator.warrants.w2.title'))
        summary.append(self.lm.get_string('report_generator.warrants.w2.met', status=self.lm.get_string(f"boolean.{w2.get('met', False)}")))
        summary.append(self.lm.get_string('report_generator.warrants.w2.hours_met_major', hours=w2.get('hours_met_major', 0), required=w2.get('required_hours', 'N/A')))
        summary.append(self.lm.get_string('report_generator.warrants.w2.peak_vph_major', value=w2.get('peak_vph_major', 0), threshold=w2.get('threshold_major', 'N/A')))
        summary.append(self.lm.get_string('report_generator.warrants.w2.peak_vph_minor', value=w2.get('peak_vph_minor', 0), threshold=w2.get('threshold_minor', 'N/A')))
        summary.append("") # Espaçador
        
        # --- CÓDIGO ADICIONADO ---

        # Warrant 3: Pico Horário (Atraso/Fila)
        w3 = data.get('W3_PeakHour', {})
        summary.append(self.lm.get_string('report_generator.warrants.w3.title'))
        summary.append(self.lm.get_string('report_generator.warrants.w3.met', status=self.lm.get_string(f"boolean.{w3.get('met', False)}")))
        summary.append(self.lm.get_string('report_generator.warrants.w3.reason', reason=self.lm.get_string(w3.get('reason', 'reason.not_applicable'))))
        summary.append(self.lm.get_string('report_generator.warrants.w3.peak_delay', value=f"{w3.get('peak_delay', 0):.0f}", threshold=p.get('unacceptable_delay', 'N/A')))
        summary.append(self.lm.get_string('report_generator.warrants.w3.peak_queue', value=f"{w3.get('peak_queue', 0):.0f}", threshold=p.get('unacceptable_queue', 'N/A')))
        summary.append("") # Espaçador

        # Warrant 4: Volume de Pedestres
        w4 = data.get('W4_PedestrianVolume', {})
        summary.append(self.lm.get_string('report_generator.warrants.w4.title'))
        summary.append(self.lm.get_string('report_generator.warrants.w4.met', status=self.lm.get_string(f"boolean.{w4.get('met', False)}")))
        summary.append(self.lm.get_string('report_generator.warrants.w4.hours_met', hours=w4.get('hours_met', 0), required=w4.get('required_hours', 'N/A')))
        summary.append(self.lm.get_string('report_generator.warrants.w4.peak_ped_volume', value=w4.get('peak_ped_volume', 0), threshold=w4.get('threshold_ped', 'N/A')))
        summary.append("") # Espaçador

        # --- FIM DO CÓDIGO ADICIONADO ---

        return "\n".join(summary)