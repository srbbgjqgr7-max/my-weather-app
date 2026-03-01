import streamlit as st
import pandas as pd
import requests
import numpy as np
from datetime import datetime

# 1. Page Configuration
st.set_page_config(page_title="High-Res Weather Ensemble", page_icon="🎯")
st.title("🎯 High-Accuracy Weather Ensemble")
st.markdown("Fetching hourly data for maximum accuracy in the next 48 hours.")

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
            loc = geo_res['results'][0]
            lat, lon = loc['latitude'], loc['longitude']
            st.success(f"Scanning Hourly Data for: {loc['name']}, {loc.get('country', '')}")

            # 5. Fetch Hourly Data (More reliable for <48h)
            # Models: best_match (auto-selects best regional), HRRR (US), ICON (Global/EU)
            date_str = target_date.strftime('%Y-%m-%d')
            api_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=temperature_2m,precipitation&timezone=auto&start_date={date_str}&end_date={date_str}&models=best_match,hrrr,icon_seamless,gem_seamless"
            
            response = requests.get(api_url).json()
            hourly = response.get('hourly', {})

            # 6. Extract "Daily Highs" and "Rain Totals" from hourly members
            temp_keys = [k for k in hourly.keys() if 'temperature_2m' in k]
            rain_keys = [k for k in hourly.keys() if 'precipitation' in k]
            
            # Find the Peak Temp and Total Rain for each model
            temps_c = [max(hourly[k]) for k in temp_keys if hourly[k] and any(x is not None for x in hourly[k])]
            rains = [sum(filter(None, hourly[k])) for k in rain_keys if hourly[k]]

            if temps_c:
                # 7. Unit Conversion
                if unit == "Fahrenheit (°F)":
                    temps = [(t * 9/5) + 32 for t in temps_c]
                    label = "°F"
                else:
                    temps = temps_c
                    label = "°C"

                # 8. Rain Risk & Analytics
                # Count models predicting > 0.1mm of rain
                rainy_models = sum(1 for r in rains if r > 0.1)
                rain_prob = (rainy_models / len(rains)) * 100
                avg_temp, std_dev = np.mean(temps), np.std(temps)

                # 9. Visual Display
                m1, m2, m3 = st.columns(3)
                m1.metric("Ensemble High", f"{avg_temp:.1f}{label}")
                
                # Confidence: Tight grouping = High agreement
                conf_text = "High ✅" if std_dev < 1.5 else "Moderate ⚠️" if std_dev < 3.0 else "Low 🚩"
                m2.metric("Confidence", conf_text)
                m3.metric("Rain Risk", f"{rain_prob:.0f}%")

                # 10. Data Table & Chart
                df = pd.DataFrame({
                    "Model": [k.replace('temperature_2m_', '').upper() for k in temp_keys],
                    f"Max Temp ({label})": temps
                })
                
                st.subheader(f"Model High Temperature Comparison")
                st.bar_chart(df.set_index("Model"))
                
                with st.expander("Show Raw Model Values"):
                    st.table(df)
            else:
                st.warning("Data not yet available. High-res regional models update every 1-6 hours.")

    except Exception as e:
        st.error(f"Technical Error: {e}")
