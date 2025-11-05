# File: ui/main_ui.py (CORRIGIDO E FINALIZADO)
# Author: Gabriel Moraes
# Date: 01 de Outubro de 2025

import sys
import os
import logging

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

import flet as ft
from ui.views.dashboard_view import DashboardView
from ui.views.diagnostics_view import DiagnosticsView
from ui.views.planning_view import PlanningView
from ui.views.settings_view import SettingsView 
from ui.handlers.live_data_provider import LiveDataProvider
from ui.clients.control_client import ControlClient
from src.utils.logging_setup import setup_logging
from ui.handlers.locale_manager import LocaleManager
from ui.clients.settings_client import SettingsClient

def main(page: ft.Page):
    """Função principal que constrói e configura a página da aplicação Flet."""
    log_dir = os.path.join(project_root, "logs", "ui_worker")
    os.makedirs(log_dir, exist_ok=True)
    setup_logging(log_dir=log_dir)

    logging.info("--- O PROGRAMA DA UI INICIOU COM SUCESSO ---")
    
    locale_manager = LocaleManager()
    
    page.title = locale_manager.get_string("main_ui.app_title")
    page.window_width = 1280
    page.window_height = 800
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 10
    
    caminho_do_icone = os.path.join(project_root, "ui", "assets", "images", "logo.ico")
    if not os.path.exists(caminho_do_icone):
        caminho_do_icone = os.path.join(project_root, "ui", "assets", "images", "logo.png")

    if os.path.exists(caminho_do_icone):
        page.window_favicon_path = caminho_do_icone

    live_data_provider = LiveDataProvider(on_data_received=lambda data: dashboard_view.update_live_data(data))
    control_client = ControlClient(live_data_provider=live_data_provider)
    settings_client = SettingsClient(live_data_provider=live_data_provider)

    dashboard_view = DashboardView(control_client=control_client, locale_manager=locale_manager)
    planning_view = PlanningView(locale_manager=locale_manager)
    diagnostics_view = DiagnosticsView(locale_manager=locale_manager)
    
    def apply_translations_to_ui():
        # Esta função ainda é necessária para a tradução inicial da UI
        page.title = locale_manager.get_string("main_ui.app_title")
        page.appbar.title.value = locale_manager.get_string("main_ui.app_long_title")
        page.appbar.actions[0].tooltip = locale_manager.get_string("main_ui.settings_tooltip")
        
        main_tabs.tabs[0].text = locale_manager.get_string("main_ui.tab_dashboard")
        main_tabs.tabs[1].text = locale_manager.get_string("main_ui.tab_planning")
        main_tabs.tabs[2].text = locale_manager.get_string("main_ui.tab_diagnostics")

        dashboard_view.update_translations(locale_manager)
        planning_view.update_translations(locale_manager)
        diagnostics_view.update_translations(locale_manager)
        settings_view.update_translations(locale_manager)

        page.update()

    # --- MUDANÇA PRINCIPAL AQUI ---
    # A referência 'on_language_change_callback' foi removida da chamada,
    # pois a SettingsView não precisa mais dela.
    settings_view = SettingsView(
        locale_manager=locale_manager,
        settings_client=settings_client
    )
    # --- FIM DA MUDANÇA ---
    
    def close_settings_dialog(e=None):
        settings_dialog.open = False
        page.update()

    settings_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Row([ft.Icon(ft.Icons.SETTINGS), ft.Text("Configurações")]),
        content=settings_view,
        actions=[ft.TextButton("Fechar", on_click=close_settings_dialog)],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    page.overlay.append(settings_dialog)

    def open_settings_dialog(e):
        settings_dialog.open = True
        page.update()

    page.on_resize = lambda e: None
    page.on_keyboard_event = lambda e: page.window_full_screen if e.key == "F11" else None

    page.appbar = ft.AppBar(
        leading=ft.Icon(ft.Icons.TRAFFIC_ROUNDED),
        title=ft.Text(),
        center_title=False,
        bgcolor=ft.Colors.BLUE_GREY_800,
        actions=[ft.IconButton(ft.Icons.SETTINGS_ROUNDED, on_click=open_settings_dialog)],
    )
    
    def on_disconnect(e):
        logging.info("--- O PROGRAMA DA UI FOI ENCERRADO ---")
        if live_data_provider:
            live_data_provider.stop()

    page.on_disconnect = on_disconnect
    live_data_provider.start()
    
    def on_tab_change(e):
        if e.control.selected_index == 2:
            diagnostics_view.start_log_watcher()
        else:
            diagnostics_view.stop_log_watcher()

    main_tabs = ft.Tabs(
        selected_index=0,
        animation_duration=300,
        on_change=on_tab_change,
        tabs=[
            ft.Tab(icon=ft.Icons.SPACE_DASHBOARD_ROUNDED, content=dashboard_view),
            ft.Tab(icon=ft.Icons.EDIT_ROAD_ROUNDED, content=planning_view),
            ft.Tab(icon=ft.Icons.BUILD_ROUNDED, content=diagnostics_view),
        ],
        expand=True,
    )
    
    # A chamada aqui no final ainda é necessária para definir os textos iniciais
    apply_translations_to_ui()
    page.add(main_tabs)
    page.update()


if __name__ == "__main__":
    ft.app(target=main)