import re
import os
import json
from crewai import Agent, Task, Crew, LLM
from dotenv import load_dotenv
from crewai.tools import BaseTool
import requests
from datetime import datetime, date
import streamlit as st

load_dotenv()
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# Ensure you have these in your .env file
UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY")
UNSPLASH_SECRET_KEY = os.getenv("UNSPLASH_SECRET_KEY")


# ----------------------------
# Tools
# ----------------------------
class UnsplashSearchTool(BaseTool):
    name: str = "Unsplash Image Search"
    description: str = "A tool to search for high-quality images on Unsplash."

    def _run(self, query: str) -> str:
        """
        Searches Unsplash for images based on a query and returns a list of URLs.
        """
        try:
            url = "https://api.unsplash.com/search/photos"
            params = {
                "query": query,
                "per_page": 6,
                "client_id": UNSPLASH_ACCESS_KEY
            }

            response = requests.get(url, params=params)
            response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
            data = response.json()

            if not data.get("results"):
                return "No images found for the query."

            image_urls = [photo["urls"]["regular"] for photo in data["results"]]
            return json.dumps(image_urls)

        except requests.exceptions.RequestException as e:
            return f"An error occurred while making an API request: {e}"
        except Exception as e:
            return f"An error occurred while searching Unsplash: {e}"


# NEW: OpenWeather Tool Class
class OpenWeatherTool(BaseTool):
    name: str = "OpenWeather Tool"
    description: str = "A tool to fetch current weather data for a specified city."

    def _run(self, city_name: str) -> str:
        """
        Fetches current weather data for a given city and returns a JSON string.
        """
        if not OPENWEATHER_API_KEY:
            return "OpenWeather API key not found. Cannot fetch weather."
        try:
            url = (
                f"http://api.openweathermap.org/data/2.5/weather?q={city_name}"
                f"&appid={OPENWEATHER_API_KEY}&units=metric"
            )
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            data = response.json()
            weather_data = {
                "temperature": data["main"]["temp"],
                "description": data["weather"][0]["description"],
                "humidity": data["main"]["humidity"],
                "wind_speed": data["wind"]["speed"],
            }
            return json.dumps(weather_data)
        except Exception as e:
            return f"Failed to fetch weather for {city_name}: {e}"


# ----------------------------
# Agents
# ----------------------------
class TripAgents:
    def __init__(self):
        self.llm = LLM(
            model="gemini/gemini-2.0-flash",
            temperature=0.1
        )
        st.write("DEBUG — LLM initialized", self.llm)
        self.unsplash_tool = UnsplashSearchTool()
        self.openweather_tool = OpenWeatherTool()

    def city_selector_agent(self):
        return Agent(
            role='Indian Travel Destination Expert',
            goal='Identify the best Indian places to visit—including cities, villages, valleys, beaches, historical and devotional sites, and hidden gems—based on user preferences. Also fetch photo and weather data.',
            backstory=(
                "A passionate Indian travel curator with deep knowledge of India’s iconic and offbeat spots."
                "From the majestic Himalayas and serene coastal beaches to sacred pilgrimage towns and offbeat rural villages, "
                "this expert helps travelers discover both iconic and lesser-known gems across India tailored to their interests, and provides visual and weather-related inspiration for their trip."
            ),
            llm=self.llm,
            verbose=True,
            tools=[self.unsplash_tool, self.openweather_tool]
        )

    def local_expert_agent(self):
        return Agent(
            role='Local Indian Travel Expert',
            goal='Provide insights about selected places: attractions, local traditions, cuisines, festivals, hidden gems.',
            backstory="A seasoned local guide across India.",
            llm=self.llm,
            verbose=True
        )

    def trip_scheduler_agent(self):
        return Agent(
            role="Indian Trip Itinerary Planner",
            goal="Organize selected attractions, food, and experiences into a day-wise schedule.",
            backstory="An experienced Indian travel coordinator.",
            llm=self.llm,
            verbose=True
        )

    # NEW
    def safety_info_agent(self):
        return Agent(
            role="Travel Safety Analyst",
            goal="Summarize destination-specific safety guidance, local norms, health notes, and emergency contacts.",
            backstory="A cautious analyst compiling safety practices for Indian destinations.",
            llm=self.llm,
            verbose=True
        )

    def packing_list_agent(self):
        return Agent(
            role="Packing List Generator",
            goal="Create a tailored packing list by season, activities, duration, and group needs.",
            backstory="A practical packer who hates overpacking.",
            llm=self.llm,
            verbose=True
        )

    def budget_advisor_agent(self):
        return Agent(
            role="Budget Allocation Advisor",
            goal="Translate total budget into category ranges and per-day estimates based on trip style and destination costs.",
            backstory="A frugal traveler who knows what things usually cost in India.",
            llm=self.llm,
            verbose=True
        )

    def transport_agent(self):
        return Agent(
            role="Transport Options Expert",
            goal="Recommend intercity and in-city transport options with time, cost and suitability.",
            backstory="Knows Indian rail, flights, buses, metros, autos, and cabs.",
            llm=self.llm,
            verbose=True
        )

    def stay_advisor_agent(self):
        return Agent(
            role="Accommodation Curator",
            goal="Propose stay options (budget → premium) with area, vibe, and approximate prices.",
            backstory="A stay matcher with strong sense of neighborhood fit.",
            llm=self.llm,
            verbose=True
        )

    def reviews_agent(self):
        return Agent(
            role="Review & Ratings Summarizer",
            goal="Synthesize likely pros/cons and average sentiment for attractions and eateries based on common patterns.",
            backstory="Aggregates user feedback patterns and typical traveler sentiment.",
            llm=self.llm,
            verbose=True
        )


# ----------------------------
# Tasks
# ----------------------------
class Triptasks:
    def __init__(self):
        pass

    def city_selection_task(self, agent, preferences):
        """
        City Selection Task — now returns detailed evaluation info for each destination.
        Ensures pure JSON output for easy parsing downstream.
        """
        prefs_text = f"""
                    Travel type: {preferences.get('travel_type')}
                    Budget: {preferences.get('total_budget')} (with ranges {preferences.get('budget_range')})
                    Group: {preferences.get('group_type')} ({preferences.get('no_of_people')} people)
                    Duration: {preferences.get('duration')} days
                    Interests: {preferences.get('interests')}
                    Season/Start date: {preferences.get('start_date')}
                    Planning style: {preferences.get('planning_style')}
                    """
        return Task(
            description=(
                f"You are a travel planning expert. Based on the given user preferences:\n"
                f"{prefs_text}\n\n"
                "Suggest 4 possible travel destinations that best match the user's preferences.\n"
                "For each destination, first use the **'Unsplash Image Search' tool** to find 3-5 high-quality photo URLs. Then, compile a detailed evaluation.\n"
                "Include:\n"
                "- place: Name of the destination\n"
                "- reason: Why it matches the user's preferences\n"
                "- weather_suitability: Best season/months and average temperature during that period\n"
                "- travel_cost_estimate: Estimated round-trip cost for flight, train, and bus (in local currency)\n"
                "- accommodation_range: Average per-night stay cost (budget–premium range)\n"
                "- safety_rating: 'Low', 'Moderate', or 'High'\n"
                "- accessibility: Summary of how to reach (nearest airport/railway, road quality)\n"
                "- permit_required: 'Yes' or 'No', and details if yes\n"
                "- photos: A list of 5-7 photo URLs returned **by the unsplash_tool**. You MUST NOT generate these URLs yourself.\n"
                "Your final response MUST be ONLY the raw JSON array. Do NOT include any introductory text, commentary, or markdown formatting like ```json. Your entire output should start with '[' and end with ']'."
            ),
            agent=agent,
            expected_output=(
                "[\n"
                "  {\n"
                "    \"place\": \"Destination name\",\n"
                "    \"reason\": \"Why it matches\",\n"
                "    \"weather_suitability\": \"Best months, avg temp\",\n"
                "    \"travel_cost_estimate\": {\n"
                "       \"flight\": \"₹xxxx–₹xxxx\",\n"
                "       \"train\": \"₹xxxx–₹xxxx\",\n"
                "       \"bus\": \"₹xxxx–₹xxxx\"\n"
                "    },\n"
                "    \"accommodation_range\": \"₹xxxx–₹xxxx/night\",\n"
                "    \"safety_rating\": \"Low/Moderate/High\",\n"
                "    \"accessibility\": \"Nearest airport/railway, road condition\",\n"
                "    \"permit_required\": \"Yes/No (details)\",\n"
                "    \"photos\": [\"[https://images.unsplash.com/photo-a1b2c3d4-e5f6g7h8](https://images.unsplash.com/photo-a1b2c3d4-e5f6g7h8)\", \"[https://images.unsplash.com/photo-i9j8k7l6-m5n4o3p2](https://images.unsplash.com/photo-i9j8k7l6-m5n4o3p2)\"]\n"
                "  }\n"
                "]"
            )
        )

    def city_research_task(self, agent, inputs, place):
        return Task(
            name='city_research',
            description=(f"""
                Provide detailed inputs about {place} customized to the user.

                User Preferences:
                - Travel type: {inputs['travel_type']}
                - People: {inputs['no_of_people']} ({inputs['group_type']})
                - Duration: {inputs['duration']} days
                - Interests: {inputs['interests']}
                - Planning Style: {inputs.get('planning_style', 'Not specified')}
                - Budget Breakdown:
                  - Transport: ₹{inputs.get('budget_range', {}).get('transport', ('N/A', 'N/A'))}
                  - Accommodation: ₹{inputs.get('budget_range', {}).get('accommodation', ('N/A', 'N/A'))}
                  - Food: ₹{inputs.get('budget_range', {}).get('food', ('N/A', 'N/A'))}
                  - Entertainment: ₹{inputs.get('budget_range', {}).get('entertainment', ('N/A', 'N/A'))}
                - Start Date: {inputs.get('start_date', 'Not provided')}

                Return ONLY JSON:
                {{
                  "top_attractions": [
                    {{
                      "name": "string",
                      "description": "string",
                      "category": "Historical|Natural|Cultural|Spiritual|Adventure|Other",
                      "why_visit": "string",
                      "best_time_of_day": "string"
                    }}
                  ],
                  "local_cuisine": [
                    {{
                      "dish": "string",
                      "description": "string",
                      "recommended_places": ["string"]
                    }}
                  ]
                }}
            """),
            agent=agent,
            expected_output='{"top_attractions":[...],"local_cuisine":[...]}'
        )

    def schedule_trip_task(self, agent, place, inputs, attractions, cuisines):
        return Task(
            name='trip_scheduling',
            description=(f"""
                Create a detailed travel itinerary for a trip to {place}.

                - Travel type: {inputs['travel_type']}
                - People: {inputs['no_of_people']} ({inputs['group_type']})
                - Duration: {inputs['duration']} days
                - Interests: {inputs['interests']}
                - Planning Style: {inputs.get('planning_style', 'Not specified')}
                - Budget Breakdown:
                  - Transport: ₹{inputs.get('budget_range', {}).get('transport', ('N/A', 'N/A'))}
                  - Accommodation: ₹{inputs.get('budget_range', {}).get('accommodation', ('N/A', 'N/A'))}
                  - Food: ₹{inputs.get('budget_range', {}).get('food', ('N/A', 'N/A'))}
                  - Entertainment: ₹{inputs.get('budget_range', {}).get('entertainment', ('N/A', 'N/A'))}
                - Start Date: {inputs.get('start_date', 'Not provided')}
                - Selected Place: {place}
                - Selected Attractions: {", ".join(attractions)}
                - Selected Cuisines: {", ".join(cuisines)}

                Your job:
                - Distribute attractions and cuisines across {inputs["duration"]} days.
                - Consider budget, group type, and transit time between spots.
                - Include variety across days and insert breaks.
                - Add travel steps (mode/time/approx cost) between locations.

                Return ONLY valid JSON in this structure:
                {{
                  "itinerary": [
                    {{
                      "day": <int>,
                      "steps": [
                        {{
                          "type": "spot",
                          "name": <string>,
                          "category": <string>,
                          "visit_time": <string>,
                          "must_visit_time": <string>,
                          "reason": <string>,
                          "arrival_time": <string>,
                          "depart_time": <string>
                        }},
                        {{
                          "type": "accommodation",
                          "options": [
                            {{
                              "name": <string>,
                              "location": <string>,
                              "price_range": <string>,
                              "rating": <float>,
                              "arrival_time": <string>,
                              "depart_time": <string>
                            }}
                          ]
                        }},
                        {{
                          "type": "restaurant",
                          "options": [
                            {{
                              "name": <string>,
                              "location": <string>,
                              "rating": <float>,
                              "cuisines_served": [<string>],
                              "arrival_time": <string>,
                              "depart_time": <string>
                            }}
                          ]
                        }},
                        {{
                          "type": "cuisine",
                          "dish": <string>,
                          "origin": <string>,
                          "time_to_consume": <string>
                        }},
                        {{
                          "type": "break",
                          "duration": <string>,
                          "activity": <string>,
                          "arrival_time": <string>,
                          "depart_time": <string>
                        }},
                        {{
                          "type": "travel",
                          "from": <string>,
                          "to": <string>,
                          "options": [
                            {{
                              "mode": <string>,
                              "time": <string>,
                              "cost": <string>,
                              "arrival_time": <string>,
                              "depart_time": <string>
                            }}
                          ]
                        }}
                      ]
                    }}
                  ]
                }}
            """),
            agent=agent,
            expected_output="{'itinerary':[...]}"
        )

    # ---------- NEW FEATURE TASKS ----------

    def safety_info_task(self, agent, inputs, place):
        return Task(
            name="safety_information",
            description=(f"""
                Provide concise safety guidance for {place} tailored to this traveler.

                Context:
                - Travel type: {inputs['travel_type']}
                - Group: {inputs['no_of_people']} ({inputs['group_type']})
                - Duration: {inputs['duration']} days
                - Interests: {inputs['interests']}
                - Start Date: {inputs.get('start_date', 'Not provided')}

                Return ONLY JSON:
                {{
                  "overall_risk_level": "Low|Moderate|High",
                  "common_scams": ["string"],
                  "neighborhood_safety": [
                    {{
                      "area": "string",
                      "note": "string",
                      "best_time_to_visit": "string"
                    }}
                  ],
                  "local_laws_and_norms": ["string"],
                  "health": {{
                    "food_water_safety": "string",
                    "mosquito_advice": "string",
                    "altitude_note": "string"
                  }},
                  "emergency_contacts": {{
                    "all_emergencies": "112",
                    "police": "100",
                    "ambulance": "108",
                    "fire": "101"
                  }},
                  "solo_travel_tips": ["string"]
                }}
            """),
            agent=agent,
            expected_output='{"overall_risk_level":"...",...}'
        )

    def packing_list_task(self, agent, inputs, place):
        return Task(
            name="packing_list",
            description=(f"""
                Generate a practical packing list for {place}.

                Inputs:
                - Duration: {inputs['duration']} days
                - Interests: {inputs['interests']}
                - Group Type: {inputs['group_type']}
                - Start Date: {inputs.get('start_date', 'Not provided')} (infer likely season for {place})
                - Travel Type: {inputs['travel_type']}

                Return ONLY JSON:
                {{
                  "season": "Winter|Summer|Monsoon|Transitional",
                  "essentials": [{{"item":"string","why":"string","qty":"string"}}],
                  "clothing": [{{"item":"string","why":"string","qty":"string"}}],
                  "footwear": [{{"item":"string","why":"string","qty":"string"}}],
                  "toiletries_health": [{{"item":"string","why":"string","qty":"string"}}],
                  "gadgets": [{{"item":"string","why":"string","qty":"string"}}],
                  "documents_money": [{{"item":"string","why":"string","qty":"string"}}],
                  "optional_activity_specific": [{{"item":"string","why":"string","qty":"string"}}]
                }}
            """),
            agent=agent,
            expected_output='{"season":"...", "essentials":[...], ...}'
        )

    def budget_advisor_task(self, agent, inputs, place=None):
        return Task(
            name="dynamic_budget_handling",
            description=(f"""
                If total budget is given, allocate into ranges for transport, accommodation, food, entertainment.
                If per-category is given, validate and add per-day estimates for {inputs['duration']} days and {inputs['no_of_people']} people.

                Inputs:
                - Total budget (optional): {inputs.get('total_budget')}
                - Existing category ranges (optional): {inputs.get('budget_range')}
                - Trip style: {inputs['travel_type']}
                - Group type: {inputs['group_type']}
                - People: {inputs['no_of_people']}
                - Duration: {inputs['duration']} days
                - Destination (optional): {place or 'Not specified'}

                Return ONLY JSON:
                {{
                  "budget_range": {{
                    "transport": ["min","max"],
                    "accommodation": ["min","max"],
                    "food": ["min","max"],
                    "entertainment": ["min","max"]
                  }},
                  "per_day_estimate_per_person": {{
                    "transport": "₹",
                    "accommodation": "₹",
                    "food": "₹",
                    "entertainment": "₹",
                    "total": "₹"
                  }},
                  "notes": ["string"]
                }}
            """),
            agent=agent,
            expected_output='{"budget_range":{...},"per_day_estimate_per_person":{...},"notes":[...]}'
        )

    def transport_options_task(self, agent, inputs, place):
        return Task(
            name="transport_options",
            description=(f"""
                Recommend intercity and in-city transport options for {place}.

                User:
                - Group: {inputs['no_of_people']} ({inputs['group_type']})
                - Budget: {inputs.get('budget_range')}
                - Duration: {inputs['duration']} days
                - Travel Type: {inputs['travel_type']}

                Return ONLY JSON:
                {{
                  "intercity": [
                    {{
                      "mode": "Flight|Train|Volvo Bus|Self-drive|Cab",
                      "from": "Common origin (generic)",
                      "to": "{place}",
                      "time": "e.g., 2h",
                      "approx_cost": "₹",
                      "pro_tip": "string"
                    }}
                  ],
                  "in_city": [
                    {{
                      "mode": "Metro|Local Bus|Auto|Cab|Rental Scooter|Walk",
                      "when_to_use": "string",
                      "approx_cost": "₹",
                      "coverage": "Area/neighborhood coverage",
                      "pro_tip": "string"
                    }}
                  ]
                }}
            """),
            agent=agent,
            expected_output='{"intercity":[...],"in_city":[...]}'
        )

    def stay_advisor_task(self, agent, inputs, place):
        return Task(
            name="accommodation_suggestions",
            description=(f"""
                Propose accommodation options in {place} across budget tiers.

                User:
                - People: {inputs['no_of_people']} ({inputs['group_type']})
                - Trip style: {inputs['travel_type']}
                - Duration: {inputs['duration']} days
                - Budget ranges: {inputs.get('budget_range')}

                Return ONLY JSON:
                {{
                  "stays": [
                    {{
                      "name": "string",
                      "type": "Hostel|Budget Hotel|Boutique|Resort|Homestay|Heritage",
                      "area": "string",
                      "approx_price_per_night": "₹",
                      "suits": "Solo|Couple|Family|Friends",
                      "vibe": "Calm|Nightlife|Scenic|Central|Heritage",
                      "why": "string"
                    }}
                  ],
                  "neighborhoods": [
                    {{
                      "name": "string",
                      "good_for": ["string"],
                      "avoid_if": ["string"]
                    }}
                  ]
                }}
            """),
            agent=agent,
            expected_output='{"stays":[...],"neighborhoods":[...]}'
        )

    def reviews_task(self, agent, place):
        return Task(
            name="reviews_and_ratings",
            description=(f"""
                Summarize likely reviews & ratings patterns for {place} (typical traveler sentiment).

                Return ONLY JSON:
                {{
                  "attractions": [
                    {{
                      "name": "string",
                      "average_rating": 4.3,
                      "pros": ["string"],
                      "cons": ["string"],
                      "tip": "string"
                    }}
                  ],
                  "restaurants": [
                    {{
                      "name": "string",
                      "average_rating": 4.2,
                      "pros": ["string"],
                      "cons": ["string"],
                      "tip": "string"
                    }}
                  ]
                }}
            """),
            agent=agent,
            expected_output='{"attractions":[...],"restaurants":[...]}'
        )


# ----------------------------
# Orchestration
# ----------------------------
class Tripcrew:
    def __init__(self, inputs):
        self.inputs = inputs
        self.output = None
        st.write("DEBUG — Tripcrew initialized with inputs", self.inputs)

        # Auto-split total budget if category ranges missing
        if (not self.inputs.get("budget_range") or
            all(v is None for v in self.inputs.get("budget_range", {}).values())) and self.inputs.get("total_budget"):
            total = self.inputs["total_budget"]
            split = {
                "transport": (int(0.25 * total), int(0.35 * total)),
                "accommodation": (int(0.35 * total), int(0.45 * total)),
                "food": (int(0.15 * total), int(0.25 * total)),
                "entertainment": (int(0.05 * total), int(0.15 * total)),
            }
            self.inputs["budget_range"] = split

    # --- Weather helpers ---
    def get_current_weather(self, city_name: str):
        if not OPENWEATHER_API_KEY:
            st.write("DEBUG — Tripcrew initialized with inputs:", self.inputs)
            return None
        try:
            url = (
                f"[http://api.openweathermap.org/data/2.5/weather?q=](http://api.openweathermap.org/data/2.5/weather?q=){city_name}"
                f"&appid={OPENWEATHER_API_KEY}&units=metric"
            )
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            data = response.json()
            st.write(f"DEBUG — Weather API raw response for {city_name}:", data)
            return {
                "temperature": data["main"]["temp"],
                "description": data["weather"][0]["description"],
                "humidity": data["main"]["humidity"],
                "wind_speed": data["wind"]["speed"],
            }
        except Exception as e:
            print(f"Failed to fetch weather for {city_name}: {e}")
            return None

    def should_show_weather(self) -> bool:
        st.write("DEBUG — Checking whether to show weather...")
        start_date_str = self.inputs.get("start_date")
        planning_style = self.inputs.get("planning_style")
        if not start_date_str or not planning_style:
            return False
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        except Exception:
            return False
        today = datetime.utcnow().date()
        days_until_trip = (start_date - today).days
        if planning_style == "holiday_based" and 0 <= days_until_trip <= 3:
            return True
        return False

    # --- Core flows already in your app ---
    def run(self):
        st.write("DEBUG — [run] Starting city selection")
        agents = TripAgents()
        tasks = Triptasks()

        city_selector = agents.city_selector_agent()
        st.write("DEBUG — Created city_selector_agent:", city_selector)
        st.write("DEBUG — Agent description:", getattr(city_selector, "description", "N/A"))
        st.write("DEBUG — Agent expected_output:", getattr(city_selector, "expected_output", "N/A"))

        select_cities = tasks.city_selection_task(city_selector, self.inputs)
        st.write("DEBUG — Created city_selection_task", select_cities)

        crew = Crew(
            agents=[city_selector],
            tasks=[select_cities],
            verbose=True
        )
        st.write("DEBUG — Crew created", crew)

        result = crew.kickoff()
        st.write("DEBUG — Crew kickoff result", result)

        if hasattr(result, "tasks_output"):
            task_output = result.tasks_output[0].raw if result.tasks_output else "No output"
            st.write("DEBUG — Raw Task Output", task_output)
            self.output = task_output
        else:
            st.write("DEBUG — No output from crew")
            self.output = "No output"

        formatter = format_data()
        formatted_places = formatter.format_city_suggestions(self.output)
        st.write("DEBUG — Formatted City Suggestions", formatted_places)

        if self.should_show_weather():
            st.write("DEBUG — Weather display enabled")
            for place in formatted_places:
                city_name = place.get("place")
                if city_name:
                    weather = self.get_current_weather(city_name)
                    place["weather"] = weather if weather else {}

        self.output = formatted_places
        return self.output

    def run_local_expert(self, selected_place):
        st.write(f"DEBUG — [run_local_expert] Starting for {selected_place}")
        agents = TripAgents()
        tasks = Triptasks()

        local_expert = agents.local_expert_agent()
        st.write("DEBUG — Created local_expert_agent:", local_expert)

        research_task = tasks.city_research_task(local_expert, self.inputs, selected_place)
        st.write("DEBUG — Created city_research_task:", research_task)

        crew = Crew(agents=[local_expert], tasks=[research_task], verbose=True)
        st.write("DEBUG — Crew created:", crew)

        result = crew.kickoff()
        st.write("DEBUG — Raw Crew result:", result)

        if hasattr(result, "tasks_output") and result.tasks_output:
            self.output = result.tasks_output[0].raw
            st.write("DEBUG — Raw Task Output:", self.output)
        else:
            self.output = "No output"
        return self.output

    def run_schedule_trip(self, selected_place, selected_attractions, selected_cuisines):
        st.write(f"DEBUG — [run_schedule_trip] for {selected_place}")
        st.write("DEBUG — Selected attractions:", selected_attractions)
        st.write("DEBUG — Selected cuisines:", selected_cuisines)

        agents = TripAgents()
        tasks = Triptasks()

        scheduling_expert = agents.trip_scheduler_agent()
        st.write("DEBUG — Created trip_scheduler_agent:", scheduling_expert)

        schedule_task = tasks.schedule_trip_task(
            scheduling_expert, selected_place, self.inputs, selected_attractions, selected_cuisines
        )
        st.write("DEBUG — Created schedule_trip_task:", schedule_task)

        crew = Crew(agents=[scheduling_expert], tasks=[schedule_task], verbose=True)
        result = crew.kickoff()
        st.write("DEBUG — Raw Crew result:", result)

        if hasattr(result, "tasks_output") and result.tasks_output:
            self.output = result.tasks_output[0].raw
            st.write("DEBUG — Raw Task Output:", self.output)
        else:
            self.output = "No output"
        return self.output

    # --- NEW feature flows (call these from your API endpoints) ---
    def run_safety_info(self, selected_place):
        st.write(f"DEBUG — [run_safety_info] for {selected_place}")
        agents = TripAgents()
        tasks = Triptasks()
        agent = agents.safety_info_agent()
        task = tasks.safety_info_task(agent, self.inputs, selected_place)
        crew = Crew(agents=[agent], tasks=[task], verbose=True)
        result = crew.kickoff()
        st.write("DEBUG — Raw result:", result)
        return result.tasks_output[0].raw if hasattr(result, "tasks_output") else "No output"

    def run_packing_list(self, selected_place):
        st.write(f"DEBUG — [run_packing_list] for {selected_place}")
        agents = TripAgents()
        tasks = Triptasks()
        agent = agents.packing_list_agent()
        task = tasks.packing_list_task(agent, self.inputs, selected_place)
        crew = Crew(agents=[agent], tasks=[task], verbose=True)
        result = crew.kickoff()
        st.write("DEBUG — Raw result:", result)
        return result.tasks_output[0].raw if hasattr(result, "tasks_output") else "No output"

    def run_budget_breakdown(self, selected_place=None):
        st.write(f"DEBUG — [run_budget_breakdown] for {selected_place}")
        agents = TripAgents()
        tasks = Triptasks()
        agent = agents.budget_advisor_agent()
        task = tasks.budget_advisor_task(agent, self.inputs, selected_place)
        crew = Crew(agents=[agent], tasks=[task], verbose=True)
        result = crew.kickoff()
        st.write("DEBUG — Raw result:", result)
        return result.tasks_output[0].raw if hasattr(result, "tasks_output") else "No output"

    def run_transport_options(self, selected_place):
        st.write(f"DEBUG — [run_transport_options] for {selected_place}")
        agents = TripAgents()
        tasks = Triptasks()
        agent = agents.transport_agent()
        task = tasks.transport_options_task(agent, self.inputs, selected_place)
        crew = Crew(agents=[agent], tasks=[task], verbose=True)
        result = crew.kickoff()
        st.write("DEBUG — Raw result:", result)
        return result.tasks_output[0].raw if hasattr(result, "tasks_output") else "No output"

    def run_accommodation_suggestions(self, selected_place):
        st.write(f"DEBUG — [run_accommodation_suggestions] for {selected_place}")
        agents = TripAgents()
        tasks = Triptasks()
        agent = agents.stay_advisor_agent()
        task = tasks.stay_advisor_task(agent, self.inputs, selected_place)
        crew = Crew(agents=[agent], tasks=[task], verbose=True)
        result = crew.kickoff()
        st.write("DEBUG — Raw result:", result)
        return result.tasks_output[0].raw if hasattr(result, "tasks_output") else "No output"

    def run_reviews_and_ratings(self, selected_place):
        st.write(f"DEBUG — [run_reviews_and_ratings] for {selected_place}")
        agents = TripAgents()
        tasks = Triptasks()
        agent = agents.reviews_agent()
        task = tasks.reviews_task(agent, selected_place)
        crew = Crew(agents=[agent], tasks=[task], verbose=True)
        result = crew.kickoff()
        st.write("DEBUG — Raw result:", result)
        return result.tasks_output[0].raw if hasattr(result, "tasks_output") else "No output"


# ----------------------------
# Formatters / Parsers
# ----------------------------
class format_data:
    def _extract_json_in_backticks(self, text):
        if not isinstance(text, str):
            return None
        match = re.search(r"```json\s*(\{.*?\}|\[.*?\])\s*```", text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1)
        # Fallback: try to find array/object
        alt = re.search(r"(\{.*\}|\[.*\])", text, re.DOTALL)
        return alt.group(1) if alt else None

    def format_city_suggestions(self, places_data):
        # Try to parse the input into a list of dicts
        if isinstance(places_data, list):
            places = places_data
        else:
            raw = self._extract_json_in_backticks(places_data) or places_data
            try:
                places = json.loads(raw)
            except Exception:
                st.write("DEBUG — Failed to parse places_data:", raw)
                return []

        formatted = []
        for item in places:
            formatted.append({
                "place": item.get("place", "Unknown"),
                "reason": item.get("reason", "No reason provided."),
                "weather_suitability": item.get("weather_suitability", "—"),
                "travel_cost_estimate": item.get("travel_cost_estimate", {}),
                "accommodation_range": item.get("accommodation_range", "—"),
                "safety_rating": item.get("safety_rating", "—"),
                "accessibility": item.get("accessibility", "—"),
                "permit_required": item.get("permit_required", "—"),
                "photos": item.get("photos", [])
            })

        return formatted

    def format_local_expertise(self, local_output):
        raw = self._extract_json_in_backticks(local_output) or local_output
        try:
            data = json.loads(raw) if isinstance(raw, str) else (raw or {})
        except Exception:
            return {}
        return {
            "top_attractions": data.get("top_attractions", []) if isinstance(data.get("top_attractions", []),
                                                                             list) else [],
            "local_cuisine": data.get("local_cuisine", []) if isinstance(data.get("local_cuisine", []), list) else []
        }

    def format_trip_schedule(self, schedule_json):
        if isinstance(schedule_json, dict):
            return schedule_json
        raw = self._extract_json_in_backticks(schedule_json) or (schedule_json or "")
        try:
            return json.loads(raw)
        except Exception:
            return {"error": "Invalid JSON format received from the model."}

    # ---- NEW parsers (optional) ----
    def format_safety_info(self, raw):
        js = self._extract_json_in_backticks(raw) or raw
        try:
            return json.loads(js)
        except Exception:
            return {}

    def format_packing_list(self, raw):
        js = self._extract_json_in_backticks(raw) or raw
        try:
            return json.loads(js)
        except Exception:
            return {}

    def format_budget_breakdown(self, raw):
        js = self._extract_json_in_backticks(raw) or raw
        try:
            return json.loads(js)
        except Exception:
            return {}

    def format_transport_options(self, raw):
        js = self._extract_json_in_backticks(raw) or raw
        try:
            return json.loads(js)
        except Exception:
            return {}

    def format_accommodation_suggestions(self, raw):
        js = self._extract_json_in_backticks(raw) or raw
        try:
            return json.loads(js)
        except Exception:
            return {}

    def format_reviews(self, raw):
        js = self._extract_json_in_backticks(raw) or raw
        try:
            return json.loads(js)
        except Exception:
            return {}