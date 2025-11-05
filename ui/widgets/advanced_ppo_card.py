# File: ui/widgets/advanced_ppo_card.py (MODIFICADO PARA SUPORTE A TRADUÇÃO)
# Author: Gabriel Moraes
# Date: 29 de Setembro de 2025

"""
Define o AdvancedPPOCard, um widget componente para a tela de Configurações.
"""

import flet as ft
from typing import Dict, Any

# --- MUDANÇA 1: Importar o LocaleManager para anotação de tipo ---
from ui.handlers.locale_manager import LocaleManager

class AdvancedPPOCard(ft.Card):
    """
    Um Card que encapsula as configurações avançadas do Agente PPO.
    """
    def __init__(self, initial_values: Dict[str, Any]):
        """
        Inicializa o Card com os valores fornecidos.
        """
        super().__init__()

        numeric_filter = ft.InputFilter(allow=True, regex_string=r"[0-9.-]")

        # --- Controles ---
        self.title_text = ft.Text(size=18, weight=ft.FontWeight.BOLD)
        self.tf_performance_margin = ft.TextField(
            value=initial_values.get('performance_margin', '-100.0'),
            input_filter=numeric_filter
        )
        self.tf_ppo_gamma = ft.TextField(
            value=initial_values.get('ppo_gamma', '0.99'),
            input_filter=numeric_filter
        )
        self.tf_ppo_k_epochs = ft.TextField(
            value=initial_values.get('ppo_k_epochs', '4'),
            input_filter=numeric_filter
        )
        self.tf_ppo_eps_clip = ft.TextField(
            value=initial_values.get('ppo_eps_clip', '0.2'),
            input_filter=numeric_filter
        )
        
        # --- Estrutura do Card ---
        self.content = ft.Container(
            padding=15,
            content=ft.Column([
                self.title_text,
                ft.Divider(),
                self.tf_ppo_gamma,
                self.tf_ppo_k_epochs,
                self.tf_ppo_eps_clip,
                self.tf_performance_margin
            ])
        )

    def get_values(self) -> Dict[str, Any]:
        """
        Retorna um dicionário com os valores atuais dos controles neste card.
        """
        return {
            'performance_margin': self.tf_performance_margin.value,
            'ppo_gamma': self.tf_ppo_gamma.value,
            'ppo_k_epochs': self.tf_ppo_k_epochs.value,
            'ppo_eps_clip': self.tf_ppo_eps_clip.value,
        }

    def set_values(self, values: Dict[str, Any]):
        """
        Atualiza os valores dos controles neste card com base no dicionário fornecido.
        """
        self.tf_performance_margin.value = values.get('performance_margin', '-100.0')
        self.tf_ppo_gamma.value = values.get('ppo_gamma', '0.99')
        self.tf_ppo_k_epochs.value = values.get('ppo_k_epochs', '4')
        self.tf_ppo_eps_clip.value = values.get('ppo_eps_clip', '0.2')
        if self.page: self.update()

    # --- MUDANÇA 2: Novo método para traduzir o widget ---
    def update_translations(self, lm: LocaleManager):
        """Atualiza os textos deste card com base no LocaleManager."""
        self.title_text.value = lm.get_string("settings_view.advanced_ppo_card.title")
        self.tf_performance_margin.label = lm.get_string("settings_view.advanced_ppo_card.performance_margin")
        self.tf_ppo_gamma.label = lm.get_string("settings_view.advanced_ppo_card.gamma")
        self.tf_ppo_k_epochs.label = lm.get_string("settings_view.advanced_ppo_card.k_epochs")
        self.tf_ppo_eps_clip.label = lm.get_string("settings_view.advanced_ppo_card.eps_clip")
        if self.page: self.update()