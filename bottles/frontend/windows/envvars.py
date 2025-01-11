# envvars.py
#
# Copyright 2022 brombinmirko <send@mirko.pm>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, in version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

from gettext import gettext as _

from gi.repository import Gtk, GLib, Adw

from bottles.backend.logger import Logger
from bottles.frontend.utils.gtk import GtkUtils
from bottles.frontend.utils.sh import ShUtils

logging = Logger()


@Gtk.Template(resource_path="/com/usebottles/bottles/env-var-entry.ui")
class EnvironmentVariableEntryRow(Adw.EntryRow):
    __gtype_name__ = "EnvironmentVariableEntryRow"

    # region Widgets
    btn_remove = Gtk.Template.Child()
    # endregion

    def __init__(self, parent, env, **kwargs):
        super().__init__(**kwargs)

        # common variables and references
        self.parent = parent
        self.manager = parent.window.manager
        self.config = parent.config
        self.env = env
        self.set_text("=".join(self.env))

        # connect signals
        self.connect("changed", self.__validate)
        self.connect("apply", self.__save)
        self.btn_remove.connect("clicked", self.__remove)

        try:
            widget = (
                self.get_child().get_first_child().get_next_sibling().get_first_child()
            )
            while isinstance(widget, Gtk.Label):
                widget.set_visible(False)
                widget = widget.get_next_sibling()

            if isinstance(widget, Gtk.Text):
                widget.set_valign(Gtk.Align.CENTER)
            else:
                raise RuntimeError("Could not find widget Gtk.Text")
        except Exception as e:
            logging.error(
                f"{type(e)}: {e}\nEnvironmentVariableEntryRow could not find text widget. Did AdwEntryRow change it's widget tree?"
            )

    def __save(self, *_args):
        """
        Change the env var value according to the
        user input and update the bottle configuration
        """
        if not self.__valid_name:
            return

        new_name, new_value = ShUtils.split_assignment(self.get_text())
        self.manager.update_config(
            config=self.config,
            key=new_name,
            value=new_value,
            scope="Environment_Variables",
        )
        if new_name != self.env[0]:
            self.__remove_config()

        self.env = (new_name, new_value)

    def __remove(self, *_args):
        """
        Remove the env var from the bottle configuration and
        destroy the widget
        """
        self.__remove_config()
        self.parent.group_vars.remove(self)

    def __remove_config(self, *_args):
        """
        Remove the env var from the bottle configuration
        """
        self.manager.update_config(
            config=self.config,
            key=self.env[0],
            value=False,
            remove=True,
            scope="Environment_Variables",
        )

    def __validate(self, *_args):
        self.__valid_name = GtkUtils.validate_entry(
            self, lambda var_name: not var_name == "WINEDLLOVERRIDES"
        )

        if not self.__valid_name:
            self.add_css_class("error")


@Gtk.Template(resource_path="/com/usebottles/bottles/dialog-env-vars.ui")
class EnvironmentVariablesDialog(Adw.Dialog):
    __gtype_name__ = "EnvironmentVariablesDialog"

    # region Widgets
    entry_new_var = Gtk.Template.Child()
    group_vars = Gtk.Template.Child()
    # endregion

    def __init__(self, window, config, **kwargs):
        super().__init__(**kwargs)

        # common variables and references
        self.window = window
        self.manager = window.manager
        self.config = config

        self.__populate_vars_list()

        # connect signals
        self.entry_new_var.connect("changed", self.__validate)
        self.entry_new_var.connect("apply", self.__save_var)

    def present(self):
        return super().present(self.window)

    def __validate(self, *_args):
        self.__valid_name = GtkUtils.validate_entry(
            self.entry_new_var, lambda var_name: not var_name == "WINEDLLOVERRIDES"
        )

    def __save_var(self, *_args):
        """
        This function save the new env var to the
        bottle configuration
        """
        if not self.__valid_name:
            return

        new_name, new_value = ShUtils.split_assignment(self.entry_new_var.get_text())
        self.manager.update_config(
            config=self.config,
            key=new_name,
            value=new_value,
            scope="Environment_Variables",
        )
        _entry = EnvironmentVariableEntryRow(parent=self, env=(new_name, new_value))
        self.group_vars.set_description()
        self.group_vars.add(_entry)
        self.entry_new_var.set_text("")

    def __populate_vars_list(self):
        """
        This function populate the list of env vars
        with the existing ones from the bottle configuration
        """
        envs = self.config.Environment_Variables.items()
        if len(envs) == 0:
            self.group_vars.set_description(_("No environment variables defined"))
            return

        for env in envs:
            _entry = EnvironmentVariableEntryRow(parent=self, env=env)
            self.group_vars.add(_entry)
