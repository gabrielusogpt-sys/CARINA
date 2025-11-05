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

# File: src/utils/map_data_parser.py (MODIFICADO PARA LER O TIPO DO NÓ)
# Author: Gabriel Moraes
# Date: 23 de Setembro de 2025

"""
Define um parser para ler os ficheiros "plain XML" (.nod.xml, .edg.xml)
gerados pelo netconvert do SUMO, extraindo as coordenadas para renderização.

Esta versão foi atualizada para também ler o atributo 'type' de cada nó,
permitindo diferenciar entre cruzamentos comuns e semáforos.
"""
import xml.etree.ElementTree as ET
import logging
from typing import Dict, List, Tuple

def parse_map_data(plain_xml_prefix: str) -> Tuple[Dict, List, Dict] | None:
    """
    Lê os ficheiros .nod.xml e .edg.xml e extrai os dados para desenhar o mapa.

    Args:
        plain_xml_prefix (str): O caminho e prefixo dos ficheiros plain XML.

    Returns:
        Um tuplo contendo (dicionário_de_nós, lista_de_arestas, mapa_de_via_para_rua)
        em caso de sucesso, ou None em caso de falha.
    """
    nodes_path = plain_xml_prefix + ".nod.xml"
    edges_path = plain_xml_prefix + ".edg.xml"

    try:
        # --- Ler os Nós (Cruzamentos) ---
        logging.info(f"[MapParser] A ler ficheiro de nós: {nodes_path}")
        nodes_tree = ET.parse(nodes_path)
        nodes_root = nodes_tree.getroot()
        nodes = {}
        for node in nodes_root.findall('node'):
            node_id = node.get('id')
            x = float(node.get('x'))
            y = float(node.get('y')) 
            
            # --- MUDANÇA ADICIONADA AQUI ---
            # Capturamos também o tipo do nó (ex: 'traffic_light', 'priority')
            node_type = node.get('type')
            
            nodes[node_id] = {'x': x, 'y': y, 'type': node_type}
        
        if not nodes:
            logging.warning("[MapParser] Nenhum nó encontrado no ficheiro .nod.xml.")
            return None

        # --- Ler as Arestas (Ruas) e Mapear as Vias ---
        logging.info(f"[MapParser] A ler ficheiro de arestas: {edges_path}")
        edges_tree = ET.parse(edges_path)
        edges_root = edges_tree.getroot()
        edges = []
        
        lane_to_edge_map = {}

        for edge in edges_root.findall('edge'):
            edge_id = edge.get('id')
            
            for lane in edge.findall('lane'):
                lane_id = lane.get('id')
                if lane_id:
                    lane_to_edge_map[lane_id] = edge_id

            shape_str = edge.get('shape')
            shape_points = []
            if shape_str:
                for point_str in shape_str.split(' '):
                    px, py_str = point_str.split(',')
                    px = float(px)
                    py = float(py_str)
                    shape_points.append((px, py))
            else:
                from_node_id = edge.get('from')
                to_node_id = edge.get('to')
                if from_node_id in nodes and to_node_id in nodes:
                    start_node = nodes[from_node_id]
                    end_node = nodes[to_node_id]
                    shape_points = [(start_node['x'], start_node['y']), (end_node['x'], end_node['y'])]

            if shape_points:
                edges.append({
                    'id': edge_id,
                    'shape': shape_points
                })

        if not edges:
            logging.warning("[MapParser] Nenhuma aresta processável encontrada no ficheiro .edg.xml.")
            return None

        logging.info(f"[MapParser] Leitura concluída: {len(nodes)} nós, {len(edges)} arestas e {len(lane_to_edge_map)} vias mapeadas.")
        
        return nodes, edges, lane_to_edge_map

    except FileNotFoundError as e:
        logging.error(f"[MapParser] ERRO: Ficheiro de mapa não encontrado: {e.filename}")
        return None
    except Exception as e:
        logging.error(f"[MapParser] ERRO ao ler os ficheiros XML do mapa: {e}", exc_info=True)
        return None