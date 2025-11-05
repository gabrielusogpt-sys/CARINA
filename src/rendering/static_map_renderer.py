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

# File: src/rendering/static_map_renderer.py (DPI Reduzido)
# Author: Gabriel Moraes
# Date: 23 de Outubro de 2025 # <-- DATA ATUALIZADA

import logging
import os
import sys
import json
from typing import Dict, List, Tuple, TYPE_CHECKING

# --- MANTIDO: Importar resource_path corretamente ---
project_root_render = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
src_path_render = os.path.join(project_root_render, 'src')
if src_path_render not in sys.path:
    sys.path.insert(0, src_path_render)

from src.utils.paths import resource_path # Alterado para importar de src.utils.paths
# --- FIM ---

# --- REVERTIDO: Importar LocaleManagerBackend ---
if TYPE_CHECKING:
    # A importação correta é do backend, pois este arquivo está em 'src'
    from src.utils.locale_manager_backend import LocaleManagerBackend
# --- FIM ---

# Adiciona o diretório 'src' ao path para a importação funcionar
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from utils.map_generator import generate_map_data_files
from utils.map_data_parser import parse_map_data
import matplotlib.pyplot as plt
from matplotlib.offsetbox import OffsetImage, AnnotationBbox

# --- REMOVIDO: Comentário sobre matplotlib.use('Agg') ---

class StaticMapRenderer:
    """O especialista em renderizar mapas estáticos e seus ativos associados."""

    # --- REVERTIDO: Usar LocaleManagerBackend ---
    def __init__(self, locale_manager: 'LocaleManagerBackend'):
    # --- FIM ---
        self.locale_manager = locale_manager

        # --- MANTIDO: Usar resource_path para carregar os ícones ---
        self.icon_paths = {
            "existing": resource_path(os.path.join("ui", "assets", "icon_existing.png")),
            "add": resource_path(os.path.join("ui", "assets", "icon_add.png")),
            "remove": resource_path(os.path.join("ui", "assets", "icon_remove.png")),
        }
        # --- FIM ---
        # --- REVERTIDO: Remover fallback ---
        logging.info(self.locale_manager.get_string("static_map_renderer.init.created"))
        # --- FIM ---

    def _draw_map_and_icons_with_matplotlib(self, nodes, edges, icon_requests, output_path: str):
        lm = self.locale_manager
        # --- REVERTIDO: Remover fallback ---
        logging.info(lm.get_string("static_map_renderer.run.rendering_map", path=output_path))
        # --- FIM ---
        # --- REVERTIDO: Tamanho original da figura ---
        fig, ax = plt.subplots(figsize=(6.4, 3.6))
        # --- FIM ---

        # Desenha as ruas
        for edge in edges:
            shape = edge.get('shape') # Usar .get() para segurança
            if not shape: continue # Pular se a forma não existir
            try:
                x_coords, y_coords = zip(*shape)
                ax.plot(x_coords, y_coords, color='black', linewidth=2.0, zorder=1)
            except ValueError: # Lidar com caso de shape vazio ou inválido
                 logging.warning(f"Forma inválida encontrada para aresta: {edge.get('id', 'N/A')}")


        # Desenha os nós (cruzamentos)
        if nodes:
            node_x = [n['x'] for n in nodes.values() if 'x' in n] # Garantir que x existe
            node_y = [n['y'] for n in nodes.values() if 'y' in n] # Garantir que y existe
            if node_x and node_y: # Apenas desenhar se houver coordenadas
                ax.scatter(node_x, node_y, s=20, color='#808080', zorder=2)

        # Desenha os ícones de recomendação
        if icon_requests:
            for junction_id, icon_type in icon_requests.items():
                if junction_id not in nodes: continue

                icon_path = self.icon_paths.get(icon_type)
                # --- REMOVIDO: Verificação extra de os.path.exists e try...except ---
                if not icon_path or not os.path.exists(icon_path): # Adicionado check de existência aqui por segurança
                    logging.warning(f"Ícone '{icon_type}' não encontrado em '{icon_path}'")
                    continue

                node_coords = nodes[junction_id]
                x, y = node_coords.get('x'), node_coords.get('y') # Usar .get()
                if x is None or y is None: continue # Pular se x ou y não existirem

                try: # Adicionado try-except para leitura da imagem
                    icon_image = plt.imread(icon_path)
                    imagebox = OffsetImage(icon_image, zoom=0.5)
                    ab = AnnotationBbox(imagebox, (x, y), frameon=False, pad=0.0, zorder=3)
                    ax.add_artist(ab)
                except Exception as img_err:
                    logging.error(f"Erro ao carregar ou adicionar ícone '{icon_path}': {img_err}")
                # --- FIM ---

        # Configurações de estilo do gráfico
        ax.set_aspect('equal', adjustable='box')
        ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
        ax.spines['bottom'].set_visible(False); ax.spines['left'].set_visible(False)
        ax.get_xaxis().set_ticks([]); ax.get_yaxis().set_ticks([])
        ax.set_facecolor('#F7F7F7')

        # --- MUDANÇA PRINCIPAL AQUI: DPI Reduzido ---
        # Reduzir de 600 para 150 (ou 300 se a qualidade ficar muito baixa)
        try:
            plt.savefig(output_path, format='png', dpi=150, facecolor=ax.get_facecolor(), pad_inches=0.1)
        except MemoryError as me: # Captura especificamente MemoryError
             logging.critical(f"MemoryError ao salvar a imagem '{output_path}'. Tente reduzir ainda mais o DPI ou verificar a RAM disponível.")
             raise me # Re-lança o erro após logar
        except Exception as save_err: # Captura outros erros
             logging.error(f"Erro inesperado ao salvar a imagem '{output_path}': {save_err}")
             raise save_err # Re-lança o erro
        finally:
            plt.close(fig) # Garante que a figura seja fechada
        # --- FIM DA MUDANÇA ---

        # --- REVERTIDO: Remover fallback ---
        logging.info(lm.get_string("static_map_renderer.run.render_complete", filename=os.path.basename(output_path)))
        # --- FIM ---

    def create_map_with_icons(
        self, net_file_path: str, scenario_results_dir: str,
        icon_requests: dict, output_filename: str
    ) -> tuple[str | None, tuple | None]:
        """
        Orquestra a criação de um mapa estático com ícones.
        """
        lm = self.locale_manager
        plain_xml_prefix = None # Inicializa para o bloco finally
        nodes = None # Inicializa
        edges = None # Inicializa
        try:
            maps_output_dir = os.path.join(scenario_results_dir, "maps")
            os.makedirs(maps_output_dir, exist_ok=True) # Cria o diretório se não existir

            # --- CORREÇÃO IMPORTANTE: Passar 'lm' para generate_map_data_files ---
            plain_xml_prefix = generate_map_data_files(net_file_path=net_file_path, output_dir=scenario_results_dir, lm=self.locale_manager) # Passa lm
            # --- FIM CORREÇÃO ---

            if not plain_xml_prefix:
                logging.error("Falha ao gerar arquivos de dados do mapa. Prefixo plain XML não retornado.")
                return None, None

            map_data = parse_map_data(plain_xml_prefix)
            if not map_data:
                logging.error("Falha ao parsear os dados do mapa a partir dos arquivos XML.")
                return None, None

            nodes, edges, _ = map_data
            if not nodes:
                logging.error("Nenhum nó encontrado nos dados do mapa parseados.")
                return None, None

            final_image_path = os.path.join(maps_output_dir, output_filename)
            self._draw_map_and_icons_with_matplotlib(nodes, edges, icon_requests, final_image_path)

            return final_image_path, (nodes, edges)
        except MemoryError: # Captura MemoryError especificamente vindo de _draw_map...
            logging.critical("Falha ao gerar mapa devido a erro de memória (RAM). Verifique o log anterior.")
            return None, None
        except Exception as e:
            # --- REVERTIDO: Remover fallback ---
            logging.error(lm.get_string("static_map_renderer.run.critical_error_icons", error=e), exc_info=True)
            # --- FIM ---
            return None, None
        finally:
             # Limpeza dos arquivos XML temporários, se foram criados
             if plain_xml_prefix:
                 try:
                     if os.path.exists(plain_xml_prefix + ".nod.xml"): os.remove(plain_xml_prefix + ".nod.xml")
                     if os.path.exists(plain_xml_prefix + ".edg.xml"): os.remove(plain_xml_prefix + ".edg.xml")
                 except Exception as cleanup_err:
                     logging.warning(f"Erro ao limpar arquivos XML temporários: {cleanup_err}")


    def generate_coordinates_file(
        self, map_data: tuple, traffic_light_ids: list,
        scenario_results_dir: str, image_width: int = 3840, image_height: int = 2160
    ) -> str | None:
        """
        Gera um arquivo JSON com as coordenadas em pixels de cada semáforo no mapa renderizado.
        """
        lm = self.locale_manager
        try:
            # --- REVERTIDO: Remoção de logs ---
            if not isinstance(map_data, tuple) or len(map_data) != 2:
                 logging.error("Dados do mapa inválidos para gerar coordenadas.")
                 return None
            nodes, edges = map_data
            if not nodes or not edges:
                 logging.error("Nós ou arestas ausentes nos dados do mapa para gerar coordenadas.")
                 return None
            # --- FIM ---

            # --- REVERTIDO: Lógica de cálculo de coordenadas original (aproximada) ---
            # Coleta todas as coordenadas x e y para encontrar os limites
            all_x = [n['x'] for n in nodes.values() if 'x' in n]
            all_y = [n['y'] for n in nodes.values() if 'y' in n]
            for e in edges:
                if 'shape' in e and e['shape']:
                    try:
                        x_coords, y_coords = zip(*e['shape'])
                        all_x.extend(x_coords)
                        all_y.extend(y_coords)
                    except ValueError:
                         pass # Ignora shapes inválidos

            if not all_x or not all_y:
                 logging.error("Não foi possível extrair coordenadas dos nós/arestas.")
                 return None

            min_x, max_x = min(all_x), max(all_x)
            min_y, max_y = min(all_y), max(all_y)

            map_width = max_x - min_x
            map_height = max_y - min_y
            # --- REVERTIDO: Remover log de aviso ---
            if map_width <= 0 or map_height <= 0:
                 logging.warning(f"Dimensões do mapa inválidas calculadas: W={map_width}, H={map_height}. Não é possível gerar coordenadas.")
                 return None
            # --- FIM ---

            # Usa padding_ratio baseado no figsize original
            padding_ratio = (0.1 * 2) / 6.4 # 0.1 pad_inches em cada lado, 6.4 figsize width
            padding = image_width * padding_ratio / 2 # Padding em pixels para cada lado
            view_width = image_width - (padding * 2)
            view_height = image_height - (padding * 2)

            # Calcula a escala garantindo que o mapa caiba na área de visualização
            scale_x = view_width / map_width if map_width > 0 else 1
            scale_y = view_height / map_height if map_height > 0 else 1
            scale = min(scale_x, scale_y)

            # Calcula a largura e altura do mapa escalado
            centered_map_width = map_width * scale
            centered_map_height = map_height * scale

            # Calcula os offsets para centralizar o mapa na imagem
            # Offset X: (largura total - largura do mapa)/2 - (coordenada mínima * escala)
            offset_x = (image_width - centered_map_width) / 2 - (min_x * scale)

            # Offset Y: (altura total - altura do mapa)/2 + (coordenada MÁXIMA * escala)
            # Soma max_y * scale porque a origem Y da imagem é no TOPO esquerdo,
            # enquanto a origem Y do SUMO/matplotlib é na BASE esquerda.
            offset_y_canvas_top = (image_height - centered_map_height) / 2 # Espaço vazio acima do mapa
            offset_y = offset_y_canvas_top + (max_y * scale) # Move a origem para max_y (topo do mapa SUMO) e ajusta pelo scale

            coordinates = {}
            for tl_id in traffic_light_ids:
                if tl_id in nodes:
                    node = nodes[tl_id]
                    # Garante que x e y existam
                    if 'x' in node and 'y' in node:
                        # Aplica escala e offset
                        pixel_x = node['x'] * scale + offset_x
                        # Inverte a coordenada Y ao aplicar escala e offset
                        pixel_y = offset_y - (node['y'] * scale)
                        coordinates[tl_id] = {'x': round(pixel_x, 2), 'y': round(pixel_y, 2)}
                    else:
                         logging.warning(f"Nó '{tl_id}' não possui coordenadas 'x' ou 'y'.")
            # --- FIM DA LÓGICA REVERTIDA ---

            maps_output_dir = os.path.join(scenario_results_dir, "maps")
            os.makedirs(maps_output_dir, exist_ok=True)
            output_path = os.path.join(maps_output_dir, "map_coords.json")

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(coordinates, f, indent=4)

            return output_path
        except Exception as e:
            # --- REVERTIDO: Remover fallback ---
            logging.error(lm.get_string("static_map_renderer.run.critical_error_coords", error=e), exc_info=True)
            # --- FIM ---
            return None