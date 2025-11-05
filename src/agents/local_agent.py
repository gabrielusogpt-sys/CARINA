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

# File: src/agents/local_agent.py (MODIFICADO PARA TRADUÇÃO COMPLETA)
# Author: Gabriel Moraes
# Date: 03 de Outubro de 2025

import torch
import torch.nn as nn
from torch.distributions import Categorical
import torch.optim as optim
from torch.utils.tensorboard import SummaryWriter
import logging
import numpy as np
from typing import TYPE_CHECKING

# --- MUDANÇA 1: Adicionar importações ---
if TYPE_CHECKING:
    from utils.locale_manager_backend import LocaleManagerBackend

from models.actor_critic_lstm import ActorCriticNet
from memory.on_policy_buffer import OnPolicyBuffer
from memory.replay_memory import ReplayMemory


class LocalAgent:
    """
    O agente tático que controla um único semáforo usando o algoritmo PPO.
    """
    # --- MUDANÇA 2: Modificar o construtor ---
    def __init__(self, tlight_id, n_observations, n_actions, initial_hyperparams: dict, log_dir: str, locale_manager: 'LocaleManagerBackend'):
        self.id = tlight_id
        self.n_actions = n_actions
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.n_observations = n_observations
        self.locale_manager = locale_manager
        
        self.hyperparams = initial_hyperparams
        self._load_hyperparameters()
        
        self._build_network()
        self._create_optimizer()
        
        self.memory = OnPolicyBuffer()
        self.xai_memory = ReplayMemory(capacity=5000)
        
        self.current_reward_bonus = 0.0
        self.writer = SummaryWriter(log_dir)
        self.steps_done = 0
        self.episodes_done = 0
        
        self.scaler = torch.amp.GradScaler(enabled=(self.device.type == 'cuda'))
        
    def _load_hyperparameters(self):
        """Carrega os hiperparâmetros a partir de um dicionário."""
        self.gamma = float(self.hyperparams.get('gamma', 0.99))
        self.gae_lambda = float(self.hyperparams.get('gae_lambda', 0.95))
        self.learning_rate = float(self.hyperparams.get('learning_rate', 0.0001))
        self.eps_clip = float(self.hyperparams.get('eps_clip', 0.2))
        self.k_epochs = int(self.hyperparams.get('k_epochs', 4))
        self.target_kl = float(self.hyperparams.get('target_kl', 0.02))
        self.grad_clip_norm = float(self.hyperparams.get('grad_clip_norm', 0.5))
        self.dropout_p = float(self.hyperparams.get('dropout_p', 0.1))
        self.critic_loss_coef = 0.5

    def update_hyperparameters(self, new_hyperparams: dict):
        """Atualiza os hiperparâmetros e recria a rede e o otimizador (para PBT)."""
        self.hyperparams = new_hyperparams
        self._load_hyperparameters()
        if self.optimizer:
            self.optimizer.param_groups[0]['lr'] = self.learning_rate
        if self.policy_net:
             for module in self.policy_net.modules():
                if isinstance(module, nn.Dropout):
                    module.p = self.dropout_p

    def _build_network(self):
        """Instancia a rede Actor-Critic a partir do componente importado."""
        self.policy_net = ActorCriticNet(self.n_observations, self.n_actions, dropout_p=self.dropout_p).to(self.device)

    def _create_optimizer(self):
        """Cria o otimizador para a rede."""
        self.optimizer = optim.AdamW(self.policy_net.parameters(), lr=self.learning_rate)
    
    def save_checkpoint(self, filepath: str):
        """Salva o estado do agente, incluindo a memória XAI, em um arquivo de checkpoint."""
        checkpoint = {
            'episodes_done': self.episodes_done, 
            'steps_done': self.steps_done,
            'policy_net_state_dict': self.policy_net.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'hyperparameters': self.hyperparams,
            'xai_memory': self.xai_memory,
            'n_observations': self.n_observations
        }
        torch.save(checkpoint, filepath)

    def load_checkpoint(self, filepath: str):
        """Carrega o estado do agente, incluindo a memória XAI, de um arquivo de checkpoint."""
        lm = self.locale_manager
        try:
            checkpoint = torch.load(filepath, map_location=self.device, weights_only=False)
            
            if self.n_observations != checkpoint.get('n_observations'):
                # --- MUDANÇA 3 ---
                logging.warning(lm.get_string(
                    "local_agent.load.obs_mismatch_warning", 
                    agent_id=self.id, 
                    chk_obs=checkpoint.get('n_observations'), 
                    cur_obs=self.n_observations
                ))
            
            self.update_hyperparameters(checkpoint['hyperparameters'])
            self.policy_net.load_state_dict(checkpoint['policy_net_state_dict'])
            self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
            self.episodes_done = checkpoint.get('episodes_done', 0)
            self.steps_done = checkpoint.get('steps_done', 0)

            loaded_xai_memory = checkpoint.get('xai_memory')
            if loaded_xai_memory:
                self.xai_memory = loaded_xai_memory
            
            self.policy_net.train()
            # --- MUDANÇA 4 ---
            logging.info(lm.get_string(
                "local_agent.load.success", 
                agent_id=self.id, 
                path=filepath, 
                count=len(self.xai_memory)
            ))
        except FileNotFoundError:
            # --- MUDANÇA 5 ---
            logging.warning(lm.get_string("local_agent.load.not_found_warning", agent_id=self.id, path=filepath))
        except Exception as e:
            # --- MUDANÇA 6 ---
            logging.error(lm.get_string("local_agent.load.error", agent_id=self.id, error=e), exc_info=True)

    def push_memory(self, state_sequence, action, log_prob, reward, done, state_value):
        """Adiciona uma transição às memórias do agente."""
        self.memory.push(
            state_sequence, 
            action.cpu().numpy(),
            log_prob.cpu().numpy(), 
            np.float32(reward), 
            done, 
            state_value.cpu().numpy().flatten()
        )
        state_for_xai = np.array(state_sequence, dtype=np.float32)
        self.xai_memory.push(state_for_xai, None, None, None)

    def choose_action(self, state_tensor: torch.Tensor) -> tuple:
        """Toma uma decisão com base em um tensor de sequência de estados."""
        with torch.no_grad():
            action_probs, state_val = self.policy_net(state_tensor)
            
            dist = Categorical(action_probs)
            action = dist.sample()
            action_log_prob = dist.log_prob(action)
            dist_entropy = dist.entropy()
            
        return action, action_log_prob, state_val, dist_entropy

    def learn(self):
        """Executa o ciclo de otimização do PPO."""
        self.steps_done += 1
        old_states, old_actions, old_log_probs, rewards, dones, old_state_values = self.memory.get_batch()
        old_states, old_actions, old_log_probs, old_state_values = old_states.to(self.device), old_actions.to(self.device), old_log_probs.to(self.device), old_state_values.to(self.device)
        
        with torch.no_grad():
            last_state_value = old_state_values[-1]
            advantages = torch.zeros_like(torch.tensor(rewards), dtype=torch.float32, device=self.device); gae = 0
            for t in reversed(range(len(rewards))):
                is_done = 1.0 - float(dones[t])
                next_value = old_state_values[t+1] if t < len(rewards) - 1 else last_state_value
                delta = rewards[t] + self.gamma * next_value * is_done - old_state_values[t]
                gae = delta + self.gamma * self.gae_lambda * is_done * gae
                advantages[t] = gae
        
        rewards_to_go = advantages + old_state_values
        advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)

        for i in range(self.k_epochs):
            self.optimizer.zero_grad()
            with torch.amp.autocast(device_type=self.device.type, enabled=self.scaler.is_enabled()):
                new_log_probs, state_values, dist_entropy = self.evaluate(old_states, old_actions)
                ratios = torch.exp(new_log_probs - old_log_probs.detach())
                surr1 = ratios * advantages
                surr2 = torch.clamp(ratios, 1 - self.eps_clip, 1 + self.eps_clip) * advantages
                actor_loss = -torch.min(surr1, surr2).mean()
                critic_loss = nn.MSELoss()(state_values, rewards_to_go.detach())
                entropy_bonus = -0.01 * dist_entropy.mean()
                total_loss = actor_loss + (self.critic_loss_coef * critic_loss) + entropy_bonus
            
            self.scaler.scale(total_loss).backward()
            torch.nn.utils.clip_grad_norm_(self.policy_net.parameters(), self.grad_clip_norm)
            self.scaler.step(self.optimizer)
            self.scaler.update()
            
            with torch.no_grad(): kl_div = torch.mean(old_log_probs.detach() - new_log_probs).item()
            if abs(kl_div) > self.target_kl:
                break
        
        self.memory.clear()
        
        self.writer.add_scalar('Treinamento/Loss_Total', total_loss.item(), self.steps_done)

    def evaluate(self, state_sequence_batch, action) -> tuple:
        """Reavalia as ações para o lote de dados durante o aprendizado."""
        action_probs, state_values = self.policy_net(state_sequence_batch)
        dist = Categorical(action_probs)
        action_log_probs = dist.log_prob(action.squeeze())
        dist_entropy = dist.entropy()
        return action_log_probs, torch.squeeze(state_values), dist_entropy