# File: ui/widgets/advanced_system_card.py (MODIFICADO PARA SUPORTE A TRADUÇÃO)
# Author: Gabriel Moraes
# Date: 29 de Setembro de 2025

"""
Define o AdvancedSystemCard, um widget componente para a tela de Configurações.
"""

import flet as ft
from typing import Dict, Any

# --- MUDANÇA 1: Importar o LocaleManager para anotação de tipo ---
from ui.handlers.locale_manager import LocaleManager

class AdvancedSystemCard(ft.Card):
    """
    Um Card que encapsula as configurações avançadas de Treinamento e Sistema.
    """
    def __init__(self, initial_values: Dict[str, Any]):
        """
        Inicializa o Card com os valores fornecidos.
        """
        super().__init__()

        numeric_filter = ft.InputFilter(allow=True, regex_string=r"[0-9.-]")

        # --- Controles ---
        self.title_text = ft.Text(size=18, weight=ft.FontWeight.BOLD)
        self.tf_pbt_frequency = ft.TextField(
            value=initial_values.get('pbt_frequency', '10'),
            input_filter=numeric_filter
        )
        self.tf_pbt_exploitation = ft.TextField(
            value=initial_values.get('pbt_exploitation', '25'),
            input_filter=numeric_filter
        )
        self.tf_watchdog_grace = ft.TextField(
            value=initial_values.get('watchdog_grace', '30'),
            input_filter=numeric_filter
        )
        self.tf_infra_analysis_freq = ft.TextField(
            value=initial_values.get('infra_analysis_freq', '1'),
            input_filter=numeric_filter
        )
        
        # --- Estrutura do Card ---
        self.content = ft.Container(
            padding=15,
            content=ft.Column([
                self.title_text,
                ft.Divider(),
                self.tf_pbt_frequency,
                self.tf_pbt_exploitation,
                self.tf_watchdog_grace,
                self.tf_infra_analysis_freq
            ])
        )

    def get_values(self) -> Dict[str, Any]:
        """
        Retorna um dicionário com os valores atuais dos controles neste card.
        """
        return {
            'pbt_frequency': self.tf_pbt_frequency.value,
            'pbt_exploitation': self.tf_pbt_exploitation.value,
            'watchdog_grace': self.tf_watchdog_grace.value,
            'infra_analysis_freq': self.tf_infra_analysis_freq.value,
        }

    def set_values(self, values: Dict[str, Any]):
        """
        Atualiza os valores dos controles neste card com base no dicionário fornecido.
        """
        self.tf_pbt_frequency.value = values.get('pbt_frequency', '10')
        self.tf_pbt_exploitation.value = values.get('pbt_exploitation', '25')
        self.tf_watchdog_grace.value = values.get('watchdog_grace', '30')
        self.tf_infra_analysis_freq.value = values.get('infra_analysis_freq', '1')
        if self.page: self.update()

    # --- MUDANÇA 2: Novo método para traduzir o widget ---
    def update_translations(self, lm: LocaleManager):
        """Atualiza os textos deste card com base no LocaleManager."""
        self.title_text.value = lm.get_string("settings_view.advanced_system_card.title")
        self.tf_pbt_frequency.label = lm.get_string("settings_view.advanced_system_card.pbt_frequency")
        self.tf_pbt_exploitation.label = lm.get_string("settings_view.advanced_system_card.pbt_exploitation")
        self.tf_watchdog_grace.label = lm.get_string("settings_view.advanced_system_card.watchdog_grace")
        self.tf_infra_analysis_freq.label = lm.get_string("settings_view.advanced_system_card.infra_analysis_freq")
        if self.page: self.update()