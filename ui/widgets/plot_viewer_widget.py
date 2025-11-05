# File: ui/widgets/plot_viewer_widget.py (Revertido para altura fixa)
# Author: Gabriel Moraes
# Date: 03 de Setembro de 2025

"""
Define o PlotViewerWidget, um widget especializado e reutilizável
cujo único propósito é exibir uma imagem de forma centralizada e contida.

Revertido para a versão com 'height' fixa para garantir a estabilidade
do layout.
"""

import flet as ft
import os

class PlotViewerWidget(ft.Container):
    """
    Um contêiner que exibe uma imagem, garantindo que ela seja
    centralizada e totalmente visível (contida) dentro do espaço disponível.
    """
    def __init__(self):
        self.image_content = ft.Image(
            fit=ft.ImageFit.CONTAIN,
            expand=True
        )

        # Revertido para a versão com altura fixa
        super().__init__(
            content=self.image_content,
            alignment=ft.alignment.center,
            height=600,
            expand=True, # Mantém a expansão horizontal
            border=ft.border.all(1, ft.Colors.WHITE24),
            border_radius=10,
            padding=ft.padding.all(5),
        )

    def update_image(self, src_path: str | None):
        """
        Método público para atualizar a imagem exibida.
        """
        if src_path and os.path.exists(src_path):
            self.image_content.src = src_path
            self.image_content.error_content = None
        else:
            self.image_content.src = None
            if src_path is not None:
                self.image_content.error_content = ft.Text(f"Erro: Imagem não encontrada.", color=ft.Colors.RED)
        
        if self.page:
            self.page.update()