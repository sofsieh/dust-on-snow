import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import geopandas as gpd

# --- 1. App Configuration ---
st.set_page_config(page_title="SNOTEL Dust & Snowmelt Calculator", layout="wide")
st.title("Real-Time Dust & Snowmelt Calculator")
st.markdown("Calculate empirical albedo drop and melt acceleration using field snowpit data and SNOTEL station locations.")

# --- 2. The Data Engine ---
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
    index=1
)

dust_thickness = st.sidebar.number_input("Dust Layer Thickness", min_value=0.0, value=15.0, step=1.0)
depth_from_top = st.sidebar.number_input("Depth from Top of Snowpack (cm)", min_value=0.0, value=1.0, step=0.5)

# --- 4. The Live Math Engine ---
clean_albedo = snow_grain_albedos[selected_grain]
raw_albedo_drop = dust_thickness * 0.00067

if depth_from_top <= 3.0:
    active_albedo_drop = raw_albedo_drop
else:
    active_albedo_drop = 0.0

df['empirical_albedo'] = clean_albedo - active_albedo_drop
df['empirical_albedo'] = df['empirical_albedo'].clip(lower=0.35)
df['melt_multiplier'] = clean_albedo / df['empirical_albedo']
df['backtracked_layer_val'] = max(raw_albedo_drop, 0.001) 

# --- 5. Draw the Dynamic Folium Map ---
st.markdown("### Interactive Melt Acceleration Map")

m = folium.Map(location=[39.2, -106.5], zoom_start=7, tiles=None)

folium.TileLayer(
    tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    attr='Esri',
    name='Esri World Imagery',
    overlay=False,
    control=True
).add_to(m)

# --- 5.5 Add the River Basins Shapefile ---
try:
    # Tell Geopandas to read directly inside the zipped folder
    basins = gpd.read_file("zip://All_River_Basins.zip")
    
    # Convert to the standard web map coordinate system (WGS84)
    basins = basins.to_crs(epsg=4326)
    
    # Add to the Folium map
    folium.GeoJson(
        basins,
        name="Colorado River Basins",
        style_function=lambda feature: {
            'fillColor': '#3186cc',
            'color': '#3186cc',
            'weight': 1.5,
            'fillOpacity': 0.15 
        }
    ).add_to(m)
except Exception as e:
    st.error(f"Could not load River Basins: {e}")

# Add our dynamic station markers to the map
for idx, row in df.iterrows():
    dynamic_radius = 6 * row['melt_multiplier']
    
    if row['melt_multiplier'] >= 2.0:
        marker_color = '#d73027' 
    elif row['melt_multiplier'] >= 1.4:
        marker_color = '#fc8d59' 
    else:
        marker_color = '#fee08b' 

    popup_text = f"""
    <b>{row['name']} ({row['elev']})</b><br>
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
        popup=folium.Popup(popup_text, max_width=250)
    ).add_to(m)

# Add a layer control box so the user can toggle the river basins on/off
folium.LayerControl().add_to(m)

st_folium(m, width=1000, height=600)

# --- 6. Show the Raw Data Table ---
st.markdown("### Live Site Data")
display_df = df[['name', 'elev', 'empirical_albedo', 'melt_multiplier', 'backtracked_layer_val']].copy()
display_df.columns = ['Station', 'Elevation', 'Empirical Albedo', 'Melt Multiplier', 'Backtracked Val']
st.dataframe(display_df.style.format({
    'Empirical Albedo': '{:.2f}', 
    'Melt Multiplier': '{:.2f}x',
    'Backtracked Val': '{:.4f}'
}))
