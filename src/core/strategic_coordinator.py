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

# File: src/core/strategic_coordinator.py (Corrigido: Movido edge_index para self.device)
# Author: Gabriel Moraes
# Date: 01 de Novembro de 2025

import logging
import torch
from torch_geometric.data import Data as GraphData
from typing import TYPE_CHECKING
import sys # Import sys
import os  # Import os

# Adiciona o diretório 'src' ao path para permitir importações absolutas
project_root_strat = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
src_path_strat = os.path.join(project_root_strat, 'src')
if src_path_strat not in sys.path:
    sys.path.insert(0, src_path_strat)


# --- MUDANÇA 1: Adicionar importações ---
if TYPE_CHECKING:
    from utils.locale_manager_backend import LocaleManagerBackend

from agents.gat_strategist import GATStrategist
from utils.network_parser import build_structural_neighborhood_map
from core.system_reporter import SystemReporter # Corrigido para importar de core

class StrategicCoordinator:
    """Gerencia o ciclo de vida e a execução do GAT Strategist."""

    # --- MUDANÇA 2: Modificar o construtor ---
    def __init__(self, settings, device, locale_manager: 'LocaleManagerBackend'):
        self.settings = settings
        self.device = device # Mantém o device (GPU) para o modelo GAT
        self.locale_manager = locale_manager
        lm = self.locale_manager

        gat_settings = settings['GAT_STRATEGIST'] # Acessa diretamente do settings passado
        self.update_frequency = gat_settings.getint('update_frequency_seconds')
        self.output_dim = gat_settings.getint('output_dim')
        self.gat_model = None
        self.last_update_time = -self.update_frequency # Garante primeira execução
        self.strategic_vectors = None
        
        # --- MUDANÇA (Corrigida): graph_edge_index agora vai para self.device ---
        self.graph_edge_index = None # Será um tensor no self.device
        # --- FIM ---

        self.tl_id_to_idx = {}
        self.tl_idx_to_id = {}
        self.max_state_dim = 0
        logging.info(lm.get_string("strategic_coordinator.init.created"))

    # --- MUDANÇA 3: Modificar assinatura da função ---
    def initialize(self, traci_conn):
        """
        Constrói o grafo da rede, inicializa o modelo GAT e retorna as métricas.
        """
        lm = self.locale_manager
        logging.info(lm.get_string("strategic_coordinator.initialize.start"))
        net_file = traci_conn.simulation.getOption("net-file")

        tls_ids = sorted(traci_conn.trafficlight.getIDList())
        if not tls_ids:
            # Esta mensagem de erro é para o programador, pode ser em inglês
            raise ValueError("No traffic lights found in the simulation to initialize the Strategic Coordinator.")

        num_nodes = len(tls_ids)
        self.tl_id_to_idx = {tl_id: i for i, tl_id in enumerate(tls_ids)}
        self.tl_idx_to_id = {i: tl_id for i, tl_id in enumerate(tls_ids)}

        # --- MUDANÇA 4: Passar 'lm' para a função ---
        neighborhoods = build_structural_neighborhood_map(
            net_file_path=net_file, tls_ids_in_sim=tls_ids, lm=lm
        )

        edge_list = []
        for tl_id, neighbors in neighborhoods.items():
            for neighbor_id in neighbors:
                # Garante que ambos os IDs existam no mapeamento antes de adicionar a aresta
                if tl_id in self.tl_id_to_idx and neighbor_id in self.tl_id_to_idx:
                    edge_list.append([self.tl_id_to_idx[tl_id], self.tl_id_to_idx[neighbor_id]])

        # --- MUDANÇA 5: O edge_index agora é movido para o self.device (GPU/CUDA) ---
        self.graph_edge_index = torch.tensor(edge_list, dtype=torch.long).t().contiguous().to(self.device)
        logging.info(f"[StrategicCoordinator] graph_edge_index criado no {self.device} com shape: {self.graph_edge_index.shape}")
        # --- FIM DA MUDANÇA 5 ---
        
        num_edges = self.graph_edge_index.size(1) if self.graph_edge_index.dim() == 2 else 0

        # --- MUDANÇA 6: Passar 'lm' para a função ---
        SystemReporter.report_graph_structure(num_nodes=num_nodes, num_edges=num_edges, lm=lm)

        all_state_dims = []
        for tl_id in tls_ids:
            try: # Adicionado try-except para robustez
                num_lanes = len(set(traci_conn.trafficlight.getControlledLanes(tl_id)))
                # Verifica se há definições de lógica antes de tentar acessar
                logic_defs = traci_conn.trafficlight.getCompleteRedYellowGreenDefinition(tl_id)
                if not logic_defs:
                    logging.warning(f"Nenhuma definição de lógica encontrada para TL {tl_id}, usando 0 fases verdes.")
                    num_green_phases = 0
                else:
                    logic = logic_defs[0]
                    num_green_phases = len([p for p in logic.phases if 'g' in p.state.lower() and 'y' not in p.state.lower()])
                all_state_dims.append(num_lanes + num_green_phases)
            except Exception as e:
                 logging.warning(f"Erro ao obter dimensões para TL {tl_id}: {e}")


        self.max_state_dim = max(all_state_dims) if all_state_dims else 0
        logging.info(lm.get_string("strategic_coordinator.initialize.max_state_dim", size=self.max_state_dim))

        # Certifica-se que max_state_dim não seja zero para evitar erro no GATConv
        if self.max_state_dim <= 0:
            logging.error("max_state_dim calculado como zero ou negativo. Não é possível inicializar o modelo GAT.")
            raise ValueError("Calculated max_state_dim is zero or negative.")

        gat_settings = self.settings['GAT_STRATEGIST']
        self.gat_model = GATStrategist(
            input_dim=self.max_state_dim,
            hidden_dim=gat_settings.getint('hidden_dim'),
            output_dim=self.output_dim,
            heads=gat_settings.getint('heads')
        ).to(self.device) # O modelo GAT ainda vai para a GPU
        logging.info(lm.get_string("strategic_coordinator.initialize.model_created", device=self.device))

        num_agents = len(tls_ids)
        # Os vetores estratégicos de saída também vão para a GPU
        self.strategic_vectors = torch.zeros((num_agents, self.output_dim), device=self.device)

        # Retorna o max_state_dim (local) e o output_dim (GAT)
        # O LifecycleManager usará isso para calcular o tamanho total
        # (max_local_obs + gat_output + num_override_flags)
        return self.max_state_dim, num_nodes, num_edges

    def update_if_needed(self, sim_time, current_states_dict):
        """
        Verifica se é hora de executar a GAT e atualiza os vetores estratégicos.
        """
        lm = self.locale_manager
        if self.gat_model is None: return
        # Garante que graph_edge_index foi inicializado
        if self.graph_edge_index is None:
             logging.warning("[StrategicCoordinator] graph_edge_index não inicializado. Pulando update.")
             return

        if (sim_time - self.last_update_time) >= self.update_frequency:
            # --- MUDANÇA 7: Chave de tradução corrigida (será adicionada no próximo arquivo) ---
            logging.info(lm.get_string("strategic_coordinator.update.running", fallback=f"Running GAT update at time {sim_time}"))

            num_agents = len(self.tl_id_to_idx)
            node_features = []
            valid_agent_indices = [] # Lista para rastrear quais agentes têm estado válido
            for i in range(num_agents):
                tl_id = self.tl_idx_to_id.get(i) # Usar .get() por segurança
                if not tl_id: continue

                state = current_states_dict.get(tl_id)
                 # Pula agentes sem estado válido neste passo
                if state is None or not isinstance(state, list):
                     logging.debug(f"Estado inválido ou ausente para {tl_id} no tempo {sim_time}. Usando padding.")
                     # Usamos um vetor de zeros como fallback para manter a estrutura
                     padded_state = [0.0] * self.max_state_dim
                else:
                    # Garante que o padding seja aplicado corretamente
                    current_len = len(state)
                    padding_needed = max(0, self.max_state_dim - current_len)
                    padded_state = state + ([0.0] * padding_needed)
                    # Garante que o tamanho final seja exatamente max_state_dim
                    padded_state = padded_state[:self.max_state_dim]
                    valid_agent_indices.append(i) # Marca este índice como válido

                node_features.append(padded_state)

            # Só continua se houver features para processar
            if not node_features:
                 logging.warning(f"Nenhum feature de nó válido para processar no tempo {sim_time}.")
                 return

            # Os node_features vão para a GPU antes de alimentar o modelo
            node_features_tensor = torch.tensor(node_features, dtype=torch.float32).to(self.device)

            self.gat_model.eval()
            with torch.no_grad():
                try:
                    # --- MUDANÇA 8: O edge_index_input agora vem direto de self.graph_edge_index (que já está no device) ---
                    # Não precisamos mais do .to('cpu')
                    output_vectors = self.gat_model(node_features_tensor, self.graph_edge_index)
                    # --- FIM DA MUDANÇA 8 ---

                    # Atualiza self.strategic_vectors APENAS para os agentes que tinham estado válido
                    if len(valid_agent_indices) > 0:
                        valid_indices_tensor = torch.tensor(valid_agent_indices, device=self.device)
                        if output_vectors.shape[0] == len(node_features):
                             self.strategic_vectors.index_put_((valid_indices_tensor,), output_vectors[valid_indices_tensor])
                        else:
                             logging.error(f"Shape mismatch: output_vectors ({output_vectors.shape[0]}) vs node_features ({len(node_features)}). Não foi possível atualizar strategic_vectors.")
                    else:
                         logging.warning(f"Nenhum agente com estado válido no tempo {sim_time}. strategic_vectors não atualizados.")

                except Exception as gat_err:
                     logging.error(f"Erro durante a execução do GAT model: {gat_err}", exc_info=True)


            self.last_update_time = sim_time

    def get_strategic_vector_for_agent(self, tl_id: str) -> list:
        """Retorna o vetor estratégico mais recente para um agente específico."""
        if tl_id not in self.tl_id_to_idx:
            # Retorna um vetor de zeros se o ID não for encontrado
            return [0.0] * self.output_dim

        agent_idx = self.tl_id_to_idx[tl_id]

        if self.strategic_vectors is None or agent_idx >= self.strategic_vectors.shape[0]:
             logging.warning(f"strategic_vectors não inicializado ou índice {agent_idx} fora dos limites para tl_id {tl_id}.")
             return [0.0] * self.output_dim

        try:
            return self.strategic_vectors[agent_idx].cpu().numpy().tolist()
        except IndexError:
             logging.error(f"IndexError ao acessar strategic_vectors no índice {agent_idx} para tl_id {tl_id}. Shape: {self.strategic_vectors.shape}")
             return [0.0] * self.output_dim