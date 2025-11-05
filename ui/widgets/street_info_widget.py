# File: ui/widgets/street_info_widget.py (MODIFICADO PARA SUPORTE A TRADUÇÃO)
# Author: Gabriel Moraes
# Date: 29 de Setembro de 2025

"""
Define o StreetInfoWidget.
"""

import flet as ft
from typing import Callable, Dict

# --- MUDANÇA 1: Importar o LocaleManager ---
from handlers.locale_manager import LocaleManager

class StreetInfoWidget(ft.Card):
    """
    Um Card que exibe os dados de uma rua e pode ser escondido.
    """
    def __init__(
        self,
        locale_manager: LocaleManager, # <-- Recebe o gerenciador
        on_close: Callable[[], None] = None
    ):
        super().__init__(
            elevation=4,
            visible=False,
            animate_opacity=200
        )

        # --- MUDANÇA 2: Armazenar o LocaleManager e refatorar controles ---
        self.locale_manager = locale_manager
        self.on_close = on_close
        self.street_id_text_template = "" # Template para o título
        
        # Controles de texto para os labels (para que possam ser traduzidos)
        self.street_id_text = ft.Text(weight=ft.FontWeight.BOLD)
        self.congestion_label = ft.Text()
        self.flow_label = ft.Text()
        self.speed_label = ft.Text()
        self.vehicles_label = ft.Text()
        
        # Controles de texto para os valores
        self.congestion_text = ft.Text("--")
        self.flow_text = ft.Text("--")
        self.speed_text = ft.Text("--")
        self.vehicles_text = ft.Text("--")
        
        self.content = ft.Container(
            padding=10,
            content=ft.Column(
                [
                    ft.Row(
                        [ft.Icon(ft.Icons.EDIT_ROAD_ROUNDED), self.street_id_text],
                    ),
                    ft.Divider(height=10),
                    ft.Row([self.congestion_label, self.congestion_text]),
                    ft.Row([self.flow_label, self.flow_text]),
                    ft.Row([self.speed_label, self.speed_text]),
                    ft.Row([self.vehicles_label, self.vehicles_text]),
                    ft.IconButton(
                        icon=ft.Icons.CLOSE_ROUNDED,
                        on_click=self.hide,
                        tooltip="Fechar painel" # Este tooltip será traduzido no pai
                    )
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER
            )
        )

    def did_mount(self):
        """Chamado quando o widget é montado na página."""
        self.update_translations(self.locale_manager)
        if self.page: self.update()

    # --- MUDANÇA 3: Novo método para traduzir o widget ---
    def update_translations(self, lm: LocaleManager):
        """Atualiza todos os textos deste widget com base no LocaleManager."""
        self.street_id_text_template = lm.get_string("dashboard_view.street_info_title_prefix")
        self.congestion_label.value = lm.get_string("dashboard_view.street_congestion")
        self.flow_label.value = lm.get_string("dashboard_view.street_flow")
        self.speed_label.value = lm.get_string("dashboard_view.street_speed")
        self.vehicles_label.value = lm.get_string("dashboard_view.street_vehicles")
        # O tooltip do botão de fechar é traduzido pelo seu widget pai (SpecificControlsWidget)
        
    def update_and_show(self, street_id: str, street_data: Dict):
        """
        Atualiza os campos de texto com novos dados e torna o widget visível.
        """
        # --- MUDANÇA 4: Usar o template de tradução para o texto dinâmico ---
        self.street_id_text.value = f"{self.street_id_text_template} {street_id}"
        
        congestion = street_data.get('congestion', 0.0)
        flow = street_data.get('flow', '--')
        speed = street_data.get('speed', 0.0)
        vehicles = street_data.get('vehicles', '--')

        self.congestion_text.value = f"{congestion:.1f}" # A unidade (%) virá do label
        self.flow_text.value = str(flow)
        self.speed_text.value = f"{speed:.1f} km/h"
        self.vehicles_text.value = str(vehicles)
        
        self.visible = True

    def hide(self, e=None):
        """
        Torna o widget invisível e notifica o pai.
        """
        self.visible = False
        if self.on_close:
            self.on_close()