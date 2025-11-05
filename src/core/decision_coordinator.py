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

# File: src/core/decision_coordinator.py (CORRIGIDO)
# Author: Gabriel Moraes
# Date: 01 de Novembro de 2025

"""
Define a classe DecisionCoordinator.
Este componente encapsula a lógica de comunicação entre agentes e
a tomada de decisão coordenada a cada passo da simulação.

Esta versão foi corrigida para:
1. Adicionar self.override_states.
2. Receber o strategic_coordinator.
3. Construir o vetor de estado completo (local + vizinhos + GAT + overrides)
   e aplicar padding para corresponder ao tamanho de observação do agente.
"""
import logging
import torch
from typing import TYPE_CHECKING, Dict, List

# --- MUDANÇA 1: Importar dependências necessárias ---
if TYPE_CHECKING:
    from core.strategic_coordinator import StrategicCoordinator
    from engine.environment import SumoEnvironment
    from agents.local_agent import LocalAgent

try:
    from traci.exceptions import TraCIException
except (ImportError, ModuleNotFoundError):
    # Lógica de fallback para ambientes onde o traci não está no path padrão
    import sys, os
    if 'SUMO_HOME' in os.environ:
        tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
        if tools not in sys.path:
            sys.path.append(tools)
        from traci.exceptions import TraCIException
    else:
        # Não encerra o programa, apenas loga um aviso, pois o Trainer já faz isso.
        logging.warning("SUMO_HOME não definido, a importação de TraCIException pode falhar.")
        TraCIException = Exception # Fallback para uma exceção genérica
# --- FIM DA MUDANÇA 1 ---

class DecisionCoordinator:
    # --- MUDANÇA 2: Assinatura do __init__ atualizada ---
    def __init__(self, agents: Dict[str, 'LocalAgent'], 
                 neighborhoods: dict, 
                 environment: 'SumoEnvironment', 
                 strategic_coordinator: 'StrategicCoordinator', # Adicionado
                 message_size: int,
                 n_observations: int): # Adicionado
        """
        Inicializa o Coordenador de Decisões.
        """
        self.agents = agents
        self.neighborhoods = neighborhoods
        self.env = environment
        self.strategic_coordinator = strategic_coordinator # Armazenado
        self.message_size = message_size
        self.n_observations = n_observations # Tamanho final que o agente espera
        
        # Adiciona o atributo que faltava (causa do AttributeError)
        self.override_states: Dict[str, str] = {} 
        
        logging.info("[COORDINATOR] Coordenador de Decisões (Corrigido) criado.")
    # --- FIM DA MUDANÇA 2 ---

    # --- MUDANÇA 3: Assinatura de get_coordinated_actions atualizada ---
    def get_coordinated_actions(self, 
                                current_states: dict, 
                                state_history: dict,
                                current_operation_mode: str) -> tuple: # Adicionado
    # --- FIM DA MUDANÇA 3 ---
        """
        Executa o ciclo de comunicação em 2 fases e retorna as ações finais.
        """
        if not current_states:
            return {}, {}

        # --- FASE 1: Publicação de Mensagens (Inalterada) ---
        messages = self._gather_messages(current_states)

        # --- FASE 2: Decisão Coordenada ---
        actions_to_apply = {}
        last_decision_data = {}

        # Determina o modo de operação (afeta os flags de override)
        is_manual_mode = current_operation_mode == "MANUAL"

        for tl_id, agent in self.agents.items():
            local_state = current_states.get(tl_id)
            if not local_state or not isinstance(local_state, list):
                logging.debug(f"[Coordinator] Estado local ausente ou inválido para {tl_id}. Pulando decisão.")
                continue

            # --- MUDANÇA 4: Construção do Vetor de Estado Completo ---
            
            # 1. Mensagens dos Vizinhos (Como antes)
            neighbor_messages = []
            for neighbor_id in self.neighborhoods.get(tl_id, []):
                message = messages.get(neighbor_id, [0.0] * self.message_size)
                neighbor_messages.extend(message)

            # 2. Vetor GAT (Novo)
            gat_vector = self.strategic_coordinator.get_strategic_vector_for_agent(tl_id)

            # 3. Flags de Override (Novo)
            override_state = self.override_states.get(tl_id)
            is_alert = 1.0 if override_state == "ALERT" else 0.0
            is_off = 1.0 if override_state == "OFF" else 0.0
            
            # Se estamos em modo MANUAL, todos os flags ficam 0 (IA não deve aprender sobre isso)
            if is_manual_mode:
                 override_flags = [0.0, 0.0]
            else:
                 override_flags = [is_alert, is_off]

            # 4. Combina tudo
            # O `local_state` já é o `max_local_obs_size` (vindo do state_extractor com padding)
            # Mas vamos garantir o padding para o local_state primeiro, caso ele venha "puro"
            
            # (Início - Lógica de Padding para estado local)
            # Precisamos saber o max_local_obs_size
            # n_observations = local_state + neighbors + gat + overrides
            max_local_obs_size = self.n_observations - len(neighbor_messages) - len(gat_vector) - len(override_flags)
            
            padded_local_state = local_state
            local_len = len(local_state)
            
            if local_len < max_local_obs_size:
                padded_local_state.extend([0.0] * (max_local_obs_size - local_len))
            elif local_len > max_local_obs_size:
                padded_local_state = padded_local_state[:max_local_obs_size]
            # (Fim - Lógica de Padding)

            augmented_state = padded_local_state + neighbor_messages + gat_vector + override_flags
            
            # 5. Validação final do tamanho (Resolve o erro de "expected 18, got 5")
            current_len = len(augmented_state)
            if current_len != self.n_observations:
                logging.warning(f"[Coordinator] Discrepância de tamanho para {tl_id}! Esperado: {self.n_observations}, Obtido: {current_len} (LocalPadded: {len(padded_local_state)}, Neigh: {len(neighbor_messages)}, GAT: {len(gat_vector)}, Over: {len(override_flags)}). Ajustando...")
                
                padding_needed = self.n_observations - current_len
                if padding_needed > 0:
                    augmented_state.extend([0.0] * padding_needed) # Adiciona padding se faltar
                elif padding_needed < 0:
                    augmented_state = augmented_state[:self.n_observations] # Trunca se sobrar
            
            # --- FIM DA MUDANÇA 4 ---

            # Adiciona ao histórico (deque)
            if tl_id not in state_history:
                 logging.warning(f"[Coordinator] Histórico de estado não inicializado para {tl_id}. Pulando decisão.")
                 continue

            state_history[tl_id].append(augmented_state)
            state_sequence = list(state_history[tl_id])

            try:
                state_sequence_tensor = torch.tensor([state_sequence], dtype=torch.float32).to(agent.device)
            except Exception as e_tensor:
                 # Este erro não deve mais acontecer, mas mantemos o log
                 logging.error(f"[Coordinator] Erro ao criar tensor para {tl_id}: {e_tensor}. Estado (último item): {state_sequence[-1] if state_sequence else 'N/A'}")
                 continue 

            try:
                action, log_prob, state_val, dist_entropy = agent.choose_action(state_sequence_tensor)
                actions_to_apply[tl_id] = action.item()

                last_decision_data[tl_id] = {
                    'state_sequence': state_sequence,
                    'action': action,
                    'log_prob': log_prob,
                    'state_val': state_val,
                    'entropy': dist_entropy.item()
                }
            except Exception as e_action:
                 logging.error(f"[Coordinator] Erro ao chamar choose_action para {tl_id}: {e_action}", exc_info=True)

        return actions_to_apply, last_decision_data

    def _gather_messages(self, current_states: dict) -> dict:
        """
        Gera as mensagens de status de cada agente com base em seu estado local.
        (Lógica interna inalterada, mas corrigida para robustez)
        """
        messages = {}
        for tl_id, local_state in current_states.items():
            if not local_state or not isinstance(local_state, list):
                messages[tl_id] = [0.0] * self.message_size
                continue

            try:
                # Usa o state_extractor (via env) para obter as fases verdes
                green_phases_indices = self.env.state_extractor._get_green_phases_for_tl(tl_id)

                if green_phases_indices:
                    num_green_phases = len(green_phases_indices)
                    
                    # O estado local recebido (current_states) é APENAS ocupação + one-hot
                    # Ele NÃO deve ser maior que o número de vias + número de fases
                    
                    # Assume que o state_extractor.py está correto e local_state é (ocupações + one-hot)
                    if len(local_state) >= num_green_phases:
                        phase_part = local_state[-num_green_phases:]
                        occupancy_part = local_state[:-num_green_phases]
                        
                        current_phase_one_hot_idx = -1
                        if 1 in phase_part:
                             try:
                                 current_phase_one_hot_idx = phase_part.index(1)
                             except ValueError:
                                 pass 

                        congestion_index = sum(occupancy_part)
                        messages[tl_id] = [float(current_phase_one_hot_idx), float(congestion_index)]

                        # Padding/Truncamento da MENSAGEM (não do estado)
                        if self.message_size > 2:
                            messages[tl_id].extend([0.0] * (self.message_size - 2))
                        messages[tl_id] = messages[tl_id][:self.message_size]
                    else:
                        logging.warning(f"[Coordinator] Tamanho do estado local ({len(local_state)}) para {tl_id} menor que o número de fases verdes ({num_green_phases}). Enviando msg padrão.")
                        messages[tl_id] = [0.0] * self.message_size
                else:
                    logging.debug(f"[Coordinator] Nenhuma fase verde encontrada para {tl_id}. Enviando msg padrão.")
                    messages[tl_id] = [0.0] * self.message_size

            except (TraCIException, ValueError, TypeError) as e:
                logging.warning(f"[Coordinator] Erro ao processar mensagem para {tl_id}: {e}. Enviando msg padrão.")
                messages[tl_id] = [0.0] * self.message_size

        return messages