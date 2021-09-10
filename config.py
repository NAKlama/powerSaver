# noinspection SpellCheckingInspection
from typing import List, Dict, Union

import powerSaver

# Debugging on or off
DEBUG = False
# DEBUG = True

# Shall we call commands using sudo?
USE_SUDO = False

# What init system are we running
# Valid options: OpenRC
# Planned options: systemd
INIT_SYSTEM = "OpenRC"

# How often to query process and service status, and update menu
DEFAULT_REFRESH_RATE = 5

# How often to query power data while discharging or charging
DEFAULT_POWER_SAMPLING_RATE = 5

# The maximum value the previous ones can be set during runtime
REFRESH_MAXIMUM = 15

# The path pointing to your battery information
SYS_CLASS_BATTERY_PATH = "/sys/class/power_supply/BAT0"

# Thresholds for battery percentage color
#  Red if below [0]
#  Yellow if below [1]
#  Green if below [2]
#  Cyan if below [2] but below 100.0
BATTERY_COLOR_LEVELS = [15.0, 60.0, 95.0]

# Thresholds for battery charge / discharge colors
#  Cyan up to [0]
#  Green up to [1]
#  Yellow up to [2]
#  Red up to [3]
#  Magenta above [3]
POWER_COLOR_LEVELS = [5.0, 8.0, 14.0, 20.0]


# A list of processes to monitor and send STOP and CONT signals to
#
# noinspection SpellCheckingInspection
processes: List[Dict[str, Union[str, List[str], powerSaver.ProcessStatus]]] = [
  {'title': "Chrome",
   'name':  ["chrome"]},
  {'title': "Qutebrowser",
   'name':  ['qutebrowser', 'QtWebEngineProcess']},
  {'title': "Discord",
   'name': ["Discord"]},
  {'title': "JetBrains Toolbox",
   'name': ["jetbrains-toolbox"]},
  {'title': "PyCharm",
   'name': ["java"],
   'cmdline': "PyCharm"},
  {'title': "CLion",
   'name': ["java"],
   'cmdline': "CLion"},
  {'title': "DataGrip",
   'name': ["java"],
   'cmdline': "datagrip"},
  {'title': "LibreOffice",
   'name': ["soffice.bin"]},
  {'title': "Pulse Audio Volume Control",
   'name': ["pavucontrol"]},
  {'title': "Zen Monitor",
   'name': ["zenmonitor"]},
]

# A list of services to monitor and switch on/off
#
# noinspection SpellCheckingInspection
services: List[Dict[str, Union[str, List[str], powerSaver.ServiceStatus]]] = [
  {'title': "Bluetooth",
   'name':  "bluetooth",
   'needs-modules': ['uhid', 'hidp']},
  {'title': "Docker",
   'name':  "docker"},
  {'title': "sshd",
   'name':  "sshd"},
  {'title': "Mosquitto",
   'name':  "mosquitto"},
  {'title': "WiFi",
   'name':  "net.wlo1",
   'needs-modules': ['iwlmvm']},
  {'title': "Ethernet (Builtin)",
   'name':  "net.enp2s0"},
  {'title': "Ethernet (eth0)",
   'name':  "net.eth0",
   'needs-modules': ['cdc_ether', 'r8152']},
]

# A list of modules to monitor and load/unload
#
# noinspection SpellCheckingInspection
modules: List[Dict[str, Union[str, List[str], powerSaver.ModuleStatus]]] = [
  {'title': "Bluetooth",
   'usage-modules': ['uhid', 'hidp'],
   'modules': ['btintel', 'btbcm', 'btrtl', 'btusb', 'hidp', 'uhid'],
   'service': 'bluetooth'},
  {'title': "WiFi",
   'usage-modules': ['iwlmvm'],
   'modules': ['iwlwifi', 'iwlmvm'],
   'service': 'net.wlo1'},
  {'title': "USB-Ethernet",
   'usage-modules': ['cdc_ether', 'r8152'],
   'modules': ['mii', 'r8152', 'usbnet', 'cdc_ether']},

]
