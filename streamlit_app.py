import streamlit as st
import pandas as pd
import requests
import numpy as np
from meteostat import Stations
from datetime import datetime

# 1. Page Configuration & Sidebar Setup
st.set_page_config(page_title="Weather Ensemble Scanner", page_icon="🌤️")
st.title("📊 30-Model Weather Ensemble")

# Sidebar for Units
with st.sidebar:
    st.header("Settings")
    unit = st.radio("Temperature Unit", ["Celsius (°C)", "Fahrenheit (°F)"])

# 2. User Inputs
station_code = st.text_input("Enter Station ICAO (e.g., KLGA, EGLL, KLAX)", "KLGA").upper()
target_date = st.date_input("Select Forecast Date", datetime.now())

if st.button("Scan Models"):
    # 3. Station Lookup (Fixed Logic)
    stations_tool = Stations()
    stations_found = stations_tool.identifier('icao', station_code)
    station_data = stations_found.fetch(1)

    if station_data.empty:
        st.error("Station not found. Please check the ICAO code.")
    else:
        lat = station_data.latitude.iloc[0]
        lon = station_data.longitude.iloc[0]
        st.success(f"Found {station_data.name.iloc[0]} ({lat}, {lon})")

        # 4. Fetch 30 Ensemble Members (GEFS)
        api_url = f"https://ensemble-api.open-meteo.com/v1/ensemble?latitude={lat}&longitude={lon}&models=gefs_seamless&daily=temperature_2m_max&start_date={target_date}&end_date={target_date}&timezone=auto"
        
        try:
            response = requests.get(api_url).json()
            daily_data = response.get('daily', {})
            
            # Extract temps from all 30+ members
            temps_c = [v[0] for k, v in daily_data.items() if 'temperature_2m_max_member' in k]

            if temps_c:
                # 5. Unit Conversion Logic
                if unit == "Fahrenheit (°F)":
                    temps = [(t * 9/5) + 32 for t in temps_c]
                    label = "°F"
                else:
                    temps = temps_c
                    label = "°C"

                # 6. Analytics & Probability
                df = pd.DataFrame({
                    "Model Member": [f"Run {i+1}" for i in range(len(temps))],
                    f"High Temp ({label})": temps
                })
                
                avg_temp = np.mean(temps)
                max_temp = np.max(temps)
                min_temp = np.min(temps)
                std_dev = np.std(temps)

                # 7. Visual Display
                col1, col2, col3 = st.columns(3)
                col1.metric("Ensemble Average", f"{avg_temp:.1f}{label}")
                col2.metric("Temp Range", f"{min_temp:.1f}° - {max_temp:.1f}{label}")
                
                # Confidence Logic: Tight grouping = High Probability
                if std_dev < 1.5:
                    confidence = "High ✅"
                elif std_dev < 3.5:
                    confidence = "Moderate ⚠️"
                else:
                    confidence = "Low 🚩"
                
                col3.metric("Forecast Confidence", confidence)

                st.subheader(f"Model Distribution ({label})")
                st.line_chart(df.set_index("Model Member"))
                
                with st.expander("See Raw Model Data"):
                    st.write(df)
            else:
                st.warning("No ensemble data available for this date/location.")
        
        except Exception as e:
            st.error(f"Error fetching weather data: {e}")
