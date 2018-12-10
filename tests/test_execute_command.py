from unittesting import DeferrableTestCase
import sublime
from os.path import dirname
from LSP.plugin.core.types import ClientConfig, ClientStates, LanguageConfig
from LSP.plugin.core.test_session import MockClient
from LSP.plugin.core.sessions import Session
from LSP.plugin.core.registry import windows  # , session_for_view
from LSP.plugin.core.settings import client_configs
from LSP.plugin.core.types import Command

test_language = LanguageConfig("test", ["text.plain"], ["Plain text"])
test_commands = [Command("command1", dict()), Command("command2", dict())]
text_config = ClientConfig("test", [], None, languages=[test_language], commands=test_commands,)


class LspExecuteCommandTests(DeferrableTestCase):

    def setUp(self):
        self.view = sublime.active_window().new_file()
        self.old_configs = client_configs.all
        client_configs.all = [text_config]

    def test_show_inputlistener(self):
        wm = windows.lookup(self.view.window())
        wm._configs.all.append(text_config)

        session = Session(text_config, dirname(__file__), MockClient())
        session.state = ClientStates.READY
        wm._sessions[text_config.name] = session

        self.view.run_command('lsp_execute')

        # popup should be visible eventually
        yield self.view.is_popup_visible()
        # TODO: check the content of the pallet, select one element and hit enter

    def test_execute_command(self):
        wm = windows.lookup(self.view.window())
        wm._configs.all.append(text_config)

        session = Session(text_config, dirname(__file__), MockClient())
        session.state = ClientStates.READY
        wm._sessions[text_config.name] = session
        self.view.run_command("lsp_execute_command", {"command_name": "command1"})

    def tearDown(self):
        client_configs.all = self.old_configs
        if self.view:
            self.view.set_scratch(True)
            self.view.window().focus_view(self.view)
            self.view.window().run_command("close_file")