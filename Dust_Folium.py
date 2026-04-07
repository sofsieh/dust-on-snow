import streamlit as st
import folium
from streamlit_folium import st_folium
import requests
import pandas as pd
import numpy as np
import math

# ==========================================
# 1. DATA & CONSTANTS CONFIGURATION
# ==========================================
station_data = {
    # USGS Sites
    "USGS: Berthoud Pass": {"id": "394759105464101", "type": "USGS", "lat": 39.7997, "lon": -105.7733},
    "USGS: Blue Ridge": {"id": "395709105582701", "type": "USGS", "lat": 39.9525, "lon": -105.9741},
    "USGS: Cameron Pass": {"id": "402945105543801", "type": "USGS", "lat": 40.4958, "lon": -105.9066},
    "USGS: Devil's Thumb": {"id": "395811105480401", "type": "USGS", "lat": 39.9697, "lon": -105.8011},
    "USGS: Ranch Creek Meadow": {"id": "395448105453601", "type": "USGS", "lat": 39.9133, "lon": -105.7599},
    "USGS: Senator Beck": {"id": "375429107433201", "type": "USGS", "lat": 37.9080, "lon": -107.7258},
    
    # SNOTEL Sites
    "SNOTEL: Site 335": {"id": "335:CO:SNTL", "type": "SNOTEL", "lat": 39.798, "lon": -105.778},
    "SNOTEL: Site 412": {"id": "412:CO:SNTL", "type": "SNOTEL", "lat": 40.224, "lon": -105.565},
    "SNOTEL: Site 1325": {"id": "1325:CO:SNTL", "type": "SNOTEL", "lat": 37.382, "lon": -106.732},
    "SNOTEL: Site 1057": {"id": "1057:CO:SNTL", "type": "SNOTEL", "lat": 38.871, "lon": -105.064},
    "SNOTEL: Site 717": {"id": "717:CO:SNTL", "type": "SNOTEL", "lat": 40.118, "lon": -107.164},
    "SNOTEL: Site 793": {"id": "793:CO:SNTL", "type": "SNOTEL", "lat": 40.160, "lon": -105.892},
    "SNOTEL: Site 839": {"id": "839:CO:SNTL", "type": "SNOTEL", "lat": 37.741, "lon": -107.494}
}

k_values = {
    # USGS k-values
    "394759105464101": 206.95, 
    "395709105582701": 76.1,  
    "402
