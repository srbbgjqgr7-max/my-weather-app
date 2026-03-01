import streamlit as st
import pandas as pd
import requests
import numpy as np
from datetime import datetime

st.set_page_config(page_title="Weather Ensemble Scanner", page_icon="🌤️")
st.title("📊 30-Model Weather Ensemble")

with st.sidebar:
    st.header("Settings")
    unit = st.radio("Temperature Unit", ["Celsius (°C)", "Fahrenheit (°F)"])
    st.info("Rain Risk is the % of 30 models predicting >0.1mm of precip.")

location_input = st.text_input("Enter Station or City (e.g., KLGA, London, Tokyo)", "KLGA")
target_date = st.date_input("Select Forecast Date", datetime.now())

if st.button("Scan Models"):
    try:
        # 1. Geocoding
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={location_input}&count=1&language=en&format=json"
        geo_res = requests.get(geo_url).json()

        if not geo_res.get('results'):
            st.error(f"Could not find location: {location_input}")
        else:
            location_data = geo_res['results'][0]
            lat, lon = location_data['latitude'], location_data['longitude']
            st.success(f"Scanning 30 Models for: {location_data['name']}")

            # 2. API Call (Updated for better reliability)
            date_str = target_date.strftime('%Y-%m-%d')
            api_url = f"https://ensemble-api.open-meteo.com/v1/ensemble?latitude={lat}&longitude={lon}&models=gefs_seamless&daily=temperature_2m_max,precipitation_sum&timezone=auto&start_date={date_str}&end_date={date_str}"
            
            response = requests.get(api_url).json()
            daily = response.get('daily', {})

            # 3. Data Extraction
            temps_c = [v[0] for k, v in daily.items() if 'temperature_2m_max_member' in k and v[0] is not None]
            rains = [v[0] for k, v in daily.items() if 'precipitation_sum_member' in k and v[0] is not None]

            if temps_c and len(temps_c) > 0:
                # Convert units
                if unit == "Fahrenheit (°F)":
                    temps = [(t * 9/5) + 32 for t in temps_c]
                    label = "°F"
                else:
                    temps = temps_c
                    label = "°C"

                # Stats
                rain_prob = (sum(1 for r in rains if r > 0.1) / len(rains)) * 100
                avg_t, std_t = np.mean(temps), np.std(temps)

                # UI
                m1, m2, m3 = st.columns(3)
                m1.metric("Avg High", f"{avg_t:.1f}{label}")
                m2.metric("Confidence", "High ✅" if std_t < 1.5 else "Moderate ⚠️" if std_t < 3.5 else "Low 🚩")
                m3.metric("Rain Risk", f"{rain_prob:.0f}%")

                df = pd.DataFrame({"Model": [f"Run {i+1}" for i in range(len(temps))], f"Temp ({label})": temps})
                st.line_chart(df.set_index("Model"))
            else:
                st.warning("The model ensemble hasn't updated for this specific date yet. Try a date 2-7 days in the future!")

    except Exception as e:
        st.error(f"Connection Error: {e}")
