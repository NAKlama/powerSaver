import curses
from typing import List, Tuple, Union, Optional


class FormattedMessageAppendDatatypeError(Exception):
  pass


class FormattedMessage:
  message: List[Tuple[str, int]]

  def __init__(self):
    self.message = []

  def append_message(self,
                     msg: Union[List[Tuple[str, int]], Tuple[str, int], str, "FormattedMessage"],
                     attr: Optional[int] = None) -> None:
    if isinstance(msg, list):
      for m in msg:
        self.message.append(m)
    elif isinstance(msg, tuple):
      self.message.append(msg)
    elif isinstance(msg, str):
      if attr is not None:
        self.message.append((msg, attr))
      else:
        self.message.append((msg, curses.A_NORMAL))
    elif isinstance(msg, FormattedMessage):
      for m in msg.message:
        self.message.append(m)
    else:
      FormattedMessageAppendDatatypeError("Please only append the correct data types to a FormattedMessage\n"
                                          "  These are a single: Union[List[Tuple[str, int]], Tuple[str, int], "
                                          "FormattedMessage]\n"
                                          "  Or these two: str, int")

  def display(self, screen: curses.window, y: int, x_in: int,
              max_width: Optional[int] = None,
              restore_format: Optional[List[int]] = None):
    if restore_format is None:
      restore_format = [curses.A_NORMAL, curses.color_pair(1)]
    x = x_in
    for msg, attr in self.message:
      msg_out = msg
      if max_width is not None and x + len(msg) > max_width:
        msg_out = msg_out[:max_width - x]
      screen.addstr(y, x, msg_out, attr)
      x += len(msg)
      if msg != msg_out:
        break
    for attr in restore_format:
      screen.attrset(attr)

  def __len__(self):
    msg_length = 0
    for msg, attr in self.message:
      msg_length += len(msg)
    return msg_length

  def __add__(self,
              other: Union[List[Tuple[str, int]], Tuple[str, int], str, "FormattedMessage"]) -> "FormattedMessage":
    out = FormattedMessage()
    out.append_message(self.message)
    try:
      out.append_message(other.message)
    except FormattedMessageAppendDatatypeError:
      raise FormattedMessageAppendDatatypeError("Please only append the correct data types to a FormattedMessage\n"
                                                "  These are: Union[List[Tuple[str, int]], Tuple[str, int], "
                                                "FormattedMessage]")
    return out

  def __iadd__(self,
               other: Union[List[Tuple[str, int]], Tuple[str, int], str, "FormattedMessage"]) -> "FormattedMessage":
    try:
      self.append_message(other)
    except FormattedMessageAppendDatatypeError:
      raise FormattedMessageAppendDatatypeError("Please only append the correct data types to a FormattedMessage\n"
                                                "  These are: Union[List[Tuple[str, int]], Tuple[str, int], "
                                                "FormattedMessage]")
    return self
