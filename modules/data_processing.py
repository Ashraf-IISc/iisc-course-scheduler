import re
import io
import pandas as pd
import streamlit as st
from modules.time_parser import parse_time_slot

"""Data loading and normalization helpers for the course scheduler app.

The functions in this module handle file ingestion, parsing, display-name
generation, and schedule-conflict classification.
"""

@st.cache_data(max_entries=16)
def load_and_parse_data(file_identifier, file_path=None, file_bytes=None):
    """Load a course file, normalize its columns, and expand parsed schedule blocks.

    Args:
        file_identifier: Stable identifier used by Streamlit's cache key.
        file_path: Optional path to a CSV/XLSX file on disk.
        file_bytes: Optional in-memory file contents for uploaded files.

    Returns:
        A normalized ``pandas.DataFrame`` with parsed schedule metadata.
    """
    if file_path is not None:
        is_csv = file_path.endswith('.csv')
    else:
        is_csv = str(file_identifier).endswith('.csv')

    # Load CSV and Excel inputs through the same normalization path.
    if is_csv:
        if file_path is not None:
            df = pd.read_csv(file_path)
        else:
            df = pd.read_csv(io.BytesIO(file_bytes))
    else:
        if file_path is not None:
            df_raw = pd.read_excel(file_path)
        else:
            df_raw = pd.read_excel(io.BytesIO(file_bytes))
        header_idx = None
        for i, row in df_raw.iterrows():
            if row.astype(str).str.contains('Course Code', case=False, na=False).any():
                header_idx = i
                break
        
        if header_idx is not None:
            df_raw.columns = df_raw.iloc[header_idx]
            df = df_raw.iloc[header_idx + 1:].reset_index(drop=True)
        else:
            df = df_raw
            
    # Normalize the incoming column names so downstream lookups are stable.
    col_map = {c: str(c).strip() for c in df.columns}
    df = df.rename(columns=col_map)
            
    if 'Course Code' not in df.columns:
        st.error("Missing 'Course Code' column. Invalid file format.")
        return pd.DataFrame()
        
    df = df.dropna(subset=['Course Code'])
    
    # Standardize the fields used throughout the UI and conflict checks.
    df['Course Code Clean'] = df['Course Code'].astype(str).str.replace(' ', '').str.strip()
    if 'Course Name' not in df.columns: df['Course Name'] = 'Unknown Name'
    if 'Faculty' not in df.columns: df['Faculty'] = 'Unknown Faculty'
    if 'Department' not in df.columns: df['Department'] = 'Unknown Department'
    if 'Credit' not in df.columns: df['Credit'] = df.get('Total Credits', 0)
    
    if 'Approved Time Slot' not in df.columns:
        time_col = next((c for c in df.columns if 'time' in str(c).lower()), None)
        df['Approved Time Slot'] = df[time_col] if time_col else 'No Time Listed'
        
    df['Course Name'] = df['Course Name'].fillna('Unknown Name')
    df['Faculty'] = df['Faculty'].fillna('Unknown Faculty')
    df['Department'] = df['Department'].fillna('Unknown Department')
    df['Approved Time Slot'] = df['Approved Time Slot'].fillna('No Time Listed')
    df['Original Time Slot'] = df['Approved Time Slot']
    
    def parse_credits(credit_str):
        """Convert a messy credit string into a numeric total."""
        if pd.isna(credit_str): return 0.0
        c_str = str(credit_str).strip()
        
        # Treat the common separator variants as split points for summed credits.
        c_str = re.sub(r'[^0-9\.]+', ':', c_str)
        
        if ':' in c_str:
            try:
                # Safely split and sum all credit fragments.
                parts = [float(p) for p in c_str.split(':') if p.strip()]
                return sum(parts)
            except: return 0.0
        try: return float(c_str)
        except: return 0.0
        
    df['Total Credits'] = df['Credit'].apply(parse_credits)
    
    # Expand each raw time slot into one or more normalized meeting blocks.
    df['Schedule_Blocks'] = df['Original Time Slot'].apply(parse_time_slot)
    df = df.explode('Schedule_Blocks').reset_index(drop=True)
    
    df['Parsed_Days'] = df['Schedule_Blocks'].apply(lambda x: ", ".join(x['Parsed_Days']))
    df['Start_Min'] = df['Schedule_Blocks'].apply(lambda x: x['Start_Min'])
    df['End_Min'] = df['Schedule_Blocks'].apply(lambda x: x['End_Min'])
    df['Needs Initial Review'] = df['Schedule_Blocks'].apply(lambda x: x['Needs_Review'])
    df = df.drop(columns=['Schedule_Blocks'])
    
    # Prebuild a human-readable label for selectors and editing previews.
    df['Editor Display Name'] = (df['Course Code'].astype(str) + " - " + df['Course Name'] + 
                                 " | " + df['Faculty'] + " | " + df['Original Time Slot'].astype(str))
    return df

def format_military_time(days_str, start_min, end_min, original_str):
    """Format parsed minutes back into the display string used in the UI.

    Args:
        days_str: Parsed day tokens such as ``Mon, Wed``.
        start_min: Start time in minutes since midnight.
        end_min: End time in minutes since midnight.
        original_str: Original raw time string used as a fallback.

    Returns:
        A formatted schedule string or the original fallback text.
    """
    if pd.isna(start_min) or pd.isna(end_min) or not days_str:
        return original_str if pd.notna(original_str) else "No Time Listed"
    start_h, start_m = int(start_min) // 60, int(start_min) % 60
    end_h, end_m = int(end_min) // 60, int(end_min) % 60
    return f"{days_str} {start_h:02d}:{start_m:02d}-{end_h:02d}:{end_m:02d}"

def get_course_conflict_status(course_code, core_codes, blocks_df, walking_buffer_mins):
    """Classify a course as core, hard conflict, buffer conflict, or clear.

    Args:
        course_code: Cleaned course code to evaluate.
        core_codes: Codes already locked into the user's mandatory schedule.
        blocks_df: Parsed dataframe containing all course meeting blocks.
        walking_buffer_mins: Extra minutes added on both sides of a meeting when
            evaluating buffer conflicts.

    Returns:
        One of ``"Core"``, ``"Hard Conflict"``, ``"Buffer Conflict"``, or
        ``"No Conflict"``.
    """
    if course_code in core_codes: return "Core"
    
    prosp_blocks = blocks_df[blocks_df['Course Code Clean'] == course_code]
    core_blocks = blocks_df[blocks_df['Course Code Clean'].isin(core_codes)]
    
    status = "No Conflict"
    for _, p_row in prosp_blocks.iterrows():
        p_start, p_end = p_row['Start_Min'], p_row['End_Min']
        if pd.isna(p_start) or pd.isna(p_end): continue
        # Parse days into sets so overlap checks stay simple and order-independent.
        p_days = set([d.strip() for d in str(p_row['Parsed_Days']).split(',') if d.strip()])
        
        for _, c_row in core_blocks.iterrows():
            c_start, c_end = c_row['Start_Min'], c_row['End_Min']
            if pd.isna(c_start) or pd.isna(c_end): continue
            c_days = set([d.strip() for d in str(c_row['Parsed_Days']).split(',') if d.strip()])
            
            if p_days.intersection(c_days):
                if (p_start < c_end) and (c_start < p_end): return "Hard Conflict" 
                if (p_start < (c_end + walking_buffer_mins)) and (c_start < (p_end + walking_buffer_mins)):
                    status = "Buffer Conflict"
    return status