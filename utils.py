import pandas as pd
import plotly.express as px
import unicodedata
import textwrap
import math
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from colormath.color_objects import sRGBColor, CMYKColor
from colormath.color_conversions import convert_color
from auth import AUTH_ENABLED
from collections import OrderedDict
from constants import (
    NARRATIVE_ERROR_TEMPLATES,
    START_YEAR,
    TREND_THRESHOLDS,
)
from dash import dcc, get_app, html
from flask_login import current_user
from math import isnan
from shapely.geometry import shape, MultiPolygon, Polygon


CORRELATION_THRESHOLDS = {
    0: "no",
    0.1: "no",
    0.3: "weak",
    0.7: "moderate",
    0.9: "strong",
    1: "very strong",
}

# Constant for which region to sample for disputed overlay color
DISPUTED_REGION_COLOR_SAMPLE = {
    "Ilemi Triangle": "Turkana"
}
DISPUTED_REGION_DEFAULT_COLOR = "rgba(211, 211, 211, 0.3)" # gray

def _blend_region_and_gray(fig, region):
    """
    Sample the color from the main map for the specified region and blend it with the given gray color in CMYK space.
    If the region is not found, return the gray color.
    """
    region = DISPUTED_REGION_COLOR_SAMPLE.get(region)
    if region is None:
        return DISPUTED_REGION_DEFAULT_COLOR

    region_col = None

    # Find the first choropleth trace with color assignments
    tr = fig.data[0] if fig.data else None
    if tr and hasattr(tr, "locations") and hasattr(tr, "z"):
        if region in tr.locations:
            idx = list(tr.locations).index(region)
            z_val = tr.z[idx] if isinstance(tr.z, (list, tuple, np.ndarray)) else tr.z

            # Extract colorscale and normalize z value
            coloraxis = getattr(fig.layout, tr.coloraxis, None) if hasattr(tr, "coloraxis") else None
            colorscale = getattr(coloraxis, "colorscale", None)
            cmin =  min(tr.z)
            cmax = max(tr.z)

            if pd.isna(cmin):
                return DISPUTED_REGION_DEFAULT_COLOR
            if colorscale:
                # Ensure norm is a valid float between 0 and 1
                norm = max(0.0, min(1.0, float((z_val - cmin) / (cmax - cmin)))) if cmax != cmin else 0.5
                colors = [c[1] for c in colorscale]
                region_col = px.colors.sample_colorscale(colors, norm, colortype='tuple')[0]
            else:
                raise ValueError("Colorscale not found or invalid")

    if region_col is None:
        return DISPUTED_REGION_DEFAULT_COLOR

    # Blend the sampled color with the gray color in CMYK space
    def to_rgba_str(vals):
        return f"rgba({int(vals[0])}, {int(vals[1])}, {int(vals[2])}, 0.5)"

    t_rgb = sRGBColor(region_col[0], region_col[1], region_col[2])
    g_rgb = sRGBColor(211 / 255.0, 211 / 255.0, 211 / 255.0)  # Default gray color

    t_cmyk = convert_color(t_rgb, CMYKColor)
    g_cmyk = convert_color(g_rgb, CMYKColor)

    blended_cmyk = CMYKColor(
        (t_cmyk.cmyk_c + g_cmyk.cmyk_c) / 2,
        (t_cmyk.cmyk_m + g_cmyk.cmyk_m) / 2,
        (t_cmyk.cmyk_y + g_cmyk.cmyk_y) / 2,
        (t_cmyk.cmyk_k + g_cmyk.cmyk_k) / 2,
    )

    blended_rgb = convert_color(blended_cmyk, sRGBColor).get_upscaled_value_tuple()

    # Average alpha
    return to_rgba_str(blended_rgb)


def parse_rgba_str(s):
    """Parse an RGBA or hex color string into a list of [r, g, b, a]."""
    s = s.strip()
    if s.startswith("#"):
        h = s.lstrip("#")
        r, g, b = tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
        return [r, g, b, 1.0]
    if s.startswith("rgb"):
        vals = s.replace("rgba(", "").replace("rgb(", "").replace(")", "").split(",")
        vals = [float(v) for v in vals]
        if len(vals) == 3:
            vals.append(1.0)
        return vals
    return [211, 211, 211, 0.3]  # Default fallback color


def filter_country_sort_year(df, country, start_year=START_YEAR):
    """
    Preprocess the dataframe to filter by country and sort by year
    :param df: DataFrame
    :param country: str
    :return: DataFrame
    """
    df = df.loc[df["country_name"] == country]

    df = df[df.year >= start_year]
    if not df.empty:
        earliest_year = df["year"].min()
        df["earliest_year"] = earliest_year

    df = df.sort_values(["year"], ascending=False)

    return df


millnames = ["", " K", " M", " B", " T"]


def millify(n):
    n = float(n)
    millidx = max(
        0,
        min(
            len(millnames) - 1, int(math.floor(0 if n == 0 else math.log10(abs(n)) / 3))
        ),
    )

    return "{:.2f}{}".format(n / 10 ** (3 * millidx), millnames[millidx])


def filter_geojson_by_country(geojson, country):
    """Filter geojson object by country
    Params:
        geojson (GeoJSON object): input geojson
        country:  str
    """
    filtered_features = [
        feature
        for feature in geojson["features"]
        if feature["properties"].get("country") == country
    ]
    filtered_geojson = {"type": "FeatureCollection", "features": filtered_features}
    return filtered_geojson


def map_center(geojson):
    polygons = []
    for feature in geojson["features"]:
        geom = shape(feature["geometry"])
        if isinstance(geom, Polygon):  # If it's a single Polygon, add it directly
            polygons.append(geom)
        elif isinstance(
            geom, MultiPolygon
        ):  # If it's a MultiPolygon, extend the list with its polygons
            polygons.extend(geom.geoms)

    if len(polygons) > 1:
        multi_polygon = MultiPolygon(polygons)
    else:
        multi_polygon = polygons[0]

    centroid = multi_polygon.centroid
    center_lat, center_lon = (centroid.y, centroid.x)

    return {"lat": center_lat, "lon": center_lon}


def empty_plot(message, fig_title="", max_line_length=40):
    wrapped_text = "<br>".join(textwrap.wrap(message, width=max_line_length))

    fig = go.Figure()
    fig.add_annotation(
        text=wrapped_text,
        xref="paper",
        yref="paper",
        x=0.5,
        xanchor="center",
        showarrow=False,
        font=dict(size=14),
    )
    fig.update_layout(
        title=fig_title,
        xaxis={"visible": False},
        yaxis={"visible": False},
    )
    return fig


def get_percentage_change_text(percent):
    if abs(percent) < 0.01:
        return "mostly remained unchanged"
    elif percent > 0:
        return f"increased by {percent:.0%}"
    else:
        return f"decreased by {-1 * percent:.0%}"


# TODO: add unit tests
def get_ts_correlation_text(
    df,
    x_col,
    y_col,
    *,
    min_n_unknown=6,         # below this: "unknown"
    min_n_caution=10,        # below this: add small-sample caution
    warn_delta=0.25,         # warn if levels vs changes differ a lot
    use_logdiff_for_x=True,  # spending: log-diff by default
):
    """
    Time-series correlation narrative for national spending (real currency) vs outcome index (0-1).

    Primary statistic: Pearson correlation on transformed series:
      - x (spending): log difference Δlog(x) if possible, else % change, else first difference
      - y (outcome index): first difference Δy

    Secondary diagnostic: Pearson correlation on levels (x, y) to flag trend-driven/spurious patterns.

    Params
    ------
    df: DataFrame
    x_col / y_col: {"col_name": str, "display": str}
    min_n_unknown: int
        If effective sample size after transformation is < min_n_unknown, return "unknown".
    min_n_caution: int
        If effective sample size < min_n_caution, append a caution note.
    warn_delta: float
        If |corr_levels - corr_changes| >= warn_delta or sign differs, warn about trend sensitivity.
    use_logdiff_for_x: bool
        Try log-diff for x when x values are strictly positive.
    """

    x = x_col["col_name"]
    y = y_col["col_name"]
    x_name = x_col["display"]
    y_name = y_col["display"]

    d0 = df[[x, y]].dropna()
    if d0.shape[0] < min_n_unknown:
        return (
            f"the association between {y_name} and {x_name} is unknown due to limited time coverage "
            f"or insufficient variability."
        )

    # --- Transformations ---
    # y: first difference (index 0-1 -> percentage-point-like change)
    dy = d0[y].diff()

    # x: prefer log difference (approx % change), fallback to % change, fallback to first diff
    x_series = d0[x].astype(float)

    dx = None
    x_transform_label = None

    if use_logdiff_for_x and (x_series > 0).all():
        dx = np.log(x_series).diff()
        x_transform_label = "log change (approx. % change)"
    else:
        # % change requires previous value > 0
        prev = x_series.shift(1)
        pct = x_series.diff() / prev
        if (prev > 0).all():
            dx = pct
            x_transform_label = "% change"
        else:
            dx = x_series.diff()
            x_transform_label = "absolute change"

    dchg = np.c_[dx.values, dy.values]
    # drop rows where either diff is nan/inf (first row will be nan by construction)
    mask = np.isfinite(dchg).all(axis=1)
    dx2 = dx[mask]
    dy2 = dy[mask]

    n_eff = int(min(dx2.shape[0], dy2.shape[0]))
    if n_eff < min_n_unknown:
        return (
            f"the association between {y_name} and {x_name} is unknown due to limited time coverage "
            f"or insufficient variability."
        )

    corr_changes = float(dx2.corr(dy2, method="pearson"))
    if isnan(corr_changes):
        return (
            f"the association between {y_name} and {x_name} is unknown due to limited data availability "
            f"or variability."
        )

    # Secondary diagnostic: levels correlation (often trend-driven)
    corr_levels = float(d0[x].corr(d0[y], method="pearson"))

    # Trend sensitivity flag: sign flip or big divergence levels vs changes
    trend_sensitive = False
    if not isnan(corr_levels):
        if np.sign(corr_levels) != np.sign(corr_changes):
            trend_sensitive = True
        elif abs(corr_levels - corr_changes) >= warn_delta:
            trend_sensitive = True

    # --- Narrative pieces ---
    if corr_changes > 0:
        direction = "positive"
        assoc_phrase = "faster growth in"
    else:
        direction = "inverse"
        assoc_phrase = "slower growth in"

    intensity = None
    for threshold, pcc_text in sorted(CORRELATION_THRESHOLDS.items(), key=lambda kv: float(kv[0])):
        if abs(corr_changes) <= float(threshold):
            intensity = pcc_text
            break

    if intensity == "no":
        text = (
            f"there is no clear association between year-to-year changes in {y_name} and "
            f"{x_name}."
        )
    else:
        text = (
            f"the correlation between year-to-year changes in {y_name} and {x_name} is "
            f"{corr_changes:.1f}, indicating a {intensity} {direction} relationship. "
            f"Years with {assoc_phrase} {x_name} are generally associated with "
            f"{'larger' if corr_changes > 0 else 'smaller'} improvements in {y_name}."
        )

    notes = []
    notes.append(f"{x_name} is measured as {x_transform_label}, and {y_name} as year-to-year changes.")

    if n_eff < min_n_caution:
        notes.append("interpret with caution due to limited time coverage")

    if trend_sensitive:
        notes.append("the association appears sensitive to long-term trends (levels correlation differs from changes)")

    if notes:
        text += " Note: " + "; ".join(notes) + "."

    return text


# TODO: rename to get_subnat_correlation_text & use in subnat analysis
# TODO: adjust language based on number of data points
def get_correlation_text(df, x_col, y_col):
    """
    Get the correlation text based on Spearman correlation with Pearson as secondary check
    :param df: DataFrame
    :param x_col: {"col_name": str, "display": str} // col_name is the column name in the DataFrame and display is the name to be displayed in the text
    :param y_col: {"col_name": str, "display": str} // col_name is the column name in the DataFrame and display is the name to be displayed in the text
    :return: str
    """
    spearman_corr = df[x_col["col_name"]].corr(df[y_col["col_name"]], method='spearman')
    pearson_corr = df[x_col["col_name"]].corr(df[y_col["col_name"]], method='pearson')

    x_display_name = x_col["display"]
    y_display_name = y_col["display"]

    if isnan(spearman_corr) or df.shape[0] <= 2:
        return f"the correlation between {x_display_name} and {y_display_name} is unknown due to limited data availability or variability."

    corr = spearman_corr

    opposite_signs = False
    if not isnan(pearson_corr):
        if (spearman_corr > 0 and pearson_corr < 0) or (spearman_corr < 0 and pearson_corr > 0):
            opposite_signs = True

    # TODO: try handling outliers before giving up
    if opposite_signs:
        return f"the association between {y_display_name} and {x_display_name} is sensitive to outliers."

    if corr > 0:
        direction = "positive"
        association = "higher"
    else:
        direction = "inverse"
        association = "lower"

    intensity = None
    for threshold, pcc_text in sorted(CORRELATION_THRESHOLDS.items()):
        if abs(corr) <= float(threshold):
            intensity = pcc_text
            break

    if intensity == "no":
        return f"there is no correlation between {y_display_name} and {x_display_name}."

    text = f"the correlation between {y_display_name} and {x_display_name} is {corr:.1f}, indicating a {intensity} {direction} relationship. Higher {y_display_name} is generally associated with {association} {x_display_name}."""
    return text


def detect_trend(df, x_col):
    """
    Detect the trend of the data based on the PCC value
    :param df: DataFrame
    :param x_col: str
    :return: str
    """
    pcc = df.year.corr(df[x_col["col_name"]])
    abs_pcc = abs(pcc)
    if abs_pcc > TREND_THRESHOLDS:
        if pcc > 0:
            return "an increasing trend"
        else:
            return "a decreasing trend"

    return ""


def generate_error_prompt(template_key, **kwargs):
    """
    Generate a prompt message based on the template and the keyword arguments
    :param template: str
    :param kwargs: dict
    :return: str
    """
    template = NARRATIVE_ERROR_TEMPLATES[template_key]
    return template.format(**kwargs)


def remove_accents(input_str):
    normalized_str = unicodedata.normalize("NFD", input_str)
    stripped_str = "".join(c for c in normalized_str if not unicodedata.combining(c))
    return stripped_str


zoom = {
    "Albania": 5.7,
    "Bangladesh": 5,
    "Bhutan": 6,
    "Burkina Faso": 4.7,
    "Colombia": 3.6,
    "Kenya": 4.35,
    "Mozambique": 3.35,
    "Nigeria": 4.2,
    "Pakistan": 3.7,
    "Paraguay": 4.4,
    "Tunisia": 4.5,
    "Chile": 1,
}


def add_opacity(rgb, opacity):
    first = rgb.split(")")[0]
    rgba = (first + "," + str(opacity) + ")").replace("rgb", "rgba")
    return rgba


def get_prefixed_path(pathname):
    base_path = get_app().config.requests_pathname_prefix
    return f"{base_path.rstrip('/')}/{pathname}"


def get_login_path():
    return get_prefixed_path("login")


def require_login(layout_func):
    def wrapper(*args, **kwargs):
        if not AUTH_ENABLED or current_user.is_authenticated:
            return layout_func(*args, **kwargs)
        else:
            return html.Div([
                dcc.Location(pathname=get_login_path(), id="redirect-to-login")
            ])

    return wrapper


def calculate_cagr(start_value, end_value, time_period):
    if isinstance(time_period, (np.integer, np.floating)):
        time_period = int(time_period)
    if (
        start_value is None
        or end_value is None
        or pd.isna(start_value)
        or pd.isna(end_value)
    ):
        return None
    if not isinstance(time_period, (int, float)) or time_period <= 0:
        return None
    if start_value <= 0:
        return None
    if start_value == end_value:
        return 0.0
    cagr = ((end_value / start_value) ** (1 / time_period) - 1) * 100
    return cagr


def add_disputed_overlay(fig, disputed_geojson, zoom):
    """
    Adds disputed region overlay to a choropleth mapbox figure.
    Args:
        fig: plotly figure to add the overlay to
        disputed_geojson: geojson for disputed regions
        zoom: map zoom level
        color: overlay color (default: light gray)
    """
    if not disputed_geojson:
        return fig

    disputed_regions = []
    color_map = {}
    for f in disputed_geojson.get("features", []):
        region_name = f["properties"]["region"]
        disputed_regions.append(region_name)
        color_map[region_name] = _blend_region_and_gray(fig, region_name)

    if not disputed_regions:
        return fig

    df_disputed = pd.DataFrame({"region_name": disputed_regions})

    trace = px.choropleth_mapbox(
        df_disputed,
        geojson=disputed_geojson,
        locations="region_name",
        featureidkey="properties.region",
        color="region_name",
        color_discrete_map=color_map,
        zoom=zoom,
    ).data[0]
    # Remove border by setting marker.line.width to 0
    if hasattr(trace, "marker") and hasattr(trace.marker, "line"):
        trace.marker.line.width = 0
    trace.hovertemplate = "Region: %{location}<extra></extra>"
    trace.showscale = False
    trace.showlegend = False
    fig.add_trace(trace)

    # Simulate dashed border overlay
    def add_dashed_line(lons, lats, dash_length=1, gap_length=1):
        # dash_length and gap_length are in number of points, not meters
        n = len(lons)
        i = 0
        while i < n - 1:
            # Draw dash
            dash_end = min(i + dash_length, n - 1)
            fig.add_trace(go.Scattermapbox(
                lon=list(lons[i:dash_end+1]),
                lat=list(lats[i:dash_end+1]),
                mode="lines",
                line=dict(color="black", width=2),
                fill=None,
                showlegend=False,
                hoverinfo="skip",
            ))
            i = dash_end + gap_length

    for feature in disputed_geojson["features"]:
        geometry = feature["geometry"]
        polygons = geometry["coordinates"]

        for poly in polygons:
            # poly is a list of linear rings, first is exterior
            if not poly or not poly[0]:
                continue
            exterior = poly[0]
            if len(exterior) < 2:
                continue
            lons, lats = zip(*exterior)
            add_dashed_line(lons, lats)
    return fig
