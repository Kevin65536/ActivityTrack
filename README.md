# ActivityTrack

A privacy-focused, lightweight input tracking tool for Windows. Inspired by WhatPulse, ActivityTrack allows you to monitor your keyboard and mouse usage, visualize heatmaps, and track application-specific statistics locally on your machine.

## Features

- **Keyboard Heatmap**: visualize your most used keys with a color-coded keyboard overlay.
- **Mouse Heatmap**: Track click density across multiple monitors with smooth gradient visualization and accurate screen positioning.
- **Input Statistics**:
  - Track total keystrokes and mouse clicks.
  - Calculate mouse travel distance (in meters).
  - Calculate scroll wheel usage.
- **History & Trends**: View daily, weekly, and monthly storage trends with interactive charts.
- **Application Statistics**: See which applications you use the most, including per-app keystrokes, clicks, and scroll data.
- **Privacy First**: All data is stored locally in a SQLite database (`tracker.db`). No data is ever sent to the cloud.

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
    - **Dashboard**: Quick overview of today's stats.
    - **Heatmap**: Keyboard and Mouse heatmaps.
    - **Applications**: Per-application usage stats.
    - **History**: Long-term usage trends.

## Privacy Note

This tool uses low-level system hooks (`SetWindowsHookEx`) to count keystrokes and mouse events. 
- It **does not** log what you type (no keylogging of passwords or text content).
- It only counts **frequency** of keys (e.g., "Spacebar pressed 50 times").
- All data is stored in `tracker.db` in the application directory.

## License

MIT License
