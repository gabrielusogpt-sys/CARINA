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

# File: src/analysis/warrant_evaluator.py
# Author: Gabriel Moraes
# Date: 01 de Outubro de 2025

# -*- coding: utf-8 -*-
import logging
import pandas as pd
from utils.settings_manager import SettingsManager

logger = logging.getLogger(__name__)

class WarrantEvaluator:
    """
    Avalia os 'warrants' (critérios técnicos de engenharia de tráfego) para
    determinar a necessidade de um semáforo.
    """
    def __init__(self, settings_manager):
        self.settings = settings_manager
        logger.debug("WarrantEvaluator inicializado.")

    def evaluate_warrants(self, junction_id, hourly_data_df):
        """
        Executa todas as avaliações de warrants para um determinado cruzamento.
        """
        results = {}
        
        # Obter dados agregados para o W1 e W2
        aggregated_data = self._aggregate_data_for_warrants(hourly_data_df)
        
        # Warrant 1: Volume Veicular Mínimo
        results['W1_MinVehicularVolume'] = self._evaluate_warrant_1(junction_id, hourly_data_df)
        
        # Warrant 2: Interrupção de Tráfego Contínuo
        results['W2_InterruptionOfContinuousTraffic'] = self._evaluate_warrant_2(junction_id, aggregated_data)
        
        # Warrant 3: Pico Horário (Atraso/Fila)
        results['W3_PeakHour'] = self._evaluate_warrant_3(junction_id, aggregated_data, hourly_data_df)

        # Warrant 4: Volume de Pedestres
        results['W4_PedestrianVolume'] = self._evaluate_warrant_4(junction_id, hourly_data_df)
        
        return results

    def _aggregate_data_for_warrants(self, hourly_data_df):
        """
        Agrega dados horários para métricas de desempenho de todo o período.
        """
        if hourly_data_df.empty:
            return {
                'total_vehicles': 0,
                'avg_delay_stopped': 0,
                'avg_queue_length': 0,
                'peak_vph': 0,
                'peak_hour': -1,
                'analysis_hours': 0
            }
            
        total_vehicles = hourly_data_df['total_vehicles'].sum()
        avg_delay = hourly_data_df['avg_delay_stopped'].mean()
        avg_queue = hourly_data_df['avg_queue_length'].mean()
        peak_vph = hourly_data_df['total_vehicles'].max()
        peak_hour = hourly_data_df['total_vehicles'].idxmax()
        analysis_hours = len(hourly_data_df)

        return {
            'total_vehicles': total_vehicles,
            'avg_delay_stopped': avg_delay,
            'avg_queue_length': avg_queue,
            'peak_vph': peak_vph,
            'peak_hour': peak_hour,
            'analysis_hours': analysis_hours
        }

    def _evaluate_warrant_1(self, junction_id, hourly_data_df):
        """
        Warrant 1: Condição de Volume Mínimo (Exemplo baseado no MUTCD)
        Verifica se os volumes horários excedem os mínimos por 8 horas.
        """
        logger.debug(f"Avaliando Warrant 1 (Min Volume) para {junction_id}")
        
        # Limiares (devem vir do settings.ini)
        min_vph_major = self.settings.getint('AnalysisParameters', 'warrant_min_vph')
        min_vph_minor = self.settings.getint('AnalysisParameters', 'warrant_min_vph_minor')
        required_hours = self.settings.getint('AnalysisParameters', 'warrant_required_hours')
        
        # Simulação de dados (no sistema real, isso viria do data collector)
        # Aqui, estamos a usar os dados horários agregados
        
        hours_met = 0
        peak_vph_major = 0
        peak_vph_minor = 0
        
        if not hourly_data_df.empty:
            # Simplificação: Usamos o volume total como 'major' e 1/3 como 'minor' para fins de teste
            # No mundo real, 'vph_major' e 'vph_minor' viriam separados do data collector
            hourly_data_df['vph_major_calc'] = hourly_data_df['total_vehicles']
            hourly_data_df['vph_minor_calc'] = hourly_data_df['total_vehicles'] / 3 # Suposição
            
            warrant_met_df = hourly_data_df[
                (hourly_data_df['vph_major_calc'] >= min_vph_major) &
                (hourly_data_df['vph_minor_calc'] >= min_vph_minor)
            ]
            hours_met = len(warrant_met_df)
            
            peak_vph_major = hourly_data_df['vph_major_calc'].max()
            peak_vph_minor = hourly_data_df['vph_minor_calc'].max()

        met = hours_met >= required_hours
        
        return {
            'met': met,
            'hours_met': hours_met,
            'required_hours': required_hours,
            'peak_vph_major': peak_vph_major,
            'peak_vph_minor': peak_vph_minor
        }

    def _evaluate_warrant_2(self, junction_id, aggregated_data):
        """
        Warrant 2: Interrupção de Tráfego Contínuo (Exemplo)
        Verifica se o volume da via principal é tão alto que impede o tráfego da via menor.
        """
        logger.debug(f"Avaliando Warrant 2 (Interruption) para {junction_id}")
        
        # Limiares (exemplo)
        threshold_major = 700 # VPH na via principal
        threshold_minor = 70  # VPH na via menor
        required_hours = self.settings.getint('AnalysisParameters', 'warrant_required_hours')
        
        # Simulação (WIP - Lógica de exemplo)
        # Esta lógica precisaria de dados mais detalhados
        peak_vph_major = aggregated_data.get('peak_vph', 0) # Usando VPH total como 'major'
        peak_vph_minor = peak_vph_major / 3 # Suposição
        hours_met_major = 0 # Simulação
        
        if peak_vph_major > threshold_major and peak_vph_minor > threshold_minor:
            hours_met_major = required_hours # Simulação de que foi atingido
            
        met = hours_met_major >= required_hours

        return {
            'met': met,
            'hours_met_major': hours_met_major,
            'required_hours': required_hours,
            'peak_vph_major': peak_vph_major,
            'threshold_major': threshold_major,
            'peak_vph_minor': peak_vph_minor,
            'threshold_minor': threshold_minor
        }

    def _evaluate_warrant_3(self, junction_id, data, hourly_data_df):
        """
        Warrant 3: Peak Hour
        Avalia se o tráfego de pico justifica um semáforo com base em atrasos ou filas.
        """
        logger.debug(f"Avaliando Warrant 3 (Peak Hour) para {junction_id}")
        
        unacceptable_delay = self.settings.getint('AnalysisParameters', 'unacceptable_delay_threshold')
        unacceptable_queue = self.settings.getint('AnalysisParameters', 'unacceptable_queue_threshold')
        
        peak_hour_data = hourly_data_df.loc[hourly_data_df['total_vehicles'].idxmax()]
        
        peak_delay = peak_hour_data.get('avg_delay_stopped', 0)
        peak_queue = peak_hour_data.get('avg_queue_length', 0)
        
        met = False
        reason = "reason.w3.conditions_not_met"

        if peak_delay > unacceptable_delay:
            met = True
            reason = "reason.w3.unacceptable_delay"
        elif peak_queue > unacceptable_queue:
            met = True
            reason = "reason.w3.unacceptable_queue"
            
        return {
            'met': met,
            'reason': reason,
            'peak_delay': peak_delay,
            'peak_queue': peak_queue
        }

    def _evaluate_warrant_4(self, junction_id, hourly_data_df):
        """
        Warrant 4: Volume de Pedestres (Exemplo)
        """
        logger.debug(f"Avaliando Warrant 4 (Pedestrian) para {junction_id}")
        
        # Limiares (exemplo)
        threshold_ped = 100 # Pedestres por hora
        required_hours = 4  # (Diferente do W1/W2)
        
        # Simulação (WIP - Lógica de exemplo)
        # O data collector precisaria fornecer 'ped_volume_hourly'
        
        # Vamos assumir 0 por agora, pois não temos dados de pedestres
        peak_ped_volume = 0 
        hours_met = 0
        
        if 'ped_volume_hourly' in hourly_data_df.columns:
            peak_ped_volume = hourly_data_df['ped_volume_hourly'].max()
            hours_met = len(hourly_data_df[hourly_data_df['ped_volume_hourly'] >= threshold_ped])
        else:
            logger.warning(f"Sem dados de 'ped_volume_hourly' para Warrant 4 em {junction_id}. Assumindo 0.")

        met = hours_met >= required_hours

        return {
            'met': met,
            'hours_met': hours_met,
            'required_hours': required_hours,
            'peak_ped_volume': peak_ped_volume,
            'threshold_ped': threshold_ped
        }