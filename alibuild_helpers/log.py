import logging
import sys
import re
import time
import datetime

def dieOnError(err, msg) -> None:
  if err:
    error("%s", msg)
    sys.exit(1)

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


class ProgressPrinter:
  """
  Progress printer that uses Docker-style output if TTY, otherwise plain debug output.
  """
  def __init__(self, build_progress=None, begin_msg=""):
    self.build_progress = build_progress
    self.begin_msg = begin_msg
    self.started = False

  def __call__(self, txt: str, *args):
    """Log a line of output."""
    if args:
      txt = txt % args

    if self.build_progress:
      # Docker-style output
      if not self.started:
        self.started = True
        # Parse package name from begin_msg if present
        # Format: "Compiling PACKAGE@VERSION" or "Unpacking PACKAGE@VERSION"
        if self.begin_msg:
          match = re.match(r'(?:Compiling|Unpacking)\s+([^@]+)(?:@(.+))?',
                         self.begin_msg)
          if match:
            package = match.group(1)
            version = match.group(2) or ""
            self.build_progress.start_package(package, version)

      self.build_progress.log(txt)
    else:
      # No TTY: just print debug output
      debug(txt)

  def erase(self):
    """No-op for compatibility."""
    pass

  def end(self, msg: str = "", error: bool = False):
    """Finish the current operation."""
    if self.build_progress and self.started:
      self.build_progress.finish_package(failed=error)
    elif msg:
      # No TTY: print the final message
      debug(msg)


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
