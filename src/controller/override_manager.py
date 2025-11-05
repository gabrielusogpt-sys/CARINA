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

# File: src/controller/override_manager.py (Refatorado com importação robusta de TraCIException)
# Author: Gabriel Moraes
# Date: 26 de Outubro de 2025

import logging
import os
import sys # Import sys for path manipulation
import json
from typing import Dict, Tuple, TYPE_CHECKING

# Adiciona o diretório 'src' ao path (mantido)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

if TYPE_CHECKING:
    # Assume que LocaleManagerBackend está em src/utils
    from utils.locale_manager_backend import LocaleManagerBackend

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
            # Usar logging aqui pode ser problemático
            # logging.info(f"TraCI importado com sucesso via SUMO_HOME: {tools}")
        except (ImportError, ModuleNotFoundError) as e_sumohome:
            # Mesmo com SUMO_HOME, a importação falhou (ou estamos no proxy)
            # logging.warning(f"Falha ao importar TraCI/TraCIException mesmo com SUMO_HOME: {e_sumohome}. Definindo fallback.")
            print(f"[OverrideManager WARNING] Falha ao importar TraCI/TraCIException mesmo com SUMO_HOME: {e_sumohome}. Definindo fallback.") # Usar print
            # Define um fallback para TraCIException
            class TraCIException(Exception): pass
    else:
        # SUMO_HOME não definido E importação inicial falhou (ou estamos no proxy)
        # logging.warning(f"SUMO_HOME não definido e importação de TraCI/TraCIException falhou: {e_traci}. Definindo fallback.")
        print(f"[OverrideManager WARNING] SUMO_HOME não definido e importação de TraCI/TraCIException falhou: {e_traci}. Definindo fallback.") # Usar print
        # Define um fallback para TraCIException
        class TraCIException(Exception): pass

# Agora, o código pode usar 'TraCIException' sabendo que ela sempre existirá (real ou fallback).
# --- FIM DA MUDANÇA ---

class OverrideManager:
    """
    Um especialista que gerencia o estado e a execução de overrides manuais
    nos semáforos, persistindo o seu estado em disco.
    """
    def __init__(self, locale_manager: 'LocaleManagerBackend'): # Corrigido type hint
        self.locale_manager = locale_manager
        self.active_overrides: Dict[str, str] = {}
        self.state_file_path: str | None = None
        logging.info("Gerenciador de Overrides Manuais criado.")

    def init_persistence(self, scenario_name: str):
        """
        Define o caminho do arquivo de estado e carrega o estado anterior.
        """
        if not scenario_name:
            logging.error("[OverrideManager] Nome do cenário não fornecido. A persistência de override está desativada.")
            return

        # Recalcula project_root aqui também para garantir
        project_root_local = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        scenario_dir = os.path.join(project_root_local, "results", scenario_name)
        os.makedirs(scenario_dir, exist_ok=True)
        self.state_file_path = os.path.join(scenario_dir, "override_state.json")
        self._load_state_from_disk()

    def _load_state_from_disk(self):
        """Lê o arquivo JSON de estado, se ele existir."""
        if self.state_file_path and os.path.exists(self.state_file_path):
            try:
                with open(self.state_file_path, "r", encoding="utf-8") as f:
                    self.active_overrides = json.load(f)
                logging.info(f"Estado de override carregado de {self.state_file_path}. {len(self.active_overrides)} semáforos em modo manual.")
            except (IOError, json.JSONDecodeError) as e:
                logging.error(f"Erro ao carregar o estado de override: {e}")

    def _save_state_to_disk(self):
        """Salva o dicionário de overrides ativos no arquivo JSON."""
        if not self.state_file_path:
            logging.warning("[OverrideManager] Tentativa de salvar o estado de override antes da inicialização completa. Ignorando.")
            return
        try:
            with open(self.state_file_path, "w", encoding="utf-8") as f:
                json.dump(self.active_overrides, f, indent=4)
        except IOError as e:
            logging.error(f"Erro ao salvar o estado de override: {e}")

    def restore_sumo_state(self, sumo_conn):
        """
        Aplica os estados de override carregados na simulação do SUMO.
        """
        if not self.active_overrides or not sumo_conn: # Adiciona verificação de sumo_conn
            return

        logging.info("Restaurando estados de override manuais na simulação do SUMO...")
        for semaphore_id, state in self.active_overrides.items():
            payload = {"semaphore_id": semaphore_id, "state": state}
            # Chama handle_ui_command que já tem o try/except TraCIException
            self.handle_ui_command(payload, sumo_conn, is_restoring=True)

    def handle_ui_command(self, payload: Dict, sumo_conn, is_restoring: bool = False):
        """
        Processa um comando de override vindo da UI e o aplica no SUMO.
        """
        semaphore_id = payload.get("semaphore_id")
        state = payload.get("state")

        if not semaphore_id or not state or not sumo_conn: # Adiciona verificação de sumo_conn
            logging.warning(f"[OverrideManager] Comando UI inválido ou conexão SUMO ausente. Payload: {payload}")
            return

        try:
            # Verifica se o semáforo existe na simulação antes de tentar controlá-lo
            # (Pode ser útil se o estado for carregado de um cenário diferente)
            all_tls_ids = sumo_conn.trafficlight.getIDList()
            if semaphore_id not in all_tls_ids:
                 logging.warning(f"[OverrideManager] Tentativa de override no semáforo '{semaphore_id}' que não existe na simulação atual. Ignorando.")
                 # Remove do estado ativo se não existe mais
                 if semaphore_id in self.active_overrides:
                     del self.active_overrides[semaphore_id]
                     if not is_restoring: self._save_state_to_disk()
                 return

            if state == "ALERT":
                self.active_overrides[semaphore_id] = state
                num_lights = len(sumo_conn.trafficlight.getRedYellowGreenState(semaphore_id))
                state_str = "y" * num_lights
                sumo_conn.trafficlight.setRedYellowGreenState(semaphore_id, state_str)
                if not is_restoring: logging.info(f"SUMO: Semáforo '{semaphore_id}' comandado para estado de Alerta ('{state_str}').")

            elif state == "OFF":
                self.active_overrides[semaphore_id] = state
                num_lights = len(sumo_conn.trafficlight.getRedYellowGreenState(semaphore_id))
                # Define como 'o' (off/laranja piscante) se disponível, senão 'r'
                # Nota: SUMO pode não suportar 'o' visualmente em todas as configurações
                state_str = "o" * num_lights if hasattr(traci.constants, 'TLSTATE_OFF_BLINKING') else "r" * num_lights
                sumo_conn.trafficlight.setRedYellowGreenState(semaphore_id, state_str)
                if not is_restoring: logging.info(f"SUMO: Semáforo '{semaphore_id}' comandado para estado Desativado ('{state_str}').")

            elif state == "NORMAL":
                if semaphore_id in self.active_overrides:
                    del self.active_overrides[semaphore_id]
                    # Ao retornar ao normal, o Central Controller (ou Watchdog) reassumirá
                    # o controle da fase no próximo passo, não precisamos definir uma fase aqui.
                if not is_restoring: logging.info(f"SUMO: Semáforo '{semaphore_id}' devolvido ao controle automático.")

            if not is_restoring:
                self._save_state_to_disk()

        except TraCIException as e: # Usa a TraCIException (real ou fallback)
            logging.error(f"Erro TraCI ao aplicar override no SUMO para o semáforo '{semaphore_id}': {e}")
        except Exception as e_general: # Captura outros erros
             logging.error(f"Erro inesperado ao aplicar override para '{semaphore_id}': {e_general}", exc_info=True)


    def is_ai_command_blocked(self, request: Tuple) -> bool:
        """Verifica se um comando vindo da IA deve ser bloqueado devido a um override."""
        # A lógica interna permanece a mesma
        try:
            module_name, func_name, args, _ = request
            # Bloqueia apenas comandos 'setPhase' vindos da IA para semáforos com override ativo
            if module_name == 'trafficlight' and func_name == 'setPhase' and args:
                tl_id = args[0]
                if tl_id in self.active_overrides:
                    # O log de ação ignorada é tratado no request_processor
                    return True
        except (IndexError, TypeError, ValueError) as e:
             # Erro ao desempacotar a requisição - loga e considera não bloqueado por segurança
             logging.warning(f"[OverrideManager] Erro ao analisar requisição da IA para bloqueio: {e}. Requisição: {request}")
        return False