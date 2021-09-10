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
import string
from copy import copy
from datetime import datetime
from enum import Enum
from typing import Dict, List, Tuple, Set

import psutil

_signal_processes_table = []
for c in string.ascii_letters:
  _signal_processes_table.append(c)
for c in string.digits:
  _signal_processes_table.append(c)
for c in "_.-+/":
  _signal_processes_table.append(c)


def sanitize_process_name(name: str) -> str:
  output = ""
  for c in name:
    if c in _signal_processes_table:
      output += c
  return output


class ProcessStatus(Enum):
  RUNNING = 0
  STOPPED = 1
  NO_PROC = 2
  MANY    = 3
  ERROR   = 100


class ProcessManager(object):
  sudo: bool
  processes: Dict[str, List[Tuple[int, str, str]]]
  processes_updated: datetime

  def __init__(self, sudo: bool = True):
    self.sudo = sudo
    self.update_processes_information()

  def signal_processes(self, name: str, cmdline_filter: str = None, stop: bool = True) -> bool:
    command = []
    call_results = []
    if self.sudo:
      command.append("sudo")
    command.append("kill")
    command.append("-s")
    if stop:
      command.append("SIGSTOP")
    else:
      command.append("SIGCONT")
    self.update_processes_information()
    for pid, cmdline_list, status in self.processes[name]:
      run_command = copy(command)
      run_command.append(str(pid))
      if cmdline_filter is None:
        call_result = subprocess.run(run_command, capture_output=True)
        call_results.append(call_result.returncode)
      else:
        for cmdline in cmdline_list:
          if cmdline_filter in cmdline:
            call_result = subprocess.run(run_command, capture_output=True)
            call_results.append(call_result.returncode)

    if sum(call_results) == 0:
      return True
    return False

  def update_processes_information(self):
    self.processes = {}
    for proc in psutil.process_iter(['name', 'pid', 'cmdline', 'status']):
      if proc.info["name"] not in self.processes:
        self.processes[proc.info["name"]] = []
      self.processes[proc.info["name"]].append((proc.info["pid"],
                                                proc.info["cmdline"],
                                                proc.info["status"]))

  @staticmethod
  def decode_status(status: str) -> ProcessStatus:
    if status == psutil.STATUS_STOPPED:
      return ProcessStatus.STOPPED
    if status in [psutil.STATUS_DEAD, psutil.STATUS_ZOMBIE]:
      return ProcessStatus.ERROR
    return ProcessStatus.RUNNING

  def get_process_status(self, name: str,
                         cmdline_filter: str = None) -> Set[ProcessStatus]:
    output = set()
    if name in self.processes:
      proc = name
    else:
      return set()

    for pid, cmdline_list, status in self.processes[proc]:
      if cmdline_filter is not None:
        for cmdline in cmdline_list:
          if cmdline_filter in cmdline:
            output.add(ProcessManager.decode_status(status))
      else:
        output.add(ProcessManager.decode_status(status))

    return output
