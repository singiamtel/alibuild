# Modern Terminal Output for alibuild

This document describes the Docker-style terminal output for alibuild, which provides a cleaner and more informative build experience.

## Overview

The modern output format is **enabled by default** for interactive terminal sessions and displays builds in a Docker-like style:
1. **Compact completed builds** as single lines with status, name, and timing
2. **Current build** with streaming output showing the last 5 lines
3. **Animated spinner** for in-progress builds
4. **Automatic terminal resize handling** for smooth experience

Modern output automatically activates when running in a TTY (interactive terminal) and is disabled in debug mode or when output is redirected.

## Example Output

The output looks like this (similar to Docker):

```
[1/8] ✓ zlib@1.2.11 2.3s
[2/8] ✓ OpenSSL@1.1.1 12.5s
[3/8] ⠹ ROOT@6.24.00 45.2s
 => Configuring ROOT build system
 => [ 42%] Building CXX object CMakeFiles/ROOT.dir/src/analysis.cxx.o
 => Compiling analysis framework
 => Linking shared library libROOT.so
 => Installing ROOT to build directory
[4/8] • GEANT3@4.0.0
[5/8] • GEANT4@10.7.2
[6/8] • AliRoot@v5-09-55
```

### Status Symbols

- **✓** (green checkmark) - Package built successfully
- **✗** (red X) - Package build failed
- **⠹** (cyan spinner) - Package currently building (animated)
- **•** (gray bullet) - Package pending

## Usage

### Default Behavior

Modern output is **enabled by default** when you run aliBuild in an interactive terminal:

```bash
# Modern output is automatically used
aliBuild build O2
```

### Complete Example

```bash
# Modern output is active by default in TTY
aliBuild build \
  --defaults o2 \
  --jobs 8 \
  O2
```

### All Standard Options Work

Modern output works seamlessly with all alibuild options:

```bash
# With development mode
aliBuild build -z devel O2

# With remote store
aliBuild build \
  --remote-store rsync://myserver/alibuild-store \
  O2

# With Docker
aliBuild build \
  --docker \
  --architecture slc9_x86-64 \
  O2
```

## Behavior

### Automatic Activation
Modern output is automatically enabled when:
- Running in an interactive terminal (TTY detected)
- **NOT** in debug mode (`--debug` not specified)

### Automatic Fallback to Traditional Output
Modern output automatically falls back to traditional line-by-line output when:
- **Debug mode** is enabled: `aliBuild build --debug O2`
- **Output is redirected** to a file: `aliBuild build O2 > build.log`
- **Running in CI/CD** environments without TTY
- **Non-interactive shells** where stdout is not a TTY

### Log Lines Configuration
By default, the Docker-style output shows the last 5 lines of build output for the currently building package. This can be customized by modifying the `max_log_lines` parameter in the code (future versions may expose this as a command-line option).

## Technical Details

### Implementation
The Docker-style output uses only ANSI escape codes for terminal control - no external dependencies:
- Cursor positioning: `\033[{n}A` (move up n lines)
- Cursor visibility: `\033[?25l` (hide), `\033[?25h` (show)
- Screen clearing: `\033[J` (clear to end of screen)
- Colors: Standard ANSI color codes (green, red, cyan, dim/bold)
- Terminal resize: Uses SIGWINCH signal handler to detect and adapt to terminal size changes
- Unicode spinners: Braille pattern characters for smooth animation

### Files Modified
- `alibuild_helpers/modern_output.py` - New module containing the modern output classes
- `alibuild_helpers/build.py` - Integration into the build process with automatic TTY detection

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
If your terminal doesn't display colors or positioning correctly, the output will automatically fall back to traditional mode when:
- Output is redirected to a file
- Running in a non-TTY environment

If you're in a TTY but experiencing issues, use `--debug` mode to force traditional output.

### Output looks garbled
This can happen if:
- Terminal size changes during build
- Terminal doesn't fully support ANSI escape codes

Solution: Use `--debug` mode to get traditional line-by-line output, or use a different terminal emulator.

### Want to see all output
Use `--debug` mode to see complete verbose output:

```bash
aliBuild build --debug O2
```

Or redirect output to capture everything:

```bash
aliBuild build O2 2> full_build.log
```

## Compatibility

- **Python**: Requires Python 3.6+
- **Terminals**: Works with most modern terminal emulators (xterm, GNOME Terminal, iTerm2, Windows Terminal, etc.)
- **Operating Systems**: Linux, macOS, Windows (with appropriate terminal)
- **alibuild**: Integrated into the main build system

---

**Note**: Modern output is designed for interactive terminal use and automatically activates in TTY environments. For automated builds, CI/CD pipelines, or when output is redirected, traditional line-by-line output is automatically used. You can always force traditional output by using `--debug` mode.
