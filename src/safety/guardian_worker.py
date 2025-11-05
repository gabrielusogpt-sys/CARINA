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

# File: src/safety/guardian_worker.py (CORRIGIDO)
# Author: Gabriel Moraes
# Date: 05 de Outubro de 2025

"""
Define a lógica para o processo do Guardião Assíncrono.

Esta versão contém o loop de operação principal do worker, que consome
estados da simulação de uma fila, executa a inferência do GuardianAgent
e envia sinais de veto de volta para o processo principal.
"""
import logging
import time
import os
import sys
from multiprocessing import Queue
from queue import Empty
import configparser

def run_guardian_worker(
    settings: configparser.ConfigParser,
    state_queue: Queue,
    signal_queue: Queue,
    scenario_checkpoint_dir: str,
    agent_ids: list
):
    """
    O ponto de entrada e loop principal para o processo do Guardião Assíncrono.
    """
    # Adiciona o diretório 'src' ao path para permitir importações relativas
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    src_path = os.path.join(project_root, 'src')
    if src_path not in sys.path:
        sys.path.insert(0, src_path)

    from utils.logging_setup import setup_logging
    from agents.guardian_agent import GuardianAgent
    # --- CORREÇÃO 1: Importar o LocaleManagerBackend ---
    from utils.locale_manager_backend import LocaleManagerBackend

    # Configura um logger específico para este processo
    log_dir = os.path.join(project_root, "logs", "guardian_worker")
    os.makedirs(log_dir, exist_ok=True)
    setup_logging(log_dir)

    logging.info("[GUARDIAN_WORKER] Processo do Guardião Assíncrono iniciado.")

    # --- CORREÇÃO 2: Criar a instância do LocaleManagerBackend ---
    lm = LocaleManagerBackend()

    # --- Inicialização ---
    guardians = {}
    guardian_config = settings['GUARDIAN_AGENT']
    for tl_id in agent_ids:
        # No futuro, podemos adicionar carregamento de checkpoint aqui se necessário
        # --- CORREÇÃO 3: Passar o locale_manager para o construtor ---
        guardians[tl_id] = GuardianAgent(aiconfig=guardian_config, locale_manager=lm)
    
    logging.info(f"[GUARDIAN_WORKER] {len(guardians)} guardiões criados e prontos.")
    
    # --- Loop Principal ---
    while True:
        try:
            latest_state_package = None
            
            # 1. Esvazia a fila para pegar apenas o estado mais recente
            try:
                while True:
                    latest_state_package = state_queue.get_nowait()
            except Empty:
                pass # Fila está vazia, normal.

            # 2. Se um estado foi recebido, processa-o
            if latest_state_package:
                # O pacote contém o estado e as recompensas
                global_state, rewards, done, mode = latest_state_package
                
                for tl_id, guardian in guardians.items():
                    local_state = global_state.get(tl_id)
                    if not local_state:
                        continue
                    
                    # --- Lógica de Inferência e Aprendizado (similar ao antigo SafetyManager) ---
                    # (Esta lógica será expandida para usar o 'soft override')
                    
                    # Ação do Guardião (Inferência)
                    # action = guardian.choose_action(local_state)
                    # if action == 1: # Exemplo: Ação 1 significa 'veto'
                    #     signal_queue.put_nowait({'veto_action': 0, 'target_tl': tl_id})

                    # Aprendizado do Guardião (se em modo de treino)
                    if mode == 'training' and rewards:
                        # A lógica de aprendizado do antigo SafetyManager seria adaptada aqui
                        # guardian.memory.push(...)
                        # guardian.learn()
                        pass

            # Pausa para não consumir 100% da CPU se não houver trabalho
            time.sleep(0.05) 

        except (KeyboardInterrupt, SystemExit):
            logging.info("[GUARDIAN_WORKER] Sinal de encerramento recebido.")
            break
        except Exception as e:
            logging.error(f"[GUARDIAN_WORKER] Erro fatal no loop: {e}", exc_info=True)
            time.sleep(1)
    
    logging.info("[GUARDIAN_WORKER] Processo finalizado.")