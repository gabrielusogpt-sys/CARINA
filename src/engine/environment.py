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

# File: src/engine/environment.py (Refatorado com importação robusta de TraCIException)
# Author: Gabriel Moraes
# Date: 26 de Outubro de 2025

import logging
import configparser
import sys
import os
from typing import TYPE_CHECKING

# Adiciona o diretório 'src' ao path (mantido)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

if TYPE_CHECKING:
    from utils.locale_manager_backend import LocaleManagerBackend

from engine.state_extractor import StateExtractor
from engine.reward_calculator import RewardCalculator
from engine.action_supervisor import ActionSupervisor
from simulation.connector import SumoConnector # Presume que está em src/simulation

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
            print(f"[Environment WARNING] Falha ao importar TraCI/TraCIException mesmo com SUMO_HOME: {e_sumohome}. Definindo fallback.") # Usar print
            # Define um fallback para TraCIException para evitar NameErrors
            class TraCIException(Exception): pass
    else:
        # SUMO_HOME não definido E importação inicial falhou (ou estamos no proxy)
        # logging.warning(f"SUMO_HOME não definido e importação de TraCI/TraCIException falhou: {e_traci}. Definindo fallback.")
        print(f"[Environment WARNING] SUMO_HOME não definido e importação de TraCI/TraCIException falhou: {e_traci}. Definindo fallback.") # Usar print
        # Define um fallback para TraCIException
        class TraCIException(Exception): pass

# Agora, o código pode usar 'TraCIException' sabendo que ela sempre existirá (real ou fallback).
# --- FIM DA MUDANÇA ---

class SumoEnvironment:
    """O "Maestro" do ambiente: orquestra os especialistas."""

    def __init__(self, settings: configparser.ConfigParser, locale_manager: 'LocaleManagerBackend'):
        self.settings = settings
        self.locale_manager = locale_manager
        lm = self.locale_manager

        traci_port = self.settings.getint('SUMO', 'traci_port')

        self.connector = SumoConnector(port=traci_port, locale_manager=lm)
        self.conn = None # Será definido em connect()
        self.scenario_path = None

        self.episode_max_steps = self.settings.getint('AI_TRAINING', 'episode_max_steps', fallback=5000)
        self.current_episode_steps = 0

        self.state_extractor: StateExtractor | None = None
        self.reward_calculator: RewardCalculator | None = None
        self.action_supervisor: ActionSupervisor | None = None

        self._last_batched_data = {}

        logging.info(lm.get_string("environment.init.maestro_created"))

    def connect(self):
        """Conecta ao SUMO e inicializa os componentes especialistas."""
        lm = self.locale_manager
        self.connector.connect() # Conecta ao proxy
        self.conn = self.connector.conn # Obtém a referência ao módulo traci (ou proxy)

        if self.conn:
            try:
                # Mesmo via proxy, tentamos obter o nome do cenário (o Controller responderá)
                self.scenario_path = self.conn.simulation.getOption('configuration-file')

                # Inicializa os especialistas passando a conexão (que pode ser o proxy)
                self.state_extractor = StateExtractor(self.conn, self.locale_manager)
                self.reward_calculator = RewardCalculator(self.settings, self.locale_manager)
                # O ActionSupervisor também precisa da conexão para interagir (via proxy)
                self.action_supervisor = ActionSupervisor(self.conn, self.settings, self.state_extractor, self.locale_manager)

                logging.info(lm.get_string("environment.connect.success", scenario=self.scenario_path))

            except TraCIException as e: # Captura a TraCIException real ou o fallback
                # Este erro pode ocorrer se o Central Controller não responder ou retornar um erro
                logging.error(lm.get_string("environment.connect.error", error=e))
                self.scenario_path = lm.get_string("environment.connect.unknown_scenario")
                # Considerar lançar uma exceção aqui se a conexão inicial falhar criticamente
                # raise RuntimeError(f"Falha crítica na conexão inicial via proxy: {e}")
            except Exception as e_general: # Captura outros erros inesperados
                 logging.error(f"[Environment] Erro inesperado durante a inicialização pós-conexão: {e_general}", exc_info=True)
                 self.scenario_path = lm.get_string("environment.connect.unknown_scenario")
                 # raise RuntimeError(f"Erro inesperado na inicialização pós-conexão: {e_general}")


    def close(self):
        """Fecha a conexão com o proxy."""
        self.connector.close()
        self.conn = None

    def reset(self):
        """Reseta o ambiente para um novo episódio, delegando aos especialistas."""
        lm = self.locale_manager
        logging.info(lm.get_string("environment.reset.start"))

        # Verifica se a conexão (proxy) existe
        if not self.conn:
            logging.error("[Environment] Tentativa de reset sem conexão ativa.")
            # Dependendo da lógica, pode retornar ou lançar um erro
            return # Ou raise RuntimeError("...")

        try:
            # Continua usando self.conn, que agora aponta para o proxy
            vehicle_ids = self.conn.vehicle.getIDList()
            for v_id in vehicle_ids:
                try:
                    self.conn.vehicle.remove(v_id)
                except TraCIException: # Usa a TraCIException (real ou fallback)
                    # Este log pode ser útil para depuração via proxy
                    logging.debug(lm.get_string("environment.reset.vehicle_already_removed", vehicle_id=v_id))
                    pass # Continua se o veículo já foi removido (normal em alguns cenários)
        except TraCIException as e: # Captura erros gerais do TraCI no reset
            logging.error(lm.get_string("environment.reset.clear_error", error=e))
            # Pode ser um erro de comunicação com o Controller via proxy
            error_msg = lm.get_string("environment.reset.runtime_error")
            raise RuntimeError(error_msg) # Re-lança como erro crítico
        except Exception as e_general: # Captura outros erros
             logging.error(f"[Environment] Erro inesperado durante o reset de veículos: {e_general}", exc_info=True)
             raise RuntimeError("Erro inesperado no reset")

        # Reseta os especialistas (ActionSupervisor precisa ser resetado)
        if self.action_supervisor:
            self.action_supervisor.reset()
        # StateExtractor e RewardCalculator geralmente não precisam de reset de estado interno aqui

        self.current_episode_steps = 0
        self._last_batched_data = {}
        logging.info(lm.get_string("environment.reset.success"))

    def step(self, actions: dict) -> tuple:
        """Executa um passo completo no ambiente, orquestrando os especialistas."""
        if not self.conn:
             logging.error("[Environment] Tentativa de step sem conexão ativa.")
             return {}, {}, True # Retorna estado vazio, recompensa vazia, done=True

        try:
            # Aplica ações via ActionSupervisor (que usa o proxy self.conn)
            if self.action_supervisor:
                self.action_supervisor.apply_actions(actions)

            # --- O passo da simulação é delegado ao proxy ---
            # O proxy envia 'simulationStep' para o Controller, que o executa
            # e SÓ DEPOIS responde ao proxy, destravando esta chamada.
            # self.conn.simulationStep() # Esta linha NÃO é mais necessária aqui, pois o proxy a trata internamente.

            # Obtém os dados JÁ ATUALIZADOS do Controller via proxy
            # O Controller coleta os dados APÓS o simulationStep real ter ocorrido.
            current_batched_data = self.conn.custom.get_batched_step_data()

            if not current_batched_data:
                logging.warning(self.locale_manager.get_string("environment.step.no_batch_data"))
                # Se não há dados, consideramos o fim ou um erro grave
                self.close() # Fecha a conexão proxy
                return {}, {}, True # Retorna estado vazio, recompensa vazia, done=True

            self.current_episode_steps += 1

            # Verifica condições de término (o Controller deve incluir MinExpectedNumber nos dados?)
            # Por enquanto, confiamos no Controller para avançar e no max_steps
            # Ou podemos pedir ao Controller para incluir 'min_expected_number' no batch
            min_expected_num = current_batched_data.get('sim_min_expected_number', 1) # Assume > 0 se não vier
            time_limit_reached = self.current_episode_steps >= self.episode_max_steps
            natural_end = min_expected_num == 0 # Usa o valor do batch se disponível
            done = time_limit_reached or (natural_end and self.current_episode_steps > 1) # Garante que não termine no passo 0

            # Extrai o estado dos dados recebidos
            next_states = {}
            if self.state_extractor:
                next_states = self.state_extractor.get_global_state_from_batch(current_batched_data)

            # Garante que as chaves de metadados importantes sejam repassadas (mantido)
            if "override_commands" in current_batched_data:
                next_states["override_commands"] = current_batched_data["override_commands"]
            if "active_overrides" in current_batched_data:
                next_states["active_overrides"] = current_batched_data["active_overrides"]
            if "operation_mode" in current_batched_data:
                next_states["operation_mode"] = current_batched_data["operation_mode"]

            # Calcula recompensas
            rewards = {}
            if self.reward_calculator:
                rewards = self.reward_calculator.calculate_rewards_from_batch(
                    list(next_states.keys()), # Usa as chaves do estado extraído
                    current_batched_data,
                    self._last_batched_data # Dados do passo anterior
                )

            # Guarda os dados atuais para o próximo cálculo de recompensa
            self._last_batched_data = current_batched_data

            return next_states, rewards, done

        except TraCIException as e: # Captura a TraCIException (real ou fallback)
            # Provavelmente um erro de comunicação com o Controller via proxy
            logging.warning(self.locale_manager.get_string("environment.step.traci_lost", error=e))
            self.close() # Fecha a conexão proxy
            return {}, {}, True # Considera como fim do episódio
        except Exception as e_general: # Captura outros erros
             logging.error(f"[Environment] Erro inesperado durante o step: {e_general}", exc_info=True)
             self.close()
             return {}, {}, True


    def get_global_state(self) -> dict:
        """Obtém o estado inicial do ambiente, antes do primeiro passo."""
        if not self.conn:
             logging.error("[Environment] Tentativa de get_global_state sem conexão ativa.")
             return {}
        try:
            # Pede os dados iniciais ao Controller via proxy
            initial_batch = self.conn.custom.get_batched_step_data()
            if not initial_batch:
                 logging.warning("[Environment] Não foram recebidos dados iniciais do batch.")
                 return {}

            self._last_batched_data = initial_batch # Guarda para o primeiro step

            initial_states = self.state_extractor.get_global_state_from_batch(initial_batch) if self.state_extractor else {}

            # Garante que o modo de operação inicial também seja propagado (mantido)
            if "operation_mode" in initial_batch:
                initial_states["operation_mode"] = initial_batch["operation_mode"]

            return initial_states

        except TraCIException as e:
            logging.error(f"[Environment] Erro TraCI ao obter estado global inicial: {e}")
            self.close()
            return {}
        except Exception as e_general:
            logging.error(f"[Environment] Erro inesperado ao obter estado global inicial: {e_general}", exc_info=True)
            self.close()
            return {}


    def get_traffic_light_ids(self) -> list:
        """Delega a obtenção dos IDs para o StateExtractor."""
        return self.state_extractor.get_traffic_light_ids() if self.state_extractor else []

    def get_observation_space_size_for_tl(self, tl_id: str) -> int:
        """Delega o cálculo do tamanho da observação para o StateExtractor."""
        # Nota: StateExtractor agora usa self.conn (proxy) internamente
        return self.state_extractor.get_observation_space_size_for_tl(tl_id) if self.state_extractor else 0

    def get_num_green_phases_for_tl(self, tl_id: str) -> int:
        """Delega a obtenção do número de fases verdes para o StateExtractor."""
        # Nota: StateExtractor agora usa self.conn (proxy) e cache interno
        return self.state_extractor._get_green_phases_for_tl(tl_id) if self.state_extractor else 0 # Chama método cacheado