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

# File: src/hooks/pyi_runtime_hooks.py
# Author: Gabriel Moraes
# Date: 25 de Outubro de 2025 # <-- DATA ATUALIZADA

import sys
import os

print(f"[Runtime Hook] Initial sys.path: {sys.path}")

# sys._MEIPASS aponta para a pasta _internal (raiz do bundle)
bundle_dir = getattr(sys, '_MEIPASS', None)

if bundle_dir:
    # Constrói o caminho absoluto para 'src' dentro do bundle
    src_path = os.path.abspath(os.path.join(bundle_dir, 'src'))

    if os.path.isdir(src_path):
        # Tenta adicionar 'src' no início do path
        if src_path not in sys.path:
            # Insere no índice 1, logo após o diretório do script/bundle base
            # Isso pode ser mais seguro que inserir em 0
            sys.path.insert(1, src_path)
            print(f"[Runtime Hook] Added bundle src path to sys.path: {src_path}")
        else:
            print(f"[Runtime Hook] Bundle src path already in sys.path: {src_path}")
    else:
        print(f"[Runtime Hook] Bundle src path NOT found: {src_path}")

    # Garante que a raiz do bundle também esteja no path (geralmente adicionado automaticamente, mas confirma)
    abs_bundle_dir = os.path.abspath(bundle_dir)
    if abs_bundle_dir not in sys.path:
        sys.path.append(abs_bundle_dir) # Adiciona no final
        print(f"[Runtime Hook] Added bundle root path to sys.path: {abs_bundle_dir}")

else:
     print("[Runtime Hook] Not running in frozen mode (no _MEIPASS). Hook skipping modification.")

print(f"[Runtime Hook] sys.path after hook: {sys.path}")