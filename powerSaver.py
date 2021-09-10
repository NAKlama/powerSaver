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

import curses
import select
import sys
from datetime import datetime, timedelta
from typing import Tuple

import powerSaver
from config import processes, services, modules

version = "1.1"


def process_color(status: powerSaver.ProcessStatus) -> Tuple[int, int]:
  if status == powerSaver.ProcessStatus.RUNNING:
    return 3, curses.A_NORMAL
  if status == powerSaver.ProcessStatus.STOPPED:
    return 5, curses.A_NORMAL
  if status == powerSaver.ProcessStatus.NO_PROC:
    return 2, curses.A_DIM
  if status == powerSaver.ProcessStatus.MANY:
    return 4, curses.A_NORMAL
  return 17, curses.A_NORMAL


def service_color(status: powerSaver.ServiceStatus) -> Tuple[int, int]:
  if status == powerSaver.ServiceStatus.RUNNING:
    return 3, curses.A_NORMAL
  if status == powerSaver.ServiceStatus.STOPPED:
    return 5, curses.A_NORMAL
  if status == powerSaver.ServiceStatus.TOGGLED:
    return 4, curses.A_NORMAL
  if status == powerSaver.ServiceStatus.NOT_FOUND:
    return 2, curses.A_DIM
  if status == powerSaver.ServiceStatus.CRASHED:
    return 8, curses.A_NORMAL
  if status == powerSaver.ServiceStatus.NO_MODULES:
    return 7, curses.A_NORMAL
  return 17, curses.A_NORMAL


def module_color(status: powerSaver.ModuleStatus) -> Tuple[int, int]:
  if status == powerSaver.ModuleStatus.LOADED:
    return 3, curses.A_NORMAL
  if status == powerSaver.ModuleStatus.USED:
    return 6, curses.A_NORMAL
  if status == powerSaver.ModuleStatus.NOT_LOADED:
    return 5, curses.A_NORMAL
  if status == powerSaver.ModuleStatus.PARTIAL:
    return 4, curses.A_NORMAL
  return 17, curses.A_NORMAL


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


def draw_menu(std_screen: curses.window):
  poll_object = select.poll()
  poll_object.register(sys.stdin, select.POLLIN)

  k = 0
  # cursor_x = 0
  cursor_y = 0
  refresh  = 5
  last_update = datetime.now() - timedelta(seconds=refresh)

  std_screen.clear()
  std_screen.refresh()
  std_screen.nodelay(True)
  curses.curs_set(0)

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

  process_manager = powerSaver.ProcessManager(False)
  service_manager = powerSaver.ServiceManager("sysvinit", False)
  module_manager  = powerSaver.ModuleManager(False)
  power_stats     = powerSaver.PowerStats(refresh)

  first_run = True
  while k != ord('q'):
    height, width = std_screen.getmaxyx()
    now = datetime.now()

    toggle = False
    skip   = False

    if k == curses.KEY_DOWN:
      cursor_y = cursor_y + 1
    elif k == curses.KEY_UP:
      cursor_y = cursor_y - 1
    elif k == ord('+'):
      refresh += 1
    elif k == ord('-'):
      refresh -= 1
    elif k in [curses.KEY_ENTER, ord('\n'), ord(' '), ord('\r')]:
      toggle = True
    elif not first_run:
      skip = True

    first_run = False

    # Update caches
    if last_update + timedelta(seconds=refresh) < now:
      last_update = now
      process_manager.update_processes_information()
      module_manager.update_modules_list()
      power_stats.refresh_status()

      skip = False
    # elif k == curses.KEY_RIGHT:
    #   cursor_x = cursor_x + 1
    # elif k == curses.KEY_LEFT:
    #   cursor_x = cursor_x - 1

    # cursor_x = max(0, cursor_x)
    # cursor_x = min(width - 1, cursor_x)

    if not skip:
      cursor_y = max(0, cursor_y)
      cursor_y = min(min(height - 1, len(processes) + len(services) + len(modules) - 1), cursor_y)
      refresh  = max(0, min(refresh, 15))

    # Strings
    title = f"powerSaver v{version}"[:width-1]
    status_msg = f"refresh rate -({refresh}s)+ | cursor: {cursor_y}"[:width-1]

    # Power Stats
    battery_status, battery_percent, battery_watts, battery_h, battery_m = power_stats.get_current_stats()
    power_status_msg = f"Battery: {battery_percent:5.1f}% {battery_status.value}"
    if battery_watts > 0.0 and battery_status in [powerSaver.BatteryStatus.CHARGING,
                                                  powerSaver.BatteryStatus.DISCHARGING]:
      power_status_msg += f" | {battery_watts:5.2f}W ({battery_h:2d}:{battery_m:02d}) "
    if battery_status == powerSaver.BatteryStatus.DISCHARGING:
      power_load = power_stats.get_power_load()
      if power_load is not None:
        battery_w_1min, battery_w_5min, battery_w_15min = power_load
        power_status_msg_len = len(power_status_msg) + 3
        power_status_msg += f" | {battery_w_1min:5.2f}W {battery_w_5min:5.2f}W {battery_w_15min:5.2f}W"
        status_msg_space = " " * (power_status_msg_len - len(status_msg))
        time_est = power_stats.get_time_estimate_h_min()
        if time_est is not None:
          h_1min, m_1min, h_5min, m_5min, h_15min, m_15min = time_est
          status_msg += f"{status_msg_space}" \
                        f"{h_1min:02d}:{m_1min:02d}  " \
                        f"{h_5min:02d}:{m_5min:02d}  " \
                        f"{h_15min:02d}:{m_15min:02d}"

    max_len = len(title)
    no_proc = 0
    for y, p in enumerate(processes):
      p["display_title"] = p["title"][:width-1]
      max_len = max(len(p["display_title"]), max_len)
      p_status = set()
      for proc in p["name"]:
        if "cmdline" in p:
          proc_status = process_manager.get_process_status(proc, p["cmdline"])
        else:
          proc_status = process_manager.get_process_status(proc)
        for p_s in proc_status:
          p_status.add(p_s)
      if len(p_status) > 0:
        no_proc = 0
      if powerSaver.ProcessStatus.ERROR in p_status:
        p["status"] = powerSaver.ProcessStatus.ERROR
      elif len(p_status) == 0:
        no_proc += 1
        p["status"] = powerSaver.ProcessStatus.NO_PROC
        if cursor_y == y:
          if k == curses.KEY_UP:
            cursor_y -= no_proc
          else:
            cursor_y += 1
      elif len(p_status) > 1:
        p["status"] = powerSaver.ProcessStatus.MANY
      else:
        p["status"] = p_status.pop()
    not_found = 0
    for y, s in enumerate(services):
      s["display_title"] = s["title"][:width-1]
      max_len = max(len(s["display_title"]), max_len)
      if "status" not in s or last_update > now - timedelta(seconds=refresh):
        s["status"] = service_manager.get_status(s["name"])
        if "needs-modules" in s:
          for mod in s["needs-modules"]:
            if module_manager.get_module_status(mod) not in [powerSaver.ModuleStatus.LOADED,
                                                             powerSaver.ModuleStatus.USED]:
              s["status"] = powerSaver.ServiceStatus.NO_MODULES
      if s["status"] in [powerSaver.ServiceStatus.NOT_FOUND, powerSaver.ServiceStatus.NO_MODULES]:
        not_found += 1
        if cursor_y - len(processes) == y:
          if k == curses.KEY_UP:
            cursor_y -= not_found
          else:
            cursor_y += 1
      else:
        not_found = 0
    for y, m in enumerate(modules):
      m["display_title"] = m["title"][:width-1]
      max_len = max(len(m["display_title"]), max_len)
      if "status" not in m or last_update > now - timedelta(seconds=refresh):
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

    if not skip:
      # Execute action
      error_msg = ""
      if toggle:
        if cursor_y < len(processes):
          status = processes[cursor_y]["status"]
          for name in processes[cursor_y]["name"]:
            cmdline_filter = None
            if "cmdline" in processes[cursor_y]:
              cmdline_filter = processes[cursor_y]["cmdline"]
            if status in [powerSaver.ProcessStatus.STOPPED, powerSaver.ProcessStatus.MANY]:
              process_manager.signal_processes(name, cmdline_filter, False)
            elif status == powerSaver.ProcessStatus.RUNNING:
              process_manager.signal_processes(name, cmdline_filter, True)
        elif cursor_y - len(processes) < len(services):  # Services
          cursor = cursor_y - len(processes)
          status = services[cursor]["status"]
          if status in [powerSaver.ServiceStatus.STOPPED, powerSaver.ServiceStatus.CRASHED]:
            service_manager.start_service(services[cursor]["name"])
            services[cursor]["status"] = powerSaver.ServiceStatus.TOGGLED
          elif status == powerSaver.ServiceStatus.RUNNING:
            service_manager.stop_service(services[cursor]["name"])
            services[cursor]["status"] = powerSaver.ServiceStatus.TOGGLED
        elif cursor_y - len(processes) - len(services) < len(modules):  # Modules
          cursor = cursor_y - len(processes) - len(services)
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

      std_screen.clear()

      # Draw Title
      std_screen.attron(curses.A_BOLD)
      std_screen.addstr(0, 0, title)

      # Divider
      std_screen.addstr(1, 0, "-" * min(width - 1, max_len))
      std_screen.attroff(curses.A_BOLD)

      n = 2
      y_offset = 0

      # Processes
      if len(processes) > 0:
        for y, p in enumerate(processes):
          offset = color_offset(cursor_y == y)
          menu_entry(std_screen, y + n, p["display_title"], process_color(p["status"]), offset)
        n += len(processes)

        # Divider
        std_screen.addstr(n, 0, "-" * min(width - 1, max_len))
        n += 1

      # Services
      if len(services) > 0:
        y_offset = len(processes)
        for y, s in enumerate(services):
          offset = color_offset(cursor_y == y + y_offset)
          menu_entry(std_screen, y + n, s["display_title"], service_color(s["status"]), offset)
        n += len(services)

        # Divider
        std_screen.addstr(n, 0, "-" * min(width - 1, max_len))
        n += 1

      # Modules
      if len(modules) > 0:
        y_offset += len(services)
        for y, m in enumerate(modules):
          offset = color_offset(cursor_y == y + y_offset)
          menu_entry(std_screen, y + n, m["display_title"], module_color(m["status"]), offset)

      # Status
      if len(error_msg) > 0:
        status_msg = f"{status_msg} | {error_msg}"[:width-1]
      std_screen.addstr(height - 1, 0, status_msg)
      std_screen.addstr(height - 2, 0, power_status_msg)

      # Refresh the screen
      std_screen.refresh()

    # Wait for next input
    poll_object.poll(refresh * 1000)
    k = std_screen.getch()


if __name__ == '__main__':
  curses.wrapper(draw_menu)
