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

# File: src/engine/trainer.py (Corrigido: Corrigida a lógica de inicialização da População)
# Author: Gabriel Moraes
# Date: 01 de Novembro de 2025

import logging
import configparser
import os
from multiprocessing import Queue
from multiprocessing.connection import Connection
import torch
import sys
from typing import TYPE_CHECKING

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

if TYPE_CHECKING:
    from utils.locale_manager_backend import LocaleManagerBackend

from engine.initialization_orchestrator import InitializationOrchestrator
from engine.post_episode_coordinator import PostEpisodeCoordinator
from engine.episode_runner import EpisodeRunner
from engine.service_manager import ServiceManager
from database.database_manager import DatabaseManager
from utils.locale_manager_backend import LocaleManagerBackend

class Trainer:
    """O Maestro que gerencia o serviço de treinamento, agora focado apenas na IA."""

    def __init__(self, settings: configparser.ConfigParser, log_dir: str, gpu_info: str,
                 pipe_conn: Connection,
                 guardian_state_queue: Queue, guardian_signal_queue: Queue, db_data_queue: Queue):
        self.settings = settings
        self.log_dir = log_dir
        self.gpu_info = gpu_info
        self.pipe_conn = pipe_conn
        
        self.locale_manager = LocaleManagerBackend()
        
        self.initialization_orchestrator = InitializationOrchestrator(
            self.settings, self.log_dir, self.gpu_info, self.locale_manager
        )
        
        self.env = None
        self.service_manager = None
        
        self.guardian_state_queue = guardian_state_queue
        self.guardian_signal_queue = guardian_signal_queue
        self.db_data_queue = db_data_queue
        self.run_id = None
        self.shutdown_requested = False
        
    def _check_for_shutdown_signal(self):
        """Verifica se o CentralController enviou um sinal de encerramento."""
        lm = self.locale_manager
        if self.pipe_conn.poll():
            try:
                message = self.pipe_conn.recv()
                if isinstance(message, tuple) and message[0] == "system" and message[1] == "shutdown":
                    logging.info(lm.get_string("trainer.shutdown.signal_received"))
                    self.shutdown_requested = True
            except (EOFError, OSError):
                logging.warning(lm.get_string("trainer.shutdown.connection_lost"))
                self.shutdown_requested = True

    def start_continuous_service(self):
        """O ponto de entrada principal que orquestra o ciclo de vida do treinamento."""
        lm = self.locale_manager
        try:
            # Importa o traci_proxy e aplica o monkey patch
            from core import traci_proxy
            sys.modules['traci'] = traci_proxy
            traci_proxy.init_proxy_pipe(self.pipe_conn)
            import traci
            
            # 1. Inicialização
            init_payload = self.initialization_orchestrator.initialize_system()
            
            self.service_manager = ServiceManager(locale_manager=lm)

            self.env = init_payload["env"]
            lifecycle_manager = init_payload["lifecycle_manager"]
            childhood_analyzer = init_payload["childhood_analyzer"]
            scenario_results_dir = init_payload["scenario_results_dir"]
            
            db_manager = DatabaseManager(locale_manager=lm)
            
            scenario_name = "unknown"
            if self.env and self.env.scenario_path:
                 scenario_name = os.path.basename(self.env.scenario_path).replace(".sumocfg", "")
            
            self.run_id = db_manager.create_simulation_run(scenario_name=scenario_name)
            
            if self.run_id is None:
                raise RuntimeError(lm.get_string("trainer.run.db_error"))
            
            logging.info(lm.get_string("trainer.run.new_run_id", run_id=self.run_id))
            
            # 2. Importações Pesadas (após inicialização leve)
            from core.population_manager import PopulationManager
            from core.strategic_coordinator import StrategicCoordinator
            from core.maturity_manager import MaturityManager
            from core.threshold_calibrator import ThresholdCalibrator
            from core.learning_coordinator import LearningCoordinator
            from core.maturity_reporter import MaturityReporter
            from core.action_authorizer import ActionAuthorizer

            # 3. Criação dos Componentes de IA
            strategic_coordinator = StrategicCoordinator(self.settings, init_payload['device'], lm)
            
            # --- MUDANÇA 1: Lógica de inicialização corrigida ---
            
            # Primeiro, inicializa o GAT para saber o max_local_obs_size
            max_local_obs_size, _, _ = strategic_coordinator.initialize(self.env.conn)

            # Cria o PopulationManager
            population_manager = PopulationManager(self.settings, lifecycle_manager, lm)
            
            # Agora, delega a criação dos agentes ao PopulationManager,
            # passando os argumentos necessários que ele (agora) espera.
            n_observations = population_manager.initialize_population(
                self.env, 
                max_local_obs_size, # Passa o tamanho local
                strategic_coordinator.output_dim # Passa o tamanho do GAT
            )
            # O PopulationManager agora tem self.agents e self.guardians preenchidos
            # E nós capturamos o n_observations (tamanho total) que ele retornou.
            
            # --- FIM DA MUDANÇA 1 ---

            maturity_reporter = MaturityReporter(locale_manager=lm)
            
            action_authorizer = ActionAuthorizer(traffic_profiles={}, locale_manager=lm)
            maturity_manager = MaturityManager(settings=self.settings['MATURITY'], baseline={}, locale_manager=lm, reporter=maturity_reporter)
            maturity_state_path = os.path.join(scenario_results_dir, "checkpoints", "maturity_state.json")
            maturity_manager.load_state(maturity_state_path)
            maturity_manager.register_agents(list(population_manager.agents.keys()))
            
            logging.info("Enviando estado de maturidade inicial para o Controle Central...")
            traci.update_maturity_state(maturity_manager.get_state())

            learning_coordinator = LearningCoordinator(agents=population_manager.agents, state_history={}, locale_manager=lm)
            calibrator = ThresholdCalibrator(self.settings['CALIBRATION'], locale_manager=lm)
            
            self.service_manager.start_all_services(
                settings=self.settings,
                guardian_state_queue=self.guardian_state_queue,
                guardian_signal_queue=self.guardian_signal_queue,
                scenario_dir=init_payload["scenario_results_dir"],
                agent_ids=list(population_manager.agents.keys())
            )
            
            # --- MUDANÇA 2: Passar 'n_observations' para o EpisodeRunner ---
            # (Esta parte já estava correta da correção anterior, mas agora
            # o n_observations vem da chamada correta ao population_manager)
            episode_runner = EpisodeRunner(
                settings=self.settings, env=self.env, 
                population_manager=population_manager,
                maturity_manager=maturity_manager,
                learning_coordinator=learning_coordinator,
                strategic_coordinator=strategic_coordinator,
                childhood_analyzer=childhood_analyzer,
                action_authorizer=action_authorizer,
                n_observations=n_observations, # <<< ARGUMENTO FORNECIDO
                guardian_state_queue=self.guardian_state_queue,
                guardian_signal_queue=self.guardian_signal_queue
            )
            # --- FIM DA MUDANÇA 2 ---
            
            post_episode_coordinator = PostEpisodeCoordinator(
                settings=self.settings, 
                population_manager=population_manager,
                maturity_manager=maturity_manager,
                calibrator=calibrator,
                lifecycle_manager=lifecycle_manager,
                db_data_queue=self.db_data_queue,
                run_id=self.run_id,
                locale_manager=lm
            )

            # 4. Loop Principal de Treino (inalterado)
            episode_count = 0
            if childhood_analyzer.check_cache():
                profiles, baseline = childhood_analyzer.load_from_cache()
                action_authorizer.traffic_profiles = profiles
                maturity_manager.baseline_performance = baseline.get('mean_reward', -10000)
            else:
                logging.info(lm.get_string("trainer.run.cache_not_found"))
                episode_count = 1
                episode_metrics = episode_runner.run(episode_count)
                profiles, baseline = childhood_analyzer.run_analysis([episode_metrics])
                childhood_analyzer.save_to_cache(profiles, baseline)
                action_authorizer.traffic_profiles = profiles
                maturity_manager.baseline_performance = baseline.get('mean_reward', -10000)
                post_episode_coordinator.run(episode_count, episode_metrics)

            while not self.shutdown_requested:
                episode_count += 1
                self._check_for_shutdown_signal()
                if self.shutdown_requested:
                    break
                episode_metrics = episode_runner.run(episode_count)
                post_episode_coordinator.run(episode_count, episode_metrics)
                
        except KeyboardInterrupt:
            if lm: logging.info(lm.get_string("trainer.main.keyboard_interrupt"))
        except Exception as e:
            if lm: logging.error(lm.get_string("trainer.main.fatal_error", error=e), exc_info=True)
        finally:
            # 5. Encerramento (inalterado)
            if lm and self.service_manager and 'maturity_manager' in locals() and 'lifecycle_manager' in locals() and 'population_manager' in locals():
                self.service_manager.stop_all_services()
                logging.info(lm.get_string("trainer.main.final_checkpoint"))
                maturity_state_path = os.path.join(lifecycle_manager.scenario_checkpoint_dir, "maturity_state.json")
                maturity_manager.save_state(maturity_state_path)
                shutdown_reason = lm.get_string("trainer.shutdown.reason")
                lifecycle_manager.save_all_checkpoints(population_manager.agents, shutdown_reason)
                
                if self.env:
                    self.env.close()
                logging.info(lm.get_string("trainer.main.service_finished"))