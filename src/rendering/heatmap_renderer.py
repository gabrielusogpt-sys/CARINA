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

# File: src/rendering/heatmap_renderer.py (MODIFICADO PARA TRADUÇÃO)
# Author: Gabriel Moraes
# Date: 04 de Outubro de 2025

import logging
import io
import base64
from typing import TYPE_CHECKING

# --- MUDANÇA 1: Adicionar importações ---
if TYPE_CHECKING:
    from utils.locale_manager_backend import LocaleManagerBackend

import matplotlib.pyplot as plt

class HeatmapRenderer:
    """O especialista em renderizar mapas de calor dinâmicos em memória."""

    # --- MUDANÇA 2: Modificar o construtor ---
    def __init__(self, locale_manager: 'LocaleManagerBackend'):
        """Inicializa o renderizador de mapas de calor."""
        self.locale_manager = locale_manager
        # --- MUDANÇA 3 ---
        logging.info(self.locale_manager.get_string("heatmap_renderer.init.created"))

    def create_heatmap_image_in_memory(
        self, 
        map_data: tuple, 
        congestion_data: dict,
        saturation_threshold: float = 100.0
    ) -> str | None:
        """
        Gera uma imagem de mapa com as ruas coloridas pelo nível de
        congestionamento e a retorna como uma string Base64.
        """
        lm = self.locale_manager
        try:
            nodes, edges = map_data
            fig, ax = plt.subplots(figsize=(6.4, 3.6))

            cmap = plt.get_cmap('jet')

            threshold = max(saturation_threshold, 1.0)

            for edge in edges:
                edge_id = edge.get('id', '')
                congestion_index = congestion_data.get(edge_id, 0.0)
                
                normalized_congestion = min(congestion_index / threshold, 1.0)
                color = cmap(normalized_congestion)
                
                shape = edge['shape']
                x_coords, y_coords = zip(*shape)

                ax.plot(
                    x_coords, y_coords, 
                    color=color, 
                    linewidth=3.5,
                    zorder=1, 
                    solid_capstyle='round'
                )

            if nodes:
                node_x = [n['x'] for n in nodes.values()]
                node_y = [n['y'] for n in nodes.values()]
                ax.scatter(node_x, node_y, s=15, color='#808080', zorder=2)

            ax.set_aspect('equal', adjustable='box')
            ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
            ax.spines['bottom'].set_visible(False); ax.spines['left'].set_visible(False)
            ax.get_xaxis().set_ticks([]); ax.get_yaxis().set_ticks([])
            ax.set_facecolor('#F7F7F7')
            
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=600, facecolor=ax.get_facecolor(), pad_inches=0.1)
            plt.close(fig)
            buf.seek(0)
            
            image_base64 = base64.b64encode(buf.read()).decode('utf-8')
            return image_base64

        except Exception as e:
            # --- MUDANÇA 4 ---
            logging.error(lm.get_string("heatmap_renderer.run.error", error=e), exc_info=True)
            return None