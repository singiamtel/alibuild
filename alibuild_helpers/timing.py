"""Build timing instrumentation for alibuild."""

import time
from collections import defaultdict
from alibuild_helpers.log import info, success, banner


class BuildTimer:
    """Track timing information for build operations."""

    def __init__(self):
        self.start_time = time.time()
        self.phase_times = {}
        self.package_times = {}
        self.current_phase_start = None
        self.current_package_start = None
        self.current_package = None

    def start_phase(self, phase_name):
        """Start timing a build phase."""
        self.current_phase_start = time.time()
        return self.current_phase_start

    def end_phase(self, phase_name):
        """End timing a build phase and record the duration."""
        if self.current_phase_start is not None:
            duration = time.time() - self.current_phase_start
            self.phase_times[phase_name] = duration
            self.current_phase_start = None
            return duration
        return 0

    def start_package(self, package_name):
        """Start timing a package build."""
        self.current_package = package_name
        self.current_package_start = time.time()
        if package_name not in self.package_times:
            self.package_times[package_name] = {"total": 0, "phases": {}}

    def end_package(self, package_name):
        """End timing a package build."""
        if (
            self.current_package_start is not None
            and package_name in self.package_times
        ):
            duration = time.time() - self.current_package_start
            self.package_times[package_name]["total"] = duration
            self.current_package_start = None
            self.current_package = None
            return duration
        return 0

    def record_package_phase(self, package_name, phase_name, duration):
        """Record timing for a specific phase of a package build."""
        if package_name not in self.package_times:
            self.package_times[package_name] = {"total": 0, "phases": {}}
        self.package_times[package_name]["phases"][phase_name] = duration

    def record_package_metadata(self, package_name, **metadata):
        """Record metadata about a package build (e.g., skipped, cached)."""
        if package_name not in self.package_times:
            self.package_times[package_name] = {"total": 0, "phases": {}}
        self.package_times[package_name].update(metadata)

    def print_summary(self):
        """Print a comprehensive timing summary."""
        total_time = time.time() - self.start_time

        banner("Build Timing Summary")
        success(
            "Total build time: %.1f seconds (%.1f minutes)", total_time, total_time / 60
        )
        info("")

        if self.phase_times:
            info("Global phase timings:")
            for phase, duration in self.phase_times.items():
                info("  %-25s: %7.1f s", phase, duration)
            info("")

        if self.package_times:
            info("Per-package timings:")
            for pkg, data in self.package_times.items():
                total = data.get("total", 0)
                skipped = data.get("skipped", False)
                cached = data.get("cached", False)
                already_built = data.get("already_built", False)

                if already_built:
                    info("  %-30s: %7.1f s (already built)", pkg, total)
                elif skipped:
                    info("  %-30s: %7.1f s (skipped)", pkg, total)
                elif cached:
                    info("  %-30s: %7.1f s (unpacked from cache)", pkg, total)
                else:
                    info("  %-30s: %7.1f s", pkg, total)

                # Print phase breakdown
                phases = data.get("phases", {})
                if phases:
                    for phase_name, phase_duration in sorted(phases.items()):
                        if phase_duration > 0.1:  # Only show phases > 100ms
                            info("      %-21s: %7.1f s", phase_name, phase_duration)

            info("")

            # Calculate summary statistics
            total_package_time = sum(
                d.get("total", 0) for d in self.package_times.values()
            )

            # Sum up specific phases across all packages
            phase_totals = defaultdict(float)
            for pkg_data in self.package_times.values():
                for phase_name, duration in pkg_data.get("phases", {}).items():
                    phase_totals[phase_name] += duration

            success("Aggregate statistics:")
            success("  Total package processing time: %.1f s", total_package_time)

            if phase_totals:
                for phase_name in sorted(phase_totals.keys()):
                    if phase_totals[phase_name] > 0.1:
                        success(
                            "  Total %-25s: %.1f s",
                            phase_name,
                            phase_totals[phase_name],
                        )


# Global timer instance
_timer = None


def get_timer():
    """Get or create the global timer instance."""
    global _timer
    if _timer is None:
        _timer = BuildTimer()
    return _timer


def reset_timer():
    """Reset the global timer."""
    global _timer
    _timer = BuildTimer()
