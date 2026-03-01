import streamlit as st
import pandas as pd
import requests
import numpy as np
from meteostat import Stations
from datetime import datetime

# 1. Page Configuration
st.set_page_config(page_title="Weather Ensemble Scanner", page_icon="🌤️")
st.title("📊 30-Model Weather Ensemble")

# 2. Sidebar Settings
with st.sidebar:
    st.header("Settings")
    unit = st.radio("Temperature Unit", ["Celsius (°C)", "Fahrenheit (°F)"])

# 3. User Inputs
station_code = st.text_input("Enter Station ICAO (e.g., KLGA, EGLL, KLAX)", "KLGA").upper()
target_date = st.date_input("Select Forecast Date", datetime.now())

# 4. The Action Button
if st.button("Scan Models"):
    # Create the tool only when the button is pressed
    stations_tool = Stations()
    
    try:
        # Search for the station
        stations_found = stations_tool.identifier('icao', station_code)
        station_data = stations_found.fetch(1)

        if station_data.empty:
            st.error(f"Station '{station_code}' not found. Please try a major ICAO code (e.g. KJFK).")
        else:
            lat = station_data.latitude.iloc[0]
            lon = station_data.longitude.iloc[0]
            st.success(f"Scanning 30 Models for: {station_data.name.iloc[0]}")

            # 5. Fetch Ensemble Members
            api_url = f"https://ensemble-api.open-meteo.com/v1/ensemble?latitude={lat}&longitude={lon}&models=gefs_seamless&daily=temperature_2m_max&start_date={target_date}&end_date={target_date}&timezone=auto"
            
            response = requests.get(api_url).json()
            daily_data = response.get('daily', {})
            
            # Filter for the 30+ model members
            temps_c = [v[0] for k, v in daily_data.items() if 'temperature_2m_max_member' in k]

            if temps_c:
                # 6. Unit Conversion
                if unit == "Fahrenheit (°F)":
                    temps = [(t * 9/5) + 32 for t in temps_c]
                    label = "°F"
                else:
                    temps = temps_c
                    label = "°C"

                # 7. Math & Metrics
                df = pd.DataFrame({
                    "Model Member": [f"Run {i+1}" for i in range(len(temps))],
                    f"High Temp ({label})": temps
                })
                
                avg_temp = np.mean(temps)
                std_dev = np.std(temps)

                # Visuals
                col1, col2 = st.columns(2)
                col1.metric("Ensemble Average", f"{avg_temp:.1f}{label}")
                
                # Confidence Calculation
                if std_dev < 1.5:
                    confidence = "High ✅"
                elif std_dev < 3.5:
                    confidence = "Moderate ⚠️"
                else:
                    confidence = "Low 🚩"
                col2.metric("Forecast Confidence", confidence)

                st.subheader(f"Model Spread ({label})")
                st.line_chart(df.set_index("Model Member"))
                
                with st.expander("Show All 30 Model Values"):
                    st.table(df)
            else:
                st.warning("No model data returned for this date. Models usually only go 14 days out!")

    except Exception as e:
        st.error(f"An error occurred: {e}")
