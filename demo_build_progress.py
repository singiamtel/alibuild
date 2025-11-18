#!/usr/bin/env python3
"""
Demo script to showcase the Docker-style terminal output for alibuild.

This simulates a build process with multiple packages to demonstrate:
- Compact single-line completed builds
- Streaming output for currently building package
- Animated spinner for in-progress builds
- Terminal resize handling
"""

import time
import random
from alibuild_helpers.build_progress import BuildProgress

def simulate_package_build(progress, package_name, version, duration=3):
    """Simulate building a package with verbose output."""
    print(f"\n[Starting {package_name}]")
    progress.start_package(package_name, version)

    # Simulate various build output messages
    log_messages = [
        f"Configuring {package_name}...",
        f"Running CMake for {package_name}",
        f"[ 10%] Building CXX object {package_name}/src/main.cpp.o",
        f"[ 25%] Building CXX object {package_name}/src/utils.cpp.o",
        f"Compiling source files...",
        f"[ 42%] Building CXX object {package_name}/src/analysis.cpp.o",
        f"[ 58%] Linking shared library lib{package_name}.so",
        f"[ 75%] Building tests for {package_name}",
        f"[ 90%] Running unit tests",
        f"[100%] Built target {package_name}",
        f"Installing {package_name} to build directory",
        f"Creating symlinks for {package_name}",
        f"Finalizing installation of {package_name}",
    ]

    # Simulate build progress with random delays
    num_messages = random.randint(8, len(log_messages))
    for i in range(num_messages):
        msg = log_messages[i % len(log_messages)]
        progress.log(msg)
        time.sleep(duration / num_messages)

    # Randomly fail sometimes (uncomment to test failures)
    # failed = random.random() < 0.2
    failed = False

    progress.finish_package(failed=failed)
    return not failed


def main():
    """Run the demo."""
    print("=" * 70)
    print("Docker-style Terminal Output Demo for alibuild")
    print("=" * 70)
    print()
    print("This demo shows the Docker-style output format:")
    print("  - Compact completed builds as single lines")
    print("  - Current build with streaming output (last 5 lines)")
    print("  - Animated spinner for in-progress builds")
    print("  - Handles terminal resize gracefully")
    print()
    print("Starting demo in 2 seconds...")
    print()
    time.sleep(2)

    # List of packages to "build"
    packages = [
        ("zlib", "1.2.11"),
        ("OpenSSL", "1.1.1"),
        ("CMake", "3.20.0"),
        ("boost", "1.75.0"),
        ("ROOT", "6.24.00"),
        ("GEANT3", "4.0.0"),
        ("GEANT4", "10.7.2"),
        ("AliRoot", "v5-09-55"),
    ]

    # Create the build progress display
    progress = BuildProgress(
        total_packages=len(packages),
        max_log_lines=5
    )

    # Pre-populate all packages
    for pkg, ver in packages:
        progress.add_package(pkg, ver)

    # Build each package
    all_success = True
    for i, (package, version) in enumerate(packages):
        success = simulate_package_build(progress, package, version, duration=2)
        if not success:
            all_success = False
            break

    # Cleanup
    progress.cleanup()

    # Final message
    print()
    if all_success:
        print("✓ All packages built successfully!")
    else:
        print("✗ Build failed!")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user.")
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
