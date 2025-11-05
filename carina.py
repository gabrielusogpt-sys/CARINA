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

# File: carina.py (CORRIGIDO - Lógica da UI restaurada)
# Author: Gabriel Moraes
# Date: 27 de Outubro de 2025

print("[LAUNCHER STARTING] Script carina.py executando...") # Debug inicial

import sys
import os

print(f"[LAUNCHER DEBUG] Initial sys.path: {sys.path}")

# --- Adiciona src ao sys.path APENAS no modo de desenvolvimento ---
IS_FROZEN = getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')
if not IS_FROZEN:
    project_root_dev = os.path.dirname(os.path.abspath(__file__))
    src_path_dev = os.path.join(project_root_dev, 'src')
    if src_path_dev not in sys.path:
        sys.path.insert(0, src_path_dev)
    print(f"[Launcher Pre-Check] Current sys.path (Dev Mode): {sys.path}")
else:
    print(f"[Launcher Pre-Check] Current sys.path (Frozen Mode - Hook should have run): {sys.path}")
# --- Fim ---


# --- Tenta importar xxhash ---
try:
    import xxhash
    print("[Launcher Pre-Check] xxhash imported successfully.")
except ImportError as e:
    print(f"[Launcher Pre-Check] FAILED to import xxhash. Error: {e}")
    print(f"[Launcher Pre-Check] Current sys.path during failure: {sys.path}")
# --- Fim ---


# Importações normais
import time
import configparser
import logging
import multiprocessing
from multiprocessing import Process, Queue, Pipe, set_start_method
from multiprocessing.connection import Connection
import threading
import psutil
import subprocess
import traceback
import datetime

# --- Lógica de importação (Importa tudo necessário) ---
try:
    if IS_FROZEN:
        print("[Launcher Pre-Check] Attempting direct imports (Frozen mode)...")
        from utils.paths import resource_path, get_base_output_dir
        from central_controller import CentralController # <<< NECESSÁRIO
        from main import run_ai_process # <<< NECESSÁRIO
        from watchdog import run_watchdog # <<< NECESSÁRIO
        from utils.logging_setup import setup_logging
        from sds.dashboard_worker import run_sds_worker # <<< NECESSÁRIO
        from sas.analysis_worker import run_analysis_worker # <<< NECESSÁRIO
        from database.database_worker import run_database_worker # <<< NECESSÁRIO
        from utils.metrics_manager import MetricsManager # NECESSÁRIO para run_controller_process
        from utils.locale_manager_backend import LocaleManagerBackend # NECESSÁRIO
        print("[Launcher Pre-Check] Successfully imported required components directly (Frozen mode).")
    else:
        print("[Launcher Pre-Check] Attempting imports with 'src.' prefix (Dev mode)...")
        from src.utils.paths import resource_path, get_base_output_dir
        from src.central_controller import CentralController # <<< NECESSÁRIO
        from src.main import run_ai_process # <<< NECESSÁRIO
        from src.watchdog import run_watchdog # <<< NECESSÁRIO
        from src.utils.logging_setup import setup_logging
        from src.sds.dashboard_worker import run_sds_worker # <<< NECESSÁRIO
        from src.sas.analysis_worker import run_analysis_worker # <<< NECESSÁRIO
        from src.database.database_worker import run_database_worker # <<< NECESSÁRIO
        from src.utils.metrics_manager import MetricsManager # NECESSÁRIO para run_controller_process
        from src.utils.locale_manager_backend import LocaleManagerBackend # NECESSÁRIO
        print("[Launcher Pre-Check] Successfully imported required components using 'src.' prefix (Dev mode).")

except ImportError as e:
     print(f"CRITICAL PRE-LOGGING IMPORT ERROR: {e}")
     # ... (lógica de log de emergência inalterada) ...
     sys.exit(1)
# --- Fim ---


os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
if sys.platform == 'win32':
    try:
        os.system('chcp 65001 > nul')
    except Exception:
        pass

# Determina project_root corretamente
if IS_FROZEN:
    project_root = os.path.dirname(sys.executable)
else:
    project_root = os.path.dirname(os.path.abspath(__file__))

print(f"[LAUNCHER DEBUG] Project root determined as: {project_root}")


# >>>>> A função run_controller_process será chamada agora <<<<<
def run_controller_process(settings: configparser.ConfigParser, pipe_conn: Connection, wd_q: Queue, sds_q: Queue, sas_q: Queue, ui_q: Queue):
    # ... (código completo de run_controller_process inalterado aqui) ...
    log_base_dir = get_base_output_dir()
    log_dir = os.path.join(log_base_dir, "logs", "central_controller")
    try:
        os.makedirs(log_dir, exist_ok=True)
        setup_logging(log_dir=log_dir)
    except Exception as e:
        print(f"Error setting up logging for CentralController: {e}")

    logging.info("[CentralController Process] Starting...")
    locale_manager = LocaleManagerBackend()

    # --- Monitor Loop Interno (Mantido) ---
    def monitor_loop(metrics: MetricsManager, process: psutil.Process, queues: dict, interval: int = 5):
        while True:
            try:
                cpu = process.cpu_percent(interval=None) # Ajustado para None
                mem = process.memory_percent()
                wd_size = queues['watchdog'].qsize() if 'watchdog' in queues else 0
                ui_size = queues['ui'].qsize() if 'ui' in queues else 0
                metrics.update_metric('process_cpu_usage_percent', cpu if cpu is not None else 0.0)
                metrics.update_metric('process_memory_usage_percent', mem)
                metrics.update_metric('watchdog_command_queue_size', wd_size)
                metrics.update_metric('ui_command_queue_size', ui_size)
            except (psutil.NoSuchProcess, ConnectionRefusedError, FileNotFoundError, BrokenPipeError):
                logging.warning("[Monitor CC] Processo encerrado, conexão recusada, erro de arquivo ou pipe quebrado. Parando monitor.")
                break
            except Exception as e:
                logging.error(f"[Monitor CC] Erro inesperado no loop: {e}", exc_info=True)
            time.sleep(interval)
    # --- Fim Monitor Loop ---

    metrics_manager = MetricsManager(process_name="CentralController", port=8001)
    # ... (registro de métricas inalterado) ...
    metrics_manager.register_metric('process_cpu_usage_percent', 'Uso de CPU do processo (%)')
    metrics_manager.register_metric('process_memory_usage_percent', 'Uso de Memória do processo (%)')
    metrics_manager.register_metric('watchdog_command_queue_size', 'Tamanho da fila de comandos do Watchdog')
    metrics_manager.register_metric('ui_command_queue_size', 'Tamanho da fila de comandos da UI')

    try: # Adicionado try/except para psutil.Process()
         current_process = psutil.Process()
         monitor_thread = threading.Thread(
             target=monitor_loop,
             args=(metrics_manager, current_process, {'watchdog': wd_q, 'ui': ui_q}),
             daemon=True
         )
         monitor_thread.start()
    except Exception as e_monitor:
         logging.error(f"[CentralController Process] Falha ao iniciar thread de monitoramento: {e_monitor}")

    controller = CentralController(settings, pipe_conn, wd_q, sds_q, sas_q, ui_q, locale_manager)
    controller.run()
    logging.info("[CentralController Process] Exiting.")
# >>>>> Fim da definição da função run_controller_process <<<<<

# --- INÍCIO DA FUNÇÃO DE UI RESTAURADA ---
def run_ui_process(log_dir: str):
    """Inicia o processo da UI (Flet) como um subprocesso separado."""
    logging.info("[Launcher] Iniciando processo da UI...")
    try:
        # Constrói o caminho para o script da UI
        ui_script_path = os.path.join(project_root, "ui", "main_ui.py")
        
        # Prepara o log
        ui_log_path = os.path.join(log_dir, "ui_process.log")
        
        # Usa 'sys.executable' para garantir que está usando o mesmo interpretador python
        # (especialmente importante em ambientes virtuais como o 'venv')
        command = [sys.executable, ui_script_path]
        
        logging.info(f"Comando de execução da UI: {' '.join(command)}")
        logging.info(f"Log da UI (stdout/stderr) será redirecionado para: {ui_log_path}")

        # Abre o arquivo de log para capturar stdout e stderr do subprocesso
        with open(ui_log_path, 'wb') as log_file:
            process = subprocess.Popen(
                command,
                stdout=log_file,
                stderr=log_file,
                cwd=project_root, # Define o CWD para a raiz (importante para 'ui/assets' funcionar)
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            )
        
        logging.info(f"Processo da UI iniciado com PID: {process.pid}")
        return process
    
    except Exception as e:
        logging.critical(f"Falha CRÍTICA ao iniciar o processo da UI: {e}", exc_info=True)
        return None
# --- FIM DA FUNÇÃO DE UI RESTAURADA ---


def main():
    """Função principal COMPLETA para iniciar o BACKEND e a UI."""
    print("[LAUNCHER DEBUG] Entering main function...")
    # ... (configuração de log inicial inalterada) ...
    log_base_dir = get_base_output_dir()
    launcher_log_dir = os.path.join(log_base_dir, "logs", "launcher")
    log_configured = False
    try:
        os.makedirs(launcher_log_dir, exist_ok=True)
        log_file_path = os.path.join(launcher_log_dir, "launcher_full_system.log") # Nome corrigido
        logging.basicConfig(level=logging.INFO,
                            format='%(asctime)s [LAUNCHER] [%(levelname)s] - %(message)s', # Prefixo corrigido
                            handlers=[
                                logging.FileHandler(log_file_path, encoding='utf-8', mode='w'),
                                logging.StreamHandler(sys.stdout)
                            ])
        root_logger = logging.getLogger()
        for handler in root_logger.handlers:
            if isinstance(handler, logging.FileHandler):
                handler.setLevel(logging.DEBUG)
        log_configured = True
        print(f"[LAUNCHER DEBUG] Logging configured. Log file: {log_file_path}")

    except Exception as e:
        print(f"CRITICAL ERROR setting up logging for Launcher: {e}")

    logging.info("--- CARINA LAUNCHER STARTED (Full System) ---")
    # ... (logs de debug iniciais inalterados) ...
    logging.debug(f"Base output directory: {log_base_dir}")
    logging.debug(f"Project root (effective): {project_root}")
    logging.debug(f"Is Frozen: {IS_FROZEN}")
    logging.debug(f"Initial sys.path in main(): {sys.path}")
    if not log_configured:
        logging.warning("Logging to file might be disabled due to earlier setup error.")


    lm = LocaleManagerBackend() # <<< NECESSÁRIO para Watchdog

    # --- Criação das Queues e Pipe (TODAS necessárias) ---
    controller_conn, ai_conn = Pipe() # <<< NECESSÁRIO
    watchdog_command_queue = Queue() # <<< NECESSÁRIO
    sds_data_queue = Queue()         # <<< NECESSÁRIO
    sas_data_queue = Queue()         # <<< NECESSÁRIO
    ui_command_queue = Queue()         # <<< NECESSÁRIO
    db_data_queue = Queue()          # <<< NECESSÁRIO
    guardian_state_queue = Queue()   # <<< NECESSÁRIO
    guardian_signal_queue = Queue()  # <<< NECESSÁRIO
    # --- Fim ---

    settings = configparser.ConfigParser()
    settings_file_path = resource_path(os.path.join("config", "settings.ini"))
    logging.debug(f"Attempting to read settings from: {settings_file_path}")
    read_files = settings.read(settings_file_path, encoding='utf-8')
    if not read_files:
        logging.critical(f"FALHA CRÍTICA: Não foi possível ler o arquivo de configurações em '{settings_file_path}'. Encerrando.")
        sys.exit(1)
    logging.info("Settings file read successfully.")

    processes = []
    ui_process = None # UI é tratada separadamente (não é um multiprocessing.Process)
    try:
        logging.info("Preparing all processes...")

        # --- Iniciar UI (RESTAURADO) ---
        logging.info("Iniciando processo da UI...")
        ui_log_dir = os.path.join(launcher_log_dir, "ui_logs")
        os.makedirs(ui_log_dir, exist_ok=True)
        ui_process = run_ui_process(ui_log_dir) # Chama a nova função
        if ui_process:
            logging.info(f" -> UI Process (PID: {ui_process.pid}) [Log: {ui_log_dir}/ui_process.log]")
        else:
            logging.error("Falha ao iniciar a UI. O backend continuará sem ela.")
        # --- Fim Iniciar UI ---


        # --- Criação dos processos filhos (TODOS DO BACKEND) ---
        central_process = Process(target=run_controller_process, args=(settings, controller_conn, watchdog_command_queue, sds_data_queue, sas_data_queue, ui_command_queue), name="CentralController") # <<< Mantido
        processes.append(central_process)
        ai_process = Process(target=run_ai_process, args=(ai_conn, guardian_state_queue, guardian_signal_queue, db_data_queue), name="AI_Process") # <<< Mantido
        processes.append(ai_process)
        watchdog_process = Process(target=run_watchdog, args=(watchdog_command_queue, lm), name="Watchdog") # <<< Mantido
        processes.append(watchdog_process)
        sds_process = Process(target=run_sds_worker, args=(sds_data_queue, settings, ui_command_queue), name="DashboardService") # <<< ADICIONADO
        processes.append(sds_process)
        sas_process = Process(target=run_analysis_worker, args=(sas_data_queue, settings, db_data_queue), name="AnalysisService") # <<< ADICIONADO
        processes.append(sas_process)
        db_worker_process = Process(target=run_database_worker, args=(db_data_queue,), name="DatabaseWorker") # <<< ADICIONADO
        processes.append(db_worker_process)
        # --- Fim Criação Processos ---

        logging.info("Starting ALL backend processes...")
        # --- Loop para iniciar processos (TODOS DO BACKEND) ---
        # Mantém a ordem original de inicialização
        for i, p in enumerate(processes):
            logging.info(f"Starting process: {p.name} (Process {i+1}/{len(processes)})")
            p.start() # <<< Inicia os processos
            if i < len(processes) - 1:
                delay_seconds = 2.5 # Mantém delay
                logging.info(f"Waiting {delay_seconds} seconds before starting next process ({processes[i+1].name})...")
                time.sleep(delay_seconds)
        logging.info("All backend processes initiated.")
        # --- Fim Loop Iniciar ---

        # --- Logs de inicialização (TODOS DO BACKEND) ---
        logging.info(f" -> Central Controller (PID: {central_process.pid}) [Metrics: http://localhost:8001]")
        logging.info(f" -> AI Process (PID: {ai_process.pid}) [Metrics: http://localhost:8002]")
        logging.info(f" -> Watchdog (PID: {watchdog_process.pid})")
        logging.info(f" -> Dashboard Service (PID: {sds_process.pid}) [Metrics: http://localhost:8003]")
        logging.info(f" -> Analysis Service (PID: {sas_process.pid}) [Metrics: http://localhost:8004]")
        logging.info(f" -> Database Worker (PID: {db_worker_process.pid}) [Metrics: http://localhost:8005]")
        # --- Fim Logs ---

        print("-" * 50)
        logging.info("CARINA system running with FULL BACKEND + UI.")

        # Aguarda o processo central terminar (ou ser interrompido)
        logging.info("Waiting for Central Controller process to join...")
        central_process.join() # <<< AGUARDA O CENTRAL CONTROLLER <<<
        logging.info("Central Controller process joined.")


    except KeyboardInterrupt:
        logging.info("\nInterrupt signal (Ctrl+C) received. Shutting down...")
    except Exception as e:
         logging.critical(f"Unexpected error in main(): {e}", exc_info=True)
    finally:
        logging.info("--- INITIATING SHUTDOWN SEQUENCE ---")
        # --- Lógica de finalização (Inalterada da versão completa) ---
        # Termina a UI primeiro
        if ui_process and ui_process.poll() is None:
             # ... (código completo inalterado) ...
            logging.info(f"   -> Terminating UI process (PID: {ui_process.pid})...")
            try:
                # Tenta terminar de forma graciosa
                if sys.platform == "win32":
                    ui_process.terminate()
                else:
                    ui_process.terminate() # SIGTERM
                
                ui_process.wait(timeout=5)
                logging.info("   -> UI process terminated gracefully.")
            except (subprocess.TimeoutExpired, psutil.NoSuchProcess):
                logging.warning(f"   -> UI process (PID: {ui_process.pid}) did not terminate gracefully. Force killing...")
                try:
                    ui_process.kill()
                    ui_process.wait(timeout=3)
                except Exception as kill_e:
                    logging.error(f"   -> Error force killing UI process: {kill_e}")
            except Exception as e_ui_term:
                 logging.error(f"Error during UI termination: {e_ui_term}")

        # Envia sinal de shutdown para DB worker (necessário)
        try:
            logging.debug("Sending shutdown signal to DB worker...")
            db_data_queue.put(None) # <<< Necessário
        except Exception as e:
            logging.warning(f"Error sending shutdown signal to DB worker queue: {e}")

        logging.info("Performing final cleanup of backend processes...")
        # Termina todos os processos do backend na ordem inversa
        for p in reversed(processes):
            if p and p.is_alive():
                logging.info(f"   -> Terminating process {p.name} (PID: {p.pid})...")
                try:
                    p.terminate()
                    p.join(timeout=5)
                    if p.is_alive():
                        logging.warning(f"Process {p.name} did not terminate gracefully, force killing.")
                        p.kill()
                        p.join(timeout=2)
                except Exception as proc_term_e:
                     logging.error(f"Error during termination of process {p.name}: {proc_term_e}")
        # --- Fim da Finalização ---

        logging.info("System shutdown.")
        logging.info("--- CARINA LAUNCHER FINISHED ---")

if __name__ == "__main__":
    multiprocessing.freeze_support() # Primeira linha

    try: # Configura 'spawn'
        current_method = multiprocessing.get_start_method(allow_none=True)
        if current_method != 'spawn':
            set_start_method('spawn', force=True)
            print(f"[Launcher] Forcing multiprocessing start method to 'spawn'. Previous: '{current_method}'.")
        else:
            print("[Launcher] Multiprocessing start method already set to 'spawn'.")
    except Exception as e:
         print(f"[Launcher Warning] Could not force 'spawn': {e}. Using default: '{multiprocessing.get_start_method(allow_none=True)}'")
         pass

    print("[LAUNCHER DEBUG] Calling main function...")
    main()
    print("[LAUNCHER DEBUG] main function returned.")