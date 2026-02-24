"""
Thin wrapper around the shared trend-narrative package.

The function signature (insight_df) is kept for compatibility with home.py.
All logic now lives in: https://github.com/yukinko-iwasaki/trend-narrative
"""

from trend_narrative import (
    get_segment_narrative as _get_segment_narrative,
    consolidate_segments,
    millify,
)


def get_segment_narrative(insight_df):
    """Generate a narrative string from a pre-filtered insight DataFrame.

    Parameters
    ----------
    insight_df : pd.DataFrame
        Single-row (or empty) DataFrame with columns:
        ``metric_name``, ``segments``, ``cv_value``.

    Returns
    -------
    str
        Plain-English trend narrative, or empty string when no data.
    """
    if insight_df is None or insight_df.empty:
        return ""

    metric = insight_df["metric_name"].iloc[0]
    segments = insight_df["segments"].iloc[0]
    cv = insight_df["cv_value"].iloc[0]

    return _get_segment_narrative(segments=segments, cv_value=cv, metric=metric)
