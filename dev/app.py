import streamlit as st
from agents_dev import Tripcrew, format_data
from dotenv import load_dotenv
import os
import re
import json

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# --- Session State Initialization ---
if "trip_output" not in st.session_state:
    st.session_state.trip_output = None
if "formatted_cities" not in st.session_state:
    st.session_state.formatted_cities = None
if "selected_place" not in st.session_state:
    st.session_state.selected_place = None
if "formatted_local_expertize" not in st.session_state:
    st.session_state.formatted_local_expertize = None
if "selected_attractions" not in st.session_state:
    st.session_state.selected_attractions = []
if "selected_cuisines" not in st.session_state:
    st.session_state.selected_cuisines = []
if "itinerary" not in st.session_state:
    st.session_state.itinerary = None
if "inputs" not in st.session_state:
    st.session_state.inputs = {}

# --- Header and Sidebar ---
st.title("✈️ AI Travel Planning Agent")
st.markdown("Plan your perfect trip with a few simple inputs!")

with st.sidebar:
    st.header("Trip Preferences")
    with st.form("trip_preferences_form"):
        travel_type = st.selectbox("Travel Type", ["Leisure", "Business", "Adventure", "Romantic", "Family"])
        budget_range = st.slider("Budget Range (in ₹)", 5000, 1000000, (10000, 50000), step=5000)
        group_type = st.text_input("Group Type", placeholder="e.g., friends, family, solo, couple")
        no_of_people = st.slider("Number of People", 1, 30, 5)
        duration = st.slider("Trip Duration (in days)", 1, 30, 5)
        interests = st.text_input("Interests", placeholder="e.g., beaches, hiking, museums")

        generate_button = st.form_submit_button("Generate Trip")

# --- Main App Logic ---

# Phase 1: Generate Trip Suggestions
if generate_button:
    st.session_state.inputs = {
        "travel_type": travel_type,
        "budget_range": budget_range,
        "no_of_people": no_of_people,
        "group_type": group_type,
        "duration": duration,
        "interests": interests,
    }
    with st.spinner("🧠 Generating trip suggestions..."):
        planner = Tripcrew(st.session_state.inputs)
        st.session_state.trip_output = planner.run()
        formatter = format_data()
        st.session_state.formatted_cities = formatter.format_city_suggestions(st.session_state.trip_output)
    st.success("✅ Suggestions generated!")

if st.session_state.formatted_cities:
    st.subheader("🌆 Suggested Places")
    # This is the updated, cleaner layout
    cols = st.columns(len(st.session_state.formatted_cities))
    for i, item in enumerate(st.session_state.formatted_cities):
        with cols[i]:
            st.markdown(f"**🏙️ {item['place']}**")
            st.markdown(f"📝 *Reason*: {item['reason']}")

            photos = item.get("photos", [])
            if photos:
                # Display all photos for the city
                for photo_url in photos:
                    st.image(photo_url, use_container_width=True)

            if st.button(f"Explore {item['place']}", key=f"explore_{i}"):
                st.session_state.selected_place = item['place']
                with st.spinner(f"🧭 Getting local expert info for {item['place']}..."):
                    planner = Tripcrew(st.session_state.inputs)
                    local_output = planner.run_local_expert(st.session_state.selected_place)
                    st.session_state.formatted_local_expertize = format_data().format_local_expertise(local_output)
                st.rerun()

# Phase 2: Get Local Expert Info
if st.session_state.selected_place and st.session_state.formatted_local_expertize:
    st.header(f"🧭 Local Expert Insights for {st.session_state.selected_place}")
    local_data = st.session_state.formatted_local_expertize

    st.subheader("Top Attractions")
    selected_attractions_names = []
    if local_data.get("top_attractions"):
        for attr in local_data["top_attractions"]:
            if st.checkbox(f"**{attr['name']}** - {attr['description']}", key=f"attraction_{attr['name']}"):
                selected_attractions_names.append(attr["name"])

    st.subheader("Local Cuisines")
    selected_cuisines_names = []
    if local_data.get("local_cuisine"):
        for cuisine in local_data["local_cuisine"]:
            if st.checkbox(f"**{cuisine['dish']}** - {cuisine['description']}", key=f"cuisine_{cuisine['dish']}"):
                selected_cuisines_names.append(cuisine["dish"])

    st.session_state.selected_attractions = selected_attractions_names
    st.session_state.selected_cuisines = selected_cuisines_names

    if st.button("📅 Schedule My Trip"):
        if not st.session_state.selected_attractions and not st.session_state.selected_cuisines:
            st.warning("⚠️ Please select at least one attraction or cuisine to schedule your trip.")
        else:
            with st.spinner("⏳ Planning your personalized trip. Please wait..."):
                planner = Tripcrew(st.session_state.inputs)
                schedule_json = planner.run_schedule_trip(
                    selected_place=st.session_state.selected_place,
                    selected_attractions=st.session_state.selected_attractions,
                    selected_cuisines=st.session_state.selected_cuisines
                )
                if schedule_json:
                    st.session_state.itinerary = format_data().format_trip_schedule(schedule_json)
                else:
                    st.session_state.itinerary = {"error": "Failed to generate schedule."}
            st.rerun()

# Phase 3: Display Itinerary
if st.session_state.itinerary:
    st.subheader("📅 Final Trip Schedule")
    if "error" in st.session_state.itinerary:
        st.error(f"🚫 {st.session_state.itinerary['error']}")
    else:
        st.success("✅ Your trip has been scheduled!")
        st.json(st.session_state.itinerary)