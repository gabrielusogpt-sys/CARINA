# File: ui/views/diagnostics_view.py (CORRIGIDO O CAMINHO DE IMPORTAÇÃO)
# Author: Gabriel Moraes
# Date: 29 de Setembro de 2025

import flet as ft

from handlers.locale_manager import LocaleManager
from ui.widgets.log_viewer_widget import LogViewerWidget
from ui.widgets.xai_viewer_widget import XaiViewerWidget
# --- MUDANÇA APLICADA AQUI: O caminho agora aponta para 'views' ---
from ui.views.system_status_view import SystemStatusView

class DiagnosticsView(ft.Container):
    """
    A classe que representa a aba de Diagnóstico.
    """
    def __init__(self, locale_manager: LocaleManager):
        super().__init__(expand=True, padding=ft.padding.only(top=10))

        self.locale_manager = locale_manager
        
        self.log_viewer = LogViewerWidget(locale_manager=self.locale_manager)
        self.xai_viewer = XaiViewerWidget(locale_manager=self.locale_manager)
        self.system_status_viewer = SystemStatusView(locale_manager=self.locale_manager)
        
        self.view_stack = ft.Stack(
            controls=[
                self.log_viewer,
                self.xai_viewer,
                self.system_status_viewer
            ]
        )
        
        self.nav_buttons = {
            "log": ft.ElevatedButton(icon=ft.Icons.DESCRIPTION_ROUNDED, on_click=lambda e: self.switch_view("log")),
            "xai": ft.ElevatedButton(icon=ft.Icons.INSIGHTS_ROUNDED, on_click=lambda e: self.switch_view("xai")),
            "sys": ft.ElevatedButton(icon=ft.Icons.INFO_OUTLINE_ROUNDED, on_click=lambda e: self.switch_view("sys"))
        }

        self.content = ft.Column(
            [
                ft.Row(list(self.nav_buttons.values()), alignment=ft.MainAxisAlignment.CENTER),
                ft.Divider(height=10),
                self.view_stack,
            ],
            expand=True
        )

        self.switch_view("log")

    def did_mount(self):
        """Chamado quando o widget é montado na página."""
        self.update_translations(self.locale_manager)

    def update_translations(self, lm: LocaleManager):
        """Atualiza os textos desta view e comanda seus filhos a se atualizarem."""
        self.nav_buttons["log"].text = lm.get_string("diagnostics_view.nav_logs")
        self.nav_buttons["xai"].text = lm.get_string("diagnostics_view.nav_xai")
        self.nav_buttons["sys"].text = lm.get_string("diagnostics_view.nav_system")
        
        self.log_viewer.update_translations(lm)
        self.xai_viewer.update_translations(lm)
        self.system_status_viewer.update_translations(lm)
        
        if self.page: self.page.update()

    def switch_view(self, view_name: str):
        """Alterna a visibilidade dos widgets no stack."""
        style_active = ft.ButtonStyle(bgcolor=ft.Colors.INDIGO, color=ft.Colors.WHITE)
        style_inactive = ft.ButtonStyle()

        for name, button in self.nav_buttons.items():
            button.style = style_active if name == view_name else style_inactive
        
        self.log_viewer.visible = (view_name == "log")
        self.xai_viewer.visible = (view_name == "xai")
        self.system_status_viewer.visible = (view_name == "sys")
        
        if self.page:
            self.page.update()
            
    def start_log_watcher(self):
        self.log_viewer.start_log_watcher()

    def stop_log_watcher(self):
        if hasattr(self, 'log_viewer'):
            self.log_viewer.stop_log_watcher()