import os
import googlemaps

from fastapi import FastAPI, Request
from pydantic import BaseModel
from agents_dev import Tripcrew, format_data
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Allow CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Preferences(BaseModel):
    travel_type: str
    budget_range: tuple
    no_of_people: int
    group_type: str
    duration: int
    interests: str

class LocalRequest(BaseModel):
    preferences: Preferences
    selected_place: str

class ScheduleRequest(BaseModel):
    preferences: Preferences
    selected_place: str
    selected_attractions: list
    selected_cuisines: list
@app.get("/")
def root():
    return {"message": "Welcome to the A"}

@app.post("/generate")
def generate_trip(preferences: Preferences):
    planner = Tripcrew(preferences.dict())
    result = planner.run()
    # This now handles the new 'photos' key in the formatted data
    formatted = format_data().format_city_suggestions(result)
    return {"raw": result, "places": formatted}

@app.post("/local-info")
def get_local_info(data: LocalRequest):
    planner = Tripcrew(data.preferences.dict())
    output = planner.run_local_expert(data.selected_place)
    formatted = format_data().format_local_expertise(output)
    return {"raw": output, "formatted": formatted}

@app.post("/schedule-trip")
def schedule(data: ScheduleRequest):
    planner = Tripcrew(data.preferences.dict())
    result = planner.run_schedule_trip(
        data.selected_place,
        data.selected_attractions,
        data.selected_cuisines
    )
    formatted = format_data().format_trip_schedule(result)
    return {"raw": result, "formatted": formatted}