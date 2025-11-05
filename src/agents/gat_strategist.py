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

# File: src/agents/gat_strategist.py (Corrigido: Atualizado de GATConv para GATv2Conv)
# Author: Gabriel Moraes
# Date: 01 de Novembro de 2025

import torch
import torch.nn as nn
import torch.nn.functional as F

# --- MUDANÇA 1: Importar GATv2Conv em vez de GATConv ---
from torch_geometric.nn import GATv2Conv, global_mean_pool
# --- FIM DA MUDANÇA 1 ---

class GATStrategist(nn.Module):
    """
    Define a arquitetura GAT Lite (agora GATv2 Lite) para o Estrategista.
    Analisa o grafo da rede e produz um vetor de orientação para cada agente.
    """
    def __init__(self, input_dim, hidden_dim, output_dim, heads):
        """
        Inicializa as camadas da rede.

        Args:
            input_dim (int): Dimensão do vetor de características de entrada (nó).
            hidden_dim (int): Dimensão da camada oculta.
            output_dim (int): Dimensão do vetor de saída (orientação estratégica).
            heads (int): Número de cabeças de atenção (multi-head attention).
        """
        super(GATStrategist, self).__init__()
        
        # --- MUDANÇA 2: Usar GATv2Conv ---
        # Camada de convolução GATv2 1
        self.conv1 = GATv2Conv(
            input_dim, 
            hidden_dim, 
            heads=heads, 
            dropout=0.1, 
            concat=True
        )
        
        # Camada de convolução GATv2 2 (saída)
        # A entrada é hidden_dim * heads porque 'concat=True'
        self.conv2 = GATv2Conv(
            hidden_dim * heads, 
            output_dim, 
            heads=1, # Cabeça única para a saída final
            dropout=0.1, 
            concat=False # Saída final não é concatenada
        )
        # --- FIM DA MUDANÇA 2 ---

        # Camadas de normalização
        self.norm1 = nn.LayerNorm(hidden_dim * heads)
        self.norm2 = nn.LayerNorm(output_dim)

    def forward(self, x, edge_index):
        """
        Define o "forward pass" da rede.
        Esta lógica permanece idêntica à do GATConv.

        Args:
            x (Tensor): Tensor de características dos nós [num_nodes, input_dim].
            edge_index (Tensor): Tensor de conectividade do grafo [2, num_edges].

        Returns:
            Tensor: Tensor de vetores estratégicos [num_nodes, output_dim].
        """
        
        # 1. Primeira Camada GATv2 + Ativação + Normalização
        x = self.conv1(x, edge_index)
        x = F.elu(x)
        x = self.norm1(x)
        x = F.dropout(x, p=0.1, training=self.training)
        
        # 2. Segunda Camada GATv2 + Normalização (Sem ativação final)
        x = self.conv2(x, edge_index)
        x = self.norm2(x)
        
        # O resultado 'x' agora é [num_nodes, output_dim]
        # Cada linha 'i' é o vetor estratégico para o nó 'i'
        return x