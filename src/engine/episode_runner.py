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

# File: src/engine/episode_runner.py (Corrigido: Re-adicionada lógica de Autorização, Log de Decisão e Timers Detalhados)
# Author: Gabriel Moraes
# Date: 01 de Novembro de 2025

import logging
from collections import deque, defaultdict
import numpy as np
import configparser
from multiprocessing import Queue
from queue import Empty, Full
import time
from typing import TYPE_CHECKING, Dict, Any, Union

# Adiciona o diretório 'src' ao path (mantido)
import sys
import os
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)


# Importações que não devem causar ciclo
from core.system_reporter import SystemReporter
from core.childhood_analyzer import ChildhoodAnalyzer
from core.maturity_manager import MaturityManager
# --- MUDANÇA 1: Importar o Enum de Maturidade ---
from core.enums import Maturity
# --- FIM DA MUDANÇA 1 ---

try:
    from core.decision_coordinator import DecisionCoordinator
    DECISION_CLASS_NAME = "DecisionCoordinator" 
except ImportError:
    try:
        from engine.decision_orchestrator import DecisionCoordinator
        DECISION_CLASS_NAME = "DecisionCoordinator" 
    except ImportError as e:
        logging.critical(f"[EpisodeRunner CRITICAL] Não foi possível importar DecisionCoordinator nem de engine nem de core: {e}")
        raise ImportError("DecisionCoordinator class not found in expected locations.") from e

if TYPE_CHECKING:
    from core.action_authorizer import ActionAuthorizer
    from utils.locale_manager_backend import LocaleManagerBackend
    from engine.environment import SumoEnvironment
    from core.population_manager import PopulationManager
    from core.learning_coordinator import LearningCoordinator
    from core.strategic_coordinator import StrategicCoordinator
    if DECISION_CLASS_NAME == "DecisionCoordinator":
        try: from core.decision_coordinator import DecisionCoordinator as DecisionCoordinatorHint
        except ImportError: from engine.decision_orchestrator import DecisionCoordinator as DecisionCoordinatorHint


class EpisodeRunner:
    """Orquestra a execução de um único episódio, focado no ciclo de RL."""

    def __init__(self, settings: configparser.ConfigParser, env: 'SumoEnvironment',
                 population_manager: 'PopulationManager', maturity_manager: MaturityManager,
                 learning_coordinator: 'LearningCoordinator', strategic_coordinator: 'StrategicCoordinator',
                 childhood_analyzer: ChildhoodAnalyzer,
                 action_authorizer: 'ActionAuthorizer',
                 n_observations: int, # Recebido do Trainer
                 guardian_state_queue: Union[Queue, None] = None,
                 guardian_signal_queue: Union[Queue, None] = None):

        self.settings = settings
        self.env = env
        self.learning_coordinator = learning_coordinator
        self.childhood_analyzer = childhood_analyzer
        self.population_manager = population_manager
        self.maturity_manager = maturity_manager
        self.strategic_coordinator = strategic_coordinator 
        self.action_authorizer = action_authorizer 
        self.n_observations = n_observations

        self.locale_manager = maturity_manager.locale_manager

        self.state_history: Dict[str, deque] = {}
        
        self.override_states: Dict[str, str] = {}
        self.current_operation_mode = "AUTOMATIC"

        self.guardian_state_queue = guardian_state_queue
        self.guardian_signal_queue = guardian_signal_queue

        # Instancia o DecisionCoordinator (corrigido na última interação)
        self.decision_coordinator = DecisionCoordinator(
            agents=population_manager.agents,
            neighborhoods=strategic_coordinator.neighborhoods if hasattr(strategic_coordinator, 'neighborhoods') and strategic_coordinator.neighborhoods else {},
            environment=env,
            strategic_coordinator=strategic_coordinator, 
            n_observations=self.n_observations,        
            message_size=2 
        )


        self.episode_max_steps = self.settings.getint('AI_TRAINING', 'episode_max_steps', fallback=5000)
        
        if self.settings.has_option('AI_TRAINING', 'update_timestep'):
             self.update_timestep = self.settings.getint('AI_TRAINING', 'update_timestep', fallback=2048)
        else:
             self.update_timestep = 2048
             logging.warning("[EpisodeRunner] Chave 'update_timestep' não encontrada em [AI_TRAINING]. Usando fallback 2048.")

        log_settings = self.settings['LOGGING'] if self.settings.has_section('LOGGING') else {}
        self.log_step_progress = log_settings.getboolean('log_step_progress', fallback=False)
        self.log_progress_frequency = log_settings.getint('log_progress_frequency', fallback=500)

        logging.info(self.locale_manager.get_string("episode_runner.init.created"))


    def run(self, episode_count: int) -> Dict[str, Dict[str, Any]]:
        lm = self.locale_manager
        self.env.reset()
        current_states_dict = self.env.get_global_state()
        if not current_states_dict:
             logging.error("[EpisodeRunner] Falha ao obter estado global inicial. Encerrando episódio.")
             return {}

        self._initialize_state_history(current_states_dict)

        self.current_operation_mode = current_states_dict.get("operation_mode", "AUTOMATIC")

        episode_metrics = defaultdict(lambda: {'reward': 0.0, 'entropies': []})
        done = False
        step_count = 0
        last_decision_data = {}

        logging.info(lm.get_string("episode_runner.run.start_unified").format(episode=episode_count))

        while not done and step_count < self.episode_max_steps:
            if not self.env.conn:
                 logging.warning("[EpisodeRunner] Conexão com o ambiente (proxy) perdida. Encerrando episódio.")
                 done = True
                 break

            t_total_start = time.perf_counter()

            step_count += 1
            current_sim_time = 0.0
            try:
                 if hasattr(self.env, 'conn') and self.env.conn and hasattr(self.env.conn, 'simulation'):
                      current_sim_time = self.env.conn.simulation.getTime()
                 else:
                      logging.warning("[EpisodeRunner] Conexão com simulação (proxy) inválida ao tentar obter tempo. Usando 0.0.")
                      done = True
                      break
            except Exception as e_time:
                 logging.warning(f"[EpisodeRunner] Erro ao obter tempo da simulação: {e_time}. Usando 0.0.")
                 done = True
                 break

            if self.log_step_progress and (step_count == 1 or step_count % self.log_progress_frequency == 0):
                SystemReporter.report_step_start(lm, step_count, current_sim_time, self.current_operation_mode)

            # --- MUDANÇA 2: Adicionar timer para o GAT (Analysis_PreStep) ---
            t_analysis_pre_start = time.perf_counter()
            if hasattr(self, 'strategic_coordinator'):
                 try:
                      state_values_for_gat = {tl_id: state for tl_id, state in current_states_dict.items() if isinstance(state, list)}
                      self.strategic_coordinator.update_if_needed(current_sim_time, state_values_for_gat)
                 except Exception as e_strat:
                      logging.error(f"[EpisodeRunner] Erro ao atualizar StrategicCoordinator: {e_strat}", exc_info=True)
            t_analysis_pre_end = time.perf_counter()
            # --- FIM DA MUDANÇA 2 ---

            t_decision_start = time.perf_counter()
            actions_to_apply, last_decision_data = self.decision_coordinator.get_coordinated_actions(
                current_states_dict, 
                self.state_history,
                self.current_operation_mode
            )
            t_decision_end = time.perf_counter()

            entropies = {}
            if last_decision_data: 
                 entropies = {tl_id: data['entropy'] for tl_id, data in last_decision_data.items() if 'entropy' in data}

            # --- MUDANÇA 3: Bloco de Autorização e Log (RE-ADICIONADO) ---
            t_auth_start = time.perf_counter()
            authorized_actions = {}
            for tl_id, action_int in actions_to_apply.items():
                agent_maturity = self.maturity_manager.agent_maturity.get(tl_id, Maturity.CHILD)
                
                # 1. Autorização (Regras da Escola de Pilotagem)
                is_authorized, reason = self.action_authorizer.is_action_authorized(
                    tl_id, agent_maturity, current_sim_time
                )
                
                # 2. Override Manual (Verificar estado)
                override_state = self.decision_coordinator.override_states.get(tl_id, "NORMAL")
                
                if override_state != "NORMAL":
                    is_authorized = False # AI não controla
                    reason_key = f"reporter.override_suffix_{override_state.lower()}"
                    reason = lm.get_string(reason_key, fallback=override_state) # Motivo é o override
                
                # Mapeia a ação (int) para string (para o log)
                action_str = lm.get_string("actions.keep_phase") # Ação 1 ou 2
                if action_int == 0:
                    action_str = lm.get_string("actions.change_phase")
                    
                # Mapeia maturidade (Enum) para string (para o log)
                maturity_str = agent_maturity.name
                
                # Loga a decisão (SEMPRE loga, mesmo se log_step_progress=False)
                SystemReporter.report_agent_decision(
                    lm, tl_id, maturity_str, action_str, is_authorized, reason, override_state
                )

                if is_authorized:
                    authorized_actions[tl_id] = action_int
                # Se não for autorizada, a ação NÃO é adicionada ao dict
                
            t_auth_end = time.perf_counter()
            # --- FIM DA MUDANÇA 3 ---

            t_guardian_send_start = time.perf_counter()
            if self.guardian_state_queue:
                try:
                    state_package = (current_states_dict, {}, done, 'training')
                    self.guardian_state_queue.put_nowait(state_package)
                except Full:
                    logging.warning("[EpisodeRunner] Fila do Guardião (estado) cheia.")
                except Exception as e_q_send:
                     logging.error(f"[EpisodeRunner] Erro ao enviar estado para fila do Guardião: {e_q_send}")
            t_guardian_send_end = time.perf_counter()

            t_guardian_recv_start = time.perf_counter()
            vetos_recebidos = {}
            if self.guardian_signal_queue:
                try:
                    while True:
                        veto = self.guardian_signal_queue.get_nowait()
                        vetos_recebidos[veto['target_tl']] = veto
                except Empty:
                    pass
                except Exception as e_q_recv:
                     logging.error(f"[EpisodeRunner] Erro ao receber sinal da fila do Guardião: {e_q_recv}")
            t_guardian_recv_end = time.perf_counter()

            if vetos_recebidos and self.env.action_supervisor:
                self.env.action_supervisor.update_vetos(vetos_recebidos)

            t_env_step_start = time.perf_counter()
            # --- MUDANÇA 4: Usar 'authorized_actions' ---
            next_states_dict, rewards, done = self.env.step(authorized_actions)
            # --- FIM DA MUDANÇA 4 ---
            t_env_step_end = time.perf_counter()

            # --- MUDANÇA 5: Adicionar timer (Analysis_PostStep) ---
            t_analysis_post_start = time.perf_counter()
            # (Nenhuma análise pós-step é necessária por enquanto, mas mantemos o timer)
            t_analysis_post_end = time.perf_counter()
            # --- FIM DA MUDANÇA 5 ---

            if next_states_dict:
                if "operation_mode" in next_states_dict:
                    self.current_operation_mode = next_states_dict["operation_mode"]
                if "override_commands" in next_states_dict:
                    commands = next_states_dict.pop("override_commands")
                    for command in commands:
                        semaphore_id = command.get("semaphore_id")
                        state = command.get("state")
                        if semaphore_id and state:
                            self.decision_coordinator.override_states[semaphore_id] = state
                if "active_overrides" in next_states_dict:
                     self.decision_coordinator.override_states.clear()
                     self.decision_coordinator.override_states.update(next_states_dict.get("active_overrides", {}))
                     next_states_dict.pop("active_overrides", None)

            t_learning_start = time.perf_counter()
            if rewards and last_decision_data:
                self.learning_coordinator.store_experience(last_decision_data, rewards, done)

            agent_list = list(self.population_manager.agents.values())
            update_ts = int(self.update_timestep) if self.update_timestep > 0 else 2048
            if agent_list and (len(agent_list[0].memory) >= update_ts or (done and len(agent_list[0].memory) > 0)):
                self.learning_coordinator.update_agents(next_states_dict, done)
            t_learning_end = time.perf_counter()

            if next_states_dict:
                current_states_dict = next_states_dict
            else:
                 logging.warning("[EpisodeRunner] Dicionário de próximos estados está inválido. Encerrando episódio.")
                 done = True

            if rewards:
                for tl_id, reward in rewards.items():
                    if tl_id not in episode_metrics: episode_metrics[tl_id] = {'reward': 0.0, 'entropies': []}
                    episode_metrics[tl_id]['reward'] += reward
            if entropies:
                for tl_id, entropy in entropies.items():
                    if tl_id not in episode_metrics: episode_metrics[tl_id] = {'reward': 0.0, 'entropies': []}
                    episode_metrics[tl_id]['entropies'].append(entropy)

            t_total_end = time.perf_counter()

            # --- MUDANÇA 6: Substituir o log do STEP_TIMER pelo formato detalhado ---
            if self.log_step_progress and (step_count == 1 or step_count % self.log_progress_frequency == 0):
                total_ms = (t_total_end - t_total_start) * 1000
                decision_ms = (t_decision_end - t_decision_start) * 1000
                auth_ms = (t_auth_end - t_auth_start) * 1000 # Tempo de autorização
                analysis_pre_ms = (t_analysis_pre_end - t_analysis_pre_start) * 1000
                guardian_send_ms = (t_guardian_send_end - t_guardian_send_start) * 1000
                guardian_recv_ms = (t_guardian_recv_end - t_guardian_recv_start) * 1000
                env_step_ms = (t_env_step_end - t_env_step_start) * 1000
                analysis_post_ms = (t_analysis_post_end - t_analysis_post_start) * 1000
                learning_ms = (t_learning_end - t_learning_start) * 1000
                
                # Log no formato desejado (PPO_Decision agora inclui autorização)
                log_message = (
                    f"[STEP_TIMER] Total: {total_ms:.2f}ms | "
                    f"PPO_Decision: {(decision_ms + auth_ms):.2f}ms | "
                    f"Analysis_PreStep: {analysis_pre_ms:.2f}ms | "
                    f"Guardian_SendState: {guardian_send_ms:.2f}ms | "
                    f"Guardian_RecvSignal: {guardian_recv_ms:.2f}ms | "
                    f"Environment_Step: {env_step_ms:.2f}ms | "
                    f"Analysis_PostStep: {analysis_post_ms:.2f}ms | "
                    f"PPO_Learning: {learning_ms:.2f}ms"
                )
                # O seu log de exemplo mostra o timer como [ERROR], mas vou manter [INFO]
                logging.info(log_message) 
            # --- FIM DA MUDANÇA 6 ---

        final_metrics: Dict[str, Dict[str, Any]] = {}
        for tl_id, data in episode_metrics.items():
            mean_entropy = np.mean(data['entropies']) if data['entropies'] else 0.0
            final_metrics[tl_id] = {'reward': data['reward'], 'entropy': mean_entropy}

        logging.info(f"Episódio {episode_count} concluído após {step_count} passos.")
        return final_metrics

    def _initialize_state_history(self, initial_states: dict):
        if not initial_states or not self.population_manager.agents:
            logging.warning("[EpisodeRunner] Não foi possível inicializar o histórico de estados (sem estados iniciais ou agentes).")
            return

        sequence_length = 4
        if self.settings.has_option('AI_TRAINING', 'sequence_length'):
             try:
                  sequence_length = self.settings.getint('AI_TRAINING', 'sequence_length', fallback=4)
             except ValueError:
                  logging.warning("[EpisodeRunner] Valor inválido para 'sequence_length'. Usando 4.")

        if sequence_length <= 0:
             logging.warning("[EpisodeRunner] 'sequence_length' deve ser > 0. Usando 1.")
             sequence_length = 1

        self.state_history.clear()
        
        agent_expected_obs_size = self.n_observations

        if agent_expected_obs_size <= 0:
             logging.error(f"[EpisodeRunner] Tamanho de observação calculado inválido ({agent_expected_obs_size}). Histórico não inicializado.")
             return

        logging.debug(f"[EpisodeRunner] Usando tamanho de observação {agent_expected_obs_size} para inicializar histórico.")

        for tl_id in self.population_manager.agents.keys():
            history = deque(maxlen=sequence_length)
            zero_state = [0.0] * agent_expected_obs_size
            for _ in range(sequence_length):
                history.append(zero_state)
            self.state_history[tl_id] = history

        logging.debug(f"[EpisodeRunner] Histórico de estados inicializado para {len(self.state_history)} agentes com sequence_length={sequence_length}.")