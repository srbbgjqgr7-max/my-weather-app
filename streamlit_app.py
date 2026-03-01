import streamlit as st
import pandas as pd
import requests
import numpy as np
from meteostat import info, Stations
from datetime import datetime

# 1. Page Configuration
st.set_page_config(page_title="Weather Ensemble Scanner", page_icon="🌤️")
st.title("📊 30-Model Weather Ensemble")

# 2. Sidebar Settings
with st.sidebar:
    st.header("Settings")
    unit = st.radio("Temperature Unit", ["Celsius (°C)", "Fahrenheit (°F)"])
    st.info("Rain Risk is calculated as the % of models predicting >0.1mm of precip.")

# 3. User Inputs
station_code = st.text_input("Enter Station ICAO (e.g., KLGA, EGLL, KLAX)", "KLGA").upper()
target_date = st.date_input("Select Forecast Date", datetime.now())

# 4. The Action Button
if st.button("Scan Models"):
    try:
        # Search for the station using the newer Meteostat method
        stations = Stations()
        stations = stations.identifier('icao', station_code)
        station_data = stations.fetch(1)

        if station_data.empty:
            st.error(f"Station '{station_code}' not found. Please try a major ICAO code.")
        else:
            lat = station_data.latitude.iloc[0]
            lon = station_data.longitude.iloc[0]
            st.success(f"Scanning 30 Models for: {station_data.name.iloc[0]}")

            # 5. Fetch Ensemble Members (Temp + Rain)
            # We added 'precipitation_sum' to the API call
            api_url = f"https://ensemble-api.open-meteo.com/v1/ensemble?latitude={lat}&longitude={lon}&models=gefs_seamless&daily=temperature_2m_max,precipitation_sum&start_date={target_date}&end_date={target_date}&timezone=auto"
            
            response = requests.get(api_url).json()
            daily_data = response.get('daily', {})
            
            # Extract Temp and Rain from the 30+ members
            temps_c = [v[0] for k, v in daily_data.items() if 'temperature_2m_max_member' in k]
            rains = [v[0] for k, v in daily_data.items() if 'precipitation_sum_member' in k]

            if temps_c:
                # 6. Unit Conversion for Temp
                if unit == "Fahrenheit (°F)":
                    temps = [(t * 9/5) + 32 for t in temps_c]
                    label = "°F"
                else:
                    temps = temps_c
                    label = "°C"

                # 7. Rain Risk Calculation
                # Count how many models show > 0.1mm of rain
                rainy_models = sum(1 for r in rains if r > 0.1)
                rain_probability = (rainy_models / len(rains)) * 100

                # 8. Math & Analytics
                df = pd.DataFrame({
                    "Model Member": [f"Run {i+1}" for i in range(len(temps))],
                    f"High Temp ({label})": temps,
                    "Rain Forecast (mm)": rains
                })
                
                avg_temp = np.mean(temps)
                std_dev = np.std(temps)

                # 9. Visual Display
                m1, m2, m3 = st.columns(3)
                m1.metric("Avg High", f"{avg_temp:.1f}{label}")
                
                # Confidence Calculation
                if std_dev < 1.5:
                    conf_text = "High ✅"
                elif std_dev < 3.5:
                    conf_text = "Moderate ⚠️"
                else:
                    conf_text = "Low 🚩"
                m2.metric("Confidence", conf_text)
                
                # Rain Risk Metric
                m3.metric("Rain Risk", f"{rain_probability:.0f}%")

                st.subheader(f"Temperature Spread ({label})")
                st.line_chart(df.set_index("Model Member")[f"High Temp ({label})"])
                
                with st.expander("Show All 30 Model Values"):
                    st.table(df)
            else:
                st.warning("No model data returned. Remember, models usually only go 14 days out!")

    except Exception as e:
        # Improved error catching to see exactly what fails
        st.error(f"Technical Error: {e}")
