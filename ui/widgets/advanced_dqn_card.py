# File: ui/widgets/advanced_dqn_card.py (MODIFICADO PARA SUPORTE A TRADUÇÃO)
# Author: Gabriel Moraes
# Date: 29 de Setembro de 2025

"""
Define o AdvancedDQNCard, um widget componente para a tela de Configurações.
"""

import flet as ft
from typing import Dict, Any

# --- MUDANÇA 1: Importar o LocaleManager para anotação de tipo ---
from ui.handlers.locale_manager import LocaleManager

class AdvancedDQNCard(ft.Card):
    """
    Um Card que encapsula as configurações avançadas do Agente DQN.
    """
    def __init__(self, initial_values: Dict[str, Any]):
        """
        Inicializa o Card com os valores fornecidos.
        """
        super().__init__()

        numeric_filter = ft.InputFilter(allow=True, regex_string=r"[0-9.-]")

        # --- Controles ---
        self.title_text = ft.Text(size=18, weight=ft.FontWeight.BOLD)
        self.tf_dqn_epsilon_decay = ft.TextField(
            value=initial_values.get('dqn_epsilon_decay', '30000'),
            input_filter=numeric_filter
        )
        self.tf_dqn_batch_size = ft.TextField(
            value=initial_values.get('dqn_batch_size', '128'),
            input_filter=numeric_filter
        )
        
        # --- Estrutura do Card ---
        self.content = ft.Container(
            padding=15,
            content=ft.Column([
                self.title_text,
                ft.Divider(),
                self.tf_dqn_epsilon_decay,
                self.tf_dqn_batch_size
            ])
        )

    def get_values(self) -> Dict[str, Any]:
        """
        Retorna um dicionário com os valores atuais dos controles neste card.
        """
        return {
            'dqn_epsilon_decay': self.tf_dqn_epsilon_decay.value,
            'dqn_batch_size': self.tf_dqn_batch_size.value,
        }

    def set_values(self, values: Dict[str, Any]):
        """
        Atualiza os valores dos controles neste card com base no dicionário fornecido.
        """
        self.tf_dqn_epsilon_decay.value = values.get('dqn_epsilon_decay', '30000')
        self.tf_dqn_batch_size.value = values.get('dqn_batch_size', '128')
        if self.page: self.update()

    # --- MUDANÇA 2: Novo método para traduzir o widget ---
    def update_translations(self, lm: LocaleManager):
        """Atualiza os textos deste card com base no LocaleManager."""
        self.title_text.value = lm.get_string("settings_view.advanced_dqn_card.title")
        self.tf_dqn_epsilon_decay.label = lm.get_string("settings_view.advanced_dqn_card.epsilon_decay")
        self.tf_dqn_batch_size.label = lm.get_string("settings_view.advanced_dqn_card.batch_size")
        if self.page: self.update()