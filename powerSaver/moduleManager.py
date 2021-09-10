# powerSaver - Save power by controlling processes and services
# Copyright (C) 2021  Nina Alexandra Klama
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import subprocess
from enum import Enum
from typing import Dict, List


class ModuleStatus(Enum):
  LOADED      = 0
  USED        = 1
  NOT_LOADED  = 2
  PARTIAL     = 3
  NEEDS_CHECK = 50
  ERROR       = 100


class ModuleManager(object):
  modules: Dict[str, int]
  sudo: bool

  def __init__(self, sudo: bool = True):
    self.sudo = sudo
    self.update_modules_list()

  def update_modules_list(self):
    lsmod_result = subprocess.run(['lsmod'], capture_output=True)
    lsmod_output = lsmod_result.stdout.decode()
    lsmod_lines  = lsmod_output.splitlines()[1:]
    self.modules = {}
    for line in lsmod_lines:
      name, size, used, *rest = line.split()
      self.modules[name] = int(used)

  def get_module_status(self, name: str) -> ModuleStatus:
    if name not in self.modules:
      return ModuleStatus.NOT_LOADED
    if self.modules[name] > 0:
      return ModuleStatus.USED
    return ModuleStatus.LOADED

  @staticmethod
  def __generate_command(command: str, name: str, sudo: bool) -> List[str]:
    output = []
    if sudo:
      output.append('sudo')
    output.append(command)
    output.append(name)
    return output

  def load_module(self, name: str) -> bool:
    modprobe_result = subprocess.run(self.__generate_command('modprobe', name, self.sudo),
                                     capture_output=True)
    if modprobe_result.returncode == 0:
      return True
    return False

  def unload_module(self, name: str) -> bool:
    rmmod_result = subprocess.run(self.__generate_command('rmmod', name, self.sudo),
                                  capture_output=True)
    if rmmod_result.returncode == 0:
      return True
    return False
