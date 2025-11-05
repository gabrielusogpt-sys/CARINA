# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2025 Gabriel Moraes - Noxfort Labs
#
# (...) [Licença omitida para brevidade] (...)

# File: src/controller/request_processor.py (Corrigido: import configparser)
# Author: Gabriel Moraes
# Date: 26 de Outubro de 2025

import logging
import os
import sys
import configparser  # <<< ADICIONADO IMPORT <<<
from multiprocessing import Queue
from multiprocessing.connection import Connection
from queue import Empty, Full
from typing import TYPE_CHECKING, Any

# Adiciona o diretório 'src' ao path (mantido)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

if TYPE_CHECKING:
    from utils.locale_manager_backend import LocaleManagerBackend
    from controller.health_monitor import AIHealthMonitor
    from controller.override_manager import OverrideManager
    from central_controller import CentralController

from utils.settings_manager import SettingsManager

# --- Bloco de importação robusto para TraCI (Mantido) ---
try:
    import traci
    from traci.exceptions import TraCIException
except (ImportError, ModuleNotFoundError) as e_traci:
    if 'SUMO_HOME' in os.environ:
        tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
        if tools not in sys.path:
            sys.path.append(tools)
        try:
            import traci
            from traci.exceptions import TraCIException
        except (ImportError, ModuleNotFoundError) as e_sumohome:
            print(f"[RequestProcessor WARNING] Falha ao importar TraCI/TraCIException mesmo com SUMO_HOME: {e_sumohome}. Definindo fallback.")
            class TraCIException(Exception): pass
    else:
        print(f"[RequestProcessor WARNING] SUMO_HOME não definido e importação de TraCI/TraCIException falhou: {e_traci}. Definindo fallback.")
        class TraCIException(Exception): pass
# --- Fim do Bloco ---

class RequestProcessor:
    def __init__(self, settings: configparser.ConfigParser, ai_pipe_conn: Connection, watchdog_q: Queue,
                 health_monitor: 'AIHealthMonitor', sds_data_queue: Queue,
                 sas_data_queue: Queue, ui_command_queue: Queue,
                 locale_manager: 'LocaleManagerBackend',
                 override_manager: 'OverrideManager',
                 controller_instance: 'CentralController'):

        self.settings = settings
        self.ai_pipe_conn = ai_pipe_conn
        self.watchdog_q = watchdog_q
        self.health_monitor = health_monitor
        self.sds_queue = sds_data_queue
        self.sas_queue = sas_data_queue
        self.ui_command_queue = ui_command_queue
        self.locale_manager = locale_manager
        self.override_manager = override_manager
        self.controller = controller_instance

        self.maturity_phases = {}
        self.current_run_id = None
        self.override_commands_buffer = []

        logging.info(self.locale_manager.get_string("request_processor.init.processor_created"))

    def process_queues(self, sumo_conn: Any, is_ai_healthy: bool):
        if not sumo_conn:
             logging.error("[RequestProcessor] Conexão SUMO inválida. Pulando processamento de filas.")
             return

        self._process_ui_commands(sumo_conn)

        if is_ai_healthy:
            self._process_ai_requests(sumo_conn)
            try:
                while True: self.watchdog_q.get_nowait()
            except Empty:
                pass
        else:
            self._process_watchdog_commands(sumo_conn)

    def _process_ui_commands(self, sumo_conn: Any):
        lm = self.locale_manager
        try:
            while True:
                command = self.ui_command_queue.get_nowait()
                if not isinstance(command, dict): continue

                cmd_type = command.get("type")
                payload = command.get("payload", {})

                logging.info(lm.get_string("request_processor.ui_command.received", type=cmd_type))

                if cmd_type == "save_settings":
                    settings_manager = SettingsManager()
                    settings_manager.save_settings(payload)
                    logging.info(lm.get_string("request_processor.ui_command.save_success"))

                elif cmd_type == "set_global_mode":
                    new_mode = payload.get("mode", "AUTOMATIC").upper()
                    old_mode = self.controller.current_operation_mode
                    if new_mode != old_mode and new_mode in ["AUTOMATIC", "SEMI_AUTOMATIC", "MANUAL"]:
                        logging.info(f"[CONTROLE GLOBAL] Modo de operação alterado de '{old_mode}' para '{new_mode}' pelo operador.")
                        self.controller.current_operation_mode = new_mode
                        self.controller._save_global_state_to_disk()
                    elif new_mode != old_mode:
                         logging.warning(f"[RequestProcessor] Tentativa de definir modo global inválido: '{new_mode}'")

                elif cmd_type == "set_semaphore_override":
                    self.override_commands_buffer.append(payload)
                    logging.warning(
                        lm.get_string(
                            "request_processor.override.manual_intervention",
                            semaphore_id=payload.get('semaphore_id', 'N/A'),
                            state=payload.get('state', 'N/A')
                        )
                    )
                    self.override_manager.handle_ui_command(payload, sumo_conn)

                elif cmd_type == "set_semaphore_timings":
                    logging.warning(
                        f"[CONFIGURAÇÃO MANUAL] Operador alterou os tempos do semáforo '{payload.get('semaphore_id', 'N/A')}': "
                        f"Tempo de Verde='{payload.get('green_time', 'N/A')}', Tempo de Amarelo='{payload.get('yellow_time', 'N/A')}' "
                        f"(Modo de Operação: {self.controller.current_operation_mode}). (Funcionalidade não implementada no backend)"
                    )
                else:
                    logging.warning(f"[RequestProcessor] Comando UI desconhecido recebido: {cmd_type}")

        except Empty:
            pass
        except TraCIException as e_traci:
             logging.error(f"[RequestProcessor] Erro TraCI ao processar comando da UI: {e_traci}", exc_info=True)
        except Exception as e:
            logging.error(lm.get_string("request_processor.ui_command.processing_error", error=e), exc_info=True)

    def _collect_batched_step_data(self, sumo_conn: Any) -> dict:
        if not sumo_conn: return {}
        try:
            traffic_light_ids = sumo_conn.trafficlight.getIDList()
            tls_lanes_state = {}
            tls_controlled_lanes_map = {}
            for tl_id in traffic_light_ids:
                controlled_lanes = sumo_conn.trafficlight.getControlledLanes(tl_id)
                unique_sorted_lanes = sorted(list(set(controlled_lanes)))
                tls_controlled_lanes_map[tl_id] = unique_sorted_lanes
                try:
                     state_string = sumo_conn.trafficlight.getRedYellowGreenState(tl_id)
                     if len(controlled_lanes) == len(state_string):
                         tls_lanes_state[tl_id] = dict(zip(controlled_lanes, state_string))
                     else:
                          logging.warning(f"[BatchCollect] Discrepância no tamanho entre vias controladas ({len(controlled_lanes)}) e string de estado ({len(state_string)}) para {tl_id}")
                          if len(unique_sorted_lanes) == len(state_string):
                               tls_lanes_state[tl_id] = dict(zip(unique_sorted_lanes, state_string))
                except TraCIException as e_state:
                     logging.warning(f"[BatchCollect] Erro TraCI ao obter estado RYG para {tl_id}: {e_state}")

            all_lane_ids = sumo_conn.lane.getIDList()
            all_edge_ids = sumo_conn.edge.getIDList()
            all_junction_ids = sumo_conn.junction.getIDList()

            batch_data = {
                "run_id": self.current_run_id,
                "sim_time": sumo_conn.simulation.getTime(),
                "net_file": sumo_conn.simulation.getOption("net-file"),
                "scenario_name": "",
                "operation_mode": self.controller.current_operation_mode,
                "lane_occupancies": {lane: sumo_conn.lane.getLastStepOccupancy(lane) for lane in all_lane_ids},
                "tls_phases": {tl: sumo_conn.trafficlight.getPhase(tl) for tl in traffic_light_ids},
                "tls_controlled_lanes": tls_controlled_lanes_map,
                "tls_lanes_state": tls_lanes_state,
                "lane_waiting_time": {lane: sumo_conn.lane.getWaitingTime(lane) for lane in all_lane_ids},
                "sim_starting_teleports_len": len(sumo_conn.simulation.getStartingTeleportIDList()),
                "sim_emergency_stops_len": len(sumo_conn.simulation.getEmergencyStoppingVehiclesIDList()),
                "sim_emergency_stop_positions": [sumo_conn.vehicle.getPosition(v_id) for v_id in sumo_conn.simulation.getEmergencyStoppingVehiclesIDList()],
                "lane_vehicle_ids": {lane: sumo_conn.lane.getLastStepVehicleIDs(lane) for lane in all_lane_ids},
                "junction_positions": {j: sumo_conn.junction.getPosition(j) for j in all_junction_ids},
                "maturity_phases": self.maturity_phases,
                "active_overrides": self.override_manager.active_overrides,
                "edge_mean_speeds": {edge: sumo_conn.edge.getLastStepMeanSpeed(edge) for edge in all_edge_ids},
                "sim_step_length": self.settings.getfloat('SUMO', 'step_length', fallback=1.0),
                "sim_min_expected_number": sumo_conn.simulation.getMinExpectedNumber(),
            }

            net_file_path = batch_data.get("net_file", "")
            if net_file_path:
                 config_file_path = sumo_conn.simulation.getOption('configuration-file')
                 scenario_filename = os.path.basename(config_file_path)
                 scenario_name, _ = os.path.splitext(scenario_filename)
                 batch_data["scenario_name"] = scenario_name

            return batch_data

        except TraCIException as e:
            logging.error(self.locale_manager.get_string("request_processor.batch_collect.error", error=e), exc_info=True)
            return {}
        except Exception as e_general:
             logging.error(f"[BatchCollect] Erro inesperado durante coleta de dados: {e_general}", exc_info=True)
             return {}

    def _process_ai_requests(self, sumo_conn: Any):
        lm = self.locale_manager
        try:
            if self.ai_pipe_conn.poll():
                request = self.ai_pipe_conn.recv()
                self.health_monitor.record_activity()

                if self.override_manager.is_ai_command_blocked(request):
                    module_name, func_name, args, _ = request
                    if module_name == 'trafficlight' and func_name == 'setPhase' and args:
                        tl_id = args[0]
                        override_state = self.override_manager.active_overrides.get(tl_id, "N/A")
                        logging.info(
                            lm.get_string(
                                "request_processor.override.ai_ignored",
                                tl_id=tl_id,
                                state=override_state
                            )
                        )
                    else:
                         logging.info(f"[RequestProcessor] Comando AI {module_name}.{func_name} bloqueado por override manual.")

                    self.ai_pipe_conn.send(None)
                    return

                module_name, func_name, args, kwargs = request
                result = None

                if module_name == 'custom':
                    if func_name == 'update_maturity_state':
                        new_phases_data = args[0] if args else {}
                        if isinstance(new_phases_data, dict):
                            self.maturity_phases = new_phases_data
                            if self.current_run_id is None and isinstance(new_phases_data.get("run_id"), int):
                                 self.current_run_id = new_phases_data.get("run_id")
                                 logging.info(f"[RequestProcessor] Run ID {self.current_run_id} recebido da IA.")
                        result = True

                    elif func_name == 'get_batched_step_data':
                        result = self._collect_batched_step_data(sumo_conn)
                        if result:
                            if self.override_commands_buffer:
                                result["override_commands"] = self.override_commands_buffer.copy()
                                self.override_commands_buffer.clear()
                            try:
                                self.sds_queue.put_nowait(result)
                                self.sas_queue.put_nowait(result)
                            except Full:
                                logging.warning(lm.get_string("request_processor.ai_request.queue_full_warning"))

                elif hasattr(sumo_conn, module_name):
                    traci_module = getattr(sumo_conn, module_name)
                    if hasattr(traci_module, func_name):
                        traci_function = getattr(traci_module, func_name)
                        result = traci_function(*args, **kwargs)
                    else:
                        result = AttributeError(f"Função '{func_name}' não encontrada no módulo traci '{module_name}'")
                        logging.error(str(result))
                else:
                    result = AttributeError(f"Módulo traci '{module_name}' não encontrado")
                    logging.error(str(result))

                self.ai_pipe_conn.send(result)

        except EOFError:
             logging.warning("[RequestProcessor] Pipe de comunicação com a IA fechado (EOFError). A IA pode ter encerrado.")
        except OSError as e_os:
             logging.error(f"[RequestProcessor] Erro de OS no Pipe da IA: {e_os}", exc_info=True)
        except TraCIException as e_traci:
             logging.error(f"[RequestProcessor] Erro TraCI ao processar pedido da IA: {e_traci}", exc_info=True)
             if self.ai_pipe_conn and not self.ai_pipe_conn.closed:
                 self.ai_pipe_conn.send(e_traci)
        except Exception as e:
            logging.error(lm.get_string("request_processor.ai_request.processing_error", error=e), exc_info=True)
            if self.ai_pipe_conn and not self.ai_pipe_conn.closed:
                try:
                    self.ai_pipe_conn.send(e)
                except Exception as send_e:
                    logging.error(f"[RequestProcessor] Falha ao enviar erro de volta para a IA: {send_e}")

    def _process_watchdog_commands(self, sumo_conn: Any):
        lm = self.locale_manager
        command_batch = None
        try:
            while True: command_batch = self.watchdog_q.get_nowait()
        except Empty:
            pass

        if not command_batch: return

        try:
            for command in command_batch:
                cmd_type = command.get("type")
                if cmd_type == "set_program_all":
                    program_id = command.get("value", "0")
                    all_tls_ids = sumo_conn.trafficlight.getIDList()
                    for tl_id in all_tls_ids:
                        if tl_id not in self.override_manager.active_overrides:
                            try:
                                if sumo_conn.trafficlight.getProgram(tl_id) != program_id:
                                    sumo_conn.trafficlight.setProgram(tl_id, program_id)
                            except TraCIException as e_wd_tl:
                                logging.warning(f"[Watchdog] Erro TraCI ao definir programa para {tl_id}: {e_wd_tl}")
                                continue
                else:
                    logging.warning(f"[RequestProcessor] Comando Watchdog desconhecido: {cmd_type}")

        except TraCIException as e_wd:
            logging.error(f"[RequestProcessor] Erro TraCI ao processar comando do Watchdog: {e_wd}", exc_info=True)
        except Exception as e:
            logging.error(lm.get_string("request_processor.watchdog.processing_error", error=e), exc_info=True)