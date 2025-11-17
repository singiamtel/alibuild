"""
Modern terminal output for alibuild.

Provides Docker-style output with compact completed steps and streaming
output for the current build step. Uses only ANSI escape codes.
"""

import sys
import time
import re
import signal
import os
from collections import deque
from typing import Optional, List


class BuildStep:
    """Represents a single build step with timing information."""

    STATUS_PENDING = "pending"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_DONE = "done"
    STATUS_FAILED = "failed"

    def __init__(self, name: str, version: str = ""):
        self.name = name
        self.version = version
        self.status = self.STATUS_PENDING
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None

    def start(self):
        """Mark this step as started."""
        self.status = self.STATUS_IN_PROGRESS
        self.start_time = time.time()

    def finish(self, failed: bool = False):
        """Mark this step as completed."""
        self.end_time = time.time()
        self.status = self.STATUS_FAILED if failed else self.STATUS_DONE

    def get_duration(self) -> float:
        """Get the duration of this step in seconds."""
        if self.start_time is None:
            return 0.0
        end = self.end_time if self.end_time is not None else time.time()
        return end - self.start_time

    def format_duration(self) -> str:
        """Format the duration as a human-readable string."""
        duration = self.get_duration()
        if duration == 0:
            return ""
        elif duration < 60:
            return f"{duration:.1f}s"
        elif duration < 3600:
            minutes = int(duration / 60)
            seconds = duration % 60
            return f"{minutes}m {seconds:.0f}s"
        else:
            hours = int(duration / 3600)
            minutes = int((duration % 3600) / 60)
            return f"{hours}h {minutes}m"


class ModernBuildProgress:
    """
    Docker-style terminal output for alibuild builds.

    Shows completed builds as single compact lines, and streams output
    for the currently building package.
    """

    def __init__(self, total_packages: int, max_log_lines: int = 5,
                 enable_modern_output: bool = True):
        """
        Initialize the modern build progress display.

        Args:
            total_packages: Total number of packages to build
            max_log_lines: Maximum number of log lines to show (default 5)
            enable_modern_output: Whether to use modern output (requires TTY)
        """
        self.total_packages = total_packages
        self.max_log_lines = max_log_lines
        self.build_steps: List[BuildStep] = []
        self.current_step: Optional[BuildStep] = None
        self.log_buffer = deque(maxlen=max_log_lines)
        self.is_tty = sys.stderr.isatty()
        self.enabled = enable_modern_output and self.is_tty
        self.last_update = 0
        self.update_interval = 0.1  # Update display at most every 100ms
        self.last_output = ""
        self.terminal_width = 80
        self.needs_redraw = False

        # ANSI escape codes
        self.CLEAR_LINE = "\033[2K"
        self.CLEAR_SCREEN = "\033[2J"
        self.CURSOR_HOME = "\033[H"
        self.HIDE_CURSOR = "\033[?25l"
        self.SHOW_CURSOR = "\033[?25h"
        self.SAVE_CURSOR = "\033[7"
        self.RESTORE_CURSOR = "\033[8"

        # Status symbols and colors
        self.SYMBOL_DONE = "\033[32m✓\033[m"      # Green checkmark
        self.SYMBOL_FAILED = "\033[31m✗\033[m"    # Red X
        self.SYMBOL_BUILDING = "\033[34m⋯\033[m"  # Blue ellipsis
        self.COLOR_DIM = "\033[2m"
        self.COLOR_RESET = "\033[m"
        self.COLOR_BOLD = "\033[1m"

        if self.enabled:
            self._update_terminal_size()
            self._setup_signal_handlers()
            sys.stderr.write(self.HIDE_CURSOR)
            sys.stderr.flush()

    def _setup_signal_handlers(self):
        """Set up signal handlers for terminal resize."""
        try:
            signal.signal(signal.SIGWINCH, self._handle_resize)
        except (AttributeError, ValueError):
            # SIGWINCH not available on this platform or not in main thread
            pass

    def _handle_resize(self, signum, frame):
        """Handle terminal resize signal."""
        self._update_terminal_size()
        self.needs_redraw = True

    def _update_terminal_size(self):
        """Update the cached terminal size."""
        try:
            size = os.get_terminal_size(sys.stderr.fileno())
            self.terminal_width = size.columns
        except (OSError, AttributeError):
            self.terminal_width = 80

    def add_package(self, package_name: str, version: str = "") -> BuildStep:
        """Add a new package to the build queue."""
        step = BuildStep(package_name, version)
        self.build_steps.append(step)
        return step

    def start_package(self, package_name: str, version: str = ""):
        """Start building a package."""
        # Find existing step or create new one
        step = None
        for s in self.build_steps:
            if s.name == package_name:
                step = s
                break

        if step is None:
            step = self.add_package(package_name, version)

        step.start()
        self.current_step = step
        self.log_buffer.clear()

        if self.enabled:
            self._render()

    def finish_package(self, failed: bool = False):
        """Finish the current package."""
        if self.current_step:
            self.current_step.finish(failed)
            self.current_step = None

        if self.enabled:
            self._render()

    def log(self, line: str):
        """Add a log line to the scrolling buffer."""
        if not line:
            return

        # Strip ANSI codes for length calculation
        clean_line = re.sub(r'\033\[[0-9;]*m', '', line)

        # Truncate very long lines to terminal width
        max_len = self.terminal_width - 5  # Leave room for " => " prefix
        if len(clean_line) > max_len:
            line = clean_line[:max_len - 3] + "..."

        self.log_buffer.append(line)

        if self.enabled:
            now = time.time()
            # Rate limit updates
            if now - self.last_update > self.update_interval or self.needs_redraw:
                self._render()
                self.last_update = now

    def _format_step_line(self, step: BuildStep, index: int) -> str:
        """Format a single build step line (Docker-style)."""
        step_num = f"[{index + 1}/{self.total_packages}]"
        version_str = f"@{step.version}" if step.version else ""
        name_with_version = f"{step.name}{version_str}"

        if step.status == BuildStep.STATUS_DONE:
            duration = step.format_duration()
            return f"{self.COLOR_DIM}{step_num}{self.COLOR_RESET} {self.SYMBOL_DONE} {name_with_version} {self.COLOR_DIM}{duration}{self.COLOR_RESET}"
        elif step.status == BuildStep.STATUS_FAILED:
            duration = step.format_duration()
            return f"{self.COLOR_DIM}{step_num}{self.COLOR_RESET} {self.SYMBOL_FAILED} {name_with_version} {self.COLOR_DIM}{duration}{self.COLOR_RESET}"
        elif step.status == BuildStep.STATUS_IN_PROGRESS:
            # Animate with spinner
            spinner_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
            spinner_idx = int((time.time() * 10) % len(spinner_chars))
            spinner = f"\033[36m{spinner_chars[spinner_idx]}\033[m"  # Cyan
            duration = step.format_duration()
            return f"{self.COLOR_DIM}{step_num}{self.COLOR_RESET} {spinner} {self.COLOR_BOLD}{name_with_version}{self.COLOR_RESET} {self.COLOR_DIM}{duration}{self.COLOR_RESET}"
        else:
            # Pending
            return f"{self.COLOR_DIM}{step_num} • {name_with_version}{self.COLOR_RESET}"

    def _format_output(self) -> str:
        """Format the complete output (Docker-style)."""
        lines = []

        # Show all build steps
        for i, step in enumerate(self.build_steps):
            lines.append(self._format_step_line(step, i))

            # Show log output only for the currently building step
            if step == self.current_step and self.log_buffer:
                for log_line in self.log_buffer:
                    # Add " => " prefix like Docker
                    lines.append(f" {self.COLOR_DIM}=>{self.COLOR_RESET} {log_line}")

        return "\n".join(lines)

    def _count_screen_lines(self, text: str) -> int:
        """Count how many screen lines the text will actually take, accounting for wrapping."""
        if not text:
            return 0

        lines = text.split("\n")
        total_screen_lines = 0

        for line in lines:
            # Strip ANSI codes for accurate length calculation
            clean_line = re.sub(r'\033\[[0-9;]*m', '', line)
            line_len = len(clean_line)

            if line_len == 0:
                total_screen_lines += 1
            else:
                # Calculate how many screen lines this logical line takes
                total_screen_lines += (line_len + self.terminal_width - 1) // self.terminal_width

        return total_screen_lines

    def _render(self):
        """Render the complete display."""
        if not self.enabled:
            return

        new_output = self._format_output()

        # Handle terminal resize by doing a more aggressive clear
        if self.needs_redraw and self.last_output:
            # After resize, line wrapping changes, so calculate actual screen lines
            # Use a conservative estimate (double the logical lines, capped at 100)
            estimated_lines = min(self.last_output.count("\n") * 2 + 5, 100)
            sys.stderr.write(f"\033[{estimated_lines}A")
            sys.stderr.write("\r")
            # Clear everything from here down
            sys.stderr.write("\033[J")
            self.needs_redraw = False
        elif self.last_output:
            # Normal case: move cursor to beginning of last output
            num_lines = self.last_output.count("\n")
            if num_lines > 0:
                sys.stderr.write(f"\033[{num_lines}A")
                sys.stderr.write("\r")
            # Clear everything below cursor
            sys.stderr.write("\033[J")

        # Write new output
        sys.stderr.write(new_output)
        sys.stderr.flush()

        self.last_output = new_output

    def cleanup(self):
        """Clean up terminal state."""
        if self.enabled:
            # Move to next line and show cursor
            sys.stderr.write("\n")
            sys.stderr.write(self.SHOW_CURSOR)
            sys.stderr.flush()

    def __del__(self):
        """Ensure cursor is shown on deletion."""
        try:
            self.cleanup()
        except:
            pass


class ModernProgressPrinter:
    """
    Adapter class that mimics the ProgressPrint interface but uses ModernBuildProgress.

    This allows drop-in replacement in the existing execute() calls.
    """

    def __init__(self, modern_progress: ModernBuildProgress, begin_msg: str = ""):
        self.modern_progress = modern_progress
        self.begin_msg = begin_msg
        self.started = False

    def __call__(self, txt: str, *args):
        """Log a line of output."""
        if args:
            txt = txt % args

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
                    self.modern_progress.start_package(package, version)

        self.modern_progress.log(txt)

    def erase(self):
        """No-op for compatibility."""
        pass

    def end(self, msg: str = "", error: bool = False):
        """Finish the current operation."""
        if self.started:
            self.modern_progress.finish_package(failed=error)
