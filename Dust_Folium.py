import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import geopandas as gpd
from folium.plugins import LocateControl

# --- 1. App Configuration ---
st.set_page_config(page_title="SNOTEL Dust & Snowmelt Calculator", layout="wide")
st.title("Real-Time Dust & Snowmelt Calculator")
st.markdown("Calculate empirical albedo drop and melt acceleration using field snowpit data and SNOTEL station locations.")

# --- 2. The Data Engine ---
# Defining our stations and coordinates
station_data = [
    {"name": "Senator Beck", "lat": 37.906, "lon": -107.726, "k": 135.38, "elev": "12,186 ft"},
    {"name": "Devil's Thumb", "lat": 39.952, "lon": -105.684, "k": 105.28, "elev": "11,500 ft"},
    {"name": "Berthoud Pass", "lat": 39.798, "lon": -105.778, "k": 86.67, "elev": "11,307 ft"},
    {"name": "Rabbit Ears", "lat": 40.383, "lon": -106.600, "k": 73.63, "elev": "9,400 ft"},
    {"name": "Grand Mesa", "lat": 39.049, "lon": -108.050, "k": 96.60, "elev": "10,500 ft"}
]
df = pd.DataFrame(station_data)

# --- 3. The Sidebar Inputs ---
st.sidebar.header("Field Measurements")
st.sidebar.markdown("Input your physical snowpit data.")

# Define the baseline optical albedo for various snow grain types
snow_grain_albedos = {
    "Depth Hoar": 0.95,
    "Precipitation Particles (Fresh)": 0.90,
    "Faceted Grains": 0.89,
    "Rounded Grains (Old Dry)": 0.80, 
    "Melt-Freeze Grains (Wet)": 0.70
}

selected_grain = st.sidebar.selectbox(
    "Surface Snow Grain Type", 
    list(snow_grain_albedos.keys()),
    index=1,
    help="Determines the pristine baseline albedo before dust is applied."
)

dust_thickness = st.sidebar.number_input(
    "Dust Layer Thickness", 
    min_value=0.0, 
    value=15.0, 
    step=1.0,
    help="Multiply by 0.00067 to find base albedo drop."
)

depth_from_top = st.sidebar.number_input(
    "Depth from Top of Snowpack (cm)", 
    min_value=0.0, 
    value=1.0, 
    step=0.5,
    help="Dust deeper than 3cm will not impact surface albedo."
)

# --- 4. The Live Math Engine ---
# 1. Fetch the dynamic clean albedo based on user's grain selection
clean_albedo = snow_grain_albedos[selected_grain]

# 2. Calculate raw drop using the exact multiplier
raw_albedo_drop = dust_thickness * 0.00067

# 3. Apply the 3cm optical depth rule
if depth_from_top <= 3.0:
    active_albedo_drop = raw_albedo_drop
else:
    active_albedo_drop = 0.0

# 4. Apply the math to the dataframe
df['empirical_albedo'] = clean_albedo - active_albedo_drop

# Prevent albedo from dropping below a realistic dirt baseline (~0.35)
df['empirical_albedo'] = df['empirical_albedo'].clip(lower=0.35)

# Calculate the melt multiplier (how many times faster it is melting)
df['melt_multiplier'] = clean_albedo / df['empirical_albedo']

# --- Backtracking Logic ---
# To track the layer backward, we ensure the historical dust value NEVER equals zero 
# and never decreases, keeping a baseline trace of the layer's existence.
df['backtracked_layer_val'] = max(raw_albedo_drop, 0.001) 

# --- 5. Draw the Dynamic Folium Map ---
st.markdown("### Interactive Melt Acceleration Map")

# Center the map on Colorado
m = folium.Map(location=[39.2, -106.5], zoom_start=7, tiles=None)

# Add the GPS "Find My Location" Button
LocateControl(
    auto_start=False, 
    position='topleft',
    strings={'title': 'See your location on the map', 'popup': 'You are here'}
).add_to(m)

# Add the official Esri World Imagery Basemap
folium.TileLayer(
    tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    attr='Esri',
    name='Esri World Imagery',
    overlay=False,
    control=True
).add_to(m)

# --- 5.5 Add River Basins & Perform Spatial Join ---
try:
    # 1. Load the live URL from the State of Colorado
    # PASTE YOUR DIRECT ZIP LINK HERE
    cdss_url = "PASTE_YOUR_CDSS_LINK_HERE" 
    
    basins = gpd.read_file(cdss_url)
    basins = basins.to_crs(epsg=4326)
    
    # 2. Add basins to the map WITH hover labels (Tooltips)
    folium.GeoJson(
        basins,
        name="Major River Basins",
        style_function=lambda feature: {
            'fillColor': '#3186cc',
            'color': '#3186cc',
            'weight': 1.5,
            'fillOpacity': 0.15 
        },
        tooltip=folium.features.GeoJsonTooltip(
            fields=['HU6NAME'],
            aliases=['Watershed:'],
            style="background-color: white; color: #333333; font-family: arial; font-size: 12px; padding: 5px;"
        )
    ).add_to(m)

    # 3. THE GIS FLEX: Spatial Join
    # Turn our basic pandas dataframe into a geospatial dataframe
    gdf_stations = gpd.GeoDataFrame(
        df, geometry=gpd.points_from_xy(df.lon, df.lat), crs="EPSG:4326"
    )
    
    # Intersect the stations with the basin polygons to grab the HU6NAME
    joined = gpd.sjoin(gdf_stations, basins, how="left", predicate="intersects")
    
    # Save that watershed name back into our main dataframe
    df['watershed'] = joined['HU6NAME'].fillna("Unknown Basin")

except Exception as e:
    st.error(f"Could not load River Basins from CDSS: {e}")
    df['watershed'] = "Data Unavailable"

# --- Add Station Markers ---
for idx, row in df.iterrows():
    dynamic_radius = 6 * row['melt_multiplier']
    
    if row['melt_multiplier'] >= 2.0:
        marker_color = '#d73027' 
    elif row['melt_multiplier'] >= 1.4:
        marker_color = '#fc8d59' 
    else:
        marker_color = '#fee08b' 

    # We updated the popup text to include the newly calculated Watershed
    popup_text = f"""
    <b>{row['name']} ({row['elev']})</b><br>
    <b>Watershed:</b> {row['watershed']}<br>
    Clean Albedo: {clean_albedo:.2f}<br>
    Empirical Albedo: {row['empirical_albedo']:.2f}<br>
    <b>Melt Speed: {row['melt_multiplier']:.2f}x</b>
    """
    
    folium.CircleMarker(
        location=[row['lat'], row['lon']],
        radius=dynamic_radius,
        color='black',
        weight=1,
        fill=True,
        fill_color=marker_color,
        fill_opacity=0.8,
        tooltip=f"{row['name']} - Click for data",
        popup=folium.Popup(popup_text, max_width=250)
    ).add_to(m)

# Add a layer control box
folium.LayerControl().add_to(m)

# Render the map in Streamlit
st_folium(m, width=1000, height=600)

# --- 6. Show the Raw Data Table ---
st.markdown("### Live Site Data")
# Updated the table to include the new Watershed column
display_df = df[['name', 'elev', 'watershed', 'empirical_albedo', 'melt_multiplier', 'backtracked_layer_val']].copy()
display_df.columns = ['Station', 'Elevation', 'Watershed', 'Empirical Albedo', 'Melt Multiplier', 'Backtracked Val']
st.dataframe(display_df.style.format({
    'Empirical Albedo': '{:.2f}', 
    'Melt Multiplier': '{:.2f}x',
    'Backtracked Val': '{:.4f}'
}))
