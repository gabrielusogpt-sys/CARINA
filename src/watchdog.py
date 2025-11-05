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

# File: src/watchdog.py (MODIFICADO PARA BOAS PRÁTICAS)
# Author: Gabriel Moraes
# Date: 03 de Outubro de 2025

import logging
import time
import sys
from multiprocessing import Queue
from typing import TYPE_CHECKING

# Adiciona o diretório 'src' ao path para permitir importações absolutas
import os
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

if TYPE_CHECKING:
    from utils.locale_manager_backend import LocaleManagerBackend

FAILSAFE_COMMAND = {
    "type": "set_program_all",
    "value": "0"
}

def run_watchdog(command_queue: Queue, locale_manager: 'LocaleManagerBackend'):
    """
    O ponto de entrada para o processo do Watchdog.
    """
    lm = locale_manager
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [WATCHDOG] [%(levelname)s] - %(message)s')
    logging.info(lm.get_string("watchdog.run.process_started"))

    while True:
        try:
            command_queue.put([FAILSAFE_COMMAND])
            time.sleep(1)

        except (KeyboardInterrupt, SystemExit):
            logging.info(lm.get_string("watchdog.run.shutdown_signal"))
            break
        except Exception as e:
            logging.error(lm.get_string("watchdog.run.loop_error", error=e), exc_info=True)
            time.sleep(5)
    
    logging.info(lm.get_string("watchdog.run.process_finished"))

if __name__ == "__main__":
    # --- MUDANÇA PRINCIPAL AQUI ---
    # Esta mensagem não pode usar o locale_manager porque ele não é inicializado aqui.
    # A boa prática nestes casos é usar uma string estática em inglês.
    print("ERROR: This script is a child process and must be started by the 'carina.py' launcher.")
    sys.exit(1)