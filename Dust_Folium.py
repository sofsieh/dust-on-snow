# -*- coding: utf-8 -*-
"""
Created on Mon Apr  6 13:19:53 2026

@author: slhill1
"""

import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

# --- 1. App Configuration ---
st.set_page_config(page_title="SNOTEL Dust & Snowmelt Calculator", layout="wide")
st.title("Real-Time Dust & Snowmelt Calculator")
st.markdown("Calculate empirical albedo drop and melt acceleration using field snowpit data and SNOTEL station locations.")

# --- 2. The Data Engine ---
# Defining our stations and coordinates (k-values kept for reference/future integration)
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