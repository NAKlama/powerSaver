# noinspection SpellCheckingInspection
from typing import List, Dict, Union

import powerSaver


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
