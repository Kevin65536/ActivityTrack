# ActivityTrack

A privacy-focused, lightweight input tracking tool for Windows. Inspired by WhatPulse, ActivityTrack allows you to monitor your keyboard and mouse usage, visualize heatmaps, and track application-specific statistics locally on your machine.

![Screen Time Tab](screenshots/Screentime.png)

<details>
<summary>📸 <b>View more Screenshots</b> (click to expand)</summary>

### Dashboard
![Dashboard Tab](screenshots/Dashboard.png)

### Heatmap
![Keyboard Heatmap](screenshots/Heatmap.png)

### Mouse Heatmap
![Mouse Click Heatmap](screenshots/MouseHeatmap.png)

### Applications
![Application Statistics](screenshots/Applications.png)

### History
![History & Trends](screenshots/History.png)

### Settings
![Settings Page](screenshots/Settings.png)

</details>

## Key Highlights

✨ **6 Comprehensive Tabs** - Dashboard, Heatmap, Applications, History, Screen Time, and Settings  
🎨 **5 Heatmap Themes** - Classic, Fire, Ocean, Purple, and Matrix color schemes  
📊 **Advanced Analytics** - Timeline and Insights charts with weekday/hourly patterns  
⏱️ **Screen Time Tracking** - Monitor foreground application usage time  
🎯 **Per-App Filtering** - Filter heatmaps and statistics by specific applications  
🔒 **100% Private** - All data stored locally, no cloud sync or telemetry

## Features

### 📊 Input Tracking
- **Keyboard Heatmap**: Visualize your most used keys with a color-coded keyboard overlay
  - Multiple color themes (Classic, Fire, Ocean, Purple, Matrix)
  - Time range filtering (Today, Week, Month, Year, All Time)
  - Per-application keyboard heatmap filtering
- **Mouse Heatmap**: Track click density across multiple monitors
  - Smooth gradient visualization with Gaussian blur
  - Accurate screen positioning and multi-monitor support
  - Per-application mouse heatmap filtering
- **Input Statistics**:
  - Track total keystrokes and mouse clicks
  - Calculate mouse travel distance in meters (with accurate physical screen size detection)
  - Calculate scroll wheel usage (in scroll steps)
  - Real-time statistics updates

### 📈 History & Analytics
- **Timeline View**: Interactive charts showing daily/hourly input trends
  - Timeline graphs for Today/Week/Month/Year
  - Combined bar and line charts with dark theme support
- **Insights View**: Statistical analysis of your usage patterns
  - Weekday distribution (average inputs per day of week)
  - Hourly distribution (average inputs by hour of day)
- **Time Range Filtering**: View statistics for Today, Week, Month, Year, or All Time

### 💻 Application Tracking
- **Application Statistics**: Comprehensive per-app usage tracking
  - Track keystrokes, clicks, scrolls, and mouse distance per application
  - Display application icons extracted from executables
  - Show friendly application names (from PE file metadata)
  - View data in table or pie chart format
  - Sort and filter by different metrics (Keys, Clicks, Scrolls, Distance)
  - Tooltip showing full executable paths

### ⏱️ Screen Time Monitoring
- **Foreground Time Tracking**: Monitor how much time you spend in each application
  - Total screen time and daily average calculations
  - Most used application display
  - Detailed breakdown table with percentages
  - Visual pie chart distribution
  - Time range filtering support

### ⚙️ Settings & Customization
- **Startup Options**: Start with Windows automatically
- **Tray Behavior**: Minimize to system tray option
- **Data Management**: Configure data retention period (7-365 days or forever)
- **Theme Customization**: Choose from 5 heatmap color themes with live preview
  - Classic (Blue → Green → Yellow → Red)
  - Fire (Dark Red → Red → Orange → Yellow)
  - Ocean (Dark Blue → Cyan → Blue → Light Blue)
  - Purple (Dark Purple → Purple → Pink → Light Pink)
  - Matrix (Dark Green → Green → Light Green → White)

### 🔒 Privacy First
- All data is stored locally in a SQLite database (`tracker.db`)
- No keylogging - only frequency counting of keys
- No data is ever sent to the cloud or external servers
- Full control over data retention

## Releases

Pre-compiled Windows executables are available in the [Releases](https://github.com/Kevin65536/ActivityTrack/releases) section.

## Requirements

- Windows 10/11 (64-bit recommended)
- Python 3.10+

### Dependencies
- `PySide6` (UI Framework)
- `pywin32` (Windows API hooks)
- `psutil` (Process information for app tracking)
- `numpy` (Heatmap data processing)
- `scipy` (Heatmap smoothing)
- `matplotlib` (History charts)

## Installation

1.  Clone the repository or download the source code.
2.  Open a terminal in the `ActivityTrack` directory.
3.  Create a virtual environment (optional but recommended):
    ```powershell
    python -m venv venv
    .\venv\Scripts\activate
    ```
4.  Install dependencies:
    ```powershell
    pip install -r requirements.txt
    ```

## Usage

1.  Run the main application script:
    ```powershell
    python main.py
    ```
    *Note: To track input in high-privilege applications (e.g., Task Manager, Admin prompts), you may need to run the terminal/script as Administrator.*

2.  The application will start, and a system tray icon will appear.
3.  Use the different tabs to view your statistics:
    - **Dashboard**: Quick overview with time range selection (Today/Week/Month/Year/All Time)
    - **Heatmap**: Keyboard and Mouse heatmaps with per-app filtering and theme customization
    - **Applications**: Detailed per-app statistics (table and pie chart views)
    - **History**: Timeline and Insights charts showing usage trends and patterns
    - **Screen Time**: Application foreground time tracking with distribution charts
    - **Settings**: Customize startup behavior, data retention, and heatmap themes

## Privacy Note

This tool uses low-level system hooks (`SetWindowsHookEx`) to count keystrokes and mouse events. 

**What we track:**
- Frequency of key presses (e.g., "Spacebar pressed 50 times")
- Mouse click counts and positions (for heatmap visualization)
- Mouse movement distance (calculated from pixel distance and physical screen size)
- Scroll wheel usage count
- Active foreground application names and usage time

**What we DON'T track:**
- Actual text or passwords you type (no keylogging)
- Clipboard content
- Screenshot or window content
- Network activity

All data is stored locally in `tracker.db` in the application directory. You have full control over data retention through the Settings page.

## License

MIT License
