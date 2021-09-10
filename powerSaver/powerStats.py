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


class BatteryStatus(Enum):
  FULL        = " "
  CHARGING    = "C"
  DISCHARGING = "D"
  ERROR       = "E"


class PowerStats(object):
  battery_path: Path

  power_usage: List[float]
  refresh: int
  last_refresh: Optional[datetime] = None
  battery_status: BatteryStatus
  charge_full: float
  charge_design: float
  charge_now:  float = 0.0
  voltage_now: float = 0.0
  current_now: float = 0.0
  working: bool

  def __init__(self, refresh: int = 5):
    self.working = True
    self.battery_path = Path("/sys/class/power_supply/BAT0")
    self.refresh = refresh
    self.power_usage = []
    if self.battery_path.is_dir():
      self.refresh_status()
      with open(self.battery_path / "charge_full", 'r') as inF:
        self.charge_full = int(inF.readline().strip()) / 1e6
      with open(self.battery_path / "charge_full_design", 'r') as inF:
        self.charge_design = int(inF.readline().strip()) / 1e6
    else:
      self.working = False

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
      self.charge_now = float(inF.readline().strip()) / 1e6
    if self.battery_status in [BatteryStatus.CHARGING, BatteryStatus.DISCHARGING]:
      with open(self.battery_path / "voltage_now", 'r') as inF:
        self.voltage_now = float(inF.readline().strip()) / 1e6
      with open(self.battery_path / "current_now", 'r') as inF:
        self.current_now = float(inF.readline().strip()) / 1e6

    if self.battery_status == BatteryStatus.DISCHARGING:
      if self.last_refresh is None:
        self.power_usage = []
        time_since_refresh = self.refresh
      else:
        time_since_refresh = int(round((datetime.now() - self.last_refresh).total_seconds()))
      self.last_refresh = datetime.now()
      if len(self.power_usage) > 900 - time_since_refresh:
        self.power_usage = self.power_usage[-900 - time_since_refresh:]
      for i in range(time_since_refresh):
        self.power_usage.append(self.voltage_now * self.current_now)
    else:
      self.power_usage = []
      self.last_refresh = None

  def get_power_load(self) -> Optional[Tuple[float, float, float]]:
    datapoints = len(self.power_usage)
    if datapoints > 0:
      datapoints_1min  = min(60, datapoints)
      datapoints_5min  = min(300, datapoints)
      datapoints_15min = min(900, datapoints)
      power_1min  = sum(self.power_usage[datapoints - datapoints_1min:])  / datapoints_1min
      power_5min  = sum(self.power_usage[datapoints - datapoints_5min:])  / datapoints_5min
      power_15min = sum(self.power_usage) / datapoints_15min
      return power_1min, power_5min, power_15min
    elif self.battery_status == BatteryStatus.CHARGING:
      return self.voltage_now * self.current_now, 0.0, 0.0
    return None

  def get_time_estimate_seconds(self) -> Optional[Tuple[int, int, int]]:
    power_load = self.get_power_load()
    if power_load is not None:
      power_1min, power_5min, power_15min = power_load
      amp_1min  = power_1min  / self.voltage_now
      amp_5min  = power_5min  / self.voltage_now
      amp_15min = power_15min / self.voltage_now
      if min(amp_1min, amp_5min, amp_15min, self.charge_now) > 0.0:
        seconds_1min  = round((self.charge_now / amp_1min)  * 3600.0)
        seconds_5min  = round((self.charge_now / amp_5min)  * 3600.0)
        seconds_15min = round((self.charge_now / amp_15min) * 3600.0)
        return seconds_1min, seconds_5min, seconds_15min
      elif self.current_now > 0.0:
        return round((self.charge_now / self.current_now)  * 3600.0), 0, 0
    return None

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
      print(f"Points: {len(p_s.power_usage)} Status: {p_s.battery_status}")
      power    = p_s.get_power_load()
      if power is not None:
        time_est = p_s.get_time_estimate_seconds()
        if time_est is not None:
          output  = f"{power[0]:5.2f}W {power[1]:5.2f}W {power[2]:5.2f}W\n"
          h_1min  = math.floor(time_est[0] / 3600.0)
          m_1min  = round(time_est[0] / 60.0 - (h_1min * 60))
          h_5min  = math.floor(time_est[1] / 3600.0)
          m_5min  = round(time_est[1] / 60.0 - (h_5min * 60))
          h_15min = math.floor(time_est[2] / 3600.0)
          m_15min = round(time_est[2] / 60.0 - (h_15min * 60))
          output += f"{h_1min:02d}:{m_1min:02d}  {h_5min:02d}:{m_5min:02d}  {h_15min:02d}:{m_15min:02d}\n"
          print(output)
    sleep(p_s.refresh)


if __name__ == '__main__':
  power_stats = PowerStats(1)
  update_thread(power_stats, True)
