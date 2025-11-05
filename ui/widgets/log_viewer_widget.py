# File: ui/widgets/log_viewer_widget.py (CÓDIGO COMPLETO E CORRIGIDO)
# Author: Gabriel Moraes
# Date: 29 de Setembro de 2025

"""
Define o LogViewerWidget, um widget auto-suficiente para exibir
um ficheiro de log em tempo real usando uma thread separada.
"""

import flet as ft
import threading
import time
import os

from handlers.locale_manager import LocaleManager

class LogViewerWidget(ft.Container):
    """
    Um widget que encapsula toda a funcionalidade de visualização de logs.
    """
    def __init__(self, locale_manager: LocaleManager):
        super().__init__(expand=True)

        self.locale_manager = locale_manager
        self.log_thread = None
        self.thread_running = False
        
        self.pause_text = "Pausar Log"
        self.resume_text = "Continuar"
        
        self.log_view_list = ft.ListView(expand=True, spacing=5, auto_scroll=True)
        self.title_text = ft.Text(size=20, weight=ft.FontWeight.BOLD)
        self.pause_button = ft.ElevatedButton(icon=ft.Icons.PAUSE_ROUNDED, on_click=self.toggle_pause_log)
        self.clear_button = ft.ElevatedButton(icon=ft.Icons.DELETE_SWEEP_ROUNDED, on_click=self.clear_log)
        
        self.content = ft.Column(
            controls=[
                 ft.Row(
                    [ft.Icon(ft.Icons.DESCRIPTION_ROUNDED), self.title_text],
                    alignment=ft.MainAxisAlignment.CENTER
                ),
                ft.Row(
                    [self.pause_button, self.clear_button],
                    alignment=ft.MainAxisAlignment.END,
                ),
                ft.Container(
                    content=self.log_view_list,
                    border=ft.border.all(1, ft.Colors.WHITE24),
                    border_radius=10,
                    padding=10,
                    expand=True,
                ),
            ],
            expand=True, spacing=10
        )

    def did_mount(self):
        self.update_translations(self.locale_manager)
        self.start_log_watcher()

    def will_unmount(self):
        self.stop_log_watcher()
        
    def update_translations(self, lm: LocaleManager):
        self.title_text.value = lm.get_string("diagnostics_view.log_viewer_title")
        self.pause_text = lm.get_string("diagnostics_view.log_pause")
        self.resume_text = lm.get_string("diagnostics_view.log_resume")
        self.clear_button.text = lm.get_string("diagnostics_view.log_clear")
        
        if self.thread_running:
            self.pause_button.text = self.pause_text
        else:
            self.pause_button.text = self.resume_text
            
        if self.page: self.update()

    def start_log_watcher(self):
        if not self.log_thread or not self.log_thread.is_alive():
            self.thread_running = True
            self.log_thread = threading.Thread(target=self._log_watcher_thread, daemon=True)
            self.log_thread.start()
            self.pause_button.text = self.pause_text
            self.pause_button.icon = ft.Icons.PAUSE_ROUNDED
            if self.page: self.update()

    def stop_log_watcher(self):
        self.thread_running = False
        if self.page:
            self.pause_button.text = self.resume_text
            self.pause_button.icon = ft.Icons.PLAY_ARROW_ROUNDED
            if self.page.session:
                try: self.update()
                except Exception: pass

    def toggle_pause_log(self, e):
        if self.thread_running:
            self.stop_log_watcher()
        else:
            self.start_log_watcher()

    def clear_log(self, e):
        self.log_view_list.controls.clear()
        self.update()
        
    def _add_log_message(self, message, color=None, font_family="monospace"):
        if not self.page or not self.page.session: return
        self.log_view_list.controls.append(ft.Text(message, style=ft.TextStyle(font_family=font_family), color=color))
        if self.thread_running:
            try:
                self.update()
            except Exception:
                pass
        
    # --- CONTEÚDO RESTAURADO ---
    def _find_latest_log_file(self):
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
            log_base_dir = os.path.join(project_root, "logs", "main_ai")
            if not os.path.isdir(log_base_dir): return None
            subfolders = [f.path for f in os.scandir(log_base_dir) if f.is_dir()]
            if not subfolders: return None
            latest_folder = max(subfolders, key=os.path.getmtime)
            log_file = os.path.join(latest_folder, "console_output.log")
            return log_file if os.path.exists(log_file) else None
        except Exception:
            return None

    def _log_watcher_thread(self):
        current_log_file = None
        
        while self.thread_running:
            latest_log_file = self._find_latest_log_file()
            if current_log_file != latest_log_file:
                current_log_file = latest_log_file
                self.log_view_list.controls.clear()
                if current_log_file:
                    msg_template = self.locale_manager.get_string("diagnostics_view.log_watching_file")
                    self._add_log_message(msg_template.format(file_path=f"...{current_log_file[-50:]}"), ft.Colors.GREEN)
                else:
                    self._add_log_message(self.locale_manager.get_string("diagnostics_view.log_searching"), ft.Colors.ORANGE)
            
            if current_log_file:
                try:
                    with open(current_log_file, "r", encoding="utf-8") as f:
                        f.seek(0, 2) # Vai para o final do arquivo
                        while self.thread_running:
                            check_latest = self._find_latest_log_file()
                            if check_latest != current_log_file:
                                self._add_log_message(self.locale_manager.get_string("diagnostics_view.log_new_detected"), ft.Colors.AMBER)
                                break
                            
                            line = f.readline()
                            if not line:
                                time.sleep(0.5)
                                continue
                            
                            self._add_log_message(line.strip())
                except Exception as e:
                    msg_template = self.locale_manager.get_string("diagnostics_view.log_read_error")
                    self._add_log_message(msg_template.format(error=e), ft.Colors.RED)
                    current_log_file = None
                    time.sleep(3)
            else:
                time.sleep(3)
    # --- FIM DO CONTEÚDO RESTAURADO ---