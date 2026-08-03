# IISc Course Scheduler

Version 1.0.0 of an open-source course scheduling dashboard built for IISc students.

This Streamlit app helps you load term course data, review and clean schedule parsing, compare mandatory and elective choices, detect timetable conflicts with a walking buffer, and generate a visual weekly timetable with Plotly.

## Key Features

- Modular Python architecture with separate data processing, time parsing, and visualization layers.
- Streamlit-based UI for uploading data, reviewing parsed rows, selecting mandatory courses, and evaluating electives.
- Plotly timetable visualizations with both timeline and classic grid views.
- Smart overnight and wrapped time handling so ambiguous schedule strings are flagged for review instead of silently misread.
- Walking-buffer conflict detection to distinguish hard overlaps from courses that are close enough to require travel time.
- Cached data loading with `@st.cache_data` to keep reruns fast and avoid reparsing the same source file repeatedly.
- Mobile-aware layout adjustments so the dashboard degrades more gracefully on smaller screens.

## Live Demo

The hosted Streamlit Community Cloud demo will be available here:

[Live demo placeholder](https://your-streamlit-community-cloud-app-url-here)

## Local Installation

### 1. Clone the repository

```bash
git clone https://github.com/Ashraf-IISc/iisc-course-scheduler.git
cd iisc-course-scheduler
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the app

```bash
streamlit run app.py
```

## Project Structure

```text
app.py
modules/
	data_processing.py
	time_parser.py
	visualization.py
requirements.txt
```

## Notes

- Preloaded term data can be shipped with the repository as CSV files such as `august_2026.csv`.
- Uploaded files are processed in memory for the current session.
- The app is designed to help students review schedules interactively before finalizing a semester plan.

## License

This project is open-source software released under the GNU General Public License v3.0 (GPLv3).

See the [LICENSE](LICENSE) file if one is included in this repository.
