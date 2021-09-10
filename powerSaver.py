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

import concurrent.futures
import curses
import math
import select
import sys
from datetime import datetime, timedelta
from typing import Tuple, List, Dict, Union, Optional

import powerSaver


application_name = "powerSaver"
version = "1.2.0"


def process_color(status: powerSaver.ProcessStatus) -> Tuple[int, int]:
  if status == powerSaver.ProcessStatus.RUNNING:
    return 3, curses.A_NORMAL  # Green
  if status == powerSaver.ProcessStatus.STOPPED:
    return 5, curses.A_NORMAL  # Red
  if status == powerSaver.ProcessStatus.NO_PROC:
    return 2, curses.A_DIM     # Gray
  if status == powerSaver.ProcessStatus.MANY:
    return 4, curses.A_NORMAL  # Yellow
  return 17, curses.A_NORMAL   # Black on Red


def service_color(status: powerSaver.ServiceStatus) -> Tuple[int, int]:
  if status == powerSaver.ServiceStatus.RUNNING:
    return 3, curses.A_NORMAL  # Green
  if status == powerSaver.ServiceStatus.STOPPED:
    return 5, curses.A_NORMAL  # Red
  if status == powerSaver.ServiceStatus.TOGGLED:
    return 4, curses.A_NORMAL  # Yellow
  if status == powerSaver.ServiceStatus.NOT_FOUND:
    return 2, curses.A_DIM     # Gray
  if status == powerSaver.ServiceStatus.CRASHED:
    return 8, curses.A_NORMAL  # Magenta
  if status == powerSaver.ServiceStatus.NO_MODULES:
    return 7, curses.A_NORMAL  # Blue
  return 17, curses.A_NORMAL   # Black on Red


def module_color(status: powerSaver.ModuleStatus) -> Tuple[int, int]:
  if status == powerSaver.ModuleStatus.LOADED:
    return 3, curses.A_NORMAL  # Green
  if status == powerSaver.ModuleStatus.USED:
    return 6, curses.A_NORMAL  # Cyan
  if status == powerSaver.ModuleStatus.NOT_LOADED:
    return 5, curses.A_NORMAL  # Red
  if status == powerSaver.ModuleStatus.PARTIAL:
    return 4, curses.A_NORMAL  # Yellow
  return 17, curses.A_NORMAL   # Black on Red


def service_status_to_module_status(status: powerSaver.ServiceStatus) -> powerSaver.ModuleStatus:
  if status == powerSaver.ServiceStatus.RUNNING:
    return powerSaver.ModuleStatus.USED
  if status == powerSaver.ServiceStatus.STOPPED:
    return powerSaver.ModuleStatus.NEEDS_CHECK
  if status == powerSaver.ServiceStatus.TOGGLED:
    return powerSaver.ModuleStatus.PARTIAL
  if status == powerSaver.ServiceStatus.NOT_FOUND:
    return powerSaver.ModuleStatus.NEEDS_CHECK
  if status == powerSaver.ServiceStatus.CRASHED:
    return powerSaver.ModuleStatus.NEEDS_CHECK
  return powerSaver.ModuleStatus.ERROR


def menu_entry(std_screen: curses.window, y: int, text: str, text_format: Tuple[int, int], offset: int = 0):
  color, attr = text_format
  std_screen.attron(attr)
  std_screen.attron(curses.color_pair(color + offset))
  std_screen.addstr(y, 0, text)
  std_screen.attroff(curses.color_pair(color + offset))
  std_screen.attroff(attr)


def color_offset(check: bool) -> int:
  if check:
    return 8
  return 0


def get_processes_length(processes: List[Dict[str, Union[str, List[str], powerSaver.ProcessStatus]]]) -> int:
  length = 0
  for p in processes:
    if 'status' in p and p['status'] == powerSaver.ProcessStatus.NO_PROC:
      continue
    length += 1
  return length


def battery_percent_color(battery_percent: float) -> int:
  from config import BATTERY_COLOR_LEVELS
  low, mid, high = BATTERY_COLOR_LEVELS
  if battery_percent < low:
    return curses.color_pair(5)  # Red
  elif battery_percent < mid:
    return curses.color_pair(4)  # Yellow
  elif battery_percent < high:
    return curses.color_pair(3)  # Green
  elif battery_percent < 100.0:
    return curses.color_pair(6)  # Cyan
  else:
    return curses.color_pair(1)  # White


def power_use_color(battery_watts: float) -> int:
  from config import POWER_COLOR_LEVELS
  very_low, low, mid, high = POWER_COLOR_LEVELS
  if battery_watts > high:
    return curses.color_pair(8)  # Magenta
  elif battery_watts > mid:
    return curses.color_pair(5)  # Red
  elif battery_watts > low:
    return curses.color_pair(4)  # Yellow
  elif battery_watts > very_low:
    return curses.color_pair(3)  # Green
  else:
    return curses.color_pair(6)  # Cyan


def calculate_menu_thread(processes: List[Dict[str, Union[str, List[str], powerSaver.ProcessStatus]]],
                          services:  List[Dict[str, Union[str, List[str], powerSaver.ServiceStatus]]],
                          modules:   List[Dict[str, Union[str, List[str], powerSaver.ModuleStatus]]],
                          process_manager: powerSaver.ProcessManager,
                          service_manager: powerSaver.ServiceManager,
                          module_manager:  powerSaver.ModuleManager,
                          refresh: int,
                          title: str,
                          last_update_display: datetime,
                          ) -> Tuple[List[Dict[str, Union[str, List[str], powerSaver.ProcessStatus]]],
                                     List[Dict[str, Union[str, List[str], powerSaver.ProcessStatus]]],
                                     List[Dict[str, Union[str, List[str], powerSaver.ServiceStatus]]],
                                     List[Dict[str, Union[str, List[str], powerSaver.ModuleStatus]]],
                                     int]:
  now = datetime.now()
  max_len = len(title)
  for y, p in enumerate(processes):
    max_len = max(len(p["title"]), max_len)
    p_status = set()
    for proc in p["name"]:
      if "cmdline" in p:
        proc_status = process_manager.get_process_status(proc, p["cmdline"])
      else:
        proc_status = process_manager.get_process_status(proc)
      for p_s in proc_status:
        p_status.add(p_s)
    if powerSaver.ProcessStatus.ERROR in p_status:
      p["status"] = powerSaver.ProcessStatus.ERROR
    elif len(p_status) == 0:
      p["status"] = powerSaver.ProcessStatus.NO_PROC
    elif len(p_status) > 1:
      p["status"] = powerSaver.ProcessStatus.MANY
    else:
      p["status"] = p_status.pop()

  active_processes = []
  for p in processes:
    if p["status"] != powerSaver.ProcessStatus.NO_PROC:
      active_processes.append(p)

  for y, s in enumerate(services):
    max_len = max(len(s["title"]), max_len)
    if "status" not in s or last_update_display > now - timedelta(seconds=refresh):
      s["status"] = service_manager.get_status(s["name"])
      if "needs-modules" in s:
        for mod in s["needs-modules"]:
          if module_manager.get_module_status(mod) not in [powerSaver.ModuleStatus.LOADED,
                                                           powerSaver.ModuleStatus.USED]:
            s["status"] = powerSaver.ServiceStatus.NO_MODULES

  for y, m in enumerate(modules):
    max_len = max(len(m["title"]), max_len)
    if "status" not in m or last_update_display > now - timedelta(seconds=refresh):
      status = []
      if "usage-modules" in m and "service" not in m:
        for mod in m["usage-modules"]:
          status.append(module_manager.get_module_status(mod))
      elif "service" in m:
        status.append(service_status_to_module_status(service_manager.get_status(m['service'])))
        if status[0] == powerSaver.ModuleStatus.NEEDS_CHECK:
          status.clear()
          for mod in m["usage-modules"]:
            status.append(module_manager.get_module_status(mod))
      if powerSaver.ModuleStatus.LOADED in status or powerSaver.ModuleStatus.USED in status:
        if powerSaver.ModuleStatus.NOT_LOADED in status:
          m['status'] = powerSaver.ModuleStatus.PARTIAL
        else:
          if powerSaver.ModuleStatus.USED in status:
            m['status'] = powerSaver.ModuleStatus.USED
          else:
            m['status'] = powerSaver.ModuleStatus.LOADED
      else:
        m['status'] = powerSaver.ModuleStatus.NOT_LOADED
  return processes, active_processes, services, modules, max_len


def execute_service_thread(service_manager: powerSaver.ServiceManager, name: str, stop: bool) -> None:
  if stop:
    service_manager.stop_service(name)
  else:
    service_manager.start_service(name)


def cleanup_executive_futures(in_futures: List[concurrent.futures.Future]) -> List[concurrent.futures.Future]:
  output = []
  for f in in_futures:
    if not f.done():
      output.append(f)
  return output


def draw_menu(std_screen: curses.window):
  from config import processes, services, modules, DEBUG, DEFAULT_POWER_SAMPLING_RATE, \
    DEFAULT_REFRESH_RATE, USE_SUDO, REFRESH_MAXIMUM, SYS_CLASS_BATTERY_PATH, INIT_SYSTEM

  poll_object = select.poll()
  poll_object.register(sys.stdin, select.POLLIN)

  k = 0
  cursor_y            = 0
  refresh             = DEFAULT_REFRESH_RATE
  power_sampling_rate = DEFAULT_POWER_SAMPLING_RATE

  effective_power_sampling_rate = power_sampling_rate

  last_update_display = datetime.now() - timedelta(seconds=refresh*2)
  last_update_power   = datetime.now() - timedelta(seconds=power_sampling_rate*2)

  std_screen.clear()
  std_screen.refresh()
  std_screen.nodelay(True)
  curses.curs_set(0)

  with concurrent.futures.ProcessPoolExecutor(max_workers=3) as process_pool:
    futures_type = Optional[concurrent.futures.Future]
    update_menu_structure_future: futures_type = None
    execute_futures: List[concurrent.futures.Future] = []

    # Colors
    if not curses.has_colors():
      Exception("No colors")
    curses.start_color()
    if curses.can_change_color():
      max_col_num = max([curses.COLOR_WHITE, curses.COLOR_CYAN, curses.COLOR_BLACK, curses.COLOR_MAGENTA,
                         curses.COLOR_BLUE, curses.COLOR_RED, curses.COLOR_GREEN, curses.COLOR_YELLOW])
      color_gray = max_col_num + 1
      if color_gray < curses.COLORS:
        curses.init_color(color_gray, 128, 128, 128)
        curses.init_pair(2, color_gray, curses.COLOR_BLACK)
        curses.init_pair(10, color_gray, curses.COLOR_WHITE)
      else:
        curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_BLACK)
        curses.init_pair(10, curses.COLOR_BLACK, curses.COLOR_WHITE)
    else:
      curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_BLACK)
      curses.init_pair(10, curses.COLOR_BLACK, curses.COLOR_WHITE)

    curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)
    curses.init_pair(3, curses.COLOR_GREEN, curses.COLOR_BLACK)
    curses.init_pair(4, curses.COLOR_YELLOW, curses.COLOR_BLACK)
    curses.init_pair(5, curses.COLOR_RED, curses.COLOR_BLACK)
    curses.init_pair(6, curses.COLOR_CYAN, curses.COLOR_BLACK)
    curses.init_pair(7, curses.COLOR_BLUE, curses.COLOR_BLACK)
    curses.init_pair(8, curses.COLOR_MAGENTA, curses.COLOR_BLACK)

    curses.init_pair(9, curses.COLOR_BLACK, curses.COLOR_WHITE)
    curses.init_pair(11, curses.COLOR_GREEN, curses.COLOR_WHITE)
    curses.init_pair(12, curses.COLOR_YELLOW, curses.COLOR_WHITE)
    curses.init_pair(13, curses.COLOR_RED, curses.COLOR_WHITE)
    curses.init_pair(14, curses.COLOR_CYAN, curses.COLOR_WHITE)
    curses.init_pair(15, curses.COLOR_BLUE, curses.COLOR_WHITE)
    curses.init_pair(16, curses.COLOR_MAGENTA, curses.COLOR_WHITE)

    curses.init_pair(17, curses.COLOR_BLACK, curses.COLOR_RED)
    curses.init_pair(17+8, curses.COLOR_BLUE, curses.COLOR_RED)

    process_manager = powerSaver.ProcessManager(USE_SUDO)
    service_manager = powerSaver.ServiceManager(INIT_SYSTEM, USE_SUDO, DEBUG)
    module_manager  = powerSaver.ModuleManager(USE_SUDO)
    power_stats     = powerSaver.PowerStats(refresh, SYS_CLASS_BATTERY_PATH)

    height, width = std_screen.getmaxyx()
    title = f"{application_name} v{version}"
    active_processes: List[Dict[str, Union[str, List[str], powerSaver.ProcessStatus]]] = []
    max_len = len(title)

    first_loop = True
    while k != ord('q'):
      now = datetime.now()

      execute_futures = cleanup_executive_futures(execute_futures)

      if update_menu_structure_future is not None and update_menu_structure_future.done():
        processes, active_processes, services, modules, max_len = update_menu_structure_future.result()

      toggle              = False
      skip_render_menu    = True
      skip_calculate_menu = True
      skip_render_power   = True

      if k == curses.KEY_DOWN:
        cursor_y = cursor_y + 1
      elif k == curses.KEY_UP:
        cursor_y = cursor_y - 1
      elif k == ord('+'):
        refresh += 1
      elif k == ord('-'):
        refresh -= 1
      elif k == ord('.'):
        power_sampling_rate += 1
        if effective_power_sampling_rate == power_sampling_rate:
          effective_power_sampling_rate += 1
      elif k == ord(','):
        power_sampling_rate -= 1
        if effective_power_sampling_rate == power_sampling_rate:
          effective_power_sampling_rate -= 1
      elif k in [curses.KEY_ENTER, ord('\n'), ord(' '), ord('\r')]:
        toggle = True

      # Update caches
      if last_update_display + timedelta(seconds=refresh) < now:
        last_update_display = now
        process_manager.update_processes_information()
        module_manager.update_modules_list()
        skip_render_menu    = False
        skip_calculate_menu = False
      elif k >= 0:
        skip_render_menu = False

      if last_update_power + timedelta(seconds=effective_power_sampling_rate) < now:
        last_update_power = now
        power_stats.refresh_status()
        skip_render_power = False
      elif k != 0:
        skip_render_power = False

      if first_loop:
        skip_render_menu    = False
        skip_render_power   = False
        skip_calculate_menu = False

      if k > 0:
        refresh = max(1, min(refresh, REFRESH_MAXIMUM))
        power_sampling_rate = max(1, min(power_sampling_rate, REFRESH_MAXIMUM))
        skip_render_menu = False

      if not skip_calculate_menu:
        height, width       = std_screen.getmaxyx()

        # Strings
        update_menu_structure_future = process_pool.submit(calculate_menu_thread,
                                                           processes, services, modules,
                                                           process_manager, service_manager, module_manager,
                                                           refresh, title, last_update_display)

        if first_loop:
          processes, active_processes, services, modules, max_len = update_menu_structure_future.result()
        not_found = 0
        for y, s in enumerate(services):
          if s["status"] in [powerSaver.ServiceStatus.NOT_FOUND, powerSaver.ServiceStatus.NO_MODULES]:
            not_found += 1
            if cursor_y - len(active_processes) == y:
              if k == curses.KEY_UP:
                cursor_y -= not_found
              else:
                cursor_y += 1
          else:
            not_found = 0

      if k > 0:
        cursor_y = min(len(active_processes) + len(services) + len(modules) - 1, max(0, cursor_y))

      # Execute action
      error_msg = ""
      if toggle:

        if cursor_y < len(active_processes):  # Processes
          status = active_processes[cursor_y]["status"]
          for name in active_processes[cursor_y]["name"]:
            cmdline_filter = None
            if "cmdline" in active_processes[cursor_y]:
              cmdline_filter = active_processes[cursor_y]["cmdline"]
            if status in [powerSaver.ProcessStatus.STOPPED, powerSaver.ProcessStatus.MANY]:
              process_manager.signal_processes(name, cmdline_filter, False)
            elif status == powerSaver.ProcessStatus.RUNNING:
              process_manager.signal_processes(name, cmdline_filter, True)
        elif cursor_y - len(active_processes) < len(services):  # Services
          cursor = cursor_y - len(active_processes)
          status = services[cursor]["status"]
          if status in [powerSaver.ServiceStatus.STOPPED, powerSaver.ServiceStatus.CRASHED]:
            future = process_pool.submit(execute_service_thread, service_manager, services[cursor]["name"], False)
            execute_futures.append(future)
          elif status == powerSaver.ServiceStatus.RUNNING:
            future = process_pool.submit(execute_service_thread, service_manager, services[cursor]["name"], True)
            execute_futures.append(future)
        elif cursor_y - len(active_processes) - len(services) < len(modules):  # Modules
          cursor = cursor_y - len(active_processes) - len(services)
          status = modules[cursor]["status"]
          if status in [powerSaver.ModuleStatus.LOADED, powerSaver.ModuleStatus.PARTIAL]:
            for module in reversed(modules[cursor]["modules"]):
              module_status = module_manager.get_module_status(module)
              if module_status == powerSaver.ModuleStatus.LOADED:
                module_manager.unload_module(module)
              elif module_status == powerSaver.ModuleStatus.USED and module in modules[cursor]["usage-modules"]:
                error_msg += f"ModUsed({module}) "
          elif status == powerSaver.ModuleStatus.NOT_LOADED:
            for module in modules[cursor]["modules"]:
              module_manager.load_module(module)

      # now = datetime.now()
      # sleep_length_display = last_update_display + timedelta(seconds=refresh) - now
      # sleep_length_power   = last_update_power + timedelta(seconds=power_sampling_rate) - now
      # sleep_length = min(sleep_length_power, sleep_length_display)
      # sleep_length = math.floor(max(0.0, sleep_length.total_seconds()) * 1000)
      # error_msg += f" D={sleep_length_display} P={sleep_length_power} Total={sleep_length/1000.0}"

      if (not skip_render_menu) or (not skip_render_power):
        std_screen.clear()

        # Draw Title
        std_screen.attron(curses.A_BOLD)
        std_screen.addstr(0, 0, title[:width - 1])

        # Divider
        std_screen.addstr(1, 0, "-" * min(width - 1, max_len))
        std_screen.attroff(curses.A_BOLD)

        n = 2
        y_offset = 0

        # Processes
        if len(active_processes) > 0:
          for y, p in enumerate(active_processes):
            offset = color_offset(cursor_y == y)
            menu_entry(std_screen, y + n, p["title"][:width-1], process_color(p["status"]), offset)
          n += len(active_processes)

          # Divider
          std_screen.addstr(n, 0, "-" * min(width - 1, max_len))
          n += 1

        # Services
        if len(services) > 0:
          y_offset = len(active_processes)
          for y, s in enumerate(services):
            offset = color_offset(cursor_y == y + y_offset)
            menu_entry(std_screen, y + n, s["title"][:width-1], service_color(s["status"]), offset)
          n += len(services)

          # Divider
          std_screen.addstr(n, 0, "-" * min(width - 1, max_len))
          n += 1

        # Modules
        if len(modules) > 0:
          y_offset += len(services)
          for y, m in enumerate(modules):
            offset = color_offset(cursor_y == y + y_offset)
            menu_entry(std_screen, y + n, m["title"][:width-1], module_color(m["status"]), offset)

        # Status
        battery_status, battery_percent, battery_watts, battery_h, battery_m = power_stats.get_current_stats()

        if battery_status == powerSaver.BatteryStatus.DISCHARGING:
          effective_power_sampling_rate = power_sampling_rate
        else:
          effective_power_sampling_rate = refresh

        status_msg = powerSaver.FormattedMessage()
        status_msg += [("Q", curses.A_BOLD),
                       ("uit | ", curses.A_NORMAL),
                       ("refresh rate: ", curses.A_NORMAL),
                       ("-", curses.A_BOLD),
                       (f"[{refresh}s]", curses.A_NORMAL),
                       ("+", curses.A_BOLD)]
        if battery_status == powerSaver.BatteryStatus.DISCHARGING:
          status_msg += [(" | power sampling rate: ", curses.A_NORMAL),
                         (",", curses.A_BOLD),
                         (f"[{power_sampling_rate}s]", curses.A_NORMAL),
                         (".", curses.A_BOLD)]
        if DEBUG:
          status_msg += [(" | ", curses.A_NORMAL),
                         (f"cursor: {cursor_y}/{len(active_processes) + len(services) + len(modules) - 1}",
                          curses.color_pair(4)),
                         (" | ", curses.A_NORMAL),
                         (f"k: {k}", curses.color_pair(6)),
                         ]
          # len(active_processes) + len(services) + len(modules) - 1

        # Power Stats
        power_status_msg = powerSaver.FormattedMessage()
        power_status_msg += [("Battery: ", curses.A_NORMAL),
                             (f"{battery_percent:5.1f}%", battery_percent_color(battery_percent)),
                             (f" {battery_status.value}", curses.A_BOLD)]
        if battery_watts > 0.0 and battery_status in [powerSaver.BatteryStatus.CHARGING,
                                                      powerSaver.BatteryStatus.DISCHARGING]:
          power_status_msg += [(" | ", curses.A_NORMAL),
                               (f"{battery_watts:5.2f}", power_use_color(battery_watts)),
                               (f"W ({battery_h:2d}:{battery_m:02d}) ", curses.A_NORMAL)]

        if battery_status == powerSaver.BatteryStatus.DISCHARGING:
          power_load = power_stats.get_power_load()
          if power_load is not None:
            battery_w_1min, battery_w_5min, battery_w_15min = power_load
            if len(status_msg) > len(power_status_msg):
              status_msg_space = ""
              power_status_msg_space = " " * (len(status_msg) - len(power_status_msg))
            else:
              power_status_msg_space = ""
              status_msg_space = " " * (len(power_status_msg) - len(status_msg))

            power_status_msg += [(f"{power_status_msg_space} | ", curses.A_NORMAL),
                                 (f"{battery_w_1min:5.2f}", power_use_color(battery_w_1min)),
                                 ("W ", curses.A_NORMAL),
                                 ("{battery_w_5min:5.2f}", power_use_color(battery_w_5min)),
                                 ("W ", curses.A_NORMAL),
                                 ("{battery_w_15min:5.2f}", power_use_color(battery_w_15min)),
                                 ("W", curses.A_NORMAL)]
            time_est = power_stats.get_time_estimate_h_min()
            if time_est is not None:
              h_1min, m_1min, h_5min, m_5min, h_15min, m_15min = time_est
              status_msg += f"{status_msg_space} | " \
                            f"{h_1min:02d}:{m_1min:02d}  " \
                            f"{h_5min:02d}:{m_5min:02d}  " \
                            f"{h_15min:02d}:{m_15min:02d}"
        if len(error_msg) > 0:
          status_msg += [(" | ", curses.A_NORMAL),
                         (f"{error_msg}", curses.color_pair(5))]
        status_msg += " "*min(0, width - len(status_msg) - 1)
        power_status_msg += " "*min(0, width - len(power_status_msg) - 1)
        status_msg.display(std_screen, height - 1, 0, max_width=width-1)
        power_status_msg.display(std_screen, height - 2, 0, max_width=width-1)

        # Refresh the screen
        std_screen.refresh()

      # calculate sleep length
      now = datetime.now()
      sleep_length_display = last_update_display + timedelta(seconds=refresh) - now
      sleep_length_power = last_update_power + timedelta(seconds=power_sampling_rate) - now
      sleep_length = min(sleep_length_power, sleep_length_display)
      sleep_length = math.floor(max(0.0, sleep_length.total_seconds() * 1000))

      first_loop = False

      # Wait for next input
      poll_object.poll(sleep_length)
      k = std_screen.getch()

    process_pool.shutdown()


if __name__ == '__main__':
  curses.wrapper(draw_menu)
