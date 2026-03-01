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
    st.info("Rain Risk is the % of 30 models predicting >0.1mm of precip.")

# 3. User Inputs
location_input = st.text_input("Enter Station or City (e.g., KLGA, London, Tokyo)", "KLGA")
target_date = st.date_input("Select Forecast Date", datetime.now())

# 4. The Action Button
if st.button("Scan Models"):
    try:
        # SEARCH LOGIC: Convert name to Lat/Lon using a free search API
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={location_input}&count=1&language=en&format=json"
        geo_res = requests.get(geo_url).json()

        if not geo_res.get('results'):
            st.error(f"Could not find location: {location_input}")
        else:
            location_data = geo_res['results'][0]
            lat = location_data['latitude']
            lon = location_data['longitude']
            st.success(f"Scanning 30 Models for: {location_data['name']}, {location_data.get('country', '')}")

            # 5. Fetch Ensemble Members (Temp + Rain)
api_url = f"https://ensemble-api.open-meteo.com/v1/ensemble?latitude={lat}&longitude={lon}&models=gefs_seamless&daily=temperature_2m_max,precipitation_sum&timezone=auto&start_date={target_date}&end_date={target_date}"

            
            response = requests.get(api_url).json()
            daily_data = response.get('daily', {})
            
            # Extract data from members
            temps_c = [v[0] for k, v in daily_data.items() if 'temperature_2m_max_member' in k]
            rains = [v[0] for k, v in daily_data.items() if 'precipitation_sum_member' in k]

            if temps_c:
                # 6. Unit Conversion
                if unit == "Fahrenheit (°F)":
                    temps = [(t * 9/5) + 32 for t in temps_c]
                    label = "°F"
                else:
                    temps = temps_c
                    label = "°C"

                # 7. Rain Risk & Math
                rainy_models = sum(1 for r in rains if r > 0.1)
                rain_probability = (rainy_models / len(rains)) * 100
                avg_temp = np.mean(temps)
                std_dev = np.std(temps)

                # 8. Visual Display
                m1, m2, m3 = st.columns(3)
                m1.metric("Avg High", f"{avg_temp:.1f}{label}")
                
                # Confidence
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
                    f"High Temp ({label})": temps,
                    "Rain (mm)": rains
                })
                st.line_chart(df.set_index("Model Member")[f"High Temp ({label})"])
                
                with st.expander("Show All 30 Model Values"):
                    st.table(df)
            else:
                st.warning("No model data. (Models usually only look 14 days ahead!)")

    except Exception as e:
        st.error(f"Something went wrong: {e}")
