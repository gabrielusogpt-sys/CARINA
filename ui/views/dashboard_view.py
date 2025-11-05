# File: ui/views/dashboard_view.py (CORRIGIDO E FINALIZADO)
# Author: Gabriel Moraes
# Date: 01 de Outubro de 2025

import flet as ft
from typing import Dict
import logging

from ui.widgets.control_panel_widget import ControlPanelWidget
from ui.widgets.live_canvas_map_widget import LiveCanvasMapWidget
from ui.clients.control_client import ControlClient
from ui.handlers.map_asset_loader import MapAssetLoader
from ui.handlers.locale_manager import LocaleManager

class DashboardView(ft.Container):
    def __init__(self, control_client: ControlClient, locale_manager: LocaleManager):
        super().__init__(expand=True)
        
        self.locale_manager = locale_manager
        self.latest_data_packet = {}
        self.current_mode = "Automático"
        self.selected_semaphore_id: str | None = None
        
        self.is_initialized = False
        self.maturity_phases: Dict[str, str] = {}

        self.control_panel = ControlPanelWidget(
            control_client=control_client,
            locale_manager=self.locale_manager,
            on_specific_command=self._handle_specific_command,
            on_details_close=self._handle_panel_close,
            on_mode_change=self._handle_mode_change
        )
        
        # --- MUDANÇA 1: Passar as referências para o LiveCanvasMapWidget ---
        self.map_widget = LiveCanvasMapWidget(
            dashboard_view=self,
            control_panel=self.control_panel,
            on_semaphore_click=self._handle_semaphore_click,
            on_street_click=self._handle_street_click
        )
        # --- FIM DA MUDANÇA 1 ---
        
        self.content = ft.Row(
            controls=[
                ft.Container(content=self.map_widget, alignment=ft.alignment.center, expand=True),
                self.control_panel,
            ],
            expand=True,
            vertical_alignment=ft.CrossAxisAlignment.START
        )
        
        self.current_mode = self.locale_manager.get_string("dashboard_view.mode_auto")

    def update_translations(self, lm: LocaleManager):
        self.current_mode = lm.get_string("dashboard_view.mode_auto")
        self.control_panel.update_translations(lm)
        if self.page: self.update()

    # --- MUDANÇA 2: Simplificar drasticamente o update_live_data ---
    def update_live_data(self, data_packet: dict):
        """
        Recebe os dados em tempo real e apenas os armazena e repassa para o animador.
        A lógica de atualização da UI foi removida daqui.
        """
        if not self.is_initialized and data_packet.get("type") == "initial_map_geometry":
            logging.info("[DashboardView] Primeiro pacote de dados ('initial_map_geometry') recebido. Inicializando mapa...")
            self.is_initialized = True
            
            asset_loader = MapAssetLoader()
            map_data = asset_loader.load_map_data()
            
            if map_data:
                nodes, _, _ = map_data
                traffic_light_ids = [node_id for node_id, data in nodes.items() if data.get('type') == 'traffic_light']
                self.maturity_phases = {tl_id: "UNKNOWN" for tl_id in traffic_light_ids}

            self.map_widget.initialize_map(map_data)
        
        # Armazena os dados mais recentes
        self.latest_data_packet = data_packet
        if data_packet.get("maturity_phases"):
            self.maturity_phases = data_packet.get("maturity_phases")
        
        # Apenas repassa o pacote de dados para o mapa/animador, que fará o trabalho pesado
        if self.map_widget:
            self.map_widget.update_data(data_packet)
        
        # A lógica de atualizar o painel de controlo foi REMOVIDA daqui.
    # --- FIM DA MUDANÇA 2 ---

    def _handle_panel_close(self):
        self.selected_semaphore_id = None
        if self.map_widget:
            self.map_widget.clear_all_selections()

    def _handle_mode_change(self, mode: str):
        self.current_mode = mode
        # Não precisa de atualizar o painel aqui, o animador fará isso
        if self.selected_semaphore_id:
            # Apenas notifica o handler de estado do mapa para que ele possa redesenhar, se necessário
            self.map_widget.clear_all_selections()
            self._handle_semaphore_click(self.selected_semaphore_id)


    def _handle_semaphore_click(self, semaphore_id: str | None):
        self.selected_semaphore_id = semaphore_id
        
        if not self.control_panel: return
        if not semaphore_id:
            self.control_panel.ocultar_todos_detalhes()
            return

        is_manual_mode = self.current_mode == self.locale_manager.get_string("dashboard_view.mode_manual")
        phase = self.maturity_phases.get(semaphore_id, "UNKNOWN")

        if is_manual_mode and phase.upper() != "ADULT":
            self.control_panel.ocultar_todos_detalhes()
            self.map_widget.clear_all_selections()
            template = self.locale_manager.get_string("dashboard_view.snackbar_manual_control_denied")
            if self.page:
                self.page.snack_bar = ft.SnackBar(
                    content=ft.Text(template.format(id=semaphore_id, phase=phase)),
                    bgcolor=ft.Colors.AMBER_700
                )
                self.page.snack_bar.open = True
                self.page.update()
            return

        # A exibição inicial é feita aqui no clique, mas as atualizações contínuas
        # serão feitas pelo MapAnimator
        panel_data = self.latest_data_packet.get("panel_data", {})
        semaphore_data = panel_data.get(semaphore_id, {})
        self.control_panel.exibir_controles_semaforo(semaphore_id, semaphore_data, phase, self.current_mode)

    def _handle_street_click(self, street_id: str | None):
        self.selected_semaphore_id = None
        
        if not self.control_panel: return
        if street_id is None:
            self.control_panel.ocultar_todos_detalhes()
            return

        street_data_payload = self.latest_data_packet.get("street_data", {})
        street_data_for_panel = street_data_payload.get(street_id, {})
        self.control_panel.exibir_info_rua(street_id, street_data_for_panel)

    def _handle_specific_command(self, semaphore_id: str, command: str):
        if self.map_widget:
            self.map_widget.set_semaphore_override_state(semaphore_id, command)