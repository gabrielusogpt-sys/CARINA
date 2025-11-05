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

# File: src/agents/guardian_agent.py (MODIFICADO PARA TRADUÇÃO COMPLETA)
# Author: Gabriel Moraes
# Date: 03 de Outubro de 2025

import torch
import torch.nn as nn
import torch.optim as optim
import random
import logging
from typing import TYPE_CHECKING

# --- MUDANÇA 1: Adicionar importações ---
if TYPE_CHECKING:
    from utils.locale_manager_backend import LocaleManagerBackend

from models.dueling_dqn import DuelingDQN
from memory.replay_memory import ReplayMemory, Transition


class GuardianAgent:
    """
    O agente de segurança que aprende uma política para mitigar riscos
    usando o algoritmo Dueling DQN.
    """
    # --- MUDANÇA 2: Modificar o construtor ---
    def __init__(self, aiconfig, locale_manager: 'LocaleManagerBackend'):
        self.locale_manager = locale_manager
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self._load_hyperparameters(aiconfig)
        
        self.policy_net = DuelingDQN().to(self.device)
        self.target_net = DuelingDQN().to(self.device)
        self.target_net.load_state_dict(self.policy_net.state_dict())
        self.target_net.eval()
        
        self.optimizer = optim.AdamW(self.policy_net.parameters(), lr=self.learning_rate)
        self.memory = ReplayMemory(self.memory_size)
        
        self.steps_done = 0
        
        self.scaler = torch.amp.GradScaler(enabled=(self.device.type == 'cuda'))
        
        # --- MUDANÇA 3 ---
        logging.info(self.locale_manager.get_string("guardian_agent.init.success", enabled=self.scaler.is_enabled()))

    def _load_hyperparameters(self, cfg):
        """Carrega os hiperparâmetros a partir da seção de configuração."""
        self.batch_size = cfg.getint('batch_size', 128)
        self.gamma = cfg.getfloat('gamma', 0.90)
        self.epsilon_start = cfg.getfloat('epsilon_start', 1.0)
        self.epsilon_end = cfg.getfloat('epsilon_end', 0.05)
        self.epsilon_decay = cfg.getint('epsilon_decay', 30000)
        self.learning_rate = cfg.getfloat('learning_rate', 0.00025)
        self.memory_size = cfg.getint('memory_size', 50000)

    def choose_action(self, state: list) -> torch.Tensor:
        """Escolhe uma ação usando uma política epsilon-greedy."""
        eps_threshold = self.epsilon_end + (self.epsilon_start - self.epsilon_end) * \
                        (1. - min(1., self.steps_done / self.epsilon_decay))
        self.steps_done += 1
        
        if random.random() > eps_threshold:
            with torch.no_grad():
                state_tensor = torch.tensor(state, dtype=torch.float32, device=self.device).unsqueeze(0)
                return self.policy_net(state_tensor).max(1)[1].view(1, 1)
        else:
            return torch.tensor([[random.randrange(3)]], device=self.device, dtype=torch.long)

    def learn(self):
        """Executa uma etapa de otimização da rede."""
        if len(self.memory) < self.batch_size:
            return
            
        transitions = self.memory.sample(self.batch_size)
        batch = Transition(*zip(*transitions))

        non_final_mask = torch.tensor(tuple(map(lambda s: s is not None, batch.next_state)), device=self.device, dtype=torch.bool)
        non_final_next_states = torch.cat([s for s in batch.next_state if s is not None])
        
        state_batch = torch.cat(batch.state)
        action_batch = torch.cat(batch.action)
        reward_batch = torch.cat(batch.reward)

        self.optimizer.zero_grad()
        
        with torch.amp.autocast(device_type=self.device.type, enabled=self.scaler.is_enabled()):
            state_action_values = self.policy_net(state_batch).gather(1, action_batch)
            
            next_state_values = torch.zeros(self.batch_size, device=self.device)
            with torch.no_grad():
                next_state_values[non_final_mask] = self.target_net(non_final_next_states).max(1)[0].float()
            
            expected_state_action_values = (next_state_values * self.gamma) + reward_batch
            
            loss = nn.SmoothL1Loss()(state_action_values, expected_state_action_values.unsqueeze(1))

        self.scaler.scale(loss).backward()
        torch.nn.utils.clip_grad_norm_(self.policy_net.parameters(), 1.0)
        self.scaler.step(self.optimizer)
        self.scaler.update()

    def update_target_net(self):
        """Copia os pesos da rede de política para a rede alvo."""
        self.target_net.load_state_dict(self.policy_net.state_dict())