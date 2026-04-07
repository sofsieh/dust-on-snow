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
    # This correctly catches the error ONLY if the API fails or returns nothing
    st.error("No valid data returned from the API for this timeframe or station.")
