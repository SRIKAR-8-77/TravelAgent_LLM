import re
import os
import json
from crewai import Agent, Task, Crew, LLM
from dotenv import load_dotenv
from crewai.tools import BaseTool
from typing import ClassVar

import requests

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# Ensure you have these in your .env file
UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY")
UNSPLASH_SECRET_KEY = os.getenv("UNSPLASH_SECRET_KEY")


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
                "per_page": 3,
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
# Instantiate the new tool
unsplash_tool = UnsplashSearchTool()


class TripAgents:
    def __init__(self):
        self.llm = LLM(
            model="gemini/gemini-2.0-flash",
            temperature=0.1
        )

    def city_selector_agent(self):
        return Agent(
            role='Indian Travel Destination Expert',
            goal='Identify the best Indian places to visit—including cities, villages, valleys, beaches, historical and devotional sites, and hidden gems—based on user preferences. Also, find and provide photo URLs for each destination.',
            backstory=(
                "A passionate Indian travel curator with deep knowledge of India's cultural, historical, natural, and spiritual destinations. "
                "From the majestic Himalayas and serene coastal beaches to sacred pilgrimage towns and offbeat rural villages, "
                "this expert helps travelers discover both iconic and lesser-known gems across India tailored to their interests, and provides visual inspiration for their trip."
            ),
            llm=self.llm,
            verbose=True,
            tools=[unsplash_tool]  # The agent now uses the Unsplash tool
        )

    def local_expert_agent(self):
        return Agent(
            role='Local Indian Travel Expert',
            goal='Provide rich insights about selected Indian places including top attractions, local traditions, cuisines, festivals, and hidden gems',
            backstory=(
                "A seasoned local guide deeply familiar with the traditions, flavors, folklore, and attractions of Indian towns, villages, and tourist spots. "
                "From spiritual ghats and ancient forts to bustling bazaars and offbeat nature retreats, "
                "this expert curates immersive experiences rooted in local Indian culture."
            ),
            llm=self.llm,
            verbose=True
        )

    def trip_scheduler_agent(self):
        return Agent(
            role="Indian Trip Itinerary Planner",
            goal="Organize selected Indian attractions, food, and experiences into a culturally rich, day-wise travel schedule",
            backstory=(
                "An experienced Indian travel coordinator who blends spiritual visits, heritage walks, scenic getaways, local food trails, "
                "and cultural fests into a smooth itinerary. Efficiently plans accommodations, transport (train, cab, local options), and rest stops, "
                "keeping in mind regional travel times, climate, and traveler preferences."
            ),
            llm=self.llm,
            verbose=True
        )


class Triptasks:
    def __init__(self):
        pass

    def city_selection_task(self, agent, inputs):
        return Task(
            name='place_selection',
            description=(
                f"Analyze the user preferences, and for each suggestion, use the 'Unsplash Image Search' tool to find and fetch 2-3 photo URLs. Return ONLY a pure JSON array with 3 Indian travel destinations. No extra description, only data.\n"
                f"Each object must have 'place', 'reason', and 'photos' keys. The 'photos' key must be an array of image URLs.\n"
                f"Do NOT include any explanation before or after.\n"
                f"Choose from various types like hill stations, beaches, historical sites, spiritual centers, scenic valleys, rural villages, etc.\n"
                f"- Travel Type: {inputs['travel_type']}\n"
                f"- budget_range: {inputs['budget_range']}\n"
                f"- Duration: {inputs['duration']}\n"
                f"- Interests: {inputs['interests']}\n"
                f"- Group Type: {inputs['group_type']}\n"
                f"- No of People: {inputs['no_of_people']}\n"
                f"Output: Provide 5 destination options with a brief rationale and 2-3 photo URLs for each."
                f"No extra description, only json data."
            ),
            agent=agent,
            expected_output=(
                "Return only a valid JSON array of 3 place recommendations, no commentary, no markdown formatting. "
                "Example:\n"
                '[\n'
                '  {\n'
                '    "place": "Hampi",\n'
                '    "reason": "Rich in ancient ruins and UNESCO heritage sites, perfect for history lovers.",\n'
                '    "photos": ["https://images.unsplash.com/photo-1...", "https://images.unsplash.com/photo-2..."]\n'
                '  },\n'
                '  {\n'
                '    "place": "Munnar",\n'
                '    "reason": "Ideal for nature lovers, with tea plantations and cool hill station weather.",\n'
                '    "photos": ["https://images.unsplash.com/photo-1...", "https://images.unsplash.com/photo-2..."]\n'
                '  },\n'
                '  {\n'
                '    "place": "Varanasi",\n'
                '    "reason": "A spiritual experience with Ganga Aarti, temples, and heritage ghats.",\n'
                '    "photos": ["https://images.unsplash.com/photo-1...", "https://images.unsplash.com/photo-2..."]\n'
                '  }\n'
                ']'
            )
        )

    def city_research_task(self, agent, inputs, place):
        return Task(
            name='city_research',
            description=(
                f"""Provide detailed inputs about {place} including:\n
                f"- Top attractions according to user preferences\n"
                f"- Local cuisine highlights according user preferences\n"
                f"according to User Preferences:\n"
                f"- Travel Type: {inputs['travel_type']}\n"
                f"- Budget: {inputs['budget_range']}\n"
                f"- Duration: {inputs['duration']}\n"
                f"- Interests: {inputs['interests']}\n"
                f"- Group Type: {inputs['group_type']}\n"
                f"- No of People: {inputs['no_of_people']}\n"
                """
            ),
            agent=agent,
            expected_output=(
                '{\n'
                '  "top_attractions": [\n'
                '    {\n'
                '      "name": "Attraction Name 1",\n'
                '      "description": "A brief description of Attraction 1",\n'
                '      "category": "Historical / Natural / Cultural / Other",\n'
                '      "why_visit": "A compelling reason to visit this attraction"\n'
                '    },\n'
                '    {\n'
                '      "name": "Attraction Name 2",\n'
                '      "description": "A brief description of Attraction 2",\n'
                '      "category": "Historical / Natural / Cultural / Other",\n'
                '      "why_visit": "A compelling reason to visit this attraction"\n'
                '    },\n'
                '    ...\n'
                '  ],\n'
                '  "local_cuisine": [\n'
                '    {\n'
                '      "dish": "Dish Name 1",\n'
                '      "description": "Brief description of the dish",\n'
                '      "origin": "Region or city of origin (optional)",\n'
                '      "recommended_places": ["Restaurant 1", "Street vendor 2", "..."]\n'
                '    },\n'
                '    {\n'
                '      "dish": "Dish Name 2",\n'
                '      "description": "Brief description of the dish",\n'
                '      "origin": "Region or city of origin (optional)",\n'
                '      "recommended_places": ["Restaurant 1", "Street vendor 2", "..."]\n'
                '    },\n'
                '    ...\n'
                '  ]\n'
                '}'
            )

        )

    def schedule_trip_task(self, agent, place, inputs, attractions, cuisines):
        return Task(
            name='trip_scheduling',
            description=(
                f"""Create a detailed travel itinerary for a trip to {place}.

                User Preferences:
                - Travel Type: {inputs["travel_type"]}
                - Budget Range: {inputs["budget_range"]}
                - Duration: {inputs["duration"]} days
                - Interests: {inputs["interests"]}
                - Group Type: {inputs['group_type']}
                - No of People: {inputs['no_of_people']}

                Selected Attractions:
                {json.dumps(attractions, indent=2)}

                Selected Local Cuisines:
                {json.dumps(cuisines, indent=2)}

                Your job:
                - Distribute the attractions and cuisines across {inputs["duration"]} days.
                - Consider the user's budget, travel type, and interests and group type.
                - Plan smart travel between locations with appropriate modes and cost.
                - Include variety: cultural, natural, or spiritual attractions as applicable.
                - Use the selected dishes appropriately in meal slots.

                For each day, include:
                - Attractions (from the selected list) with timing and reasons.
                - At least one local dish (from the selected cuisines).
                - Accommodation suggestions (3 options) .
                - Restaurant suggestions for at least one meal, with cuisines served.
                - A break (rest/flexible time).
                - Travel steps between locations, mode options.

                📦 Return only a **valid JSON** in the structure below:

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

                ❌ No extra commentary. ✅ Only return the final JSON.
                """
            ),
            agent=agent,
            expected_output="A complete itinerary JSON as per the structure given.",

        )


class Tripcrew:
    def __init__(self, inputs):
        self.inputs = inputs
        self.output = None

    def run(self):
        agents = TripAgents()
        tasks = Triptasks()

        city_selector = agents.city_selector_agent()

        select_cities = tasks.city_selection_task(city_selector, self.inputs)

        crew = Crew(
            agents=[city_selector],
            tasks=[select_cities],
            verbose=True
        )
        result = crew.kickoff()
        if hasattr(result, "tasks_output"):
            task_output = result.tasks_output[0].raw if result.tasks_output else "No output"
            self.output = task_output
        return self.output

    def run_local_expert(self, selected_place):
        agents = TripAgents()
        tasks = Triptasks()

        local_expert = agents.local_expert_agent()
        research_task = tasks.city_research_task(local_expert, self.inputs, selected_place)

        crew = Crew(
            agents=[local_expert],
            tasks=[research_task],
            verbose=True
        )

        result = crew.kickoff()

        if hasattr(result, "tasks_output"):
            task_output = result.tasks_output[0].raw if result.tasks_output else "No output"
            self.output = task_output
        return self.output

    def run_schedule_trip(self, selected_place, selected_attractions, selected_cuisines):
        agents = TripAgents()
        tasks = Triptasks()

        scheduling_expert = agents.trip_scheduler_agent()
        schedule_task = tasks.schedule_trip_task(scheduling_expert, selected_place, self.inputs, selected_attractions,
                                                 selected_cuisines)

        crew = Crew(
            agents=[scheduling_expert],
            tasks=[schedule_task],
            verbose=True
        )

        result = crew.kickoff()

        if hasattr(result, "tasks_output"):
            task_output = result.tasks_output[0].raw if result.tasks_output else "No output"
            self.output = task_output
        return self.output


class format_data:
    def format_city_suggestions(self, places_data):
        """
        Accepts a JSON-formatted string (even wrapped in ```JSON ... ```) or a list.
        Returns a clean list of dicts: [{"city": ..., "reason": ..., "photos": [...]}, ...]
        """
        if isinstance(places_data, str):
            match = re.search(r"```json\s*(\[\s*{.*?}\s*])\s*```", places_data, re.DOTALL)
            if not match:
                print("Could not find JSON data in the expected format.")
                return []
            cleaned = match.group(1)
            try:
                places = json.loads(cleaned)
            except json.JSONDecodeError as e:
                print("JSON Decode Error:", e)
                return []

        elif isinstance(places_data, list):
            places = places_data
        else:
            print("Unsupported data format")
            return []

        # Format and validate each city entry
        formatted_city_list = []
        for item in places:
            place = item.get("place", "Unknown")
            reason = item.get("reason", "No reason provided.")
            photos = item.get("photos", [])  # Get the list of photos, defaulting to an empty list
            formatted_city_list.append({"place": place, "reason": reason, "photos": photos})

        return formatted_city_list

    def format_local_expertise(self, local_output):
        """
        Accepts a string (raw JSON or wrapped in ```json ... ```), or a dict.
        Returns a dict with keys: 'top_attractions' and 'local_cuisine'.
        """
        if isinstance(local_output, str):
            # Match JSON inside ```json ... ```
            pattern = r"```json\s*(\{.*?\}|\[.*?\])\s*```"
            match = re.search(pattern, local_output, re.DOTALL)

            # If match found, extract JSON string
            if match:
                json_str = match.group(1)
            else:
                # Assume it's raw JSON (not wrapped in triple backticks)
                json_str = local_output

            # Try to parse it
            try:
                local_expertize = json.loads(json_str)
            except json.JSONDecodeError as e:
                print("JSON Decode Error:", e)
                return {}

        elif isinstance(local_output, dict):
            local_expertize = local_output
        else:
            print("Unsupported data format")
            return {}

        # Validate structure
        top_attractions = local_expertize.get("top_attractions", [])
        local_cuisine = local_expertize.get("local_cuisine", [])

        return {
            "top_attractions": top_attractions if isinstance(top_attractions, list) else [],
            "local_cuisine": local_cuisine if isinstance(local_cuisine, list) else []
        }

    def format_trip_schedule(self, schedule_json):
        """
        Accepts a JSON-formatted string (even wrapped in ```json ... ```) or a dict.
        It robustly finds the JSON, parses it, and returns it as a dictionary.
        """
        if isinstance(schedule_json, dict):
            # If it's already a dictionary, we're good.
            return schedule_json

        if isinstance(schedule_json, str):
            # This regex will find a JSON object even if it's inside markdown code fences.
            match = re.search(r"```json\s*(\{.*?\})\s*```", schedule_json, re.DOTALL)

            if match:
                # If found in backticks, extract the JSON part.
                cleaned_json_str = match.group(1)
            else:
                # Otherwise, assume the whole string is the JSON.
                cleaned_json_str = schedule_json.strip()

            try:
                # Convert the clean JSON string into a Python dictionary.
                return json.loads(cleaned_json_str)
            except json.JSONDecodeError as e:
                print(f"JSON Decode Error in format_trip_schedule: {e}")
                # Return a structured error that the frontend can identify.
                return {"error": "Invalid JSON format received from the model."}

        # If the input is not a string or dictionary, return an error.
        return {"error": "Unsupported input format."}
