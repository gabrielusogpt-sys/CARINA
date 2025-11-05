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

# File: src/xai/xai_worker.py (MODIFICADO PARA TRADUÇÃO COMPLETA)
# Author: Gabriel Moraes
# Date: 03 de Outubro de 2025

import logging
import os
import json
import time
import sys
import configparser
import torch

def run_xai_worker(
    settings: configparser.ConfigParser,
    scenario_results_dir: str
):
    """
    O ponto de entrada e loop principal para o processo do XAI Worker.
    """
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    src_path = os.path.join(project_root, 'src')
    if src_path not in sys.path:
        sys.path.insert(0, src_path)

    from utils.logging_setup import setup_logging
    from xai.captum_analyzer import CaptumAnalyzer
    from agents.local_agent import LocalAgent
    from utils.locale_manager_backend import LocaleManagerBackend

    log_dir = os.path.join(project_root, "logs", "xai_worker")
    os.makedirs(log_dir, exist_ok=True)
    setup_logging(log_dir=log_dir)

    captum_base_dir = os.path.join(scenario_results_dir, "captum")
    requests_dir = os.path.join(captum_base_dir, "requests")
    responses_dir = os.path.join(captum_base_dir, "responses")
    os.makedirs(requests_dir, exist_ok=True)
    os.makedirs(responses_dir, exist_ok=True)

    # --- MUDANÇAS APLICADAS A PARTIR DAQUI ---
    lm = LocaleManagerBackend()

    logging.info(lm.get_string("xai_worker.run.start", path=requests_dir))

    while True:
        try:
            request_files = [f for f in os.listdir(requests_dir) if f.endswith(".request")]
            if not request_files:
                time.sleep(2)
                continue

            for request_filename in request_files:
                request_path = os.path.join(requests_dir, request_filename)
                agent_id = request_filename.replace(".request", "")
                
                response_filename = f"{agent_id}.response"
                response_path = os.path.join(responses_dir, response_filename)
                response_tmp_path = response_path + ".tmp"
                
                logging.info(lm.get_string("xai_worker.run.request_received", agent_id=agent_id))

                try:
                    checkpoint_path = os.path.join(scenario_results_dir, "checkpoints", f"agent_{agent_id}.pth")
                    if not os.path.exists(checkpoint_path):
                        raise FileNotFoundError(f"Checkpoint file not found at {checkpoint_path}")

                    checkpoint = torch.load(checkpoint_path, map_location=torch.device('cpu'))
                    n_observations = checkpoint.get('n_observations')
                    if n_observations is None:
                        raise ValueError("Checkpoint does not contain 'n_observations'.")

                    agent = LocalAgent(
                        tlight_id=agent_id,
                        n_observations=n_observations,
                        n_actions=3,
                        initial_hyperparams={},
                        log_dir="",
                        locale_manager=lm 
                    )
                    agent.load_checkpoint(checkpoint_path)
                    
                    analyzer = CaptumAnalyzer(
                        agent=agent,
                        scenario_results_dir=scenario_results_dir,
                        locale_manager=lm
                    )
                    
                    analysis_result = analyzer.generate_analysis()
                    
                    if analysis_result:
                        response_data = {
                            "status": "complete", 
                            "image_path": analysis_result.get("image_path"),
                            "text_path": analysis_result.get("text_path")
                        }
                    else:
                        response_data = {"status": "error", "message": lm.get_string("xai_worker.run.analysis_failed")}

                except Exception as e:
                    logging.error(lm.get_string("xai_worker.run.processing_error", error=e), exc_info=True)
                    response_data = {"status": "error", "message": str(e)}
                
                finally:
                    try:
                        with open(response_tmp_path, "w", encoding="utf-8") as f:
                            json.dump(response_data, f, indent=4)
                        os.rename(response_tmp_path, response_path)
                    except Exception as e:
                        logging.error(lm.get_string("xai_worker.run.response_file_error", error=e))
                    
                    if os.path.exists(request_path):
                        os.remove(request_path)
                    logging.info(lm.get_string("xai_worker.run.response_sent", filename=response_filename))

            time.sleep(2)

        except (KeyboardInterrupt, SystemExit):
            break
        except Exception as e:
            logging.error(lm.get_string("xai_worker.run.critical_loop_error", error=e), exc_info=True)
            time.sleep(10)
    
    logging.info(lm.get_string("xai_worker.run.finished"))