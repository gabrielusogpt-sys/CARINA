# File: ui/handlers/map_interaction_handler.py (CORRIGIDO O CAMINHO DE IMPORTAÇÃO)
# Author: Gabriel Moraes
# Date: 24 de Setembro de 2025

"""
Define o MapInteractionHandler.

Esta versão foi corrigida para usar o caminho de importação correto para as
classes de transformação do Flet (ft.Offset, ft.Scale).
"""

import flet as ft

class MapInteractionHandler:
    """Gerencia o estado e a lógica das interações de pan e zoom do mapa."""

    def __init__(self, on_update_callback):
        """
        Inicializa o handler de interação.
        """
        # --- CORREÇÃO APLICADA AQUI ---
        # As classes são chamadas diretamente a partir de 'ft'
        self.offset = ft.Offset(0, 0)
        self.scale = ft.Scale(scale=1.0, alignment=ft.alignment.center)

        # --- Configurações de Comportamento ---
        self.max_zoom = 3.0
        self.min_zoom = 0.5
        
        self.on_update = on_update_callback

    def center_and_reset_zoom(self):
        """Reseta o estado para a visualização inicial."""
        self.scale.scale = 1.0
        self.offset.x = 0.0
        self.offset.y = 0.0
        self.on_update()

    def handle_pan_update(self, e: ft.DragUpdateEvent):
        """Calcula o novo deslocamento do mapa durante um evento de pan."""
        effective_scale = self.scale.scale if self.scale.scale > 0 else 1.0
        
        # O offset é fracional, então dividimos pelo tamanho do controle (widget)
        # para normalizar o delta do mouse. Usamos um valor grande (1000) como
        # uma aproximação do tamanho do controle para obter a sensibilidade correta.
        self.offset.x += e.delta_x / (1000 * effective_scale)
        self.offset.y += e.delta_y / (1000 * effective_scale)
        
        self.on_update()

    def handle_zoom(self, e: ft.ScrollEvent):
        """Calcula a nova escala do mapa durante um evento de scroll."""
        if e.scroll_delta_y < 0:
            self.scale.scale = min(self.max_zoom, self.scale.scale * 1.1)
        else:
            self.scale.scale = max(self.min_zoom, self.scale.scale * 0.9)
            
        self.on_update()