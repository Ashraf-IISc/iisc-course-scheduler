import plotly.express as px
import plotly.graph_objects as go
import datetime

"""Plotly chart helpers for the course scheduler timetable views."""

def create_timeline_chart(tt_df, course_colors):
    """Build the horizontal timeline view for the selected schedule blocks.

    Args:
        tt_df: Render-ready dataframe with datetime start/end columns.
        course_colors: Mapping from display name to a fixed hex color.

    Returns:
        A configured Plotly figure for the timeline view.
    """
    fig = px.timeline(
        tt_df,
        x_start="Start",
        x_end="End",
        y="Day",
        color="Display Name",
        text="Timeline_Label", # <-- Update this line
        hover_name="Course",
        # ... rest of the function stays the same ...
        hover_data={"Name": True, "Location": True, "Start": "|%H:%M", "End": "|%H:%M", "Day": False, "Display Name": False, "Day_Int": False},
        color_discrete_map=course_colors, 
        height=460
    )
    
    fig.update_traces(textposition="inside", insidetextanchor="middle", textfont=dict(color="white"))
    fig.update_yaxes(categoryorder="array", categoryarray=["Sun", "Sat", "Fri", "Thu", "Wed", "Tue", "Mon"])
    fig.update_layout(
        autosize=True,
        xaxis_tickformat='%H:%M',
        xaxis_dtick=1800000, 
        xaxis_title="Time of Day",
        yaxis_title="Day of Week",
        showlegend=False,
        margin=dict(l=16, r=16, t=36, b=16)
    )
    return fig

def create_classic_grid_chart(tt_df, course_colors, base_date):
    """Build the vertical day-by-day schedule grid view.

    Args:
        tt_df: Render-ready dataframe with datetime start/end columns.
        course_colors: Mapping from display name to a fixed hex color.
        base_date: Reference date used to anchor the y-axis date scale.

    Returns:
        A configured Plotly figure for the classic grid view.
    """
    fig = go.Figure()
    
    for name in tt_df['Display Name'].unique():
        c_df = tt_df[tt_df['Display Name'] == name]
        durations_ms = (c_df['End'] - c_df['Start']).dt.total_seconds() * 1000
        hover_texts = c_df['Name'] + "<br>" + c_df['Start'].dt.strftime('%H:%M') + " - " + c_df['End'].dt.strftime('%H:%M')
        text_labels = c_df.apply(lambda r: f"<b>{r['Course']}</b><br>{r['Location']}" if r['Location'] else f"<b>{r['Course']}</b>", axis=1)

        # Each course gets its own trace so the color and hover text stay consistent.
        fig.add_trace(go.Bar(
            name=name,
            x=c_df['Day'],
            y=durations_ms,
            base=c_df['Start'],
            orientation='v',
            marker_color=course_colors[name],
            text=text_labels,
            textposition='inside',
            insidetextanchor='middle',
            hoverinfo='text',
            hovertext=hover_texts
        ))

    # Add Lunch Break visual cue (13:00 - 14:00)
    lunch_start = datetime.datetime.combine(base_date, datetime.time(13, 0))
    lunch_end = datetime.datetime.combine(base_date, datetime.time(14, 0))
    fig.add_hrect(
        y0=lunch_start, y1=lunch_end, 
        fillcolor="rgba(128, 128, 128, 0.2)", opacity=1, layer="below", line_width=0
    )
    
    # Anchor the lunch label near the middle selected day so it stays readable.
    unique_days = tt_df['Day'].unique()
    anchor_day = unique_days[len(unique_days) // 2] if len(unique_days) > 0 else "Wed"
    
    fig.add_annotation(
        x=anchor_day, 
        y=datetime.datetime.combine(base_date, datetime.time(13, 30)),
        text="<b>LUNCH</b>",
        showarrow=False,
        font=dict(size=18, color="gray")
    )
    
    fig.update_layout(
        autosize=True,
        barmode='overlay',
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(
            title="",
            categoryorder="array",
            categoryarray=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
            side="top",
            showgrid=True,
            gridcolor="rgba(128, 128, 128, 0.2)",
            linecolor="rgba(128, 128, 128, 0.5)"
        ),
        yaxis=dict(
            title="",
            type="date",
            autorange="reversed",
            tickformat='%H:%M',
            dtick=1800000, 
            showgrid=True,
            gridcolor="rgba(128, 128, 128, 0.2)",
            linecolor="rgba(128, 128, 128, 0.5)"
        ),
        showlegend=False,
        margin=dict(l=16, r=16, t=36, b=16),
        height=600
    )
    return fig