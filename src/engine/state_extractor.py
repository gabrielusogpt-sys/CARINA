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

# File: src/engine/state_extractor.py (Refatorado com importação robusta de TraCIException)
# Author: Gabriel Moraes
# Date: 26 de Outubro de 2025

import logging
import sys
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from utils.locale_manager_backend import LocaleManagerBackend

# Adiciona o diretório 'src' ao path para permitir importações absolutas (mantido)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# --- INÍCIO DA MUDANÇA: Bloco de importação robusto para TraCI ---
try:
    # Tenta importar traci normalmente primeiro
    import traci
    # Se traci foi importado, tenta importar a exceção específica
    from traci.exceptions import TraCIException
except (ImportError, ModuleNotFoundError) as e_traci:
    # Se falhou, verifica se SUMO_HOME está definido para tentar importação forçada
    if 'SUMO_HOME' in os.environ:
        tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
        if tools not in sys.path:
            sys.path.append(tools)
        try:
            import traci
            from traci.exceptions import TraCIException
            # Usar logging aqui pode ser problemático se ele ainda não foi configurado
            # É mais seguro usar print ou remover o log de sucesso daqui
            # logging.info(f"TraCI importado com sucesso via SUMO_HOME: {tools}")
        except (ImportError, ModuleNotFoundError) as e_sumohome:
            # Mesmo com SUMO_HOME, a importação falhou (ou estamos no proxy)
            # logging.warning(f"Falha ao importar TraCI/TraCIException mesmo com SUMO_HOME: {e_sumohome}. Definindo fallback.")
            print(f"[StateExtractor WARNING] Falha ao importar TraCI/TraCIException mesmo com SUMO_HOME: {e_sumohome}. Definindo fallback.") # Usar print
            # Define um fallback para TraCIException para evitar NameErrors
            class TraCIException(Exception): pass
    else:
        # SUMO_HOME não definido E importação inicial falhou (ou estamos no proxy)
        # logging.warning(f"SUMO_HOME não definido e importação de TraCI/TraCIException falhou: {e_traci}. Definindo fallback.")
        print(f"[StateExtractor WARNING] SUMO_HOME não definido e importação de TraCI/TraCIException falhou: {e_traci}. Definindo fallback.") # Usar print
        # Define um fallback para TraCIException
        class TraCIException(Exception): pass

# Agora, o código pode usar 'TraCIException' sabendo que ela sempre existirá (real ou fallback).
# --- FIM DA MUDANÇA ---

class StateExtractor:
    """O "Sensor" do ambiente: especialista em extrair e formatar estados do SUMO."""

    def __init__(self, traci_conn, locale_manager: 'LocaleManagerBackend'):
        # Verifica se traci_conn foi passado (pode ser None se a importação falhou antes)
        if traci_conn is None and 'traci' in sys.modules:
             self.conn = sys.modules['traci'] # Tenta pegar o proxy se traci_conn for None
             logging.warning("[StateExtractor] traci_conn era None, usando traci (proxy?) diretamente.")
        else:
             self.conn = traci_conn # Usa a conexão passada

        self.locale_manager = locale_manager
        self._green_phases_cache = {}
        logging.info(self.locale_manager.get_string("state_extractor.init.sensor_created"))

        if "SUMO_HOME" not in os.environ:
             logging.critical(self.locale_manager.get_string("state_extractor.init.sumo_home_missing"))


    def get_global_state_from_batch(self, batched_data: dict) -> dict:
        """Processa um pacote de dados pré-coletado e retorna o estado de todos os semáforos."""
        states = {}
        if not batched_data:
            logging.warning(self.locale_manager.get_string("state_extractor.batch.no_data"))
            return {}

        for tl_id in batched_data.get('tls_phases', {}).keys():
            states[tl_id] = self._get_state_for_tl(tl_id, batched_data)

        return states

    def _get_state_for_tl(self, tl_id: str, batched_data: dict) -> list:
        """Extrai o vetor de estado para um semáforo a partir dos dados em lote."""
        try:
            incoming_lanes = batched_data.get('tls_controlled_lanes', {}).get(tl_id, [])
            if not incoming_lanes: # Se não há vias controladas, retorna estado vazio logo
                 logging.debug(f"[StateExtractor] Semáforo {tl_id} não controla nenhuma via segundo os dados.")
                 return []

            lane_occupancies = [batched_data.get('lane_occupancies', {}).get(lane, 0.0) for lane in incoming_lanes]

            green_phases = self._get_green_phases_for_tl(tl_id)
            if not green_phases:
                 # Se não conseguimos determinar as fases verdes (erro TraCI ou semáforo sem lógica?),
                 # retorna apenas as ocupações para evitar erro. Idealmente, isso não deveria acontecer.
                 logging.warning(f"[StateExtractor] Não foi possível determinar fases verdes para {tl_id}. Retornando apenas ocupações.")
                 return lane_occupancies # Ou retornar [] ? Depende do que a IA espera.

            current_phase_index = batched_data.get('tls_phases', {}).get(tl_id, -1)
            current_phase_one_hot = [0] * len(green_phases)

            if current_phase_index in green_phases:
                try:
                    hot_index = green_phases.index(current_phase_index)
                    current_phase_one_hot[hot_index] = 1
                except ValueError:
                     # Se o índice da fase atual não estiver na lista de fases verdes (ex: fase amarela/vermelha)
                     # O one-hot permanecerá como [0, 0, ...] que é o correto.
                     pass
            elif current_phase_index != -1: # Loga aviso se a fase existe mas não é verde
                 logging.debug(f"[StateExtractor] Fase atual {current_phase_index} de {tl_id} não está na lista de fases verdes {green_phases}.")


            return lane_occupancies + current_phase_one_hot

        except (KeyError, IndexError) as e: # Mantém a captura de erros gerais
            logging.warning(self.locale_manager.get_string("state_extractor.batch.processing_error", tl_id=tl_id, error=e))
            return []
        except TraCIException as e_traci: # Captura erro específico do TraCI (agora definido)
             logging.warning(f"[StateExtractor] Erro TraCI ao processar dados para {tl_id}: {e_traci}")
             return []


    def get_traffic_light_ids(self) -> list:
        # Verifica se self.conn existe e tem o atributo esperado antes de chamar
        if hasattr(self.conn, 'trafficlight') and hasattr(self.conn.trafficlight, 'getIDList'):
            try:
                return self.conn.trafficlight.getIDList()
            except TraCIException: # Usa a TraCIException (real ou fallback)
                logging.warning("[StateExtractor] Erro TraCI ao obter lista de IDs de semáforos.")
                return []
        else:
            # Se self.conn for None ou não tiver o método (proxy pode não ter inicializado?)
            logging.error("[StateExtractor] Conexão TraCI (ou proxy) inválida para get_traffic_light_ids.")
            return []

    def _get_green_phases_for_tl(self, tl_id: str) -> list:
        if tl_id in self._green_phases_cache:
            return self._green_phases_cache[tl_id]

        # Verifica a conexão antes de usar
        if hasattr(self.conn, 'trafficlight') and hasattr(self.conn.trafficlight, 'getCompleteRedYellowGreenDefinition'):
            try:
                # A chamada getCompleteRedYellowGreenDefinition pode retornar lista vazia
                logic_defs = self.conn.trafficlight.getCompleteRedYellowGreenDefinition(tl_id)
                if not logic_defs: # Verifica se a lista não está vazia
                    logging.warning(f"[StateExtractor] Nenhuma definição de lógica encontrada para {tl_id}.")
                    return []
                logic = logic_defs[0] # Pega o primeiro (e geralmente único) programa
                # Filtra fases verdes (g minúsculo ou G maiúsculo) que NÃO contenham amarelo (y/Y)
                green_phases = sorted([
                    i for i, phase in enumerate(logic.phases)
                    if ('g' in phase.state.lower()) and ('y' not in phase.state.lower())
                ])
                if not green_phases:
                     logging.warning(f"[StateExtractor] Nenhuma fase puramente verde encontrada para {tl_id} na lógica: {logic.phases}")

                self._green_phases_cache[tl_id] = green_phases
                return green_phases
            except TraCIException as e: # Usa a TraCIException (real ou fallback)
                logging.warning(f"[StateExtractor] Erro TraCI ao obter lógica para {tl_id}: {e}")
                return []
            except IndexError: # Caso logic_defs seja inesperadamente uma lista vazia após a verificação (raro)
                 logging.warning(f"[StateExtractor] Erro inesperado (IndexError) ao acessar lógica para {tl_id}.")
                 return []
        else:
            logging.error(f"[StateExtractor] Conexão TraCI (ou proxy) inválida para _get_green_phases_for_tl({tl_id}).")
            return []


    def get_observation_space_size_for_tl(self, tl_id: str) -> int:
         # Verifica a conexão antes de usar
        if hasattr(self.conn, 'trafficlight') and hasattr(self.conn.trafficlight, 'getControlledLanes'):
            try:
                # Usa 'set' para contar vias únicas
                num_lanes = len(set(self.conn.trafficlight.getControlledLanes(tl_id)))
                num_green_phases = len(self._get_green_phases_for_tl(tl_id)) # Reutiliza a função cacheada
                return num_lanes + num_green_phases
            except TraCIException as e: # Usa a TraCIException (real ou fallback)
                logging.warning(f"[StateExtractor] Erro TraCI ao calcular tamanho da observação para {tl_id}: {e}")
                return 0
        else:
             logging.error(f"[StateExtractor] Conexão TraCI (ou proxy) inválida para get_observation_space_size_for_tl({tl_id}).")
             return 0

    def get_local_feature_glossary(self, tl_id: str) -> list[dict]:
        """Gera uma lista de nomes e descrições APENAS para as features LOCAIS."""
        lm = self.locale_manager
        glossary = []
        # Verifica a conexão
        if not hasattr(self.conn, 'trafficlight'):
            logging.error("[StateExtractor] Conexão TraCI (ou proxy) inválida para get_local_feature_glossary.")
            return glossary

        try:
            # Garante que as vias sejam únicas e ordenadas para consistência
            incoming_lanes = sorted(list(set(self.conn.trafficlight.getControlledLanes(tl_id))))
            for lane_id in incoming_lanes:
                glossary.append({
                    "feature_name": lm.get_string("state_extractor.glossary.feature_occupancy_name", fallback="Ocupação Via {lane_id}", lane_id=lane_id),
                    "description": lm.get_string("state_extractor.glossary.feature_occupancy_desc", fallback="Percentagem de ocupação da via {lane_id}.", lane_id=lane_id)
                })

            green_phases = self._get_green_phases_for_tl(tl_id) # Reutiliza a função cacheada
            for i, phase_idx in enumerate(green_phases):
                glossary.append({
                    "feature_name": lm.get_string("state_extractor.glossary.feature_phase_name", fallback="Fase Verde {index}", index=i),
                    "description": lm.get_string("state_extractor.glossary.feature_phase_desc", fallback="Indica se a {index}ª fase verde (Índice SUMO: {phase_id}) está ativa.", index=i+1, phase_id=phase_idx)
                })

            return glossary
        except TraCIException as e: # Usa a TraCIException (real ou fallback)
            logging.error(lm.get_string("state_extractor.glossary.generation_error", fallback="Erro ao gerar glossário para {tl_id}: {error}", tl_id=tl_id, error=e))
            return []