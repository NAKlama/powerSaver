from pathlib import Path
from typing import Dict, Any, Tuple, List, Union
import powerSaver

try:
  from yaml import CLoader as Loader
except ImportError:
  from yaml import Loader

import yaml


class ConfigError(Exception):
  pass


class ConfigParser(object):
  data: Dict[str, Any]

  def __init__(self, config_file_path: Path):
    self.data = yaml.load(config_file_path.open("r"), Loader=Loader)

  def debug(self) -> bool:
    if 'debug' in self.data:
      return self.data['debug']
    return False

  def use_sudo(self) -> bool:
    if 'use_sudo' in self.data:
      return self.data['use_sudo']

  def init_system(self) -> str:
    if 'init_system' in self.data:
      return self.data['init_system']
    return "init"

  def refresh(self) -> Tuple[int, int, int]:
    default = 5
    power_default = 5
    maximum = 15
    if 'refresh' in self.data:
      if 'default' in self.data['refresh']:
        default = int(self.data['refresh']['default'])
      if 'power_default' in self.data['refresh']:
        power_default = int(self.data['refresh']['power_default'])
      if 'maximum' in self.data['refresh']:
        maximum = int(self.data['refresh']['maximum'])
    return default, power_default, maximum

  def power_sys_class_path(self) -> str:
    path_str = "/sys/class/power_supply/BAT0"
    if 'power' in self.data and 'sys_class_path' in self.data['power']:
      path_str = self.data['power']['sys_class_path']
    return path_str

  def battery_colors(self) -> Tuple[int, int, int]:
    b_min = 15.0
    b_med = 60.0
    b_max = 95.0
    if 'power' in self.data and 'colors' in self.data['power'] and 'battery' in self.data['power']['colors']:
      bat_data = self.data['power']['colors']['battery']
      if len(bat_data) != 3:
        raise ConfigError("power.colors.battery needs exactly three values")
      b_min = bat_data[0]
      b_med = bat_data[1]
      b_max = bat_data[2]
    return b_min, b_med, b_max

  def power_colors(self) -> Tuple[int, int, int, int]:
    p_low = 5.0
    p_min = 8.0
    p_med = 14.0
    p_max = 20.0
    if 'power' in self.data and 'colors' in self.data['power'] and 'power' in self.data['power']['colors']:
      pow_data = self.data['power']['colors']['power']
      if len(pow_data) != 4:
        raise ConfigError("power.colors.power needs exactly four values")
      p_low = pow_data[0]
      p_min = pow_data[1]
      p_med = pow_data[2]
      p_max = pow_data[3]
    return p_low, p_min, p_med, p_max

  def processes(self) -> List[Dict[str, Union[str, List[str], powerSaver.ProcessStatus]]]:
    if 'processes' in self.data:
      return self.data['processes']
    return []

  def services(self) -> List[Dict[str, Union[str, List[str], powerSaver.ServiceStatus]]]:
    if 'services' in self.data:
      return self.data['services']
    return []

  def modules(self) -> List[Dict[str, Union[str, List[str], powerSaver.ModuleStatus]]]:
    if 'modules' in self.data:
      return self.data['modules']
    return []
