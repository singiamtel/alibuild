import logging
import sys
import re
import time
import datetime
from collections import deque
from typing import Optional, List, Dict
try:
  from rich.live import Live
  from rich.table import Table
  from rich.console import Console, Group
  from rich.panel import Panel
  from rich.text import Text
  from rich.spinner import Spinner
  RICH_AVAILABLE = True
except ImportError:
  RICH_AVAILABLE = False

def dieOnError(err, msg) -> None:
  if err:
    error("%s", msg)
    sys.exit(1)


class BuildStep:
  """Represents a single build step with status and timing information."""
  def __init__(self, name: str, description: str = ""):
    self.name = name
    self.description = description
    self.status = "pending"  # pending, running, completed, failed
    self.start_time: Optional[float] = None
    self.end_time: Optional[float] = None
    self.progress: Optional[int] = None  # 0-100 percentage

  def start(self) -> None:
    self.status = "running"
    self.start_time = time.time()

  def complete(self, failed: bool = False) -> None:
    self.status = "failed" if failed else "completed"
    self.end_time = time.time()

  def update_progress(self, percent: int) -> None:
    self.progress = percent

  def elapsed_time(self) -> float:
    if self.start_time is None:
      return 0.0
    end = self.end_time if self.end_time else time.time()
    return end - self.start_time

  def get_icon(self) -> str:
    if self.status == "completed":
      return "✓"
    elif self.status == "failed":
      return "✗"
    elif self.status == "running":
      return "⣾"
    else:
      return "○"

  def get_status_text(self) -> str:
    if self.status == "pending":
      return "waiting..."
    elif self.status == "running":
      if self.progress is not None:
        return f"{self.progress}%"
      else:
        return "running..."
    elif self.status == "completed":
      return "done"
    elif self.status == "failed":
      return "failed"
    return ""


class ModernTerminal:
  """
  Modern terminal output manager with rich library.
  Provides a fixed display with build steps overview and scrolling output window.
  """

  def __init__(self, max_output_lines: int = 8, use_classic: bool = False):
    self.max_output_lines = max_output_lines
    self.use_classic = use_classic
    self.enabled = RICH_AVAILABLE and sys.stdout.isatty() and not use_classic
    self.steps: List[BuildStep] = []
    self.output_buffer: deque = deque(maxlen=max_output_lines)
    self.live: Optional[Live] = None
    self.console = Console() if RICH_AVAILABLE else None
    self.current_step_index: Optional[int] = None

  def add_step(self, name: str, description: str = "") -> int:
    """Add a new build step and return its index."""
    step = BuildStep(name, description)
    self.steps.append(step)
    return len(self.steps) - 1

  def start_step(self, step_index: int) -> None:
    """Mark a step as started."""
    if 0 <= step_index < len(self.steps):
      self.steps[step_index].start()
      self.current_step_index = step_index
      self._update_display()

  def complete_step(self, step_index: int, failed: bool = False) -> None:
    """Mark a step as completed or failed."""
    if 0 <= step_index < len(self.steps):
      self.steps[step_index].complete(failed)
      if self.current_step_index == step_index:
        self.current_step_index = None
      self._update_display()

  def update_progress(self, step_index: int, percent: int) -> None:
    """Update the progress percentage for a step."""
    if 0 <= step_index < len(self.steps):
      self.steps[step_index].update_progress(percent)
      self._update_display()

  def append_output(self, line: str) -> None:
    """Add a line to the output buffer."""
    if line.strip():  # Only add non-empty lines
      self.output_buffer.append(line.rstrip())
      self._update_display()

  def start(self) -> None:
    """Start the live display."""
    if self.enabled and self.console:
      self.live = Live(self._create_display(), console=self.console, refresh_per_second=4)
      self.live.start()

  def stop(self) -> None:
    """Stop the live display."""
    if self.live:
      self.live.stop()
      self.live = None

  def _create_display(self):
    """Create the display layout with build steps and output window."""
    if not self.enabled or not self.console:
      return ""

    # Create build steps table
    steps_table = Table(show_header=False, box=None, padding=(0, 1))
    steps_table.add_column("Status", justify="left", width=2)
    steps_table.add_column("Step", justify="left")
    steps_table.add_column("Time", justify="right", width=10)
    steps_table.add_column("Progress", justify="left", width=15)

    for step in self.steps:
      # Icon with color
      icon = Text(step.get_icon())
      if step.status == "completed":
        icon.stylize("bold green")
      elif step.status == "failed":
        icon.stylize("bold red")
      elif step.status == "running":
        icon.stylize("bold yellow")
      else:
        icon.stylize("dim")

      # Step name
      step_text = Text(step.description or step.name)
      if step.status == "completed":
        step_text.stylize("green")
      elif step.status == "failed":
        step_text.stylize("red")
      elif step.status == "running":
        step_text.stylize("bold")
      else:
        step_text.stylize("dim")

      # Timing
      elapsed = step.elapsed_time()
      if elapsed > 0:
        time_text = f"[{elapsed:6.1f}s]"
      else:
        time_text = ""

      # Progress/status
      status_text = step.get_status_text()
      if step.status == "running" and step.progress is not None:
        # Create a simple progress bar
        bar_width = 10
        filled = int(bar_width * step.progress / 100)
        bar = "█" * filled + "░" * (bar_width - filled)
        progress_text = Text(f"[{bar}] {step.progress}%")
        progress_text.stylize("cyan")
      else:
        progress_text = Text(status_text)
        if step.status == "failed":
          progress_text.stylize("red")
        elif step.status == "running":
          progress_text.stylize("yellow")
        else:
          progress_text.stylize("dim")

      steps_table.add_row(icon, step_text, time_text, progress_text)

    # Create output panel
    output_text = "\n".join(self.output_buffer) if self.output_buffer else "(no output yet)"
    output_panel = Panel(
      output_text,
      title=f"Build Output (last {self.max_output_lines} lines)",
      border_style="blue"
    )

    return Group(steps_table, output_panel)

  def _update_display(self) -> None:
    """Update the live display if active."""
    if self.live:
      self.live.update(self._create_display())


class LogFormatter(logging.Formatter):
  def __init__(self, fmtstr) -> None:
    self.fmtstr = fmtstr
    self.COLOR_RESET = "\033[m" if sys.stdout.isatty() else ""
    self.LEVEL_COLORS = { logging.WARNING:  "\033[4;33m",
                          logging.ERROR:    "\033[4;31m",
                          logging.CRITICAL: "\033[1;37;41m",
                          logging.SUCCESS:  "\033[1;32m" } if sys.stdout.isatty() else {}
  def format(self, record):
    record.msg = record.msg % record.args
    if record.levelno == logging.BANNER and sys.stdout.isatty():
      lines = record.msg.split("\n")
      return "\n\033[1;34m==>\033[m \033[1m%s\033[m" % lines[0] + \
             "".join("\n    \033[1m%s\033[m" % x for x in lines[1:])
    elif record.levelno == logging.INFO or record.levelno == logging.BANNER:
      return record.msg
    return "\n".join(self.fmtstr % {
      "asctime": datetime.datetime.now().strftime("%Y-%m-%d@%H:%M:%S"),
      "levelname": (self.LEVEL_COLORS.get(record.levelno, self.COLOR_RESET) +
                    record.levelname + self.COLOR_RESET),
      "message": x,
    } for x in record.msg.split("\n"))


def log_current_package(package, main_package, specs, devel_prefix) -> None:
  """Show PACKAGE as the one currently being processed in future log messages."""
  if logger_handler.level > logging.DEBUG:
    return
  if devel_prefix is not None:
    short_version = devel_prefix
  else:
    short_version = specs[main_package]["commit_hash"]
    if short_version != specs[main_package]["tag"]:
      short_version = short_version[:8]
  logger_handler.setFormatter(LogFormatter(
    "%(asctime)s:%(levelname)s:{}:{}: %(message)s"
    .format(main_package, short_version)
    if package is None else
    "%(asctime)s:%(levelname)s:{}:{}:{}: %(message)s"
    .format(main_package, package, short_version)
  ))


class ProgressPrint:
  def __init__(self, begin_msg="", min_interval=0., step_index: Optional[int] = None,
               modern_terminal: Optional[ModernTerminal] = None) -> None:
    self.count = -1
    self.lasttime = 0
    self.STAGES = ".", "..", "...", "....", ".....", "....", "...", ".."
    self.begin_msg = begin_msg
    self.percent = -1
    self.min_interval = min_interval
    self.last_update = 0
    self.step_index = step_index
    self.modern_terminal = modern_terminal
    self.use_modern = modern_terminal is not None and modern_terminal.enabled

  def __call__(self, txt, *args) -> None:
    now = time.time()
    if (now - self.last_update) < self.min_interval:
      return
    self.last_update = now

    txt %= args

    # If using modern terminal, update it
    if self.use_modern and self.modern_terminal and self.step_index is not None:
      # Extract progress percentage
      m = re.search(r"((^|[^0-9])([0-9]{1,2})%|\[([0-9]+)/([0-9]+)\])", txt)
      if m:
        if m.group(3) is not None:
          percent = int(m.group(3))
        else:
          num = int(m.group(4))
          den = int(m.group(5))
          if num >= 0 and den > 0:
            percent = int(100 * num / den)
          else:
            percent = None
        if percent is not None:
          self.modern_terminal.update_progress(self.step_index, percent)

      # Add output line to the display
      self.modern_terminal.append_output(txt)
      return

    # Classic output mode
    if logger.level <= logging.DEBUG or not sys.stdout.isatty():
      debug(txt)
      return
    if time.time() - self.lasttime < 0.5:
      return
    if self.count == -1 and self.begin_msg:
      sys.stderr.write("\033[1;35m==>\033[m " + self.begin_msg)
    self.erase()
    m = re.search(r"((^|[^0-9])([0-9]{1,2})%|\[([0-9]+)/([0-9]+)\])", txt)
    if m:
      if m.group(3) is not None:
        self.percent = int(m.group(3))
      else:
        num = int(m.group(4))
        den = int(m.group(5))
        if num >= 0 and den > 0:
          self.percent = 100 * num / den
    if self.percent > -1:
      sys.stderr.write(" [%2d%%] " % self.percent)
    self.count = (self.count+1) % len(self.STAGES)
    sys.stderr.write(self.STAGES[self.count])
    self.lasttime = time.time()
    sys.stderr.flush()

  def erase(self) -> None:
    nerase = len(self.STAGES[self.count]) if self.count > -1 else 0
    if self.percent > -1:
      nerase = nerase + 7
    sys.stderr.write("\b"*nerase+" "*nerase+"\b"*nerase)
    sys.stderr.flush()

  def end(self, msg="", error=False):
    # If using modern terminal, just mark step as complete
    if self.use_modern and self.modern_terminal and self.step_index is not None:
      self.modern_terminal.complete_step(self.step_index, failed=error)
      return

    # Classic output mode
    if self.count == -1:
      return
    self.erase()
    if msg:
      sys.stderr.write(": %s%s\033[m" % ("\033[31m" if error else "\033[32m", msg))
    sys.stderr.write("\n")
    sys.stderr.flush()


# Add loglevel BANNER (same as INFO but with more emphasis on ttys)
logging.BANNER = 25
logging.addLevelName(logging.BANNER, "BANNER")
def log_banner(self, message, *args, **kws):
  if self.isEnabledFor(logging.BANNER):
    self._log(logging.BANNER, message, args, **kws)
logging.Logger.banner = log_banner

# Add loglevel SUCCESS (same as ERROR, but green)
logging.SUCCESS = 45
logging.addLevelName(logging.SUCCESS, "SUCCESS")
def log_success(self, message, *args, **kws):
  if self.isEnabledFor(logging.SUCCESS):
    self._log(logging.SUCCESS, message, args, **kws)
logging.Logger.success = log_success

logger = logging.getLogger('alibuild')
logger_handler = logging.StreamHandler()
logger.addHandler(logger_handler)
logger_handler.setFormatter(LogFormatter("%(levelname)s: %(message)s"))

debug = logger.debug
error = logger.error
warning = logger.warning
info = logger.info
banner = logger.banner
success = logger.success

# Global modern terminal instance
# This will be initialized in build.py when the build starts
modern_terminal: Optional[ModernTerminal] = None
