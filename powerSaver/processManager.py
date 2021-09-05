import subprocess
import string
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Tuple, Set

import psutil

_signal_processes_table = defaultdict(str)
for c in string.ascii_letters:
  _signal_processes_table[c] = c
for c in string.digits:
  _signal_processes_table[c] = c
for c in "_.-+/":
  _signal_processes_table[c] = c


def sanitize_process_name(name: str) -> str:
  return name.translate(_signal_processes_table)


class ProcessManager(object):
  sudo: bool
  processes: Dict[str, List[str]]
  process_names: Set[str]
  processes_updated: datetime

  def __init__(self, sudo: bool = True):
    self.sudo = sudo

  def signal_processes(self, name: str, stop: bool = True) -> bool:
    command = []
    if self.sudo:
      command.append("sudo")
    command.append("killall")
    command.append("-s")
    if stop:
      command.append("SIGSTOP")
    else:
      command.append("SIGCONT")
    command.append(sanitize_process_name(name))
    call_result = subprocess.run(command)
    if call_result.returncode == 0:
      return True
    return False

  def update_processes_information(self):
    self.processes = {}
    self.process_names = set()
    for proc in psutil.process_iter(['name', 'status']):
      self.process_names.add(proc.info["name"])
      if proc.info["name"] not in self.processes:
        self.processes[proc.info["name"]] = []
      self.processes[proc.info["name"]].append(proc.info["status"])

  def get_process_status(self, name: str, partial: bool = False, startswith: bool = False) -> Set[str]:
    output = set()
    if name in self.processes:
      proc_list = [name]
    else:
      proc_list = []

    if partial:
      for pname in self.process_names:
        if name in pname:
          proc_list.append(pname)
    else:
      if startswith:
        for pname in self.process_names:
          if pname.startswith(name):
            proc_list.append(pname)

    for proc in proc_list:
      for status in self.processes[proc]:
        output.add(status)

    return output
