# 📅 Semester Course & Elective Scheduler

An interactive dashboard built with Streamlit and Pandas to help students automatically parse term course schedules, detect time conflicts, and optimize their elective choices.

## ✨ Key Features
* **Automated Smart Parsing:** Extracts days and military time from unstructured spreadsheet data using advanced Regex chunking. It intelligently handles multi-day courses, varied formatting, and multi-instructor redundancies.
* **Pre-Loaded & Custom Data:** Select a pre-cleaned, pre-existing term database directly from the server, or upload your own university `.xlsx` or `.csv` schedule.
* **Clean Data Export:** Built-in data editor to manually fix irregular time listings (e.g., "Any two days"). Once fixed, you can download the corrected dataset as a clean CSV to bypass manual parsing in future sessions!
* **Advanced Conflict Detection:** Identifies both direct overlap ("Hard Conflicts") and back-to-back classes ("Buffer Conflicts") based on an adjustable walking time slider. It dynamically cross-references your core courses *and* your selected electives against each other.
* **Credit Tracking:** Shopping cart system to monitor total core + elective credits against your semester limits.
* **Interactive Visual Timetable:** Generates a beautifully color-coded, mobile-responsive Gantt chart of your finalized week using Plotly.
* **Custom Locations & Colors:** Personalize your visual timetable by choosing custom colors for each course and typing in custom location tags (e.g., "Physics Lab") that render directly onto the time blocks.

---

## 🚀 How to Use the Web App (For Users)

1. **Load Data:** Navigate to the live web application link. Choose a pre-loaded term, or drag and drop your own `.xlsx` or `.csv` file into the file uploader.
2. **Review Parsing:** Check the *Parsing Checks & Manual Overrides* dropdown to fix any missing or irregularly formatted times. 
3. **Lock Core Courses:** Select your mandatory/core courses from the dropdown to instantly view available electives.
4. **Analyze Electives:** Use the walking buffer slider to see which electives fit perfectly, which require a quick walk across campus, and which have hard overlaps.
5. **Build Schedule:** Add electives to your schedule while monitoring your total credits.
6. **Visualize & Customize:** Scroll down to the Visual Timetable. Assign colors, add your lecture halls, and download your finished schedule as a CSV spreadsheet or a PNG image!

*(Note: Custom uploaded data is processed in-memory and is not saved or stored on any server.)*

---

## 💻 Developer Setup: Running Locally

### Prerequisites

Ensure you have Python installed. Your project folder should only contain:
* `app.py` (The main application script)
* `requirements.txt` (Dependencies: must include `streamlit`, `pandas`, `openpyxl`, and `plotly`)
* `README.md` (This file)
* *(Optional)* Pre-cleaned `.csv` files for default terms (e.g., `august_2026.csv`).

*(Note: Do **not** upload your raw Excel data file to GitHub.)*

### 1. Clone the repository

```bash
git clone [https://github.com/Ashraf-IISc/iisc-course-scheduler.git](https://github.com/Ashraf-IISc/iisc-course-scheduler.git)
cd iisc-course-scheduler
```

### 2. Install the dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the application

```bash
streamlit run app.py
```
