import streamlit as st
import pandas as pd
import datetime
import os
from modules.data_processing import load_and_parse_data, format_military_time, get_course_conflict_status
from modules.visualization import create_timeline_chart, create_classic_grid_chart

"""Streamlit entry point for the IISc course scheduler app.

This file wires together file loading, parsing review, elective filtering,
conflict detection, and timetable visualization.
"""

# === 1. PAGE CONFIG & MOBILE CSS ===
st.set_page_config(page_title="Course Scheduler", layout="wide")

st.markdown("""
    <style>
        .block-container { padding-top: 2rem; padding-bottom: 2rem; }
        @media (max-width: 768px) {
            .block-container { padding-top: 1rem; padding-left: 1rem; padding-right: 1rem; }
        }
    </style>
""", unsafe_allow_html=True)

st.title("Semester Course & Elective Scheduler")

# === 2. DATA SOURCE SELECTOR ===
data_source = st.radio("Choose your course data source:", ["Upload Custom File", "Use Pre-loaded Term Data"], horizontal=True)

file_to_load = None
file_identifier = None

if data_source == "Use Pre-loaded Term Data":
    preloaded_files = {
        "August Term 2026": "august_2026.csv",
        "January Term 2026": "january_2026.csv",
        "Cleaned Backup Data": "Corrected_IISc_Courses.csv"
    }
    selected_term = st.selectbox("Select Term:", list(preloaded_files.keys()))
    file_path = preloaded_files[selected_term]
    
    if os.path.exists(file_path):
        file_to_load = file_path
        file_identifier = file_path
        st.success(f"Loaded {selected_term} data successfully.")
    else:
        st.warning(f"File '{file_path}' not found on the server. Please switch to 'Upload Custom File' or ensure the file is pushed to your GitHub repository.")
else:
    uploaded_file = st.file_uploader("Upload your Term Courses file (.xlsx or .csv)", type=['xlsx', 'xls', 'csv'])
    if uploaded_file is not None:
        file_to_load = uploaded_file
        file_identifier = uploaded_file.name

# === 3. MAIN APP LOGIC ===
if file_to_load is not None:
    if 'current_file' not in st.session_state or st.session_state.current_file != file_identifier:
        # Cache the parsed dataframe per source file so reruns reuse the already parsed data.
        if isinstance(file_to_load, str):
            st.session_state.raw_df = load_and_parse_data(file_identifier, file_path=file_to_load)
        else:
            st.session_state.raw_df = load_and_parse_data(file_identifier, file_bytes=file_to_load.getvalue())
        st.session_state.current_file = file_identifier
    
    if not st.session_state.raw_df.empty:
        working_df = st.session_state.raw_df.copy()
        st.markdown("---")
        
        # --- Section: Parsing Checks & Manual Overrides ---
        with st.expander("🛠️ 1. Parsing Checks & Manual Overrides"):
            st.markdown("Review flagged courses where times couldn't be automatically extracted. **Double-click any cell to manually fix them.**")
            
            # Mark rows that still need manual review after parsing heuristics run.
            working_df['Review Status'] = working_df.apply(
                lambda r: "⚠️ Review Needed" if (r['Needs Initial Review'] or (pd.isna(r['Start_Min']) and r['Original Time Slot'] != 'No Time Listed')) else "✅ OK", 
                axis=1
            )
            
            edited_df = st.data_editor(
                working_df[['Review Status', 'Editor Display Name', 'Original Time Slot', 'Parsed_Days', 'Start_Min', 'End_Min']],
                disabled=['Review Status', 'Editor Display Name', 'Original Time Slot'],
                width="stretch", hide_index=True
            )
            
            if st.button("🔄 Review Again & Update Status"):
                # Write manual corrections back into the cached source dataframe.
                st.session_state.raw_df['Parsed_Days'] = edited_df['Parsed_Days']
                st.session_state.raw_df['Start_Min'] = edited_df['Start_Min']
                st.session_state.raw_df['End_Min'] = edited_df['End_Min']
                
                fixed_mask = edited_df['Start_Min'].notna() & edited_df['End_Min'].notna() & (edited_df['Parsed_Days'] != "")
                st.session_state.raw_df.loc[fixed_mask, 'Needs Initial Review'] = False
                st.rerun()
    
            working_df['Parsed_Days'] = edited_df['Parsed_Days']
            working_df['Start_Min'] = edited_df['Start_Min']
            working_df['End_Min'] = edited_df['End_Min']
    
        working_df['Approved Time Slot'] = working_df.apply(
            lambda r: format_military_time(r['Parsed_Days'], r['Start_Min'], r['End_Min'], r['Original Time Slot']), 
            axis=1
        )
    
        # Collapse repeated rows so one course appears once in the downstream selectors and tables.
        course_df = working_df.groupby('Course Code Clean', as_index=False).agg({
            'Course Code': 'first',
            'Course Name': 'first',
            'Department': 'first',
            'Credit': 'first',
            'Total Credits': 'first',
            'Faculty': lambda x: ' & '.join([str(f) for f in x.dropna().unique()]),
            'Original Time Slot': 'first',
            'Approved Time Slot': lambda x: ' & '.join([str(i) for i in x.unique()]) 
        })
        course_df['Display Name'] = (course_df['Course Code'] + " - " + course_df['Course Name'] + 
                                      " | " + course_df['Faculty'] + " | " + course_df['Approved Time Slot'])
    
        # --- Section: Data Export ---
        with st.expander("💾 2. Download Cleaned Data"):
            st.markdown("Download this corrected CSV. Next time, you can upload this file instead of the original Excel file to bypass manual parsing entirely!")
            export_clean_df = course_df[['Course Code', 'Course Name', 'Department', 'Credit', 'Total Credits', 'Faculty', 'Approved Time Slot']].copy()
            st.download_button(
                label="⬇️ Download Corrected Course List (CSV)",
                data=export_clean_df.to_csv(index=False).encode('utf-8'),
                file_name="Corrected_Courses.csv",
                mime="text/csv"
            )
    
        st.markdown("---")
        st.subheader("3. Select Your Mandatory Courses")
        all_courses = course_df['Display Name'].tolist()
        selected_course_names = st.multiselect(
            "Mandatory courses",
            options=all_courses,
        )
    
        if selected_course_names:
            core_schedule = course_df[course_df['Display Name'].isin(selected_course_names)]
            core_clean_codes = core_schedule['Course Code Clean'].tolist()
            
            st.markdown("**Your Locked Schedule:**")
            st.dataframe(core_schedule[['Course Code', 'Course Name', 'Total Credits', 'Faculty', 'Approved Time Slot']], width="stretch", hide_index=True)
    
            st.markdown("---")
            st.subheader("4. Elective Analysis")
            walk_buffer = st.slider("Walking Buffer Time (minutes)", min_value=0, max_value=30, value=15, step=5)
    
            # Derive course availability categories from the currently locked schedule.
            course_df['Conflict Status'] = course_df['Course Code Clean'].apply(
                lambda code: get_course_conflict_status(code, core_clean_codes, working_df, walk_buffer)
            )
            
            available_electives = course_df[course_df['Conflict Status'] == 'No Conflict']
            buffer_conflicts = course_df[course_df['Conflict Status'] == 'Buffer Conflict']
            hard_conflicts = course_df[course_df['Conflict Status'] == 'Hard Conflict']
            
            tab1, tab2, tab3 = st.tabs([f"✅ Available ({len(available_electives)})", f"🏃‍♂️ Buffer Conflicts ({len(buffer_conflicts)})", f"❌ Hard Conflicts ({len(hard_conflicts)})"])
            
            def render_tab(df_subset, tab_key):
                if df_subset.empty:
                    st.info("No courses found in this category!")
                    return
                    
                dept_list = ["All"] + sorted(df_subset['Department'].dropna().unique().tolist())
                sel_dept = st.selectbox("Filter by Department:", dept_list, key=tab_key)
                disp_df = df_subset if sel_dept == "All" else df_subset[df_subset['Department'] == sel_dept]
                st.dataframe(disp_df[['Course Code', 'Course Name', 'Department', 'Total Credits', 'Faculty', 'Approved Time Slot']], width="stretch", hide_index=True)
    
            with tab1: render_tab(available_electives, "d_avail")
            with tab2: render_tab(buffer_conflicts, "d_buff")
            with tab3: render_tab(hard_conflicts, "d_hard")
    
            st.markdown("---")
            st.subheader("5. Schedule Builder & Credit Tracker")
            
            col1, col2 = st.columns([1, 2])
            with col1: max_credits = st.number_input("Maximum allowed credits:", min_value=1.0, max_value=30.0, value=20.0, step=1.0)
            with col2:
                selectable_options = pd.concat([available_electives, buffer_conflicts])['Display Name'].tolist()
                selected_electives = st.multiselect(
                    "Electives",
                    options=selectable_options,
                )
                
            core_credits = core_schedule['Total Credits'].sum()
            elective_credits = course_df[course_df['Display Name'].isin(selected_electives)]['Total Credits'].sum()
            total_credits = core_credits + elective_credits
            
            st.metric("Total Planned Credits", f"{total_credits} / {max_credits}", delta=f"Core: {core_credits} | Electives: {elective_credits}", delta_color="off")
            
            if total_credits > max_credits: st.error(f"⚠️ Exceeded limit by {total_credits - max_credits} credits!")
            elif total_credits == max_credits: st.success("✅ Exactly at credit limit.")
            else: st.info(f"{max_credits - total_credits} credits remaining.")
            
            # --- Section: Internal Conflict Detector ---
            final_selected_names = selected_course_names + selected_electives
            
            if final_selected_names:
                # Compare every selected block against every other block to catch same-day overlaps.
                final_codes = course_df[course_df['Display Name'].isin(final_selected_names)]['Course Code Clean'].tolist()
                final_blocks = working_df[working_df['Course Code Clean'].isin(final_codes)]
                
                internal_conflicts = []
                for i in range(len(final_blocks)):
                    for j in range(i+1, len(final_blocks)):
                        b1 = final_blocks.iloc[i]
                        b2 = final_blocks.iloc[j]
                        if b1['Course Code Clean'] == b2['Course Code Clean']: continue
                        
                        if pd.isna(b1['Start_Min']) or pd.isna(b1['End_Min']) or pd.isna(b2['Start_Min']) or pd.isna(b2['End_Min']):
                            continue
                            
                        days1 = set([d.strip() for d in str(b1['Parsed_Days']).split(',') if d.strip()])
                        days2 = set([d.strip() for d in str(b2['Parsed_Days']).split(',') if d.strip()])
                        
                        if days1.intersection(days2):
                            # Apply the walking buffer to both sides so nearby classes are treated as conflicts.
                            if (b1['Start_Min'] < (b2['End_Min'] + walk_buffer)) and (b2['Start_Min'] < (b1['End_Min'] + walk_buffer)):
                                pair = tuple(sorted([b1['Course Code'], b2['Course Code']]))
                                if pair not in internal_conflicts:
                                    internal_conflicts.append(pair)
                
                if internal_conflicts:
                    st.error("🚨 **WARNING: TIMETABLE CONFLICT DETECTED!**")
                    for c1, c2 in internal_conflicts:
                        st.write(f"- **{c1}** and **{c2}** have overlapping times.")
    
                st.markdown("---")
                st.subheader("📅 Final Visual Timetable")
                
                view_type = st.radio("Select Timetable View:", ["Classic Grid (Vertical)", "Timeline (Horizontal)"], horizontal=True)
                
                course_colors = {}
                course_locations = {}
                default_palette = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"]
                
                with st.expander("🎨 Customize Colors & Add Locations", expanded=False):
                    for idx, full_name in enumerate(final_selected_names):
                        course_code = full_name.split(' - ')[0] 
                        default_color = default_palette[idx % len(default_palette)]
                        
                        ccol1, ccol2 = st.columns([1, 4])
                        with ccol1:
                            course_colors[full_name] = st.color_picker(f"Color: {course_code}", default_color, key=f"c_{course_code}")
                        with ccol2:
                            course_locations[full_name] = st.text_input(f"Location/Note: {course_code}", placeholder="e.g., Main Hall", key=f"l_{course_code}")
                
                # --- Section: Build Render Data ---
                timetable_data = []
                base_date = datetime.date(2026, 1, 5) 
                day_map = {'Mon': 0, 'Tue': 1, 'Wed': 2, 'Thu': 3, 'Fri': 4, 'Sat': 5, 'Sun': 6}
                
                for _, row in final_blocks.iterrows():
                    if pd.isna(row['Start_Min']) or pd.isna(row['End_Min']): continue
                    
                    days = [d.strip() for d in str(row['Parsed_Days']).split(',') if d.strip()]
                    for d in days:
                        if d not in day_map: continue
                        
                        start_h, start_m = int(row['Start_Min'] // 60), int(row['Start_Min'] % 60)
                        end_h, end_m = int(row['End_Min'] // 60), int(row['End_Min'] % 60)
                        
                        start_dt = datetime.datetime.combine(base_date, datetime.time(start_h, start_m))
                        end_dt = datetime.datetime.combine(base_date, datetime.time(end_h, end_m))
                        
                        course_display = course_df[course_df['Course Code Clean'] == row['Course Code Clean']]['Display Name'].values[0]
                        location_text = course_locations.get(course_display, "").strip()
                        
                        # Convert each meeting block into Plotly-friendly datetime rows.
                        timetable_data.append({
                            'Course': row['Course Code'], 'Name': row['Course Name'],
                            'Day': d, 'Start': start_dt, 'End': end_dt,
                            'Display Name': course_display, 'Location': location_text, 'Day_Int': day_map[d]
                        })
                
                # --- Section: Render Plotly ---
                if timetable_data:
                    tt_df = pd.DataFrame(timetable_data)
                    tt_df = tt_df.drop_duplicates(subset=['Course', 'Day', 'Start', 'End']).copy()
                    tt_df = tt_df.sort_values(['Day_Int', 'Start'], ascending=[False, True])
                    
                    # Create the label column BEFORE calling the Plotly function
                    tt_df['Timeline_Label'] = tt_df.apply(
                        lambda r: f"<b>{r['Course']}</b> - {r['Location']}" if r['Location'] else f"<b>{r['Course']}</b>", 
                        axis=1
                    )
                    
                    # Use the selected view while keeping the same dataset and color mapping.
                    if view_type == "Timeline (Horizontal)":
                        fig = create_timeline_chart(tt_df, course_colors)
                    else:
                        fig = create_classic_grid_chart(tt_df, course_colors, base_date)
                    
                    st.plotly_chart(fig, width="stretch", config={"responsive": True})
                    
                    # Final CSV export
                    export_df = tt_df[['Course', 'Name', 'Day', 'Start', 'End', 'Location']].copy()
                    export_df['Start'] = export_df['Start'].dt.strftime('%H:%M')
                    export_df['End'] = export_df['End'].dt.strftime('%H:%M')
                    export_df = export_df.sort_values(['Day', 'Start'])
                    
                    st.download_button(
                        label="⬇️ Download Final Schedule Data (CSV)",
                        data=export_df.to_csv(index=False).encode('utf-8'),
                        file_name="Term_Schedule.csv",
                        mime="text/csv"
                    )
        else:
            st.info("Please select at least one mandatory course above to analyze electives.")
else:
    st.info("Waiting for file upload...")