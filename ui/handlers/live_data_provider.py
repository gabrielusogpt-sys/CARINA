# File: ui/handlers/live_data_provider.py (CORRIGIDO)
# Author: Gabriel Moraes
# Date: 01 de Outubro de 2025

"""
Define o LiveDataProvider.

Nesta versão, o método de envio de comandos foi tornado mais robusto,
usando um bloco try-except para lidar com conexões fechadas, em vez de
verificar um atributo.
"""

import logging
import threading
import time
import json
import asyncio
import websockets
from typing import Callable, Dict, Any

class LiveDataProvider:
    """
    Um serviço que se conecta ao back-end via WebSocket para fornecer
    pacotes de dados da simulação em tempo real e enviar comandos.
    """
    
    def __init__(self, on_data_received: Callable[[Dict[str, Any]], None]):
        self.on_data_received = on_data_received
        self._thread = None
        self._is_running = False
        self.loop = None
        
        self.uri = "ws://127.0.0.1:8765"
        self.websocket_connection = None

    def start(self):
        """Inicia o cliente WebSocket em uma thread separada."""
        if not self._thread or not self._thread.is_alive():
            self._is_running = True
            self._thread = threading.Thread(target=self._run_async_loop, daemon=True)
            self._thread.start()
            logging.info("[LiveDataProvider] Cliente WebSocket para o back-end iniciado.")

    def stop(self):
        """Para a thread e a conexão WebSocket."""
        self._is_running = False
        if self.websocket_connection and self.loop:
            asyncio.run_coroutine_threadsafe(self.websocket_connection.close(), self.loop)
        logging.info("[LiveDataProvider] Sinal de parada enviado para o cliente WebSocket.")

    def _run_async_loop(self):
        """Define o loop de eventos para a nova thread e o executa."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._websocket_thread_loop())

    async def _websocket_thread_loop(self):
        """O loop principal que gerencia a conexão e o recebimento de dados."""
        while self._is_running:
            try:
                logging.info(f"[LiveDataProvider] Tentando conectar a {self.uri}...")
                async with websockets.connect(self.uri) as websocket:
                    self.websocket_connection = websocket
                    logging.info("[LiveDataProvider] Conectado com sucesso ao back-end (SDS).")
                    
                    async for message in websocket:
                        if not self._is_running:
                            break
                        try:
                            data_packet = json.loads(message)
                            if self.on_data_received:
                                self.on_data_received(data_packet)
                        except json.JSONDecodeError:
                            logging.warning("[LiveDataProvider] Mensagem inválida (não-JSON) recebida do back-end.")
                        
            except (ConnectionRefusedError, websockets.ConnectionClosedError, websockets.ConnectionClosedOK):
                logging.warning("[LiveDataProvider] Conexão com o back-end perdida ou recusada. Tentando novamente em 5s...")
                self.websocket_connection = None
                await asyncio.sleep(5)
            except Exception as e:
                logging.error(f"[LiveDataProvider] Erro inesperado no WebSocket: {e}", exc_info=True)
                self.websocket_connection = None
                await asyncio.sleep(5)

    def send_command_to_backend(self, command: dict):
        """
        Envia um comando (dicionário Python) para o back-end de forma segura
        a partir de qualquer thread.
        """
        # --- MUDANÇA PRINCIPAL AQUI ---
        # Verificamos apenas se os objetos existem, sem aceder a .open ou .closed
        if self.websocket_connection and self.loop:
            try:
                message_json = json.dumps(command)
                # O envio em si é agendado na thread do loop de eventos
                asyncio.run_coroutine_threadsafe(
                    self.websocket_connection.send(message_json), 
                    self.loop
                )
            except Exception as e:
                # Se o send() falhar (por exemplo, porque a conexão foi fechada),
                # capturamos a exceção aqui.
                logging.warning(f"[LiveDataProvider] Falha ao enviar comando. A conexão pode estar fechada. Erro: {e}")
        else:
            logging.warning("[LiveDataProvider] Tentativa de enviar comando sem uma conexão ativa com o back-end.")
        # --- FIM DA MUDANÇA ---