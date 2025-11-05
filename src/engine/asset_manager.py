# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2025 Gabriel Moraes - Noxfort Labs
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# File: src/engine/asset_manager.py (MODIFICADO PARA TRADUÇÃO)
# Author: Gabriel Moraes
# Date: 04 de Outubro de 2025

import logging
from typing import TYPE_CHECKING

# --- MUDANÇA 1: Adicionar importações ---
if TYPE_CHECKING:
    from utils.locale_manager_backend import LocaleManagerBackend

# Importa as novas classes especializadas da nova pasta de renderização
from rendering.static_map_renderer import StaticMapRenderer
from rendering.heatmap_renderer import HeatmapRenderer

class AssetManager:
    """O Gestor de Ativos que delega tarefas de renderização para especialistas."""

    # --- MUDANÇA 2: Modificar o construtor ---
    def __init__(self, locale_manager: 'LocaleManagerBackend'):
        """
        Inicializa o AssetManager e seus renderizadores especialistas internos.
        """
        self.locale_manager = locale_manager
        self.static_map_renderer = StaticMapRenderer(locale_manager)
        self.heatmap_renderer = HeatmapRenderer(locale_manager)
        # --- MUDANÇA 3 ---
        logging.info(self.locale_manager.get_string("asset_manager.init.created"))

    def create_heatmap_image_in_memory(
        self, 
        map_data: tuple, 
        congestion_data: dict
    ) -> str | None:
        """
        Delega a geração da imagem de mapa de calor para o especialista.
        """
        return self.heatmap_renderer.create_heatmap_image_in_memory(
            map_data=map_data,
            congestion_data=congestion_data
        )

    def create_map_with_icons(
        self, net_file_path: str, scenario_results_dir: str, 
        icon_requests: dict, output_filename: str
    ) -> tuple[str | None, tuple | None]:
        """
        Delega a geração do mapa estático com ícones para o especialista.
        """
        return self.static_map_renderer.create_map_with_icons(
            net_file_path=net_file_path,
            scenario_results_dir=scenario_results_dir,
            icon_requests=icon_requests,
            output_filename=output_filename
        )

    def generate_coordinates_file(
        self, map_data: tuple, traffic_light_ids: list,
        scenario_results_dir: str
    ) -> str | None:
        """
        Delega a geração do arquivo de coordenadas para o especialista.
        """
        return self.static_map_renderer.generate_coordinates_file(
            map_data=map_data,
            traffic_light_ids=traffic_light_ids,
            scenario_results_dir=scenario_results_dir,
            image_width=3840, 
            image_height=2160
        )