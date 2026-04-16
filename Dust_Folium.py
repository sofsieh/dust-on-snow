import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import json

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

# USER INPUT: Dust Layer Thickness
dust_thickness = st.sidebar.slider(
    "Dust Layer Thickness (mm)", 
    min_value=0.0, 
    max_value=100.0, 
    value=15.0,
    help="Adjust to see the immediate impact on albedo across all stations."
)

depth_from_top = st.sidebar.number_input(
    "Depth from Top of Snowpack (cm)", 
    min_value=0.0, 
    value=1.0, 
    step=0.5
)

# --- 4. The Live Math Engine ---
clean_albedo = snow_grain_albedos[selected_grain]
raw_albedo_drop = dust_thickness * 0.00067

# 3cm Optical Depth Rule
active_albedo_drop = raw_albedo_drop if depth_from_top <= 3.0 else 0.0
calculated_albedo = max(0.35, clean_albedo - active_albedo_drop)

# --- 5. Map & Basin Boundaries ---
st.subheader(f"Current Calculated Albedo: {calculated_albedo:.3f}")

# Initialize Map
m = folium.Map(location=[39.0, -106.5], zoom_start=7, tiles="Stamen Terrain")

# ADD BASIN BOUNDARIES 
# Note: You need a 'basins.json' file in your GitHub repo for this to work
try:
    with open('basins.json') as f:
        basin_geo = json.load(f)
    folium.GeoJson(
        basin_geo,
        name="Basin Boundaries",
        style_function=lambda x: {'fillColor': '#228B22', 'color': 'blue', 'weight': 1, 'fillOpacity': 0.1}
    ).add_to(m)
except FileNotFoundError:
    st.warning("Basin boundary file (basins.json) not found in repository.")

# Add Station Markers
for _, row in df.iterrows():
    folium.CircleMarker(
        location=[row['lat'], row['lon']],
        radius=8,
        popup=f"{row['name']}<br>Elev: {row['elev']}<br>Est. Albedo: {calculated_albedo:.3f}",
        color="red" if active_albedo_drop > 0 else "blue",
        fill=True,
    ).add_to(m)

st_folium(m, width=1000, height=500)

# --- 6. Data Summary Table ---
st.write("### Station Summary Table")
df['Current_Albedo'] = calculated_albedo
st.dataframe(df)
