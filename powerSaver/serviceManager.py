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


from enum import Enum
from typing import Callable, Dict, List, Optional

import re
import os
import os.path
import subprocess


def is_exe(path: str) -> bool:
  return os.path.isfile(path) and os.access(path, os.X_OK)


sysvinit_status_parser = re.compile(r"^.*status:\s+(\w+)\s*$")


class ServiceStatusFunctionUnimplemented(Exception):
  pass


class ServiceStatus(Enum):
  RUNNING   = "running"
  STOPPED   = "stopped"
  CRASHED   = "crashed"
  NOT_FOUND = "service not found"
  UNKNOWN   = "unknown"


class ServiceManager(object):
  functions: Dict[str, Callable]
  sudo: bool

  def __init__(self, init_type: str, sudo: bool = True):
    function_db = {
      "sysvinit": {
        "get_status": ServiceManager._get_status_init,
        "start_service": ServiceManager._start_service_init,
        "stop_service": ServiceManager._stop_service_init,
        "toggle_service": ServiceManager._toggle_service_init
      },
      "systemd": {
        "get_status": ServiceManager._unimplemented_function,
        "start_service": ServiceManager._unimplemented_function,
        "stop_service": ServiceManager._unimplemented_function,
        "toggle_service": ServiceManager._unimplemented_function
      }
    }
    corrected_type = init_type
    if init_type in ['init', 'openrc']:
      corrected_type = "sysvinit"
    if corrected_type in function_db:
      self.functions = function_db[corrected_type]
    else:
      self.functions = function_db["systemd"]
    self.sudo = sudo

  def get_status(self, name: str) -> ServiceStatus:
    return self.functions["get_status"](name, self.sudo)

  def start_service(self, name: str) -> bool:
    return self.functions["start_service"](name, self.sudo)

  def stop_service(self, name: str) -> bool:
    return self.functions["stop_service"](name, self.sudo)

  def toggle_service(self, name: str) -> bool:
    return self.functions["toggle_service"](name, self.sudo)

  @staticmethod
  def _unimplemented_function(a1 = None, a2 = None, a3 = None, a4 = None):
    raise ServiceStatusFunctionUnimplemented

  @staticmethod
  def __create_precommand(name: str, sudo: bool) -> Optional[List[str]]:
    command = []
    if sudo:
      command.append("sudo")
    script = "/etc/init.d/" + name
    if not is_exe(script):
      return None
    return command

  @staticmethod
  def _get_status_init(name: str, sudo: bool) -> ServiceStatus:
    command = ServiceManager.__create_precommand(name, sudo)
    if command is None:
      return ServiceStatus.NOT_FOUND
    command.append("status")

    status_result = subprocess.run(command, capture_output=True)
    status_output = status_result.stdout.decode()

    match = sysvinit_status_parser.match(status_output)
    if match:
      status = match.group(1)
      if status == "started":
        return ServiceStatus.RUNNING
      if status == "stopped":
        return ServiceStatus.STOPPED
      if status == "crashed":
        return ServiceStatus.CRASHED

    return ServiceStatus.UNKNOWN

  @staticmethod
  def __zap_if_crashed(status: ServiceStatus, command: List[str]) -> bool:
    if status == ServiceStatus.CRASHED:
      zap_command = command
      zap_command.append("zap")
      subprocess.run(zap_command)
      return True
    return False

  @staticmethod
  def _start_service_init(name: str, sudo: bool) -> bool:
    command = ServiceManager.__create_precommand(name, sudo)
    if command is None:
      return False

    status = ServiceManager._get_status_init(name, sudo)
    if status == ServiceStatus.RUNNING:
      return True
    elif ServiceManager.__zap_if_crashed(status, command):
      pass
    elif status != ServiceStatus.STOPPED:
      return False

    command.append("start")
    run_result = subprocess.run(command)
    if run_result.returncode != 0:
      return False
    return True

  @staticmethod
  def _stop_service_init(name: str, sudo: bool) -> bool:
    command = ServiceManager.__create_precommand(name, sudo)
    if command is None:
      return False

    status = ServiceManager._get_status_init(name, sudo)
    if status == ServiceStatus.STOPPED:
      return True
    if ServiceManager.__zap_if_crashed(status, command):
      return True
    elif status != ServiceStatus.RUNNING:
      return False

    command.append("stop")
    run_result = subprocess.run(command)
    if run_result.returncode != 0:
      return False
    return True

  @staticmethod
  def _toggle_service_init(name: str, sudo: bool) -> bool:
    status = ServiceManager._get_status_init(name, sudo)
    if status in [ServiceStatus.STOPPED, ServiceStatus.CRASHED]:
      return ServiceManager._start_service_init(name, sudo)
    elif status == ServiceStatus.RUNNING:
      return ServiceManager._stop_service_init(name, sudo)
    return False

