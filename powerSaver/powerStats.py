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

import math
from time import sleep
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Tuple, Optional

import funcy as funcy


class BatteryStatus(Enum):
  FULL        = " "
  CHARGING    = "C"
  DISCHARGING = "D"
  ERROR       = "E"


class PowerStats(object):
  battery_path: Path

  power_load: Tuple[float, float, float]
  refresh: int
  last_refresh: Optional[datetime] = None
  battery_status: BatteryStatus
  charge_full: float
  charge_design: float
  charge_now:  float = 0.0
  voltage_now: float = 0.0
  current_now: float = 0.0
  working: bool

  load_constants: List[List[float]]  # load_constants[delta_t-1][x] x=0 => 1, x=1 => 5, x=2 => 15
  load_constants_max: int

  def __init__(self, refresh: int = 5, battery_path: str = "/sys/class/power_supply/BAT0"):
    self.load_constants = []
    self.__calc_loadconstants(60)
    self.working = True
    self.battery_path = Path(battery_path)
    self.refresh = refresh
    self.power_load = (0.0, 0.0, 0.0)
    if self.battery_path.is_dir():
      self.refresh_status()
      with open(self.battery_path / "charge_full", 'r') as inF:
        self.charge_full = int(inF.readline().strip()) / 1e6
      with open(self.battery_path / "charge_full_design", 'r') as inF:
        self.charge_design = int(inF.readline().strip()) / 1e6
    else:
      self.working = False

  @staticmethod
  def calc_moving_average(in_data: Tuple[float, float, float]) -> float:
    p, l, c = in_data
    return (1.0 - c) * p + c * l

  def __calc_loadconstants(self, maximum: int) -> None:
    delta = maximum - len(self.load_constants)
    self.load_constants_max = maximum
    time_sec = [60.0, 300.0, 900.0]
    for delta_t in range(len(self.load_constants), maximum):
      time_const = funcy.lmap(lambda x: math.exp(-(delta_t + 1) / x), time_sec)
      self.load_constants.append(time_const)

  def refresh_status(self):
    with open(self.battery_path / "status", 'r') as inF:
      battery_status = inF.readline().strip()
      if battery_status == "Full":
        self.battery_status = BatteryStatus.FULL
      elif battery_status == "Discharging":
        self.battery_status = BatteryStatus.DISCHARGING
      elif battery_status == "Charging":
        self.battery_status = BatteryStatus.CHARGING
      else:
        self.battery_status = BatteryStatus.ERROR
    with open(self.battery_path / "charge_now", 'r') as inF:
      self.charge_now = float(inF.readline().strip()) / 1.0e6
    if self.battery_status in [BatteryStatus.CHARGING, BatteryStatus.DISCHARGING]:
      with open(self.battery_path / "voltage_now", 'r') as inF:
        self.voltage_now = float(inF.readline().strip()) / 1.0e6
      with open(self.battery_path / "current_now", 'r') as inF:
        self.current_now = float(inF.readline().strip()) / 1.0e6

    power = self.voltage_now * self.current_now

    if self.battery_status == BatteryStatus.DISCHARGING:
      if self.last_refresh is None:
        self.power_load = (power, power, power)
        time_since_refresh = self.refresh
      else:
        time_since_refresh = int(round((datetime.now() - self.last_refresh).total_seconds()))

      if time_since_refresh > self.load_constants_max:
        self.__calc_loadconstants(time_since_refresh*2)
      self.last_refresh = datetime.now()

      self.power_load = tuple(funcy.map(self.calc_moving_average,
                                        zip((power, power, power),
                                            self.power_load,
                                            self.load_constants[time_since_refresh-1])))
    else:
      self.power_load = (0.0, 0.0, 0.0)
      self.last_refresh = None

  def get_power_load(self) -> Tuple[float, float, float]:
    if self.battery_status == BatteryStatus.CHARGING:
      return self.voltage_now * self.current_now, 0.0, 0.0
    else:
      return self.power_load

  def get_time_estimate_seconds(self) -> Optional[Tuple[int, int, int]]:
    power_load = self.get_power_load()
    amp = tuple(funcy.map(lambda x: float(x / self.voltage_now), power_load))
    if min(min(amp), self.charge_now) > 0.0:
      return tuple(funcy.map(lambda x: round(float(self.charge_now / x)) * 3600.0, amp))
    else:
      return round((self.charge_now / self.current_now)  * 3600.0), 0, 0

  def get_time_estimate_h_min(self) -> Optional[Tuple[int, int, int, int, int, int]]:
    power_load = self.get_power_load()
    amp        = tuple(funcy.map(lambda x: float(x / self.voltage_now), power_load))
    m          = tuple(funcy.map(lambda x: x > 0 and (self.charge_now / x) * 60.0, amp))
    h = tuple(funcy.map(lambda x: math.floor(float(x) / 60.0), m))
    m = tuple(funcy.map(lambda x: round(x[0] - x[1] * 60.0), zip(m, h)))
    return tuple(funcy.flatten(zip(h, m)))

  def get_current_stats(self) -> Tuple[BatteryStatus, float, float, int, int]:
    power = self.voltage_now * self.current_now
    if self.battery_status == BatteryStatus.DISCHARGING and self.current_now > 0.0:
      time = self.charge_now / self.current_now
      h = math.floor(time)
      m = round((time * 60.0) - (h * 60))
    elif self.battery_status == BatteryStatus.CHARGING and self.current_now > 0.0:
      time = (self.charge_full - self.charge_now) / self.current_now
      h = math.floor(time)
      m = math.ceil((time * 60.0) - (h * 60))
    else:
      h = 0
      m = 0
    return self.battery_status, (self.charge_now / self.charge_full) * 100.0, power, h, m


def update_thread(p_s: PowerStats, print_data: bool = False):
  while True:
    p_s.refresh_status()
    if print_data:
      print(f"Status: {p_s.battery_status}")
      power    = p_s.get_power_load()
      if power is not None:
        time_est = p_s.get_time_estimate_h_min()
        if time_est is not None:
          output  = f"{power[0]:5.2f}W {power[1]:5.2f}W {power[2]:5.2f}W\n"
          h_1min, m_1min, h_5min, m_5min, h_15min, m_15min = time_est
          output += f"{h_1min:02d}:{m_1min:02d}  {h_5min:02d}:{m_5min:02d}  {h_15min:02d}:{m_15min:02d}\n"
          print(output)
    sleep(p_s.refresh)


if __name__ == '__main__':
  power_stats = PowerStats(1)
  update_thread(power_stats, True)
