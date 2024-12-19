# Advanced Scene Switcher

## Overview
The Advanced Scene Switcher is an OBS Studio plugin that enables automated switching between predefined groups of scenes. It allows users to organize scenes into groups, set a timer for automatic switching, and manage these groups through a simple user interface.

## Features
- Organize scenes into user-defined groups.
- Automatically switch between scenes in a group at specified intervals.
- Enable or disable the plugin through the OBS UI.
- Error handling and logging for smooth operation.
- Persistent storage of scene groups using JSON configuration files.

## Requirements
- OBS Studio
- Qt Framework
- JSON for Modern C++ (https://github.com/nlohmann/json)
- C++17-compatible compiler
- Platform-specific build tools (e.g., `cmake`, `make`, etc.)

## Installation
1. Clone this repository:
   ```bash
   git clone https://github.com/your-repo/advanced-scene-switcher.git
   cd advanced-scene-switcher
   ```
2. Build the plugin:
   ```bash
   mkdir build && cd build
   cmake ..
   make
   ```
3. Copy the compiled `.so`/`.dll` file into your OBS Studio plugins directory:
   - Linux: `~/.config/obs-studio/plugins/`
   - Windows: `C:\Program Files\obs-studio\obs-plugins\`
4. Restart OBS Studio.

## Usage
### Configuring Scene Groups
1. Open OBS Studio and go to the **Tools** menu.
2. Select **Advanced Scene Switcher**.
3. Use the interface to:
   - Add a new scene group.
   - Remove an existing scene group.
   - Configure scenes within each group.

### Enabling Scene Switching
1. Click **Enable Plugin** to start automatic scene switching.
2. Set the switch interval in the code (default: 30 seconds) or modify it dynamically in future releases.

### Saving and Loading Configuration
- Scene groups are saved to `scene_groups.json` in the OBS configuration directory.
- Groups and their scenes will automatically load when the plugin is initialized.

### Error Handling
Errors are displayed in the plugin interface and logged in the OBS log file. Common errors include:
- Missing configuration file.
- Scene not found when switching.

## Development Notes
### Code Structure
- **SceneSwitcher**: Main class for managing scene groups, timer, and user interface.
- **JSON Configuration**:
  - Loaded and saved using `nlohmann::json`.
  - Stored at `scene_groups.json`.
- **Error Handling**: Logs errors using OBS's logging API and displays them in the UI.

### Logging
- Errors and status messages are logged to the OBS log file.
- Additional logs are displayed in the UI for user awareness.

### Thread Safety
Scene switching operations use OBS task scheduling to ensure thread safety.

## Contribution
1. Fork the repository.
2. Create a feature branch.
3. Commit your changes.
4. Push the branch and create a pull request.

## License
This project is licensed under the MIT License. See the `LICENSE` file for details.

## Support
For issues, please open a ticket in the GitHub repository or contact the maintainer.

---

Enjoy seamless scene management with the Advanced Scene Switcher!