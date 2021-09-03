import subprocess


class ProcessManager(object):
  sudo: bool

  def __init__(self, sudo: bool = True):
    self.sudo = sudo

  def signal_processes(self, name: str, stop: bool = True):
    command = []
    if self.sudo:
      command.append("sudo")
    command.append("killall")
    command.append("-s")
    if stop:
      command.append("SIGSTOP")
    else:
      command.append("SIGCONT")
    command.append(name)
