from typing import Optional, Tuple, List
from fastapi import FastAPI
from pydantic import BaseModel
from agents import Tripcrew, format_data
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Trip Planner API", version="1.0.0")

# Allow CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------
# Pydantic models
# ---------------------------

class BudgetRange(BaseModel):
    transport: Optional[Tuple[int, int]] = None
    accommodation: Optional[Tuple[int, int]] = None
    food: Optional[Tuple[int, int]] = None
    entertainment: Optional[Tuple[int, int]] = None

class Preferences(BaseModel):
    travel_type: str
    total_budget: Optional[int] = None  # e.g., INR
    budget_range: Optional[BudgetRange] = None
    no_of_people: int
    group_type: str
    duration: int
    interests: str
    start_date: Optional[str] = None  # 'YYYY-MM-DD'
    planning_style: Optional[str] = None  # e.g., "holiday_based" / "season_based"

class LocalRequest(BaseModel):
    preferences: Preferences
    selected_place: str

class ScheduleRequest(BaseModel):
    preferences: Preferences
    selected_place: str
    selected_attractions: List[str]
    selected_cuisines: List[str]

# Optional: separate request for endpoints that only need preferences
class PreferencesOnly(BaseModel):
    preferences: Preferences


# ---------------------------
# Health/root
# ---------------------------

@app.get("/")
def root():
    return {"message": "Trip Planner API is running"}


# ---------------------------
# Existing endpoints
# ---------------------------

@app.post("/generate")
def generate_trip(preferences: Preferences):
    planner = Tripcrew(preferences.dict())
    result = planner.run()
    formatted = format_data().format_city_suggestions(result)
    return {"raw": result, "places": formatted}

@app.post("/local-info")
def get_local_info(data: LocalRequest):
    planner = Tripcrew(data.preferences.dict())
    raw = planner.run_local_expert(data.selected_place)
    formatted = format_data().format_local_expertise(raw)
    return {"raw": raw, "formatted": formatted}

@app.post("/schedule-trip")
def schedule(data: ScheduleRequest):
    planner = Tripcrew(data.preferences.dict())
    raw = planner.run_schedule_trip(
        data.selected_place,
        data.selected_attractions,
        data.selected_cuisines
    )
    formatted = format_data().format_trip_schedule(raw)
    return {"raw": raw, "formatted": formatted}


# ---------------------------
# NEW: Safety Information
# ---------------------------

@app.post("/safety-info")
def safety_info(data: LocalRequest):
    """
    Returns destination-specific safety advisories, local norms, scams to avoid,
    emergency numbers, hospital list, and neighborhood safety tips.
    """
    planner = Tripcrew(data.preferences.dict())
    raw = planner.run_safety_info(data.selected_place)
    formatted = format_data().format_safety_info(raw)
    return {"raw": raw, "formatted": formatted}


# ---------------------------
# NEW: Packing List Generator
# ---------------------------

@app.post("/packing-list")
def packing_list(data: LocalRequest):
    """
    Returns a smart packing list based on destination, season, activities,
    group type (family, friends), duration, and weather (if near-term).
    """
    planner = Tripcrew(data.preferences.dict())
    raw = planner.run_packing_list(data.selected_place)
    formatted = format_data().format_packing_list(raw)
    return {"raw": raw, "formatted": formatted}


# ---------------------------
# NEW: Dynamic Budget Handling
# ---------------------------

@app.post("/budget-breakdown")
def budget_breakdown(payload: PreferencesOnly):
    """
    Returns a normalized budget breakdown into transport/accommodation/food/entertainment,
    fills gaps from total_budget if category ranges are missing, and suggests daily caps.
    """
    planner = Tripcrew(payload.preferences.dict())
    raw = planner.run_budget_breakdown()
    formatted = format_data().format_budget_breakdown(raw)
    return {"raw": raw, "formatted": formatted}


# ---------------------------
# NEW: Transport Options
# ---------------------------

@app.post("/transport-options")
def transport_options(data: LocalRequest):
    """
    Returns in-city transport choices, inter-attraction routes,
    estimated times/costs, and tips (e.g., metro vs cab vs rickshaw).
    """
    planner = Tripcrew(data.preferences.dict())
    raw = planner.run_transport_options(data.selected_place)
    formatted = format_data().format_transport_options(raw)
    return {"raw": raw, "formatted": formatted}


# ---------------------------
# NEW: Accommodation Suggestions
# ---------------------------

@app.post("/accommodation-suggestions")
def accommodation_suggestions(data: LocalRequest):
    """
    Returns stay suggestions by neighborhood and price band,
    with types (hotel, homestay), pros/cons, and sample properties.
    """
    planner = Tripcrew(data.preferences.dict())
    raw = planner.run_accommodation_suggestions(data.selected_place)
    formatted = format_data().format_accommodation_suggestions(raw)
    return {"raw": raw, "formatted": formatted}


# ---------------------------
# NEW: Reviews & Ratings
# ---------------------------

@app.post("/reviews")
def reviews(data: LocalRequest):
    """
    Returns curated reviews & ratings summaries for attractions,
    restaurants, and experiences relevant to the user's interests.
    """
    planner = Tripcrew(data.preferences.dict())
    raw = planner.run_reviews_and_ratings(data.selected_place)
    formatted = format_data().format_reviews(raw)
    return {"raw": raw, "formatted": formatted}