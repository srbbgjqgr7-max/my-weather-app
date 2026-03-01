import streamlit as st
import pandas as pd
import requests
import numpy as np
from datetime import datetime

# 1. Page Configuration
st.set_page_config(page_title="Weather Ensemble Scanner", page_icon="🌤️")
st.title("📊 30-Model Weather Ensemble")

# 2. Sidebar Settings
with st.sidebar:
    st.header("Settings")
    unit = st.radio("Temperature Unit", ["Celsius (°C)", "Fahrenheit (°F)"])
    st.info("Rain Risk: % of 30 models predicting >0.1mm of precip.")

# 3. User Inputs
location_input = st.text_input("Enter Station or City (e.g., KLGA, London, Tokyo)", "KLGA")
target_date = st.date_input("Select Forecast Date", datetime.now())

# 4. The Action Button
if st.button("Scan Models"):
    try:
        # SEARCH LOGIC: Convert name to Lat/Lon
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={location_input}&count=1&language=en&format=json"
        geo_res = requests.get(geo_url).json()

        if not geo_res.get('results'):
            st.error(f"Could not find location: {location_input}")
        else:
            location_data = geo_res['results'][0]
            lat, lon = location_data['latitude'], location_data['longitude']
            st.success(f"Scanning 30 Models for: {location_data['name']}")

            # 5. Fetch Ensemble Members (Temp + Rain)
            # We use the specific start/end date format to ensure we hit the model window
            date_str = target_date.strftime('%Y-%m-%d')
            api_url = f"https://ensemble-api.open-meteo.com/v1/ensemble?latitude={lat}&longitude={lon}&models=gefs_seamless&daily=temperature_2m_max,precipitation_sum&timezone=auto&start_date={date_str}&end_date={date_str}"
            
            response = requests.get(api_url).json()
            daily = response.get('daily', {})

            # 6. Data Extraction with "None" Check
            # Filter out any 'None' values to prevent math errors
            temps_c = [v[0] for k, v in daily.items() if 'temperature_2m_max_member' in k and v[0] is not None]
            rains = [v[0] for k, v in daily.items() if 'precipitation_sum_member' in k and v[0] is not None]

            if temps_c and len(temps_c) > 0:
                # 7. Unit Conversion for Temp
                if unit == "Fahrenheit (°F)":
                    temps = [(t * 9/5) + 32 for t in temps_c]
                    label = "°F"
                else:
                    temps = temps_c
                    label = "°C"

                # 8. Rain Risk Calculation
                rainy_models = sum(1 for r in rains if r > 0.1)
                rain_probability = (rainy_models / len(rains)) * 100

                # 9. Math & Analytics
                avg_temp = np.mean(temps)
                std_dev = np.std(temps)

                # 10. Visual Display
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
                m3.metric("Rain Risk", f"{rain_probability:.0f}%")

                st.subheader(f"Temperature Spread ({label})")
                df = pd.DataFrame({
                    "Model Member": [f"Run {i+1}" for i in range(len(temps))],
                    f"Temp ({label})": temps,
                    "Rain (mm)": rains
                })
                st.line_chart(df.set_index("Model Member")[f"Temp ({label})"])
                
                with st.expander("Show All 30 Model Values"):
                    st.table(df)
            else:
                st.warning("No model data available for today yet. Try a date 1-14 days in the future!")

    except Exception as e:
        st.error(f"Technical Error: {e}")
