# File: ui/widgets/explanation_viewer_widget.py (Largura aumentada para 1100px)
# Author: Gabriel Moraes
# Date: 03 de Setembro de 2025

"""
Define o ExplanationViewerWidget.

Nesta versão, a largura do contêiner foi aumentada para 1100 pixels
para testes de layout.
"""

import flet as ft

class ExplanationViewerWidget(ft.Container):
    """
    Um contêiner que exibe um bloco de texto, garantindo que o conteúdo
    seja rolável se exceder o espaço vertical disponível.
    """
    # --- MUDANÇA AQUI: Largura aumentada para 1100 ---
    def __init__(self, width=800):
        self.text_content = ft.Text(
            font_family="monospace",
            selectable=True
        )

        self.scrollable_column = ft.Column(
            controls=[self.text_content],
            expand=True,
            scroll=ft.ScrollMode.ADAPTIVE,
        )

        super().__init__(
            content=self.scrollable_column,
            width=width,
            height=600,
            border=ft.border.all(1, ft.Colors.WHITE24),
            border_radius=10,
            padding=ft.padding.all(10),
        )

    def update_text(self, content: str | None):
        """
        Método público para atualizar o texto exibido.
        """
        if content:
            self.text_content.value = content
        else:
            self.text_content.value = "Nenhum dado de texto para exibir."
        
        if self.page:
            self.page.update()