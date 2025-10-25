#!/usr/bin/env python3
"""
InSAR Mapper
-------------
A command-line tool to filter and visualize InSAR target data on an interactive Folium map.

Usage:
    python insar_mapper.py --file InSAR_designated_Target_Database.xlsx \
        --countries NLD BEL \
        --active \
        --valid \
        --instrClass CR IGRS TR \
        --strict False \
        --map-title "Active InSAR Targets (NLD & BEL)" \
        --background "Cartodb Positron" \
        --save-html insar_map.html \
        --save-geojson insar_points.geojson
-------------
Written by: Heiko Rotteveel (Delft University of Technology)
Date: October 2025
License: CC-BY SA 4.0
"""

import argparse
import pandas as pd
import folium
import geopandas as gpd
from shapely.geometry import Point
import matplotlib.colors as mcolors

# -------------------------------------------------------------------
# Helper: Filter logging
# -------------------------------------------------------------------
def log_filter_stats(df_before, df_after, filter_name):
    """Helper function to print filter statistics (rows kept, removed, and percentage)."""
    before, after = len(df_before), len(df_after)
    removed = before - after
    pct = (after / before * 100) if before > 0 else 0
    print(f"    ↳ {filter_name}: kept {after}/{before} rows ({pct:.1f}%), removed {removed}.\n")

# -------------------------------------------------------------------
# Data Reading and Filters
# -------------------------------------------------------------------
def read_insar_db(filepath, columns=None):
    """
    Reads the 'insarTargets' sheet from the given Excel file into a DataFrame.

    Args:
        filepath (str): Path to the Excel file.
        columns (list, optional): List of columns to keep. If None, all columns are kept.

    Returns:
        pd.DataFrame: Cleaned DataFrame with optional column selection.
    """

    print(f"--> Reading InSAR database from '{filepath}'...")
    df = pd.read_excel(filepath, sheet_name='insarTargets')
    df.columns = df.iloc[0]
    df.drop(df.index[0], inplace=True)

    if columns:
        df = df.loc[:, columns]
        print(f"--> Selected {len(columns)} columns.")

    print(f"--> Data loaded: {len(df)} records, {len(df.columns)} columns.\n")
    return df

def filter_valid(df):
    """Filters DataFrame to include only rows where 'valid' == True."""
    print("--> Filtering valid entries...")
    df_before = df.copy()
    filtered_df = df[df["valid"] == True]
    log_filter_stats(df_before, filtered_df, "Valid filter")
    return filtered_df

def filter_country(df, countries):
    """Filters DataFrame to include only rows with a 'countryCode' in the given list."""
    print(f"--> Filtering for countries: {countries}...")
    df_before = df.copy()
    filtered_df = df[df["countryCode"].isin(countries)]
    log_filter_stats(df_before, filtered_df, "Country filter")
    return filtered_df

def filter_active(df):
    """Filters DataFrame to include only rows with active targets"""
    print("--> Filtering active InSAR targets...")
    df_before = df.copy()
    filtered_df = df[df["insarEnd"] == 99999999]
    log_filter_stats(df_before, filtered_df, "Active targets filter")
    return filtered_df

def filter_satSys(df, satSystems=['S1A', 'RS2']):
    """
    Filters DataFrame to include rows whose 'satSys' contains 'All' or matches any given satellite system.
    """
    print(f"--> Filtering for satellite systems: {satSystems}...")
    df_before = df.copy()
    df = df.copy()
    df['satSys'] = df['satSys'].astype(str)
    mask = (
        df['satSys'].str.contains('All', case=False, na=False) |
        df['satSys'].apply(lambda x: any(sat in x for sat in satSystems))
    )
    filtered_df = df[mask]
    log_filter_stats(df_before, filtered_df, "Satellite system filter")
    return filtered_df

def filter_instrClass(df, types=["CR"], strict=True):
    """Filters DataFrame by 'instrClass' field. If strict=True, matches exact values; otherwise allows substring matches."""
    print(f"--> Filtering by instrument class: {types} (strict={strict})...")
    df_before = df.copy()
    df = df.copy()
    df["instrClass"] = df["instrClass"].astype(str)

    if strict:
        filtered_df = df[df["instrClass"].isin(types)]
    else:
        mask = df["instrClass"].apply(lambda x: any(instr in x for instr in types))
        filtered_df = df[mask].copy()

        # Normalize mixed instrument classes
        def normalize(instr):
            for t in types:
                if t in instr:
                    return t
            return instr
        filtered_df["instrClass"] = filtered_df["instrClass"].apply(normalize)

    log_filter_stats(df_before, filtered_df, "Instrument class filter")
    return filtered_df

def filter_owner(df, owners=['TUD']):
    """Filters DataFrame to include only rows where 'owner' is in the given list."""
    print(f"--> Filtering for owners: {owners}...")
    df_before = df.copy()
    filtered_df = df[df['owner'].isin(owners)]
    log_filter_stats(df_before, filtered_df, "Owner filter")
    return filtered_df

def filter_siteId(df, sites=['HENGELO']):
    """Filters DataFrame to include only rows where 'siteId' is in the given list."""
    print(f"--> Filtering for site IDs: {sites}...")
    df_before = df.copy()
    filtered_df = df[df['siteId'].isin(sites)]
    log_filter_stats(df_before, filtered_df, "Site ID filter")
    return filtered_df

def filter_lookDir(df, directions=['E']):
    """
    Filters DataFrame by 'lookDir' (satellite look direction).
    Allows substring matches for flexibility.
    """
    print(f"--> Filtering for look directions: {directions}...")
    df_before = df.copy()
    df = df.copy()
    df['lookDir'] = df['lookDir'].astype(str)
    mask = df['lookDir'].apply(lambda x: any(direction in x for direction in directions))
    filtered_df = df[mask]
    log_filter_stats(df_before, filtered_df, "Look direction filter")
    return filtered_df
# -------------------------------------------------------------------
# Mapping Function
# -------------------------------------------------------------------
def plot_insar_points_interactive(
    df,
    lat_col="latitude",
    lon_col="longitude",
    owner_col="owner",
    instr_col="instrClass",
    popup_cols=["siteId", "owner", "instrClass", "countryCode"],
    map_title="InSAR Target Locations",
    zoom_start=6,
    save_html_path=None,
    save_geojson_path="insar_points.geojson",
    background="OpenStreetMap"
):
    """
    Plots InSAR targets interactively with colors by owner, shapes by instrument class,
    adds a legend, and exports points to GeoJSON.

    Args:
        df (pd.DataFrame): Must contain latitude and longitude columns.
        lat_col (str): Latitude column name.
        lon_col (str): Longitude column name.
        owner_col (str): Column used for color-coding.
        instr_col (str): Column used for marker shapes.
        popup_cols (list): Columns to display when clicking points.
        map_title (str): Title of the map.
        zoom_start (int): Initial zoom level.
        save_html_path (str, optional): Path to save interactive HTML map.
        save_geojson_path (str, optional): Path to save GeoJSON file.
        background (str, optional): name of leaflet map (see: https://leaflet-extras.github.io/leaflet-providers/preview/)

    Returns:
        folium.Map: Interactive Folium map.
    """

    # Basic checks
    if df.empty:
        print("Error: No data to plot (DataFrame is empty).")
        return None
    if lat_col not in df.columns or lon_col not in df.columns:
        print("Error: Missing latitude or longitude columns.")
        return None

    print(f"--> Creating interactive map for {len(df)} InSAR points...")

    # Create color map for owners
    owners = sorted(df[owner_col].dropna().unique())
    colors = list(mcolors.TABLEAU_COLORS.values())
    while len(colors) < len(owners):
        colors += list(mcolors.CSS4_COLORS.values())
    owner_color_map = {owner: colors[i] for i, owner in enumerate(owners)}

    # Marker shapes for instrument class
    icon_shapes = ["circle", "triangle", "square", "star", "diamond"]
    instr_classes = sorted(df[instr_col].dropna().unique())
    instr_icon_map = {instr: icon_shapes[i % len(icon_shapes)] for i, instr in enumerate(instr_classes)}

    # Compute center of map
    center_lat = df[lat_col].astype(float).mean()
    center_lon = df[lon_col].astype(float).mean()
    m = folium.Map(location=[center_lat, center_lon], zoom_start=zoom_start, tiles=background)

    # Add points to map
    for _, row in df.iterrows():
        lat, lon = float(row[lat_col]), float(row[lon_col])
        owner = row.get(owner_col, "Unknown")
        instr = row.get(instr_col, "Unknown")

        # Build popup info
        popup_text = "<br>".join([f"<b>{col}:</b> {row[col]}" for col in popup_cols if col in df.columns])

        # Get color and shape
        color = owner_color_map.get(owner, "gray")
        shape = instr_icon_map.get(instr, "circle")

        # Map folium marker types
        if shape == "circle":
            marker = folium.CircleMarker(location=[lat, lon], radius=5, color=color, fill=True,
                                         fill_color=color, fill_opacity=0.9,
                                         popup=folium.Popup(popup_text, max_width=250))
        else:
            marker = folium.RegularPolygonMarker(
                location=[lat, lon],
                number_of_sides={"triangle": 3, "square": 4, "star": 5, "diamond": 4}.get(shape, 4),
                radius=7, color=color, fill=True, fill_color=color,
                fill_opacity=0.9, popup=folium.Popup(popup_text, max_width=250)
            )
        marker.add_to(m)

    # Add title
    m.get_root().html.add_child(folium.Element(
        f"<h3 align='center' style='font-size:16px'><b>{map_title}</b></h3>"
    ))

    # Add legend
    legend_html = """<div style='position: fixed; 
                    bottom: 50px; 
                    left: 50px; 
                    width: 220px; 
                    background-color: white; 
                    border:2px solid grey; 
                    z-index:9999; 
                    font-size:12px; 
                    padding: 10px;'> 
                    <b>Legend</b><br>"""

    legend_html += "<u>Owners</u><br>"
    for owner, color in owner_color_map.items(): legend_html += (f"<i style='background:{color};" 
                                                                 f"width:10px;" 
                                                                 f"height:10px;" 
                                                                 f"float:left;" 
                                                                 f"margin-right:6px;" 
                                                                 f"border:1px solid grey'>" 
                                                                 f"</i>{owner}<br>")
    legend_html += "<br><u>Instrument Class</u><br>"
    for instr, shape in instr_icon_map.items(): legend_html += f"&#9679; {instr} ({shape})<br>"
    legend_html += "</div>"

    m.get_root().html.add_child(folium.Element(legend_html))

    # Export to GeoJSON
    gdf = gpd.GeoDataFrame(df.copy(),
        geometry=[Point(xy) for xy in zip(df[lon_col].astype(float), df[lat_col].astype(float))],
        crs="EPSG:4326"
    )
    gdf.to_file(save_geojson_path, driver="GeoJSON")
    print(f"    ↳ GeoJSON saved: {save_geojson_path}")

    # Save HTML
    if save_html_path:
        m.save(save_html_path)
        print(f"    ↳ HTML map saved: {save_html_path}")

    print("--> Interactive map ready.\n")
    return m

# -------------------------------------------------------------------
# Command-Line Entry Point
# -------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="InSAR Target Database Filter & Mapper")

    parser.add_argument("--file", required=True, help="Path to the InSAR Excel database file")

    # Set defaults to your original “basic values”
    parser.add_argument("--countries", nargs="*", default=["NLD", "BEL"], help="Filter by country codes")
    parser.add_argument("--owners", nargs="*", default=None, help="Filter by owners")
    parser.add_argument("--instrClass", nargs="*", default=["CR", "IGRS", "TR"], help="Filter by instrument classes")
    parser.add_argument("--strict", type=lambda x: x.lower() == "true", default=False, help="Strict instrument filtering (True/False)")
    parser.add_argument("--active", action="store_true", default=True, help="Filter only active targets (insarEnd == 99999999)")
    parser.add_argument("--valid", action="store_true", default=True, help="Filter only valid entries")

    parser.add_argument("--background", default="Cartodb Positron", help="Map tile provider")
    parser.add_argument("--map-title", default="InSAR Target Locations", help="Map title")
    parser.add_argument("--save-html", default="insar_map.html", help="Output HTML map filename")
    parser.add_argument("--save-geojson", default="insar_points.geojson", help="Output GeoJSON filename")
    parser.add_argument("--save-csv", default=None, help="Output CSV filename")

    args = parser.parse_args()

    # Columns we always want
    columns = [
        "instrClass", "owner", "siteId", "countryCode", "insarStart", "insarEnd",
        "lookDir", "latitude", "longitude", "refFrame", "valid", "satSys"
    ]

    # Read database
    df = read_insar_db(args.file, columns)

    # Apply filters only if the argument is not None or empty
    if args.countries:
        df = filter_country(df, args.countries)
    if args.valid:
        df = filter_valid(df)
    if args.active:
        df = filter_active(df)
    if args.instrClass:
        df = filter_instrClass(df, types=args.instrClass, strict=args.strict)
    if args.owners:
        df = df[df["owner"].isin(args.owners)]

    if args.save_csv:
        df.to_csv(args.save_csv, index=False)

    # Plot map
    plot_insar_points_interactive(
        df,
        map_title=args.map_title,
        save_html_path=args.save_html,
        save_geojson_path=args.save_geojson,
        background=args.background
    )

if __name__ == "__main__":
    main()
