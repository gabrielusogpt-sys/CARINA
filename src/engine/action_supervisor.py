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

# File: src/engine/action_supervisor.py (Refatorado com importação robusta de TraCIException)
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
    from engine.state_extractor import StateExtractor # Mantém a importação para type hinting

# --- INÍCIO DA MUDANÇA: Bloco de importação robusto para TraCI ---
try:
    # Tenta importar traci normally first
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
            print(f"[ActionSupervisor WARNING] Falha ao importar TraCI/TraCIException mesmo com SUMO_HOME: {e_sumohome}. Definindo fallback.") # Usar print
            # Define um fallback para TraCIException
            class TraCIException(Exception): pass
    else:
        # SUMO_HOME não definido E importação inicial falhou (ou estamos no proxy)
        # logging.warning(f"SUMO_HOME não definido e importação de TraCI/TraCIException falhou: {e_traci}. Definindo fallback.")
        print(f"[ActionSupervisor WARNING] SUMO_HOME não definido e importação de TraCI/TraCIException falhou: {e_traci}. Definindo fallback.") # Usar print
        # Define um fallback para TraCIException
        class TraCIException(Exception): pass

# Agora, o código pode usar 'TraCIException' sabendo que ela sempre existirá (real ou fallback).
# --- FIM DA MUDANÇA ---

# A importação do locale_manager aqui é apenas para o bloco de emergência (mantido da versão anterior)
from utils.locale_manager_backend import LocaleManagerBackend
lm_emergency = LocaleManagerBackend() # Instância de emergência


class ActionSupervisor:
    """O "Atuador" do ambiente: especialista em aplicar ações de forma segura."""

    def __init__(self, traci_conn, settings: configparser.ConfigParser,
                 state_extractor: 'StateExtractor', locale_manager: 'LocaleManagerBackend'):
        # Verifica se traci_conn foi passado (pode ser None se a importação falhou antes)
        if traci_conn is None and 'traci' in sys.modules:
             self.conn = sys.modules['traci'] # Tenta pegar o proxy se traci_conn for None
             logging.warning("[ActionSupervisor] traci_conn era None, usando traci (proxy?) diretamente.")
        else:
             self.conn = traci_conn # Usa a conexão passada (que pode ser o proxy)

        self.state_extractor = state_extractor # Precisa do state_extractor para obter fases verdes
        self.locale_manager = locale_manager
        lm = self.locale_manager

        self._last_phase_change_time = {}
        self.vetoed_actions = {}

        if settings.has_section('TRAFFIC_RULES'):
            rules = settings['TRAFFIC_RULES']
            self.min_green_time = rules.getfloat('min_green_time_seconds', fallback=10.0)
        else:
            self.min_green_time = 10.0

        logging.info(lm.get_string("action_supervisor.init.actuator_created"))
        logging.info(lm.get_string("action_supervisor.init.min_green_time_rule", time=self.min_green_time))

    def update_vetos(self, vetos: dict):
        """
        Atualiza a lista de ações vetadas com os novos sinais do Guardião.
        """
        lm = self.locale_manager
        if vetos:
            for tl_id, veto_signal in vetos.items():
                self.vetoed_actions[tl_id] = veto_signal.get('veto_action')
                logging.warning(lm.get_string("action_supervisor.veto.received", tl_id=tl_id, action=self.vetoed_actions[tl_id]))

    def apply_actions(self, actions: dict):
        """
        Aplica um dicionário de ações à simulação (via proxy), após validar contra as
        regras de segurança de tempo mínimo e os vetos do Guardião.
        """
        lm = self.locale_manager
        # Verifica se a conexão (proxy) existe
        if not self.conn or not hasattr(self.conn, 'simulation') or not hasattr(self.conn, 'trafficlight'):
            logging.error("[ActionSupervisor] Conexão TraCI (ou proxy) inválida. Ações não aplicadas.")
            return

        try:
            # Obtém o tempo da simulação via proxy
            current_time = self.conn.simulation.getTime()
        except TraCIException as e: # Usa a TraCIException (real ou fallback)
            logging.error(f"[ActionSupervisor] Erro TraCI ao obter tempo da simulação: {e}. Ações não aplicadas.")
            return
        except Exception as e_general:
             logging.error(f"[ActionSupervisor] Erro inesperado ao obter tempo da simulação: {e_general}. Ações não aplicadas.")
             return

        for tl_id, action in actions.items():
            # Verifica veto
            if tl_id in self.vetoed_actions and self.vetoed_actions[tl_id] == action:
                logging.info(lm.get_string("action_supervisor.apply.action_blocked", action=action, tl_id=tl_id))
                del self.vetoed_actions[tl_id] # Limpa o veto após bloquear a ação uma vez
                continue

            # Ação 0: Mudar para a próxima fase verde
            if action == 0:
                time_since_last_change = current_time - self._last_phase_change_time.get(tl_id, 0)

                # Verifica tempo mínimo de verde
                if time_since_last_change >= self.min_green_time:
                    try:
                        # Obtém fases verdes (agora usa o método do state_extractor que já tem o try/except TraCI)
                        green_phases = self.state_extractor._get_green_phases_for_tl(tl_id)
                        if not green_phases: # Se não encontrou fases verdes, não pode mudar
                            logging.warning(f"[ActionSupervisor] Não foi possível encontrar fases verdes para {tl_id}. Ação de mudança ignorada.")
                            continue

                        # Obtém fase atual via proxy
                        current_phase_idx = self.conn.trafficlight.getPhase(tl_id)

                        # Verifica se a fase atual é uma das fases verdes válidas
                        if current_phase_idx not in green_phases:
                            # Se a fase atual não é verde (amarela/vermelha), não faz sentido "avançar" a fase verde.
                            # Poderia tentar ir para a primeira fase verde, mas é mais seguro ignorar.
                            logging.debug(f"[ActionSupervisor] Semáforo {tl_id} não está em fase verde ({current_phase_idx}). Ação de mudança ignorada.")
                            continue

                        # Calcula o próximo índice na lista de fases verdes
                        current_list_idx = green_phases.index(current_phase_idx)
                        next_list_idx = (current_list_idx + 1) % len(green_phases)
                        next_phase_idx = green_phases[next_list_idx]

                        # Envia comando para mudar fase via proxy
                        self.conn.trafficlight.setPhase(tl_id, next_phase_idx)
                        self._last_phase_change_time[tl_id] = current_time # Atualiza tempo da última mudança
                        # Log de sucesso pode ser adicionado se necessário
                        # logging.debug(f"[ActionSupervisor] Semáforo {tl_id} mudou para fase verde {next_phase_idx}.")

                    except TraCIException as e_traci: # Captura erro específico do TraCI (via proxy)
                        logging.warning(f"[ActionSupervisor] Erro TraCI ao tentar mudar a fase de {tl_id}: {e_traci}")
                        continue # Pula para o próximo semáforo
                    except ValueError: # Caso current_phase_idx não esteja em green_phases (já tratado acima, mas seguro ter)
                        logging.warning(f"[ActionSupervisor] Fase atual {current_phase_idx} de {tl_id} não encontrada na lista de fases verdes {green_phases}.")
                        continue
                    except Exception as e_general: # Captura outros erros inesperados
                         logging.error(f"[ActionSupervisor] Erro inesperado ao mudar fase de {tl_id}: {e_general}", exc_info=True)
                         continue
                else:
                    # Loga que a regra de tempo mínimo impediu a mudança
                    logging.debug(lm.get_string("action_supervisor.apply.min_time_not_met", tl_id=tl_id))

            # Ações 1 e 2 (Manter fase) não requerem envio de comando para o TraCI/proxy.
            # A lógica é simplesmente *não* enviar o comando setPhase.

    def reset(self):
        """Reseta os contadores de tempo e vetos para um novo episódio."""
        self._last_phase_change_time.clear()
        self.vetoed_actions.clear()
        logging.info(self.locale_manager.get_string("action_supervisor.reset.success"))