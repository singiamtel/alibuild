#!/usr/bin/env python3
"""
Simple test script to demonstrate the modern terminal output functionality.
This simulates a build process with multiple steps and shows how the modern
terminal display updates in real-time.
"""

import sys
import time
import os

# Add the alibuild_helpers to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from alibuild_helpers.log import ModernTerminal

def test_modern_terminal():
    """Test the modern terminal with a simulated build process."""

    # Create modern terminal instance
    terminal = ModernTerminal(max_output_lines=8, use_classic=False)

    # Add build steps
    steps = [
        ("zlib", "Building zlib@1.2.11"),
        ("openssl", "Building openssl@1.1.1"),
        ("python", "Building python@3.9.0"),
        ("ROOT", "Building ROOT@v6-28-00"),
    ]

    step_indices = {}
    for name, desc in steps:
        step_indices[name] = terminal.add_step(name, desc)

    # Start the display
    terminal.start()

    # Simulate building each package
    for name, _ in steps:
        step_idx = step_indices[name]
        terminal.start_step(step_idx)

        # Simulate some build output
        outputs = [
            f"Configuring {name}...",
            f"Running cmake for {name}",
            f"[ 10%] Building CXX object src/main.o",
            f"[ 25%] Building CXX object src/utils.o",
            f"[ 50%] Linking CXX library lib{name}.so",
            f"[ 75%] Building tests",
            f"[ 90%] Installing files",
            f"[100%] Build complete",
        ]

        for i, output in enumerate(outputs):
            terminal.append_output(output)
            # Update progress
            progress = int((i + 1) * 100 / len(outputs))
            terminal.update_progress(step_idx, progress)
            time.sleep(0.3)  # Simulate build time

        # Mark step as complete
        terminal.complete_step(step_idx, failed=False)
        time.sleep(0.2)

    # Stop the display
    time.sleep(1)  # Let user see the final state
    terminal.stop()

    print("\n✓ Test completed successfully!")

if __name__ == "__main__":
    # Check if rich is available
    try:
        import rich
        print("Rich library is available. Starting test...\n")
        test_modern_terminal()
    except ImportError:
        print("Rich library not installed. Install it with: pip install rich")
        print("Falling back to classic output mode would be used in alibuild.")
        sys.exit(1)
