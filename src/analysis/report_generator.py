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

# File: src/analysis/report_generator.py (CORREÇÃO DEFINITIVA - SyntaxError f-string)
# Author: Gabriel Moraes
# Date: 01 de Outubro de 2025

from datetime import datetime
import sys
import os
from typing import TYPE_CHECKING

# Adiciona o diretório 'src' ao path para permitir importações absolutas
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

if TYPE_CHECKING:
    from utils.locale_manager_backend import LocaleManagerBackend

class ReportGenerator:
    """Formata os resultados da análise num relatório de texto."""

    def __init__(self, analysis_results: dict, analysis_params: dict, scenario_name: str, locale_manager: 'LocaleManagerBackend'):
        """
        Inicializa o gerador de relatórios.
        """
        self.results = analysis_results
        self.params = analysis_params
        self.scenario_name = scenario_name
        self.locale_manager = locale_manager

    def generate_txt_report(self) -> str:
        """
        Gera o conteúdo completo do relatório formatado como uma string.
        """
        lm = self.locale_manager
        analysis_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
        sim_duration = 86400.0

        add_count = len([r for r in self.results.values() if lm.get_string("warrant_evaluator.rec_add") in r['recommendation']])
        remove_count = len([r for r in self.results.values() if lm.get_string("warrant_evaluator.rec_remove") in r['recommendation']])
        keep_count = len([r for r in self.results.values() if lm.get_string("warrant_evaluator.rec_keep") in r['recommendation']])
        
        p = self.params
        report = [
            lm.get_string("report_generator.header.title1"),
            lm.get_string("report_generator.header.title2"),
            lm.get_string("report_generator.header.title3"),
            f"\n{lm.get_string('report_generator.general_data.title')}",
            "----------------------------------------------------------------------",
            f"* {lm.get_string('report_generator.general_data.scenario')}:         {self.scenario_name}",
            f"* {lm.get_string('report_generator.general_data.date')}:           {analysis_date}",
            f"* {lm.get_string('report_generator.general_data.duration')}: 24 horas ({sim_duration} segundos)",
            f"\n{lm.get_string('report_generator.summary.title')}",
            "----------------------------------------------------------------------",
            f"* {lm.get_string('report_generator.summary.junctions_analyzed')}: {len(self.results)}",
            f"* {lm.get_string('report_generator.summary.recommendations', add=add_count, remove=remove_count, keep=keep_count)}",
            f"\n{lm.get_string('report_generator.parameters.title')}",
            "----------------------------------------------------------------------",
            f"* {lm.get_string('report_generator.parameters.min_vol_primary')}:   {p.get('min_volume_primary', 'N/A')} vph",
            f"* {lm.get_string('report_generator.parameters.min_vol_secondary')}:  {p.get('min_volume_secondary', 'N/A')} vph",
            f"* {lm.get_string('report_generator.parameters.unacceptable_delay')}:         {p.get('unacceptable_delay', 'N/A')} segundos",
            f"* {lm.get_string('report_generator.parameters.conflict_threshold')}:   {p.get('conflict_threshold', 'N/A')} eventos/dia",
            f"* {lm.get_string('report_generator.parameters.removal_threshold')}: {p.get('removal_threshold_percent', 'N/A')}%",
            f"\n\n{lm.get_string('report_generator.detailed_rec.title1')}",
            f"{lm.get_string('report_generator.detailed_rec.title2')}",
            f"{lm.get_string('report_generator.detailed_rec.title3')}"
        ]

        for j_id, result in sorted(self.results.items()):
            w = result['warrants']
            d = result['data']
            
            satisfied_str = lm.get_string('report_generator.junction.warrant_satisfied')
            not_satisfied_str = lm.get_string('report_generator.junction.warrant_not_satisfied')
            
            report.extend([
                f"\n----------------------------------------------------------------------",
                f">>> {lm.get_string('report_generator.junction.title', id=j_id)}",
                f"----------------------------------------------------------------------",
                f"* {lm.get_string('report_generator.junction.recommendation')}:     {result.get('recommendation', 'N/A')}",
                f"* {lm.get_string('report_generator.junction.current_status')}:         {result.get('current_status', 'N/A')}",
                f"* {lm.get_string('report_generator.junction.justification')}:  {result.get('justification', 'N/A')}",
                f"* {lm.get_string('report_generator.junction.warrants_analysis')}:",
                f"  - [{'✔️' if w.get('volume') else '❌'}] {lm.get_string('report_generator.junction.warrant1_volume')}: {satisfied_str if w.get('volume') else not_satisfied_str}",
                f"  - [{'✔️' if w.get('delay') else '❌'}] {lm.get_string('report_generator.junction.warrant2_delay')}: {satisfied_str if w.get('delay') else not_satisfied_str}",
                f"  - [{'✔️' if w.get('safety') else '❌'}] {lm.get_string('report_generator.junction.warrant4_safety')}: {satisfied_str if w.get('safety') else not_satisfied_str}",
                f"\n* {lm.get_string('report_generator.junction.observed_data')}:",
            ])
            
            if result.get('recommendation') == lm.get_string("warrant_evaluator.rec_remove"):
                removal_thresh = p.get('min_volume_primary', 0) * (p.get('removal_threshold_percent', 0) / 100.0)
                report.append(f"  - {lm.get_string('report_generator.junction.volume_primary_keep', value=d.get('vol_primary_val', 0), threshold=f'{removal_thresh:.0f}')}")
            else:
                report.append(f"  - {lm.get_string('report_generator.junction.volume_primary', value=d.get('vol_primary_val', 0), threshold=p.get('min_volume_primary', 'N/A'))}")

            # --- CORREÇÃO COMPLETA DAS F-STRINGS ---
            # Corrigindo todas as f-strings problemáticas
            volume_secondary_str = f"  - {lm.get_string('report_generator.junction.volume_secondary', value=d.get('vol_secondary_val', 0), threshold=p.get('min_volume_secondary', 'N/A'))}"
            avg_delay_value = f"{d.get('avg_delay', 0):.0f}"
            avg_delay_str = f"  - {lm.get_string('report_generator.junction.avg_delay', value=avg_delay_value, threshold=p.get('unacceptable_delay', 'N/A'))}"
            conflict_events_str = f"  - {lm.get_string('report_generator.junction.conflict_events', value=d.get('conflict_events', 0), threshold=p.get('conflict_threshold', 'N/A'))}"
            
            report.extend([
                volume_secondary_str,
                avg_delay_str,
                conflict_events_str
            ])
            # --- FIM DA CORREÇÃO ---

        report.extend([
            f"\n\n{lm.get_string('report_generator.footer.title1')}",
            f"{lm.get_string('report_generator.footer.title2')}",
            f"{lm.get_string('report_generator.footer.title3')}",
            lm.get_string('report_generator.footer.generated_by')
        ])
        
        return "\n".join(report)