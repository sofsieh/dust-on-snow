import streamlit as st
import folium
from streamlit_folium import st_folium
import requests
import pandas as pd
import numpy as np

# ==========================================
# 1. DATA & CONSTANTS CONFIGURATION
# ==========================================
# Combined Sites with their specific API IDs and Coordinates
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
    "402945105543801": 25.0,  
    "395811105480401": 105.28,  
    "395448105453601": 25.0,  
    "375429107433201": 135.58,   
    # SNOTEL k-values
    "335:CO:SNTL": 73.63,  
    "412:CO:SNTL": 25.0,
    "1325:CO:SNTL": 122.63,
    "1057:CO:SNTL": 96.6,
    "717:CO:SNTL": 25.0,
    "793:CO:SNTL": 25.0,
    "839:CO:SNTL": 25.0
}

# ==========================================
# 2. DATA FETCHING & MATH FUNCTIONS
# ==========================================
@st.cache_data(ttl=3600) # Cache for 1 hour to prevent constant API calls
def fetch_and_process_data(site_id, site_type, clean_albedo):
    records = []
    
    if site_type == "USGS":
        params = ["72186", "72185", "72175", "72174", "00020", "00045"]
        param_string = ",".join(params)
        url = f"https://waterservices.usgs.gov/nwis/iv/?format=json&sites={site_id}&parameterCd={param_string}&siteStatus=all&period=P7D"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if 'value' in data and 'timeSeries' in data['value']:
                for ts in data['value']['timeSeries']:
                    param_code = ts['variable']['variableCode'][0]['value']
                    for val in ts['values'][0]['value']:
                        records.append({
                            'site_no': site_id,
                            'datetime': val['dateTime'],
                            'parameter': param_code,
                            'value': float(val['value']) if val['value'] is not None else None
                        })
        
        if not records: return None
        df = pd.DataFrame(records)
        df_pivot = df.pivot_table(index=['site_no', 'datetime'], columns='parameter', values='value').reset_index()
        df_pivot.rename(columns={'72186': 'SW_in', '72185': 'SW_out', '72175': 'LW_in', '72174': 'LW_out', '00020': 'T_air'}, inplace=True)
        
    elif site_type == "SNOTEL":
        elements = "SRADV,SRUOV,LWRDV,LWRUV,TOBS"
        url = f"https://wcc.sc.egov.usda.gov/awdbRestApi/services/v1/data?stationTriplets={site_id}&elements={elements}&duration=HOURLY&period=7"
        headers = {'accept': 'application/json'}
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            for site_data in data:
                for element_data in site_data.get('data', []):
                    param = element_data.get('stationElement', {}).get('elementCode')
                    for val_obj in element_data.get('values', []):
                        val = val_obj.get('value')
                        if val is not None:
                            records.append({
                                'site_no': site_id,
                                'datetime': val_obj.get('date'),
                                'parameter': param, 
                                'value': float(val)
                            })
                            
        if not records: return None
        df = pd.DataFrame(records)
        df_pivot = df.pivot_table(index=['site_no', 'datetime'], columns='parameter', values='value').reset_index()
        df_pivot.rename(columns={'SRADV': 'SW_in', 'SRUOV': 'SW_out', 'LWRDV': 'LW_in', 'LWRUV': 'LW_out', 'TOBS': 'T_air'}, inplace=True)
        
        # Ensure columns exist and convert temp
        required_cols = ['SW_in', 'SW_out', 'LW_in', 'LW_out', 'T_air']
        for col in required_cols:
            if col not in df_pivot.columns: df_pivot[col] = float('nan')
        df_pivot['T_air'] = (df_pivot['T_air'] - 32) * (5.0 / 9.0)

    # Core Math applied to both types
    df_pivot['datetime'] = pd.to_datetime(df_pivot['datetime'])
    df_pivot.sort_values(by=['site_no', 'datetime'], inplace=True)
    
    df_pivot['LW_net'] = df_pivot['LW_in'] - df_pivot['LW_out']
    sigma = 5.67e-8
    emissivity = 0.99
    df_pivot['T_surf'] = ((df_pivot['LW_out'] / (emissivity * sigma)) ** 0.25) - 273.15
    df_pivot['albedo'] = df_pivot.apply(lambda row: row['SW_out'] / row['SW_in'] if pd.notnull(row['SW_in']) and row['SW_in'] > 5 else None, axis=1)

    # Backtracking Logic
    k = k_values.get(site_id, 50.0)
    df_pivot['Cd_raw'] = df_pivot['albedo'].apply(lambda a: (clean_albedo - a) / k if pd.notnull(a) and a < clean_albedo else 0.0)
    df_pivot['Cd_backtracked'] = df_pivot['Cd_raw'][::-1].cummax()[::-1]
    df_pivot.loc[df_pivot['Cd_backtracked'] == 0, 'Cd_backtracked'] = 0.001
    df_pivot['empirical_albedo'] = clean_albedo - (k * df_pivot['Cd_backtracked'])

    # Final Qm
    B = 15.0 
    df_pivot['Qm_melt'] = ((1 - df_pivot['empirical_albedo']) * df_pivot['SW_in'] + df_pivot['LW_net'] + (B * (df_pivot['T_air'] - df_pivot['T_surf'])))
    
    return df_pivot

# ==========================================
# 3. PAGE SETUP & SIDEBAR CONTROLS
# ==========================================
st.set_page_config(page_title="Real-Time Dust & Snowmelt", layout="wide")
st.title("Real-Time Dust & Snowmelt Calculator")

st.sidebar.header("1. Location Settings")
location_method = st.sidebar.radio("Location Method:", ("Manual Selection", "Auto-Geolocation (Requires HTTPS)"))

if location_method == "Manual Selection":
    st.sidebar.info("Manual Override Active.")
    selected_station_name = st.sidebar.selectbox("Select Reference Station:", options=list(station_data.keys()))
    active_station = station_data[selected_station_name]
    st.sidebar.success(f"Tracking {selected_station_name}")
else:
    st.sidebar.warning("Geolocation active. (Defaulting to Berthoud Pass if blocked)")
    # Placeholder for active location component; defaulting for logic flow
    selected_station_name = "USGS: Berthoud Pass"
    active_station = station_data[selected_station_name]

st.sidebar.header("2. Snow Condition")
snow_grain_type = st.sidebar.selectbox("Current Snow Grain Type", ("Fresh Snow", "Old Dry Snow", "Wet Snow"))

if snow_grain_type == "Fresh Snow":
    clean_albedo = 0.85
elif snow_grain_type == "Old Dry Snow":
    clean_albedo = 0.70
else:
    clean_albedo = 0.60

st.sidebar.write(f"**Baseline Albedo ($\\alpha_0$):** {clean_albedo}")

# ==========================================
# 4. FETCH DATA & DISPLAY MAP
# ==========================================
st.subheader("Basin Map & Active Station")

m = folium.Map(location=[active_station["lat"], active_station["lon"]], zoom_start=9)
folium.Marker(
    [active_station["lat"], active_station["lon"]],
    popup=f"Active Site: {selected_station_name}",
    icon=folium.Icon(color="red", icon="info-sign")
).add_to(m)
st_folium(m, width=800, height=350)

# ==========================================
# 5. DATA CALCULATIONS & DISPLAY
# ==========================================
st.subheader("Live Energy Balance & Dust Accumulation")

with st.spinner("Fetching 7-day live data from API..."):
    df_live = fetch_and_process_data(active_station["id"], active_station["type"], clean_albedo)

if df_live is not None and not df_live.empty:
    # Grab the most recent valid row for the metrics
    latest_data = df_live.dropna(subset=['Qm_melt', 'Cd_backtracked']).iloc[-1]
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Empirical Albedo", f"{latest_data['empirical_albedo']:.3f}")
    col2.metric("Backtracked Dust (Cd)", f"{latest_data['Cd_backtracked']:.4f}")
    col3.metric("Energy for Melt (Qm)", f"{latest_data['Qm_melt']:.2f} W/m²")
    col4.metric("Live Air Temp", f"{latest_data['T_air']:.1f} °C")
    
    st.markdown("---")
    st.write("**Recent 7-Day Trend (Filtered)**")
    st.dataframe(df_live[['datetime', 'SW_in', 'albedo', 'Cd_backtracked', 'empirical_albedo', 'Qm_melt']].tail(10))
else:
    st.error("No valid data returned from the API for this timeframe or station.")
    st.markdown("---")
    st.write("**Recent 7-Day Trend (Filtered Data)**")
    
    # Show the raw data table
    st.dataframe(df_live[['datetime', 'SW_in', 'albedo', 'Cd_backtracked', 'empirical_albedo', 'Qm_melt']].tail(10))
    
    # ---------------- NEW CHART CODE ----------------
    st.markdown("---")
    st.subheader("7-Day Dust Accumulation Trend")
    
    # Streamlit line charts work best when the x-axis is the dataframe index
    chart_data = df_live[['datetime', 'Cd_backtracked']].copy()
    chart_data.set_index('datetime', inplace=True)
    
    # Draw the chart
    st.line_chart(chart_data, color="#ff4b4b") 
    # ------------------------------------------------
else:
    st.error("No valid data returned from the API for this timeframe or station.")
