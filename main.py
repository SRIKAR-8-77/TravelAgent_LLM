import os
import re
import json
import streamlit as st
from dotenv import load_dotenv

# Import your existing agents and formatters
from agents import Tripcrew, format_data

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


# ---------------------------
# Helpers
# ---------------------------

def _parse_json_blocks(text):
    """
    Try to extract the first JSON array or object from a block of text
    that might contain markdown fences.
    """
    if isinstance(text, (list, dict)):
        return text
    if not isinstance(text, str):
        return None

    # Try fenced code block with ```json
    m = re.search(r"```json\s*(\{.*?\}|\[.*?\])\s*```", text, flags=re.DOTALL)
    if m:
        candidate = m.group(1)
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    # Try any JSON-looking array/object in the string
    m2 = re.search(r"(\{.*\}|\[.*\])", text, flags=re.DOTALL)
    if m2:
        candidate = m2.group(1)
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    return None


def _safe_run_reviews(planner, place):
    """Support either run_reviews or run_reviews_and_ratings depending on agents.py implementation."""
    if hasattr(planner, "run_reviews"):
        return planner.run_reviews(place)
    elif hasattr(planner, "run_reviews_and_ratings"):
        return planner.run_reviews_and_ratings(place)
    else:
        raise AttributeError("Neither run_reviews nor run_reviews_and_ratings found in Tripcrew.")


def _init_state():
    defaults = dict(
        step=0,
        preferences=None,
        suggestions=[],
        suggestions_raw=None,
        selected_place=None,
        local_info=None,
        selected_attractions=[],
        selected_cuisines=[],
        itinerary=None,
        safety=None,
        packing=None,
        budget=None,
        transport=None,
        accommodation=None,
        reviews=None,
        final_export=None,
    )
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _step_header():
    steps = [
        "1) Preferences → Suggestions",
        "2) Pick Destination",
        "3) Local Insights (Attractions & Cuisine)",
        "4) Build Itinerary",
        "5) Safety",
        "6) Packing List",
        "7) Budget",
        "8) Transport Options",
        "9) Accommodation",
        "10) Reviews",
        "11) Final Plan"
    ]
    st.sidebar.title("Trip Planner Wizard")
    for idx, label in enumerate(steps):
        marker = "✅ " if idx < st.session_state.step else ("➡️ " if idx == st.session_state.step else "• ")
        st.sidebar.write(f"{marker}{label}")
    st.sidebar.markdown("---")
    if st.session_state.step > 0:
        if st.sidebar.button("⬅️ Back"):
            st.session_state.step = max(0, st.session_state.step - 1)
            st.rerun()
    if st.sidebar.button("🔄 Reset"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        _init_state()
        st.rerun()


# ---------------------------
# UI Steps
# ---------------------------

def step0_preferences():
    st.title("AI Travel Planning Wizard")
    st.subheader("Step 1 — Tell us about your trip")

    travel_type = st.selectbox(
        "Travel Type",
        ["Leisure", "Business", "Adventure", "Romantic", "Family"],
        index=0
    )
    total_budget = st.number_input("Total Budget (₹)", min_value=1000, max_value=10_000_000, value=60_000, step=1000)
    group_type = st.text_input("Group Type", placeholder="friends | family | solo | couple", value="couple")
    no_of_people = st.slider("No. of People", 1, 30, 2)
    duration = st.slider("Trip Duration (days)", 1, 45, 7)
    interests = st.text_input("Interests", placeholder="beaches, hiking, museums", value="mountains, trekking, culture")
    start_date = st.date_input("Start Date (optional)")
    planning_style = st.selectbox("Planning Style", ["Not specified", "Holiday based", "Season based"], index=1)

    # Optional fine-grained category budgets
    st.markdown("#### (Optional) Category Budget Ranges")
    col1, col2 = st.columns(2)
    with col1:
        transport_rng = st.slider("Transport (₹)", 0, int(total_budget),
                                  (int(total_budget * 0.1), int(total_budget * 0.2)))
        food_rng = st.slider("Food (₹)", 0, int(total_budget), (int(total_budget * 0.1), int(total_budget * 0.2)))
    with col2:
        accommodation_rng = st.slider("Accommodation (₹)", 0, int(total_budget),
                                      (int(total_budget * 0.3), int(total_budget * 0.5)))
        entertainment_rng = st.slider("Entertainment (₹)", 0, int(total_budget),
                                      (int(total_budget * 0.05), int(total_budget * 0.15)))

    if st.button("✨ Get Suggestions"):
        prefs = {
            "travel_type": travel_type,
            "total_budget": int(total_budget),
            "budget_range": {
                "transport": tuple(transport_rng),
                "accommodation": tuple(accommodation_rng),
                "food": tuple(food_rng),
                "entertainment": tuple(entertainment_rng),
            },
            "no_of_people": int(no_of_people),
            "group_type": group_type,
            "duration": int(duration),
            "interests": interests,
            "start_date": str(start_date) if start_date else None,
            "planning_style": planning_style,
        }
        st.session_state.preferences = prefs

        planner = Tripcrew(prefs)
        output = planner.run()  # destination suggestions + (now) comparison info
        st.session_state.suggestions_raw = output

        formatter = format_data()
        # format_city_suggestions should gracefully handle richer objects (keep 'reason', include extra keys if present)
        suggestions = formatter.format_city_suggestions(output) or []

        # If formatter returns only minimal fields, try to augment from raw parsed JSON
        parsed = _parse_json_blocks(output) or []
        # Normalize to dict list
        if isinstance(parsed, dict):
            parsed = [parsed]
        by_place = {str(item.get("place") or item.get("city") or item.get("destination")): item for item in parsed if
                    isinstance(item, dict)}

        enriched = []
        for s in suggestions:
            place = s.get("place")
            ref = by_place.get(place, {})
            combined = {
                **s,
                # Expected additional fields (if present from your updated agent)
                "weather_suitability": ref.get("weather_suitability"),
                "travel_cost_estimate": ref.get("travel_cost_estimate"),
                "accommodation_range": ref.get("accommodation_range"),
                "safety_rating": ref.get("safety_rating"),
                "accessibility": ref.get("accessibility"),
                "permit_required": ref.get("permit_required"),
                "photos": ref.get("photos") or s.get("photos"),
            }
            enriched.append(combined)

        st.session_state.suggestions = enriched
        st.session_state.step = 1
        st.rerun()

    # Helpful hint
    with st.expander("What will I get next?"):
        st.write(
            "We will suggest 3–5 destinations that match your interests and budget, **with comparison info**: "
            "weather suitability, rough travel & hotel costs, safety level, accessibility, and permits."
        )


def step1_pick_destination():
    st.title("Step 2 — Pick your destination")

    if not st.session_state.suggestions:
        st.warning("No suggestions available yet. Please go back and generate suggestions.")
        return

    # Show suggestions as selectable cards
    chosen = None
    for idx, item in enumerate(st.session_state.suggestions):
        with st.expander(f"🏙️ {item.get('place', 'Unknown Place')}"):
            st.write(f"**Why**: {item.get('reason', '—')}")

            cols = st.columns(2)
            with cols[0]:
                st.markdown("**Weather**")
                st.write(item.get("weather_suitability", "—"))
                st.markdown("**Safety**")
                st.write(item.get("safety_rating", "—"))
                st.markdown("**Accessibility**")
                st.write(item.get("accessibility", "—"))
                st.markdown("**Permits**")
                st.write(item.get("permit_required", "—"))
            with cols[1]:
                st.markdown("**Travel Cost (est.)**")
                tc = item.get("travel_cost_estimate") or {}
                if isinstance(tc, dict):
                    for k, v in tc.items():
                        st.write(f"- {k.title()}: {v}")
                else:
                    st.write("—")
                st.markdown("**Stay (per night)**")
                st.write(item.get("accommodation_range", "—"))

            # Show photos if available
            photos = item.get("photos", [])
            if photos:
                st.markdown("**Photos**")
                photo_cols = st.columns(min(3, len(photos)))  # Up to 3 photos per row
                for i, url in enumerate(photos):
                    if isinstance(url, str) and url.strip():
                        with photo_cols[i % len(photo_cols)]:
                            st.image(url, use_container_width=True)
            else:
                st.write("No photos available.")

            # Select radio per expander
            if st.radio("Select this destination?", ("No", "Yes"), key=f"pick_{idx}", index=0) == "Yes":
                chosen = item.get("place")
                st.session_state.selected_place = chosen

    st.markdown("---")
    # This button is now outside the loop and will run the next step based on the selected_place state
    if st.button("Continue ➡️", disabled=not st.session_state.selected_place):
        planner = Tripcrew(st.session_state.preferences)
        local_info_json = planner.run_local_expert(st.session_state.selected_place)
        st.session_state.local_info = format_data().format_local_expertise(local_info_json)
        st.session_state.step = 2
        st.rerun()


def step2_local_insights():
    st.title(f"Step 3 — Local insights for {st.session_state.selected_place}")

    data = st.session_state.local_info or {}
    selected_attractions = st.session_state.get("selected_attractions", [])
    selected_cuisines = st.session_state.get("selected_cuisines", [])

    st.subheader("Top Attractions")
    if data.get("top_attractions"):
        for attr in data.get("top_attractions", []):
            with st.expander(f"🏞️ {attr.get('name', 'Attraction')} ({attr.get('category', '—')})"):
                st.write(f"**Description**: {attr.get('description', '—')}")
                st.write(f"**Why Visit**: {attr.get('why_visit', '—')}")
                st.write(f"**Best Time of Day**: {attr.get('best_time_of_day', '—')}")
                key = f"attr_{attr.get('name', '')}"
                if st.checkbox(f"Add '{attr.get('name', '')}' to my itinerary", key=key,
                               value=(attr.get('name') in selected_attractions)):
                    if attr.get('name') not in selected_attractions:
                        selected_attractions.append(attr.get('name'))
                else:
                    if attr.get('name') in selected_attractions:
                        selected_attractions.remove(attr.get('name'))
    else:
        st.warning("No attraction data available.")

    st.subheader("Local Cuisines")
    if data.get("local_cuisine"):
        for dish in data.get("local_cuisine", []):
            with st.expander(f"🍽️ {dish.get('dish', 'Dish')} "):
                st.write(f"**Description**: {dish.get('description', '—')}")
                if dish.get("recommended_places"):
                    st.write("**Recommended places:**")
                    for place in dish.get("recommended_places", []):
                        st.write(f"- {place}")
                key = f"cuisine_{dish.get('dish', '')}"
                if st.checkbox(f"Add '{dish.get('dish', '')}' to my food list", key=key,
                               value=(dish.get('dish') in selected_cuisines)):
                    if dish.get('dish') not in selected_cuisines:
                        selected_cuisines.append(dish.get('dish'))
                else:
                    if dish.get('dish') in selected_cuisines:
                        selected_cuisines.remove(dish.get('dish'))
    else:
        st.warning("No cuisine data available.")

    st.session_state.selected_attractions = selected_attractions
    st.session_state.selected_cuisines = selected_cuisines

    st.markdown("---")
    col1, col2 = st.columns(2)
    if col1.button("⬅️ Back to Destinations"):
        st.session_state.step = 1
        st.rerun()

    can_continue = bool(selected_attractions or selected_cuisines)
    if col2.button("Continue to Itinerary ➡️", disabled=not can_continue):
        planner = Tripcrew(st.session_state.preferences)
        schedule_json = planner.run_schedule_trip(
            st.session_state.selected_place,
            st.session_state.selected_attractions,
            st.session_state.selected_cuisines
        )
        st.session_state.itinerary = format_data().format_trip_schedule(schedule_json)
        st.session_state.step = 3
        st.rerun()


def step3_itinerary():
    st.title(f"Step 4 — Your day-by-day itinerary for {st.session_state.selected_place}")

    itinerary = st.session_state.itinerary

    if itinerary and "itinerary" in itinerary:
        for day_plan in itinerary.get("itinerary", []):
            day_num = day_plan.get("day")
            st.header(f"Day {day_num}")
            st.markdown("---")

            for step in day_plan.get("steps", []):
                step_type = step.get("type")

                if step_type == "spot":
                    st.subheader(f"📍 Visit: {step.get('name', 'Attraction')}")
                    st.write(f"**Category**: {step.get('category', '—')}")
                    st.write(f"**Time**: {step.get('visit_time', '—')}")
                    if step.get("must_visit_time"):
                        st.write(f"**Must Visit**: {step.get('must_visit_time', '—')}")
                    st.write(f"**Reason**: {step.get('reason', '—')}")

                elif step_type == "restaurant":
                    st.subheader(f"🍽️ Lunch/Dinner: {step.get('name', 'Restaurant')}")
                    st.write(f"**Location**: {step.get('location', '—')}")
                    st.write(f"**Rating**: {step.get('rating', '—')}")
                    st.write(f"**Cuisines**: {', '.join(step.get('cuisines_served', []))}")

                elif step_type == "accommodation":
                    st.subheader("🏨 Stay Options")
                    for option in step.get("options", []):
                        st.write(f"**- {option.get('name')}**")
                        st.write(f"  - **Location**: {option.get('location', '—')}")
                        st.write(f"  - **Price Range**: {option.get('price_range', '—')}")

                elif step_type == "travel":
                    st.subheader(f"🚗 Travel: {step.get('from', '—')} → {step.get('to', '—')}")
                    for option in step.get("options", []):
                        st.write(f"- **Mode**: {option.get('mode', '—')}")
                        st.write(f"  - **Time**: {option.get('time', '—')}")
                        st.write(f"  - **Cost**: {option.get('cost', '—')}")

                elif step_type == "cuisine":
                    st.subheader(f"🥘 Try Local Dish: {step.get('dish', 'Dish')}")
                    st.write(f"**Origin**: {step.get('origin', '—')}")
                    st.write(f"**Time to Consume**: {step.get('time_to_consume', '—')}")

                elif step_type == "break":
                    st.subheader(f"☕️ Break: {step.get('activity', 'Break')}")
                    st.write(f"**Duration**: {step.get('duration', '—')}")
    else:
        st.warning("No itinerary data available. Please re-run the previous steps.")

    st.markdown("---")
    col1, col2 = st.columns(2)
    if col1.button("⬅️ Back to Local Insights"):
        st.session_state.step = 2
        st.rerun()

    if col2.button("Continue ➡️"):
        # Preload safety for next step
        raw = Tripcrew(st.session_state.preferences).run_safety_info(st.session_state.selected_place)
        st.session_state.safety = format_data().format_safety_info(raw)
        st.session_state.step = 4
        st.rerun()


def step4_safety():
    st.title("Step 5 — Safety guidance")

    safety_data = st.session_state.safety
    if safety_data:
        st.subheader(f"Overall Risk Level: {safety_data.get('overall_risk_level', '—')}")

        with st.expander("Common Scams"):
            for scam in safety_data.get("common_scams", []):
                st.write(f"- {scam}")

        with st.expander("Local Laws & Norms"):
            for law in safety_data.get("local_laws_and_norms", []):
                st.write(f"- {law}")

        with st.expander("Health Notes"):
            health = safety_data.get("health", {})
            st.write(f"**Food & Water Safety**: {health.get('food_water_safety', '—')}")
            st.write(f"**Mosquito Advice**: {health.get('mosquito_advice', '—')}")
            st.write(f"**Altitude Note**: {health.get('altitude_note', '—')}")

        with st.expander("Emergency Contacts"):
            contacts = safety_data.get("emergency_contacts", {})
            for name, number in contacts.items():
                st.write(f"**{name.replace('_', ' ').title()}**: {number}")

        with st.expander("Solo Travel Tips"):
            for tip in safety_data.get("solo_travel_tips", []):
                st.write(f"- {tip}")
    else:
        st.warning("No safety data available.")

    st.markdown("---")
    col1, col2 = st.columns(2)
    if col1.button("⬅️ Back to Itinerary"):
        st.session_state.step = 3
        st.rerun()
    if col2.button("Continue ➡️"):
        # Preload packing
        raw = Tripcrew(st.session_state.preferences).run_packing_list(st.session_state.selected_place)
        st.session_state.packing = format_data().format_packing_list(raw)
        st.session_state.step = 5
        st.rerun()


def step5_packing():
    st.title("Step 6 — Packing list")

    packing_data = st.session_state.packing
    if packing_data:
        st.subheader(f"Season: {packing_data.get('season', '—')}")

        st.markdown("---")

        sections = [
            ("Essentials", "essentials"),
            ("Clothing", "clothing"),
            ("Footwear", "footwear"),
            ("Toiletries & Health", "toiletries_health"),
            ("Gadgets", "gadgets"),
            ("Documents & Money", "documents_money"),
            ("Optional & Activity-Specific", "optional_activity_specific"),
        ]

        for title, key in sections:
            with st.expander(f"📦 {title}"):
                for item in packing_data.get(key, []):
                    st.write(f"- **{item.get('item', '—')}**")
                    st.write(f"  - **Why**: {item.get('why', '—')}")
                    st.write(f"  - **Qty**: {item.get('qty', '—')}")
    else:
        st.warning("No packing data available.")

    st.markdown("---")
    col1, col2 = st.columns(2)
    if col1.button("⬅️ Back to Safety"):
        st.session_state.step = 4
        st.rerun()
    if col2.button("Continue ➡️"):
        # Preload budget
        raw = Tripcrew(st.session_state.preferences).run_budget_breakdown()
        st.session_state.budget = format_data().format_budget_breakdown(raw)
        st.session_state.step = 6
        st.rerun()


def step6_budget():
    st.title("Step 7 — Budget breakdown")

    budget_data = st.session_state.budget
    if budget_data:
        st.subheader("Per Category Budget Range")
        budget_range = budget_data.get("budget_range", {})
        for category, values in budget_range.items():
            if values:
                st.write(f"**{category.title()}**: ₹{values[0]}–₹{values[1]}")

        st.subheader("Per Day Estimate (Per Person)")
        per_day = budget_data.get("per_day_estimate_per_person", {})
        for category, value in per_day.items():
            st.write(f"**{category.title()}**: {value}")

        with st.expander("Notes"):
            for note in budget_data.get("notes", []):
                st.write(f"- {note}")
    else:
        st.warning("No budget data available.")

    st.markdown("---")
    col1, col2 = st.columns(2)
    if col1.button("⬅️ Back to Packing"):
        st.session_state.step = 5
        st.rerun()
    if col2.button("Continue ➡️"):
        # Preload transport
        raw = Tripcrew(st.session_state.preferences).run_transport_options(st.session_state.selected_place)
        st.session_state.transport = format_data().format_transport_options(raw)
        st.session_state.step = 7
        st.rerun()


def step7_transport():
    st.title("Step 8 — Transport options")

    transport_data = st.session_state.transport
    if transport_data:
        st.subheader("Intercity Transport Options")
        for option in transport_data.get("intercity", []):
            with st.expander(f"✈️ {option.get('mode', '—')} ({option.get('from', '—')} → {option.get('to', '—')})"):
                st.write(f"**Time**: {option.get('time', '—')}")
                st.write(f"**Approx. Cost**: {option.get('approx_cost', '—')}")
                st.write(f"**Pro Tip**: {option.get('pro_tip', '—')}")

        st.subheader("In-City Transport Options")
        for option in transport_data.get("in_city", []):
            with st.expander(f"🚆 {option.get('mode', '—')}"):
                st.write(f"**When to Use**: {option.get('when_to_use', '—')}")
                st.write(f"**Approx. Cost**: {option.get('approx_cost', '—')}")
                st.write(f"**Coverage**: {option.get('coverage', '—')}")
                st.write(f"**Pro Tip**: {option.get('pro_tip', '—')}")
    else:
        st.warning("No transport data available.")

    st.markdown("---")
    col1, col2 = st.columns(2)
    if col1.button("⬅️ Back to Budget"):
        st.session_state.step = 6
        st.rerun()
    if col2.button("Continue ➡️"):
        # Preload accommodation
        raw = Tripcrew(st.session_state.preferences).run_accommodation_suggestions(st.session_state.selected_place)
        st.session_state.accommodation = format_data().format_accommodation_suggestions(raw)
        st.session_state.step = 8
        st.rerun()


def step8_accommodation():
    st.title("Step 9 — Accommodation suggestions")

    accommodation_data = st.session_state.accommodation
    if accommodation_data:
        st.subheader("Suggested Neighborhoods")
        for hood in accommodation_data.get("neighborhoods", []):
            with st.expander(f"🏡 {hood.get('name', '—')}"):
                st.write(f"**Good for**: {', '.join(hood.get('good_for', []))}")
                st.write(f"**Avoid if**: {', '.join(hood.get('avoid_if', []))}")

        st.subheader("Accommodation Options by Vibe")
        for stay in accommodation_data.get("stays", []):
            with st.expander(f"🛌 {stay.get('name', '—')} ({stay.get('type', '—')})"):
                st.write(f"**Area**: {stay.get('area', '—')}")
                st.write(f"**Price per night**: {stay.get('approx_price_per_night', '—')}")
                st.write(f"**Suits**: {stay.get('suits', '—')}")
                st.write(f"**Vibe**: {stay.get('vibe', '—')}")
                st.write(f"**Why**: {stay.get('why', '—')}")
    else:
        st.warning("No accommodation data available.")

    st.markdown("---")
    col1, col2 = st.columns(2)
    if col1.button("⬅️ Back to Transport"):
        st.session_state.step = 7
        st.rerun()
    if col2.button("Continue ➡️"):
        # Preload reviews
        planner = Tripcrew(st.session_state.preferences)
        raw = _safe_run_reviews(planner, st.session_state.selected_place)
        st.session_state.reviews = format_data().format_reviews(raw)
        st.session_state.step = 9
        st.rerun()


def step9_reviews():
    st.title("Step 10 — Reviews & traveler tips")

    reviews_data = st.session_state.reviews
    if reviews_data:
        st.subheader("Attractions")
        for attraction in reviews_data.get("attractions", []):
            with st.expander(f"⭐ {attraction.get('name', '—')} (Rating: {attraction.get('average_rating', '—')})"):
                st.write("**Pros**: " + ", ".join(attraction.get("pros", [])))
                st.write("**Cons**: " + ", ".join(attraction.get("cons", [])))
                st.write(f"**Tip**: {attraction.get('tip', '—')}")

        st.subheader("Restaurants")
        for restaurant in reviews_data.get("restaurants", []):
            with st.expander(f"⭐ {restaurant.get('name', '—')} (Rating: {restaurant.get('average_rating', '—')})"):
                st.write("**Pros**: " + ", ".join(restaurant.get("pros", [])))
                st.write("**Cons**: " + ", ".join(restaurant.get("cons", [])))
                st.write(f"**Tip**: {restaurant.get('tip', '—')}")
    else:
        st.warning("No reviews data available.")

    st.markdown("---")
    col1, col2 = st.columns(2)
    if col1.button("⬅️ Back to Accommodation"):
        st.session_state.step = 8
        st.rerun()
    if col2.button("Continue ➡️"):
        st.session_state.step = 10
        st.rerun()


def step10_final():
    st.title("Step 11 — Final trip plan")
    st.write("Here is your full trip package consolidated into one JSON payload. You can export it to a file.")

    final_payload = {
        "tripPlan":{
            "preferences": st.session_state.preferences,
            "selected_place": st.session_state.selected_place,
            "suggestions": st.session_state.suggestions,
            "local_info": st.session_state.local_info,
            "selected_attractions": st.session_state.selected_attractions,
            "selected_cuisines": st.session_state.selected_cuisines,
            "itinerary": st.session_state.itinerary,
            "safety": st.session_state.safety,
            "packing": st.session_state.packing,
            "budget": st.session_state.budget,
            "transport": st.session_state.transport,
            "accommodation": st.session_state.accommodation,
            "reviews": st.session_state.reviews,
        }
    }
    st.session_state.final_export = final_payload

    st.json(final_payload)

    # Export
    fname = "trip_plan.json"
    st.download_button(
        label="⬇️ Download Trip Plan JSON",
        data=json.dumps(final_payload, indent=2),
        file_name=fname,
        mime="application/json",
    )

    st.markdown("---")
    if st.button("🏁 Finish & Start Over"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        _init_state()
        st.rerun()


# ---------------------------
# Main
# ---------------------------

def main():
    _init_state()
    _step_header()

    step = st.session_state.step

    if step == 0:
        step0_preferences()
    elif step == 1:
        step1_pick_destination()
    elif step == 2:
        if st.session_state.selected_place:
            step2_local_insights()
        else:
            st.warning("Please select a destination first.")
            st.session_state.step = 1
            st.rerun()
    elif step == 3:
        step3_itinerary()
    elif step == 4:
        step4_safety()
    elif step == 5:
        step5_packing()
    elif step == 6:
        step6_budget()
    elif step == 7:
        step7_transport()
    elif step == 8:
        step8_accommodation()
    elif step == 9:
        step9_reviews()
    else:
        step10_final()


if __name__ == "__main__":
    main()