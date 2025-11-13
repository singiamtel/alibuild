# Modern Terminal Output for alibuild

This document describes the new modern terminal output feature for alibuild, which provides a cleaner and more informative build experience.

## Overview

The modern output format displays:
1. **Fixed header** showing all build steps with real-time timings
2. **Scrolling log area** showing the most recent verbose output (default: 10 lines)

This is similar to modern container CLIs like Docker and Podman, where you can see the overall progress while still monitoring detailed output.

## Example Output

```
==> Building packages (3/8)
    ✓ zlib           2.3s
    ✓ OpenSSL        12.5s
    ⋯ ROOT           45.2s...
    • GEANT3
    • GEANT4
    • AliRoot

─── Build Output ────────────────────────
[ 42%] Building CXX object CMakeFiles/ROOT.dir/src/analysis.cxx.o
Compiling analysis framework...
Linking shared library libROOT.so
Installing ROOT to build directory
[ 43%] Built target ROOT
```

### Status Symbols

- **✓** (green checkmark) - Package built successfully
- **✗** (red X) - Package build failed
- **⋯** (yellow ellipsis) - Package currently building
- **•** (gray bullet) - Package pending

## Usage

### Enable Modern Output

Add the `--modern-output` flag to your build command:

```bash
aliBuild build --modern-output O2
```

### Complete Example

```bash
aliBuild build --modern-output \
  --defaults o2 \
  --jobs 8 \
  O2
```

### With Other Options

```bash
# Modern output with development mode
aliBuild build --modern-output -z devel O2

# Modern output with remote store
aliBuild build --modern-output \
  --remote-store rsync://myserver/alibuild-store \
  O2

# Modern output with Docker
aliBuild build --modern-output \
  --docker \
  --architecture slc9_x86-64 \
  O2
```

## Behavior

### Debug Mode
Modern output is automatically disabled when using `--debug` mode, as debug mode shows all output immediately and is incompatible with the fixed header approach.

```bash
# This will use traditional output (modern output disabled)
aliBuild build --modern-output --debug O2
```

### Non-TTY Environments
Modern output requires a TTY (interactive terminal). It automatically falls back to traditional output when:
- Output is redirected to a file: `aliBuild build --modern-output O2 > build.log`
- Running in CI/CD environments without TTY
- Running in non-interactive shells

### Log Lines Configuration
By default, the modern output shows the last 10 lines of build output. This can be customized by modifying the `max_log_lines` parameter in the code (future versions may expose this as a command-line option).

## Technical Details

### Implementation
The modern output uses only ANSI escape codes for terminal control - no external dependencies:
- Cursor positioning: `\033[{n}A` (move up), `\033[{n}B` (move down)
- Cursor visibility: `\033[?25l` (hide), `\033[?25h` (show)
- Line clearing: `\033[K` (clear to end of line), `\033[J` (clear to end of screen)
- Colors: Standard ANSI color codes (green, red, yellow, gray)

### Files Modified
- `alibuild_helpers/modern_output.py` - New module containing the modern output classes
- `alibuild_helpers/build.py` - Integration into the build process
- `alibuild_helpers/args.py` - Added `--modern-output` command-line flag

### Key Classes

#### `ModernBuildProgress`
Main class managing the terminal output display. Tracks build steps, timings, and log buffer.

#### `ModernProgressPrinter`
Adapter class that mimics the `ProgressPrint` interface, allowing drop-in replacement in existing build code.

#### `BuildStep`
Represents a single build step with timing information and status tracking.

## Demo

A demo script is provided to showcase the modern output without running a full build:

```bash
python3 demo_modern_output.py
```

This simulates building several packages and demonstrates the scrolling log output with fixed header.

## Advantages

1. **Better situational awareness** - See all packages and their status at a glance
2. **Timing information** - Real-time duration for each build step
3. **Cleaner output** - Fixed header doesn't scroll away
4. **Verbose logs available** - Still see recent output for debugging
5. **No external dependencies** - Pure Python with ANSI codes
6. **Graceful fallback** - Automatically uses traditional output when needed

## Future Enhancements

Possible future improvements:
- Command-line option to configure number of log lines
- Collapsible/expandable log sections
- Ability to save full logs to file while showing modern output
- Progress bars for individual package builds
- Estimated time remaining based on historical data
- Color themes and customization options

## Troubleshooting

### Terminal doesn't support ANSI codes
If your terminal doesn't display colors or positioning correctly, use the traditional output (don't use `--modern-output`).

### Output looks garbled
This can happen if:
- Terminal size changes during build
- Terminal doesn't support ANSI escape codes
- Output is piped or redirected

Solution: Don't use `--modern-output` or use a different terminal emulator.

### Want to see all output
Use `--debug` mode instead of `--modern-output`, or redirect stderr to a file:

```bash
aliBuild build --modern-output O2 2> full_build.log
```

## Compatibility

- **Python**: Requires Python 3.6+
- **Terminals**: Works with most modern terminal emulators (xterm, GNOME Terminal, iTerm2, Windows Terminal, etc.)
- **Operating Systems**: Linux, macOS, Windows (with appropriate terminal)
- **alibuild**: Integrated into the main build system

---

**Note**: This feature is designed to improve the user experience during interactive builds. For automated builds, CI/CD pipelines, or when you need complete logs, the traditional output (without `--modern-output`) is recommended.
