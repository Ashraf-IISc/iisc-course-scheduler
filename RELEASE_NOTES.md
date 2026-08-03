# Release Notes - v1.0.0

## IISc Course Scheduler - Initial Release
**Date:** August 2026

### Features
* **Modular Architecture:** Refactored core logic into dedicated modules for parsing, data processing, and visualization.
* **Smart Conflict Detection:** Added internal walking buffer and overlap detection for both mandatory courses and electives.
* **Robust Time Parsing:** Fixed overnight wrap-around bugs (end < start) and added safe string casting for Edge-case course codes.
* **Native UI Alignment:** Standardized Streamlit multi-select inputs for a cleaner user experience.

### License
This project is officially released under the **GNU General Public License v3.0 (GPLv3)**.
