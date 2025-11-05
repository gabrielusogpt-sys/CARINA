# File: ui/widgets/xai_viewer_widget.py (CORRIGIDO)
# Author: Gabriel Moraes
# Date: 01 de Outubro de 2025

"""
Define o XaiViewerWidget.

Nesta versão, o carregamento da lista de agentes foi tornado assíncrono
para que a UI não congele ao abrir a aba de Diagnóstico.
"""

import flet as ft
import os
from typing import List

from ui.handlers.locale_manager import LocaleManager
from ui.clients.xai_client import XaiClient
from ui.widgets.plot_viewer_widget import PlotViewerWidget
from ui.widgets.explanation_viewer_widget import ExplanationViewerWidget

class XaiViewerWidget(ft.Container):
    def __init__(self, locale_manager: LocaleManager):
        super().__init__(expand=True)
        
        self.locale_manager = locale_manager
        # --- MUDANÇA 1: O nome do callback foi clarificado ---
        self.client = XaiClient(on_analysis_complete_callback=self.on_analysis_complete)
        
        self.title_text = ft.Text(size=20, weight=ft.FontWeight.BOLD)
        
        # O dropdown começa desativado e com uma mensagem de "a carregar"
        self.agent_dropdown = ft.Dropdown(options=[], expand=True, disabled=True, hint_text="A carregar lista de agentes...")
        
        self.analyze_button = ft.ElevatedButton(icon=ft.Icons.ANALYTICS_ROUNDED, on_click=self.run_analysis_click, width=300, disabled=True)
        self.status_text = ft.Text(italic=True)
        self.plot_viewer = PlotViewerWidget()
        self.explanation_viewer = ExplanationViewerWidget()
        
        self.analysis_results_container = ft.Row(
            controls=[self.plot_viewer, self.explanation_viewer],
            expand=True, spacing=10, visible=False,
            vertical_alignment=ft.CrossAxisAlignment.START
        )
        
        self.content = ft.Column(
            controls=[
                ft.Row([ft.Icon(ft.Icons.INSIGHTS_ROUNDED), self.title_text], alignment=ft.MainAxisAlignment.CENTER),
                ft.Row(controls=[self.agent_dropdown]),
                self.analyze_button,
                ft.Stack(
                    controls=[
                        ft.Container(content=self.status_text, alignment=ft.alignment.center, expand=True),
                        self.analysis_results_container 
                    ],
                    expand=True
                )
            ],
            expand=True, spacing=10,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER
        )
        
    def did_mount(self):
        self.update_translations(self.locale_manager)
        # --- MUDANÇA 2: Inicia a busca assíncrona pela lista de agentes ---
        self.client.start_fetching_agent_list(on_list_loaded_callback=self._on_agent_list_loaded)
        
    # --- MUDANÇA 3: Novo método de callback para popular o dropdown ---
    def _on_agent_list_loaded(self, agent_ids: List[str]):
        """Callback chamado pelo XaiClient com a lista de agentes."""
        if agent_ids:
            self.agent_dropdown.options = [ft.dropdown.Option(agent_id) for agent_id in agent_ids]
            self.agent_dropdown.disabled = False
            self.analyze_button.disabled = False
            self.agent_dropdown.hint_text = self.locale_manager.get_string("diagnostics_view.xai_dropdown_hint_select")
            self.status_text.value = self.locale_manager.get_string("diagnostics_view.xai_status_ready")
        else:
            self.agent_dropdown.hint_text = self.locale_manager.get_string("diagnostics_view.xai_dropdown_hint_no_scenario")
            self.status_text.value = self.locale_manager.get_string("diagnostics_view.xai_dropdown_hint_no_scenario")
            self.status_text.color = ft.Colors.ORANGE
        
        if self.page: self.update()

    def update_translations(self, lm: LocaleManager):
        self.title_text.value = lm.get_string("diagnostics_view.xai_title")
        self.agent_dropdown.label = lm.get_string("diagnostics_view.xai_dropdown_label")
        self.analyze_button.text = lm.get_string("diagnostics_view.xai_button")
        
        if not self.agent_dropdown.disabled:
             self.status_text.value = lm.get_string("diagnostics_view.xai_status_ready")
        
        if self.agent_dropdown.options:
            self.agent_dropdown.hint_text = lm.get_string("diagnostics_view.xai_dropdown_hint_select")
        elif self.agent_dropdown.disabled:
            self.agent_dropdown.hint_text = "A carregar lista de agentes..."
        else:
            self.agent_dropdown.hint_text = lm.get_string("diagnostics_view.xai_dropdown_hint_no_scenario")
            
        if self.page: self.update()

    def run_analysis_click(self, e):
        agent_id = self.agent_dropdown.value
        if not agent_id:
            self.agent_dropdown.error_text = self.locale_manager.get_string("diagnostics_view.xai_error_no_agent")
            self.update()
            return

        self.agent_dropdown.error_text = ""
        self.analyze_button.disabled = True
        self.status_text.value = self.locale_manager.get_string("diagnostics_view.xai_status_loading")
        self.status_text.color = ft.Colors.CYAN
        self.status_text.visible = True
        self.analysis_results_container.visible = False
        self.update()

        self.client.start_analysis(agent_id)

    def on_analysis_complete(self, response: dict):
        """Callback que é chamado pela thread de trabalho do XaiClient para a ANÁLISE."""
        self._update_ui_with_analysis_response(response)

    def _update_ui_with_analysis_response(self, response: dict):
        """Este método modifica os controles com o resultado da análise e atualiza a página."""
        self.analyze_button.disabled = False

        if response.get("status") == "complete":
            image_path = response.get("image_path")
            text_path = response.get("text_path")
            self.plot_viewer.update_image(image_path)
            
            text_content = "Erro: Arquivo de texto da análise não encontrado."
            if text_path and os.path.exists(text_path):
                with open(text_path, "r", encoding="utf-8") as f:
                    text_content = f.read()
            self.explanation_viewer.update_text(text_content)
            
            self.status_text.visible = False
            self.analysis_results_container.visible = True
        else:
            error_message = response.get("message", "Erro desconhecido.")
            self.status_text.value = f"Erro na Análise: {error_message}"
            self.status_text.color = ft.Colors.RED
            self.status_text.visible = True
            self.analysis_results_container.visible = False
        
        if self.page:
            self.page.update()