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

# File: src/sds/websocket_server.py (MODIFICADO PARA TRADUÇÃO)
# Author: Gabriel Moraes
# Date: 02 de Outubro de 2025

import asyncio
import websockets
import json
import logging
import threading
from multiprocessing import Queue
from queue import Full
import sys
import os
from typing import TYPE_CHECKING

# Adiciona o diretório 'src' ao path para permitir importações absolutas
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

if TYPE_CHECKING:
    from utils.locale_manager_backend import LocaleManagerBackend

class WebSocketServer:
    """Gerencia o servidor WebSocket, a transmissão de dados e a recepção de comandos."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8765, 
                 ui_command_queue: Queue = None, locale_manager: 'LocaleManagerBackend' = None):
        self.host = host
        self.port = port
        self.clients = set()
        self.loop = None
        self.thread = None
        self.ui_command_queue = ui_command_queue
        self.locale_manager = locale_manager

    async def _register(self, websocket):
        """Registra um novo cliente conectado."""
        logging.info(self.locale_manager.get_string("sds_websocket.register.client_connected", address=websocket.remote_address))
        self.clients.add(websocket)

    async def _unregister(self, websocket):
        """Remove um cliente desconectado."""
        logging.info(self.locale_manager.get_string("sds_websocket.unregister.client_disconnected", address=websocket.remote_address))
        self.clients.remove(websocket)

    async def _handler(self, websocket):
        """Gerencia o ciclo de vida de uma conexão de cliente, incluindo a recepção de mensagens."""
        lm = self.locale_manager
        await self._register(websocket)
        try:
            async for message in websocket:
                if self.ui_command_queue:
                    try:
                        command = json.loads(message)
                        logging.info(lm.get_string("sds_websocket.handler.command_received", command=command))
                        self.ui_command_queue.put(command)
                    except json.JSONDecodeError:
                        logging.warning(lm.get_string("sds_websocket.handler.invalid_json", address=websocket.remote_address))
                    except Full:
                        logging.warning(lm.get_string("sds_websocket.handler.queue_full"))
        finally:
            await self._unregister(websocket)

    def broadcast(self, message: dict):
        """
        Envia uma mensagem para todos os clientes conectados.
        """
        if not self.clients or not self.loop:
            return

        message_json = json.dumps(message)
        
        asyncio.run_coroutine_threadsafe(
            self._broadcast_async(message_json), 
            self.loop
        )

    async def _broadcast_async(self, message_json: str):
        """A corrotina que efetivamente envia a mensagem."""
        if not self.clients:
            return
            
        clients_to_send = list(self.clients)
        tasks = [client.send(message_json) for client in clients_to_send]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(results):
            if isinstance(result, websockets.exceptions.ConnectionClosed):
                await self._unregister(clients_to_send[i])


    async def _main_loop(self):
        """O loop principal que executa o servidor."""
        async with websockets.serve(self._handler, self.host, self.port):
            logging.info(self.locale_manager.get_string("sds_websocket.main_loop.server_started", host=self.host, port=self.port))
            await asyncio.Future()

    def start(self):
        """
        Inicia o servidor WebSocket em uma thread separada.
        """
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._run_async_loop, daemon=True)
        self.thread.start()

    def _run_async_loop(self):
        """Define o loop de eventos para a nova thread e o executa."""
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._main_loop())