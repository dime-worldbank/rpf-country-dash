from utils import millify

# Coefficient of Variation thresholds for narrative generation
CV_LOW_THRESHOLD = 5
CV_MODERATE_THRESHOLD = 15

def get_segment_narrative(insight_df):
    if insight_df is None or insight_df.empty:
        return ""
    
    metric = insight_df['metric_name'].iloc[0]
    segments = insight_df['segments'].iloc[0]
    cv = insight_df['cv_value'].iloc[0]
    narrative = []
    # TODO : refine the logic to add narratives on acceleration/deceleration, for now just consolidate same direction
    segments = consolidate_segments(segments)
    if len(segments) == 0:
        if cv < CV_LOW_THRESHOLD:
            return f"{metric} remained highly stable and range-bound"
        elif CV_LOW_THRESHOLD <= cv <= CV_MODERATE_THRESHOLD:
            return f"{metric} showed moderate fluctuations around a consistent mean"
        else:
            return f"{metric} exhibited significant volatility without a clear direction"
    if len(segments) == 1:
        seg = segments[0]
        start_val = seg['start_value']
        end_val = seg['end_value']
        
        
        total_change = end_val - start_val
        pct_change = (total_change / start_val) * 100
        direction = "increased" if total_change > 0 else "decreased"
        
        return (f"between {seg['start_year']} and {seg['end_year']}, "
                f"the {metric} {direction} by {millify(abs(total_change))} "
                f"({pct_change:+.2f}%), maintaining a consistent trajectory.")

    prefix = ['Trend then shifted,', 'This trajectory pivoted again,',  'Then,']
    for i, seg in enumerate(segments):
        direction = "an upward" if seg['slope'] > 0 else "a downward"
        
        if i == 0:
            narrative.append(f"From {seg['start_year']} to {seg['end_year']}, the {metric} showed {direction} trend.")
        else:
            prev_slope = segments[i-1]['slope']
            
            # Check for a "Sign Flip" (Peak or Trough)
            if (prev_slope > 0 and seg['slope'] < 0):
                transition = f"reaching a peak in {seg['start_year']} before reversing into a decline."
            elif (prev_slope < 0 and seg['slope'] > 0):
                transition = f"hitting a low in {seg['start_year']} followed by a recovery."
            else:
                transition = f"continuing its {direction} path through {seg['end_year']}."
            
            narrative.append(f"{prefix[i-1]} {transition}")

    return " ".join(narrative)

def consolidate_segments(segments):
    if not segments:
        return []
    
    consolidated = [segments[0]]
    
    for seg in segments[1:]:
        last_seg = consolidated[-1]
        # Check if the slope direction is the same
        if (last_seg['slope'] >= 0 and seg['slope'] >= 0) or (last_seg['slope'] < 0 and seg['slope'] < 0):
            # Merge segments
            last_seg['end_year'] = seg['end_year']
            last_seg['end_value'] = seg['end_value']
            duration = last_seg['end_year'] - last_seg['start_year']
            if duration != 0:
                last_seg['slope'] = (last_seg['end_value'] - last_seg['start_value']) / duration
            else:
                # Zero duration: treat as flat slope to avoid division by zero
                last_seg['slope'] = 0
        else:
            consolidated.append(seg)
    
    return consolidated