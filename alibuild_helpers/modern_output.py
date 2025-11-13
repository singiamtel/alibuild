"""
Modern terminal output for alibuild.

Provides a fixed header showing build steps with timings, and a scrolling
log area for verbose output. Similar to modern container CLIs.
Uses only ANSI escape codes - no external dependencies.
"""

import sys
import time
import re
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
    Modern terminal output manager for alibuild.

    Shows a fixed header with build steps and timings, and a scrolling
    log area below with the most recent output lines.
    """

    def __init__(self, total_packages: int, max_log_lines: int = 10,
                 enable_modern_output: bool = True):
        """
        Initialize the modern build progress display.

        Args:
            total_packages: Total number of packages to build
            max_log_lines: Maximum number of log lines to show (default 10)
            enable_modern_output: Whether to use modern output (requires TTY)
        """
        self.total_packages = total_packages
        self.max_log_lines = max_log_lines
        self.build_steps: List[BuildStep] = []
        self.current_step: Optional[BuildStep] = None
        self.log_buffer = deque(maxlen=max_log_lines)
        self.is_tty = sys.stdout.isatty()
        self.enabled = enable_modern_output and self.is_tty
        self.header_lines = 0
        self.last_update = 0
        self.update_interval = 0.1  # Update display at most every 100ms

        # ANSI escape codes
        self.CURSOR_UP = "\033[{n}A"
        self.CURSOR_DOWN = "\033[{n}B"
        self.CURSOR_TO_COL = "\033[{col}G"
        self.SAVE_CURSOR = "\033[s"
        self.RESTORE_CURSOR = "\033[u"
        self.CLEAR_LINE = "\033[K"
        self.CLEAR_TO_END = "\033[J"
        self.HIDE_CURSOR = "\033[?25l"
        self.SHOW_CURSOR = "\033[?25h"

        # Status symbols
        self.SYMBOL_DONE = "\033[32m✓\033[m"      # Green checkmark
        self.SYMBOL_FAILED = "\033[31m✗\033[m"    # Red X
        self.SYMBOL_PROGRESS = "\033[33m⋯\033[m"  # Yellow ellipsis
        self.SYMBOL_PENDING = "\033[90m•\033[m"   # Gray bullet

        if self.enabled:
            sys.stderr.write(self.HIDE_CURSOR)
            sys.stderr.flush()

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

        # Extract percentage if present
        percent_match = re.search(r'(\[?\s*(\d+)%\s*\]?)', line)

        # Truncate very long lines
        if len(clean_line) > 200:
            line = clean_line[:197] + "..."

        self.log_buffer.append(line)

        if self.enabled:
            now = time.time()
            # Rate limit updates
            if now - self.last_update > self.update_interval:
                self._render()
                self.last_update = now

    def _get_status_symbol(self, step: BuildStep) -> str:
        """Get the status symbol for a build step."""
        if step.status == BuildStep.STATUS_DONE:
            return self.SYMBOL_DONE
        elif step.status == BuildStep.STATUS_FAILED:
            return self.SYMBOL_FAILED
        elif step.status == BuildStep.STATUS_IN_PROGRESS:
            return self.SYMBOL_PROGRESS
        else:
            return self.SYMBOL_PENDING

    def _format_header(self) -> str:
        """Format the header showing build progress."""
        completed = sum(1 for s in self.build_steps
                       if s.status in (BuildStep.STATUS_DONE, BuildStep.STATUS_FAILED))

        lines = []
        lines.append(f"\033[1;34m==>\033[m \033[1mBuilding packages ({completed}/{self.total_packages})\033[m")

        # Show all build steps with timings
        for step in self.build_steps:
            symbol = self._get_status_symbol(step)
            duration = step.format_duration()
            version_str = f"@{step.version}" if step.version else ""

            if step.status == BuildStep.STATUS_IN_PROGRESS:
                # Animate the in-progress step
                stage_idx = int((time.time() * 2) % 3)
                dots = "." * (stage_idx + 1)
                lines.append(f"    {symbol} {step.name}{version_str}  {duration}{dots}")
            elif duration:
                lines.append(f"    {symbol} {step.name}{version_str}  {duration}")
            else:
                lines.append(f"    {symbol} {step.name}{version_str}")

        return "\n".join(lines)

    def _format_log_section(self) -> str:
        """Format the scrolling log section."""
        if not self.log_buffer:
            return ""

        lines = []
        lines.append("")  # Blank line separator
        lines.append("\033[90m─── Build Output " + "─" * 50 + "\033[m")

        for log_line in self.log_buffer:
            # Truncate if too long
            if len(log_line) > 200:
                log_line = log_line[:197] + "..."
            lines.append(log_line)

        return "\n".join(lines)

    def _render(self):
        """Render the complete display."""
        if not self.enabled:
            return

        # Move cursor back to start of header if we've already drawn
        if self.header_lines > 0:
            sys.stderr.write(self.CURSOR_UP.format(n=self.header_lines))
            sys.stderr.write("\r")

        # Render header and log section
        header = self._format_header()
        log_section = self._format_log_section()

        output = header
        if log_section:
            output += "\n" + log_section

        # Clear to end of screen and write new content
        sys.stderr.write(self.CLEAR_TO_END)
        sys.stderr.write(output)

        # Count lines for next update
        self.header_lines = output.count("\n")

        sys.stderr.flush()

    def cleanup(self):
        """Clean up terminal state."""
        if self.enabled:
            # Move cursor to end
            if self.header_lines > 0:
                sys.stderr.write("\n")
            sys.stderr.write(self.SHOW_CURSOR)
            sys.stderr.flush()

    def __del__(self):
        """Ensure cursor is shown on deletion."""
        self.cleanup()


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
            if msg:
                # Log the final message
                color = "\033[31m" if error else "\033[32m"
                self.modern_progress.log(f"{color}{msg}\033[m")
