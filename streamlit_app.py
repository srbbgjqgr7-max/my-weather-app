import streamlit as st
import pandas as pd
import requests
import numpy as np
from datetime import datetime

# 1. Page Configuration
st.set_page_config(page_title="High-Res Weather Scanner", page_icon="⛈️")
st.title("🎯 High-Accuracy Weather Ensemble")
st.markdown("Scanning high-resolution regional models for the next 48 hours.")

# 2. Sidebar Settings
with st.sidebar:
    st.header("Settings")
    unit = st.radio("Temperature Unit", ["Celsius (°C)", "Fahrenheit (°F)"])
    st.info("Rain Risk is the % of models predicting >0.1mm of precip.")

# 3. User Inputs
location_input = st.text_input("Enter Station or City (e.g., KLGA, London, Tokyo)", "KLGA")
target_date = st.date_input("Select Forecast Date", datetime.now())

if st.button("Scan Models"):
    try:
        # 4. Geocoding
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={location_input}&count=1&language=en&format=json"
        geo_res = requests.get(geo_url).json()

        if not geo_res.get('results'):
            st.error(f"Could not find location: {location_input}")
        else:
            location_data = geo_res['results'][0]
            lat, lon = location_data['latitude'], location_data['longitude']
            st.success(f"Scanning High-Res Models for: {location_data['name']}")

            # 5. Fetch High-Resolution Models (Best for <48 Hours)
            # We are using 'best_match' which combines HRRR, ICON-D2, and GFS
            date_str = target_date.strftime('%Y-%m-%d')
            api_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=temperature_2m_max,precipitation_sum&timezone=auto&start_date={date_str}&end_date={date_str}&models=best_match,hrrr,icon_seamless,gem_seamless,meteofrance_seamless"
            
            response = requests.get(api_url).json()
            daily = response.get('daily', {})

            # 6. Extracting specific models for our "Ensemble"
            # We look for all keys that contain 'temperature_2m_max'
            temp_keys = [k for k in daily.keys() if 'temperature_2m_max' in k]
            rain_keys = [k for k in daily.keys() if 'precipitation_sum' in k]
            
            temps_c = [daily[k][0] for k in temp_keys if daily[k][0] is not None]
            rains = [daily[k][0] for k in rain_keys if daily[k][0] is not None]

            if temps_c:
                # 7. Unit Conversion
                if unit == "Fahrenheit (°F)":
                    temps = [(t * 9/5) + 32 for t in temps_c]
                    label = "°F"
                else:
                    temps = temps_c
                    label = "°C"

                # 8. Rain Risk & Math
                rainy_models = sum(1 for r in rains if r > 0.1)
                rain_probability = (rainy_models / len(rains)) * 100
                avg_temp = np.mean(temps)
                std_dev = np.std(temps)

                # 9. Visual Display
                m1, m2, m3 = st.columns(3)
                m1.metric("Ensemble Avg", f"{avg_temp:.1f}{label}")
                
                # Confidence Calculation
                conf_text = "High ✅" if std_dev < 1.2 else "Moderate ⚠️" if std_dev < 2.5 else "Low 🚩"
                m2.metric("Confidence", conf_text)
                m3.metric("Rain Risk", f"{rain_probability:.0f}%")

                # 10. Data Visualization
                df = pd.DataFrame({
                    "Model Source": [k.replace('temperature_2m_max_', '').upper() for k in temp_keys],
                    f"High Temp ({label})": temps
                })
                
                st.subheader(f"Model Comparison ({label})")
                st.bar_chart(df.set_index("Model Source"))
                
                with st.expander("Show Raw Model Comparison"):
                    st.table(df)
            else:
                st.warning("No high-res data available for this specific date. Try tomorrow!")

    except Exception as e:
        st.error(f"Technical Error: {e}")
