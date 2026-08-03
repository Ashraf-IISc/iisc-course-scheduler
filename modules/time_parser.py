import re
import pandas as pd

"""Parsing helpers for IISc schedule time strings.

The parser converts loosely formatted course time text into normalized day and
minute ranges while flagging ambiguous or suspicious cases for review.
"""

def parse_time_slot(time_str):
    """Parse an unstructured time string into one or more normalized blocks.

    Args:
        time_str: Raw schedule text from the source file.

    Returns:
        A list of dictionaries with parsed days, start/end minutes, and a
        review flag for ambiguous or invalid inputs.
    """
    # 1. Handle empty or placeholder values up front.
    if pd.isna(time_str) or not isinstance(time_str, str) or time_str.strip().upper() in ['NO TIME LISTED', '--SELECT--']:
        return [{'Parsed_Days': [], 'Start_Min': None, 'End_Min': None, 'Needs_Review': True}]
    
    time_str = time_str.upper().strip()
    
    # 2. Clean formatting quirks before tokenization.
    time_str = re.sub(r'(\d)\s*/\s*([A-Z])', r'\1, \2', time_str)
    
    # 3. Chunk by delimiters so repeated instructor/day fragments stay separable.
    raw_chunks = re.split(r'[,;&]', time_str)
    chunks = []
    current_chunk = ""
    
    for c in raw_chunks:
        current_chunk += c + " "
        if bool(re.search(r'\d', c)):
            chunks.append(current_chunk.strip())
            current_chunk = ""
            
    if current_chunk.strip():
        if chunks:
            chunks[-1] += " " + current_chunk.strip()
        else:
            chunks.append(current_chunk.strip())
            
    # 4. Map shorthand tokens to canonical day labels.
    day_mapping = {
        'M': 'Mon', 'MON': 'Mon', 'MONDAY': 'Mon',
        'T': 'Tue', 'TU': 'Tue', 'TUE': 'Tue', 'TUESDAY': 'Tue', 'TUS': 'Tue',
        'W': 'Wed', 'WED': 'Wed', 'WEDNESDAY': 'Wed',
        'TH': 'Thu', 'THU': 'Thu', 'THURSDAY': 'Thu', 'THURS': 'Thu',
        'F': 'Fri', 'FRI': 'Fri', 'FRIDAY': 'Fri', 'FRIDAYS': 'Fri',
        'SA': 'Sat', 'SAT': 'Sat', 'SATURDAY': 'Sat',
        'SUN': 'Sun', 'SUNDAY': 'Sun',
        'MW': ['Mon', 'Wed'], 'WF': ['Wed', 'Fri'], 'MWF': ['Mon', 'Wed', 'Fri'],
        'TTH': ['Tue', 'Thu'], 'TUTHR': ['Tue', 'Thu']
    }
    day_order = {'Mon': 1, 'Tue': 2, 'Wed': 3, 'Thu': 4, 'Fri': 5, 'Sat': 6, 'Sun': 7}
    
    def to_minutes(t_str, chunk_str):
        """Convert a raw time token into minutes since midnight.

        Args:
            t_str: The extracted time token, such as ``830`` or ``8:30``.
            chunk_str: The surrounding chunk used to infer AM/PM context.

        Returns:
            Minutes since midnight for the parsed token.
        """
        t_str = t_str.replace('.', ':')
        if len(t_str) == 4 and t_str.isdigit(): h, m = int(t_str[:2]), int(t_str[2:])
        elif len(t_str) == 3 and t_str.isdigit(): h, m = int(t_str[:1]), int(t_str[1:])
        elif ':' in t_str: h, m = map(int, t_str.split(':'))
        else: h, m = int(t_str), 0
        
        # Infer the intended half of the day from the surrounding text.
        upper_chunk = chunk_str.upper()
        if 'AM' in upper_chunk:
            pass # Explicit morning class, no shift
        elif 'PM' in upper_chunk and h != 12:
            h += 12
        elif 1 <= h <= 6: # Stricter assumption for afternoon classes only
            h += 12 
            
        return h * 60 + m

    # 5. Extract the day/time information from each chunk.
    parsed_blocks = []
    global_review_needed = False
    
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk: continue
        
        text_only = re.sub(r'[^A-Z]', ' ', chunk)
        tokens = text_only.split()
        days_set = set()
        for t in tokens:
            if t in day_mapping:
                if isinstance(day_mapping[t], list):
                    for d in day_mapping[t]: days_set.add(d)
                else: days_set.add(day_mapping[t])
        
        days = sorted(list(days_set), key=lambda x: day_order.get(x, 99))
        times = re.findall(r'(\d{1,2}[:.]\d{2}|\d{3,4}|\d{1,2})', chunk)
        
        start, end = None, None
        if len(times) >= 2:
            start = to_minutes(times[-2], chunk)
            end = to_minutes(times[-1], chunk)
            # Wrapped or overnight intervals are treated as ambiguous and pushed to review.
            if end is not None and start is not None and end <= start:
                start, end = None, None
                global_review_needed = True
        elif len(times) < 2 and bool(re.search(r'\d', chunk)):
            global_review_needed = True
            
        if days or start is not None:
            parsed_blocks.append({'days': days, 'start': start, 'end': end})

    if not parsed_blocks:
        return [{'Parsed_Days': [], 'Start_Min': None, 'End_Min': None, 'Needs_Review': True}]

    # 6. Merge blocks that share the same time range into a single day set.
    consolidated = {}
    for block in parsed_blocks:
        time_tuple = (block['start'], block['end'])
        if time_tuple not in consolidated: consolidated[time_tuple] = set()
        for d in block['days']: consolidated[time_tuple].add(d)
            
    final_output = []
    for (start, end), d_set in consolidated.items():
        unique_days = sorted(list(d_set), key=lambda x: day_order.get(x, 99))
        # Any ambiguity in the source chunk carries through so the UI can surface it.
        needs_review = global_review_needed or (start is None) or (len(unique_days) == 0)
        final_output.append({'Parsed_Days': unique_days, 'Start_Min': start, 'End_Min': end, 'Needs_Review': needs_review})
        
    return final_output