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

# File: src/database/database_manager.py (MODIFICADO PARA TRADUÇÃO)
# Author: Gabriel Moraes
# Date: 01 de Outubro de 2025

import sqlite3
import logging
import os
from datetime import datetime
import sys
from typing import TYPE_CHECKING

# Adiciona o diretório 'src' ao path para permitir importações absolutas
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

if TYPE_CHECKING:
    from utils.locale_manager_backend import LocaleManagerBackend

class DatabaseManager:
    """
    Gerencia todas as interações com o banco de dados SQLite do CARINA.
    """
    def __init__(self, locale_manager: 'LocaleManagerBackend', db_name: str = "carina_data.db"):
        self.locale_manager = locale_manager
        lm = self.locale_manager
        
        project_root_local = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        db_dir = os.path.join(project_root_local, "results", "database")
        os.makedirs(db_dir, exist_ok=True)
        self.db_path = os.path.join(db_dir, db_name)
        
        self._initialize_db()
        logging.info(lm.get_string("db_manager.init.manager_created", path=self.db_path))

    def _get_connection(self) -> sqlite3.Connection:
        """Retorna uma nova conexão com o banco de dados."""
        return sqlite3.connect(self.db_path)

    def _initialize_db(self):
        """
        Cria as tabelas necessárias no banco de dados se elas não existirem.
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS simulation_runs (
                run_id INTEGER PRIMARY KEY AUTOINCREMENT,
                start_time TIMESTAMP NOT NULL,
                scenario_name TEXT
            );
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS episodes (
                episode_id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                episode_number INTEGER NOT NULL,
                total_reward REAL,
                end_time TIMESTAMP,
                FOREIGN KEY (run_id) REFERENCES simulation_runs (run_id)
            );
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS analysis_reports (
                report_id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                summary TEXT,
                report_content TEXT,
                FOREIGN KEY (run_id) REFERENCES simulation_runs (run_id)
            );
            """)
            
            conn.commit()
        except sqlite3.Error as e:
            logging.error(self.locale_manager.get_string("db_manager.init.db_error", error=e))
        finally:
            conn.close()

    def create_simulation_run(self, scenario_name: str) -> int | None:
        """
        Registra uma nova execução da simulação no banco de dados.
        """
        lm = self.locale_manager
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            start_time = datetime.now()
            cursor.execute(
                "INSERT INTO simulation_runs (start_time, scenario_name) VALUES (?, ?)",
                (start_time, scenario_name)
            )
            conn.commit()
            logging.info(lm.get_string("db_manager.create_run.success", scenario=scenario_name))
            return cursor.lastrowid
        except sqlite3.Error as e:
            logging.error(lm.get_string("db_manager.create_run.error", error=e))
            return None
        finally:
            conn.close()

    def log_episode(self, run_id: int, episode_number: int, total_reward: float):
        """
        Salva as métricas de um episódio finalizado no banco de dados.
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            end_time = datetime.now()
            cursor.execute(
                "INSERT INTO episodes (run_id, episode_number, total_reward, end_time) VALUES (?, ?, ?, ?)",
                (run_id, episode_number, total_reward, end_time)
            )
            conn.commit()
        except sqlite3.Error as e:
            logging.error(self.locale_manager.get_string("db_manager.log_episode.error", episode=episode_number, error=e))
        finally:
            conn.close()
            
    def log_analysis_report(self, run_id: int, summary: str, report_content: str):
        """
        Salva um relatório de análise de infraestrutura no banco de dados.
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            timestamp = datetime.now()
            cursor.execute(
                "INSERT INTO analysis_reports (run_id, timestamp, summary, report_content) VALUES (?, ?, ?, ?)",
                (run_id, timestamp, summary, report_content)
            )
            conn.commit()
        except sqlite3.Error as e:
            logging.error(self.locale_manager.get_string("db_manager.log_report.error", error=e))
        finally:
            conn.close()