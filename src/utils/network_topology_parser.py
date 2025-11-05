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

# File: src/utils/network_topology_parser.py (NOVO ARQUIVO)
# Author: Gabriel Moraes
# Date: 13 de Outubro de 2025

import logging
import xml.etree.ElementTree as ET
import gzip
from collections import defaultdict
from typing import TYPE_CHECKING, Tuple, Dict

if TYPE_CHECKING:
    from .locale_manager_backend import LocaleManagerBackend

class NetworkTopologyParser:
    """
    Um especialista em ler um ficheiro .net.xml do SUMO e extrair
    a sua topologia de rede.
    """
    def __init__(self, locale_manager: 'LocaleManagerBackend'):
        """
        Inicializa o parser de topologia.
        """
        self.locale_manager = locale_manager

    def build(self, net_file_path: str) -> Tuple[Dict, Dict]:
        """
        Lê um ficheiro .net.xml e constrói a topologia da rede.

        Args:
            net_file_path (str): O caminho para o ficheiro .net.xml.

        Returns:
            Uma tupla contendo (tipos_de_juncao, arestas_de_entrada_por_juncao).
        """
        lm = self.locale_manager
        junction_types = {}
        junction_incoming_edges = defaultdict(dict)

        try:
            opener = gzip.open if net_file_path.endswith('.gz') else open
            with opener(net_file_path, 'rb') as f:
                tree = ET.parse(f)
            
            root = tree.getroot()

            # Extrai o tipo de cada junção (ex: 'traffic_light')
            for junction in root.findall('junction'):
                j_id = junction.get('id')
                j_type = junction.get('type')
                if j_id and j_type:
                    junction_types[j_id] = j_type

            # Mapeia as ruas (edges) que chegam a cada junção
            for edge in root.findall('edge'):
                j_id = edge.get('to')
                edge_id = edge.get('id')
                if j_id and edge_id:
                    lanes = [lane.get('id') for lane in edge.findall('lane')]
                    junction_incoming_edges[j_id][edge_id] = {'lanes': lanes, 'num_lanes': len(lanes)}
        
        except FileNotFoundError:
             logging.error(f"[TopologyParser] Ficheiro de rede não encontrado em: {net_file_path}")
             return {}, defaultdict(dict)
        except Exception as e:
            # A chave de tradução já existe no backend.json
            logging.error(lm.get_string("sas_engine.topology.critical_error", error=e), exc_info=True)
            return {}, defaultdict(dict)
        
        return junction_types, junction_incoming_edges