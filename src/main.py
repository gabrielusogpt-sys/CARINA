# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
# Copyright (C) 2025 Gabriel Moraes - Noxfort Labs
#
# (...) [Licença omitida para brevidade] (...)

# File: src/main.py (Corrigido: Definição de monitor_loop e gpu_info)
# Author: Gabriel Moraes
# Date: 27 de Outubro de 2025

import sys
import os
import configparser
from datetime import datetime
import logging
import traceback
from multiprocessing import Queue
from multiprocessing.connection import Connection
import threading
import time
# psutil é importado DENTRO
# torch é importado DENTRO

# Adiciona o diretório 'src' ao path (mantido)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# --- Importações Leves Essenciais (Mantidas no Topo) ---
from utils.paths import resource_path, get_base_output_dir
from utils.logging_setup import setup_logging
from utils.locale_manager_backend import LocaleManagerBackend
from utils.metrics_manager import MetricsManager
# --- Fim ---

def run_ai_process(pipe_conn: Connection, guardian_state_queue: Queue,
                   guardian_signal_queue: Queue, db_data_queue: Queue):
    """
    O ponto de entrada principal para o processo da IA.
    Importações pesadas são feitas aqui dentro.
    """
    # --- Configuração Inicial (Logging, Locale) ---
    log_base_dir = get_base_output_dir()
    log_dir_ai = os.path.join(log_base_dir, "logs", "main_ai", datetime.now().strftime("%Y%m%d-%H%M%S"))
    try:
        os.makedirs(log_dir_ai, exist_ok=True)
        setup_logging(log_dir=log_dir_ai)
        log_configured = True
    except Exception as e:
        print(f"[AI Process ERROR] Failed to setup logging: {e}")
        log_configured = False

    def print_and_log(message, level="info"): # Função auxiliar mantida
        print(f"[AI Process] {message}")
        if log_configured:
            if level == "info": logging.info(message)
            elif level == "warning": logging.warning(message)
            elif level == "error": logging.error(message)
            elif level == "debug": logging.debug(message)

    print_and_log("--- AI Process Started ---")

    # --- INÍCIO DA MUDANÇA: Inicializar gpu_info ---
    gpu_info = "N/A" # Define um valor padrão inicial
    # --- FIM DA MUDANÇA ---

    try:
        lm = LocaleManagerBackend()
        print_and_log(f"LocaleManager initialized. Language: {lm.current_lang_data.get('lang_code', 'N/A')}")
    except Exception as e:
        print_and_log(f"Failed to initialize LocaleManagerBackend: {e}", level="error")
        class DummyLM:
             def get_string(self, key, fallback=None, **kwargs): return fallback if fallback else key
        lm = DummyLM()

    # --- INÍCIO DAS IMPORTAÇÕES ATRASADAS E MONKEY PATCH ---
    print_and_log("Attempting delayed imports and monkey patch...")
    try:
        from core import traci_proxy
        print_and_log("Imported traci_proxy.")
        sys.modules['traci'] = traci_proxy
        print_and_log("Applied monkey patch: sys.modules['traci'] = traci_proxy.")
        traci_proxy.init_proxy_pipe(pipe_conn)
        print_and_log("TraCI Proxy communication pipe initialized.")

        import psutil # <<< psutil importado aqui <<<
        import torch
        from engine.trainer import Trainer
        print_and_log("Delayed imports successful (psutil, torch, Trainer).")

    except ImportError as e_import:
        print_and_log(f"CRITICAL DELAYED IMPORT/PATCH ERROR: {e_import}", level="error")
        # ... (log de emergência omitido) ...
        return
    except Exception as e_patch:
         print_and_log(f"CRITICAL ERROR during patch/import phase: {e_patch}", level="error")
         # ... (log de emergência omitido) ...
         return
    # --- FIM ---

    # --- INÍCIO DA MUDANÇA: Definição do monitor_loop e criação da thread movidos para DEPOIS das importações ---
    # --- Monitor Thread (Usa psutil) ---
    metrics_manager = MetricsManager(process_name="AI_Process", port=8002)
    metrics_manager.register_metric('process_cpu_usage_percent', 'Uso de CPU do processo (%)')
    metrics_manager.register_metric('process_memory_usage_percent', 'Uso de Memória do processo (%)')
    # ... (outros registros de métricas) ...

    current_process = psutil.Process() # psutil já está importado

    def monitor_loop(metrics: MetricsManager, process: psutil.Process, queues: dict, interval: int = 5):
        """Coleta e atualiza métricas em um loop."""
        # A função em si precisa estar aqui para usar psutil, mas pode ser chamada pela thread
        while True:
            try:
                cpu = process.cpu_percent(interval=None)
                mem_percent = process.memory_percent()
                metrics.update_metric('process_cpu_usage_percent', cpu if cpu is not None else 0.0)
                metrics.update_metric('process_memory_usage_percent', mem_percent)
                if 'guardian_state' in queues:
                     metrics.update_metric('guardian_state_queue_size', queues['guardian_state'].qsize())
                if 'guardian_signal' in queues:
                     metrics.update_metric('guardian_signal_queue_size', queues['guardian_signal'].qsize())
                if 'db' in queues:
                     metrics.update_metric('db_data_queue_size', queues['db'].qsize())
            except (psutil.NoSuchProcess, ConnectionRefusedError, FileNotFoundError, BrokenPipeError):
                print_and_log("[Monitor AI] Processo encerrado, conexão recusada, erro de arquivo ou pipe quebrado. Parando monitor.", level="warning")
                break
            except Exception as e:
                print_and_log(f"[Monitor AI] Erro inesperado no loop: {e}", level="error")
            time.sleep(interval)

    monitor_thread = threading.Thread(
        target=monitor_loop, # Agora monitor_loop está definido
        args=(metrics_manager, current_process, {
            'guardian_state': guardian_state_queue,
            'guardian_signal': guardian_signal_queue,
            'db': db_data_queue
        }),
        daemon=True
    )
    monitor_thread.start()
    print_and_log("Monitor thread started.")
    # --- FIM DA MUDANÇA ---

    # --- Lógica Principal ---
    try:
        # Diagnóstico de Hardware
        separator = "=" * 50
        print_and_log(separator)
        print_and_log(lm.get_string("main_ai.hardware_check.starting", fallback="STARTING HARDWARE DIAGNOSTICS (PYTORCH)..."))

        # gpu_info já foi inicializado antes do try
        gpu_available = False
        try:
             if torch.cuda.is_available():
                  gpu_name = torch.cuda.get_device_name(0)
                  gpu_info = f"{gpu_name}" # Atualiza gpu_info
                  print_and_log(lm.get_string("main_ai.hardware_check.gpu_success", name=gpu_name, fallback=f"✅ SUCCESS: GPU found: {gpu_name}"))
                  gpu_available = True
             else:
                  # Mantém o gpu_info padrão "N/A" ou o de fallback do locale
                  gpu_info = lm.get_string("main_ai.hardware_check.gpu_not_found", fallback="Not detected or no CUDA support")
                  print_and_log(lm.get_string("main_ai.hardware_check.gpu_not_found_warning", fallback="❌ WARNING: No CUDA compatible GPU found."), level="warning")
        except Exception as e_cuda:
             print_and_log(f"Error during CUDA check: {e_cuda}", level="error")
             gpu_info = f"Error during check: {e_cuda}" # Atualiza com erro

        print_and_log(separator)

        # Carrega Configurações (Função load_settings mantida)
        def load_settings():
             config_path = resource_path(os.path.join("config", "settings.ini"))
             config = configparser.ConfigParser()
             read_files = config.read(config_path, encoding='utf-8')
             if not read_files:
                  error_msg = lm.get_string("main_ai.load_settings.critical_error", path=config_path, fallback=f"...")
                  print_and_log(error_msg, level="error")
                  raise FileNotFoundError(error_msg)
             else:
                  print_and_log(f"Settings loaded from {config_path}")
             return config
        settings = load_settings()

        # Cria e inicia o Trainer
        print_and_log(lm.get_string("main_ai.run.process_started", fallback="[MAIN_AI] AI Process connected via Proxy."))
        trainer = Trainer(
            settings=settings,
            log_dir=log_dir_ai,
            gpu_info=gpu_info, # Passa gpu_info (que sempre estará definido)
            pipe_conn=pipe_conn,
            guardian_state_queue=guardian_state_queue,
            guardian_signal_queue=guardian_signal_queue,
            db_data_queue=db_data_queue
        )
        print_and_log("Trainer instance created. Starting continuous service...")
        trainer.start_continuous_service()

        print_and_log("Trainer's continuous service finished.", level="info")

    except Exception as e_main:
         print_and_log(f"FATAL ERROR in AI Process main logic: {e_main}", level="error")
         # ... (log de emergência omitido) ...
         sys.exit(1)

    finally:
        print_and_log("--- AI Process Finishing ---")


if __name__ == "__main__":
    print("ERROR: This script is a child process and must be started by the 'carina.py' launcher.")
    sys.exit(1)