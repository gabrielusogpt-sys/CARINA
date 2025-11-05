# File: ui/views/settings_view.py (CORRIGIDO)
# Author: Gabriel Moraes
# Date: 01 de Outubro de 2025

import flet as ft
from typing import Callable

from ui.handlers.locale_manager import LocaleManager
from ui.handlers.settings_handler import SettingsHandler
from ui.clients.settings_client import SettingsClient
from ui.widgets.general_settings_card import GeneralSettingsCard
from ui.widgets.traffic_rules_card import TrafficRulesCard
from ui.widgets.dashboard_settings_card import DashboardSettingsCard
from ui.widgets.advanced_ppo_card import AdvancedPPOCard
from ui.widgets.advanced_dqn_card import AdvancedDQNCard
from ui.widgets.advanced_system_card import AdvancedSystemCard
from ui.dialogs.confirmation_dialog_manager import ConfirmationDialogManager
from ui.widgets.piloting_school_card import PilotingSchoolCard
from ui.widgets.reward_weights_card import RewardWeightsCard

class SettingsView(ft.Container):
    def __init__(
        self,
        locale_manager: LocaleManager,
        settings_client: SettingsClient,
        # --- MUDANÇA 1: Remover o callback de mudança de idioma ---
        # on_language_change_callback: Callable[[], None] # REMOVIDO
    ):
        super().__init__(expand=True, padding=10)

        self.locale_manager = locale_manager
        self.settings_client = settings_client
        
        self.handler = SettingsHandler()
        initial_settings = self.handler.get_current_settings()
        
        self.dialog_manager: ConfirmationDialogManager | None = None

        self.general_card = GeneralSettingsCard(initial_settings)
        self.traffic_rules_card = TrafficRulesCard(initial_settings)
        self.dashboard_card = DashboardSettingsCard(initial_settings)
        self.advanced_ppo_card = AdvancedPPOCard(initial_settings)
        self.advanced_dqn_card = AdvancedDQNCard(initial_settings)
        self.advanced_system_card = AdvancedSystemCard(initial_settings)
        self.piloting_school_card = PilotingSchoolCard(initial_settings)
        self.reward_weights_card = RewardWeightsCard(initial_settings)

        self.card_widgets = [
            self.general_card, self.traffic_rules_card, self.dashboard_card,
            self.advanced_ppo_card, self.advanced_dqn_card, self.advanced_system_card,
            self.piloting_school_card, self.reward_weights_card
        ]

        self.title_text = ft.Text(size=24, weight=ft.FontWeight.BOLD)
        self.save_button = ft.ElevatedButton(icon=ft.Icons.SAVE_ROUNDED, on_click=self._save_click)
        self.restore_button = ft.TextButton(icon=ft.Icons.SETTINGS_BACKUP_RESTORE, on_click=self._restore_click)
        self.warning_text = ft.Text(size=12, expand=True, italic=True)

        general_tab_content = ft.Column(
            controls=[self.general_card, self.traffic_rules_card, self.dashboard_card], 
            spacing=15, scroll=ft.ScrollMode.ADAPTIVE
        )

        advanced_tab_content = ft.Column(
            controls=[
                ft.Container(
                    bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.AMBER), 
                    border=ft.border.all(1, ft.Colors.AMBER),
                    border_radius=10, padding=15,
                    content=ft.Row([
                        ft.Icon(ft.Icons.WARNING_ROUNDED, color=ft.Colors.AMBER),
                        self.warning_text
                    ])
                ),
                self.advanced_ppo_card, self.advanced_dqn_card,
                self.piloting_school_card, self.reward_weights_card,
                self.advanced_system_card,
            ], 
            spacing=15, scroll=ft.ScrollMode.ADAPTIVE
        )
        
        self.content = ft.Column(
            controls=[
                ft.Row([ft.Icon(ft.Icons.SETTINGS), self.title_text]),
                ft.Tabs(
                    selected_index=0, animation_duration=300, expand=True,
                    tabs=[
                        ft.Tab(content=general_tab_content, text="", icon=ft.Icons.TUNE_ROUNDED),
                        ft.Tab(content=advanced_tab_content, text="", icon=ft.Icons.HUB_ROUNDED),
                    ],
                ),
                ft.Row([self.restore_button, self.save_button], alignment=ft.MainAxisAlignment.END, spacing=20)
            ],
            expand=True, spacing=15
        )

    def did_mount(self):
        if self.page:
            self.dialog_manager = ConfirmationDialogManager(self.page, self.locale_manager)
        self.update_translations(self.locale_manager)
        
    def update_translations(self, lm: LocaleManager):
        # A lógica de tradução inicial permanece a mesma
        self.title_text.value = lm.get_string("settings_view.title")
        self.content.controls[1].tabs[0].text = lm.get_string("settings_view.tab_general")
        self.content.controls[1].tabs[1].text = lm.get_string("settings_view.tab_advanced")
        self.save_button.text = lm.get_string("settings_view.save_button")
        self.restore_button.text = lm.get_string("settings_view.restore_button")
        self.warning_text.value = lm.get_string("settings_view.warning_text")

        for card in self.card_widgets:
            if hasattr(card, 'update_translations'):
                card.update_translations(lm)
        
        if self.dialog_manager:
            self.dialog_manager.update_translations()
        
        if self.page: self.update()

    def _load_initial_settings(self, settings: dict = None):
        if settings is None:
            settings = self.handler.get_current_settings()
        for card in self.card_widgets:
            card.set_values(settings)
        if self.page: self.update()

    def _save_click(self, e):
        if not self.dialog_manager: return
        
        # --- MUDANÇA 2: Simplificar o diálogo de confirmação ---
        # Agora, sempre mostramos o mesmo diálogo genérico de confirmação.
        title = self.locale_manager.get_string("dialogs.confirm_action_title")
        content = self.locale_manager.get_string("dialogs.save_settings_content")
            
        self.dialog_manager.show(title=title, content=content, on_confirm=self._execute_save)

    def _execute_save(self):
        if not self.page or not self.settings_client: return
        
        new_settings_values = {}
        for card in self.card_widgets:
            new_settings_values.update(card.get_values())
        
        # Envia as configurações para o backend (comportamento inalterado)
        payload_to_send = self.handler.prepare_settings_for_save(new_settings_values)
        self.settings_client.save_settings(payload_to_send)
        
        # --- MUDANÇA 3: Remover o hot-reload e mostrar um diálogo informativo ---
        # A lógica complexa de "if language changed" foi removida.
        
        # Simplesmente informamos o usuário que um reinício é necessário para que as alterações tenham efeito.
        info_title = self.locale_manager.get_string("settings_view.title") # Reutilizando um título
        info_content = "As configurações foram salvas. Por favor, reinicie a aplicação para que todas as alterações tenham efeito."
        
        self.dialog_manager.show_info(title=info_title, content=info_content)
        self.page.update()
        # --- FIM DA MUDANÇA ---

    def _restore_click(self, e):
        if not self.page: return
        default_settings = self.handler.get_default_settings()
        self._load_initial_settings(default_settings)
        self.page.snack_bar = ft.SnackBar(content=ft.Text("Configurações restauradas para os valores padrão!"))
        self.page.snack_bar.open = True
        self.page.update()