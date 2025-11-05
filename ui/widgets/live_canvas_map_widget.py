# File: ui/widgets/live_canvas_map_widget.py (CORRIGIDO)
# Author: Gabriel Moraes
# Date: 01 de Outubro de 2025

"""
Define o LiveCanvasMapWidget.

Nesta versão, ele foi atualizado para receber e repassar as referências
da DashboardView e do ControlPanelWidget para o MapAnimator.
"""

import flet as ft
import flet.canvas as cv
import logging
from typing import Dict, Any, Callable, Tuple, TYPE_CHECKING

from ui.handlers.map_interaction_handler import MapInteractionHandler
from ui.handlers.map_drawer import MapDrawer
from ui.handlers.map_animator import MapAnimator
from ui.handlers.street_interaction_handler import StreetInteractionHandler
from ui.handlers.map_state_manager import MapStateManager
from ui.widgets.traffic_light_widget import TrafficLightWidget

# Evita importação circular, permitindo anotações de tipo
if TYPE_CHECKING:
    from ui.views.dashboard_view import DashboardView
    from ui.widgets.control_panel_widget import ControlPanelWidget

class LiveCanvasMapWidget(ft.Container):
    """
    Um widget que orquestra especialistas para desenhar e animar um mapa.
    """
    def __init__(
        self,
        # --- MUDANÇA 1: Aceitar as novas referências ---
        dashboard_view: 'DashboardView',
        control_panel: 'ControlPanelWidget',
        width: int = 1280,
        height: int = 720,
        on_semaphore_click: Callable[[str | None], None] = None,
        on_street_click: Callable[[str | None], None] = None
    ):
        super().__init__(
            width=width, height=height, bgcolor="#F7F7F7", border_radius=10,
            alignment=ft.alignment.center,
            clip_behavior=ft.ClipBehavior.HARD_EDGE
        )
        
        # --- MUDANÇA 2: Armazenar as referências ---
        self.dashboard_view = dashboard_view
        self.control_panel = control_panel
        
        self.on_semaphore_click = on_semaphore_click
        self.on_street_click = on_street_click
        
        self.interaction_handler = MapInteractionHandler(on_update_callback=self.update)
        self.street_interaction_handler = StreetInteractionHandler(on_street_selected=self._handle_street_click)
        self.drawer: MapDrawer | None = None
        self.animator: MapAnimator | None = None
        self.map_state_manager: MapStateManager | None = None
        
        self.canvas = cv.Canvas(shapes=[], width=self.width, height=self.height)
        self.map_stack = ft.Stack(
            scale=self.interaction_handler.scale,
            offset=self.interaction_handler.offset,
        )
        self.gesture_detector = ft.GestureDetector(
            content=self.map_stack,
            on_pan_update=self.interaction_handler.handle_pan_update,
            on_scroll=self.interaction_handler.handle_zoom,
            on_double_tap=lambda e: self.interaction_handler.center_and_reset_zoom(),
            on_tap_down=self._handle_map_tap
        )
        
        self.content = ft.Column(
            [
                ft.ProgressRing(),
                ft.Text("Aguardando Conexão com o Cenário...")
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER
        )
        
        self.will_unmount = self.on_unmount

    def initialize_map(self, map_data: Tuple | None):
        if not map_data:
            self.content = ft.Text("ERRO: Dados de geometria do mapa não foram fornecidos.", color=ft.Colors.RED)
            if self.page: self.update()
            return

        nodes, edges, _ = map_data
        self.drawer = MapDrawer(nodes, edges)
        self.drawer.calculate_transformations(self.width, self.height)
        
        edge_paths = self.drawer.draw_initial_map(self.canvas, stroke_width=5.0)
        self.street_interaction_handler.load_paths(edge_paths)
        
        traffic_light_widgets_map: Dict[str, TrafficLightWidget] = {}
        traffic_light_widgets_list = []
        for node_id, node_data in self.drawer.nodes.items():
            if node_data.get('type') == 'traffic_light':
                tx, ty = self.drawer._transform_point(node_data['x'], node_data['y'])
                widget = TrafficLightWidget(semaphore_id=node_id)
                widget.left, widget.top = tx - (widget.width / 2), ty - (widget.height / 2)
                traffic_light_widgets_list.append(widget)
                traffic_light_widgets_map[node_id] = widget

        self.map_stack.controls = [self.canvas, *traffic_light_widgets_list]
        
        self.map_state_manager = MapStateManager(
            canvas=self.canvas, stack=self.map_stack,
            edge_paths=edge_paths, traffic_light_widgets=traffic_light_widgets_map
        )

        # --- MUDANÇA 3: Passar as referências para o MapAnimator ---
        self.animator = MapAnimator(
            widget_to_update=self,
            dashboard_view=self.dashboard_view,
            control_panel=self.control_panel,
            edge_paths=edge_paths,
            semaforo_widgets=traffic_light_widgets_map,
            interval=0.5
        )
        # --- FIM DA MUDANÇA ---
        
        self.animator.start()
        
        self.content = self.gesture_detector
        if self.page: self.update()
        logging.info("[LiveCanvasMap] Mapa inicializado e desenhado com sucesso.")

    def clear_all_selections(self):
        if self.map_state_manager:
            self.map_state_manager.set_selection(item_type=None, item_id=None)
            self.update()

    def update_data(self, data_packet: dict):
        if self.animator:
            self.animator.update_data(data_packet)
    
    def on_unmount(self):
        if self.animator: self.animator.stop()

    def _handle_street_click(self, edge_id: str | None):
        if self.map_state_manager:
            self.map_state_manager.set_selection(item_type='street', item_id=edge_id)
            self.update()
        if self.on_street_click: self.on_street_click(edge_id)

    def _handle_semaphore_click(self, semaphore_id: str):
        if not self.map_state_manager: return
        current_selection = self.map_state_manager.selected_semaphore_id
        new_selection_id = semaphore_id if current_selection != semaphore_id else None
        self.map_state_manager.set_selection(item_type='semaphore', item_id=new_selection_id)
        self.update()
        if self.on_semaphore_click: self.on_semaphore_click(new_selection_id)

    def _handle_map_tap(self, e: ft.TapEvent):
        scale = self.interaction_handler.scale.scale
        offset = self.interaction_handler.offset
        center_x, center_y = self.width / 2, self.height / 2
        offset_x_px, offset_y_px = offset.x * self.width, offset.y * self.height
        unpanned_x, unpanned_y = e.local_x - offset_x_px, e.local_y - offset_y_px
        map_space_x = ((unpanned_x - center_x) / scale) + center_x
        map_space_y = ((unpanned_y - center_y) / scale) + center_y

        if self.map_state_manager and self.map_state_manager.traffic_light_widgets:
            for tl_id, widget in self.map_state_manager.traffic_light_widgets.items():
                left, top = widget.left, widget.top
                right, bottom = left + widget.width, top + widget.height
                if left <= map_space_x <= right and top <= map_space_y <= bottom:
                    self._handle_semaphore_click(tl_id)
                    return

        self.street_interaction_handler.handle_click(map_space_x, map_space_y, scale)

    def set_semaphore_override_state(self, semaphore_id: str, state: str):
        if self.map_state_manager and self.animator:
            widget = self.map_state_manager.traffic_light_widgets.get(semaphore_id)
            if widget:
                command = {"id": semaphore_id, "state": state}
                self.animator.command_queue.put(command)