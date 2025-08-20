from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
import os
from typing import  List, Dict, Any, Optional
from dotenv import load_dotenv
from pydantic.v1.errors import cls_kwargs

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("Missing Open Ai API key, please set")

app = FastAPI(
    title="AI Tutor API",
    description="API for generating personalized tutoring content and quizzes",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods= ["*"],
    allow_headers=["*"]
)

class trip_attributes(BaseModel):
    travel_type: str = Field(description="TYPE OF TRAVEL")
    interests: str = Field(description="NATURE??")
    season: str = Field(description="SEASON")
    duration: str = Field(description="HOW MANY DAYS??")
    budget: str = Field(description="BUDGET")

@app.post("/tutor", response_model=TutorResponse)
async def get_tutoring_response(data: TutorRequest):
    """
    Generate a personalized tutoring explanation based on user preferences
    """

    try:
        explanation = generate_tutoring_response(
            data.subject,
            data.level,
            data.question,
            data.learning_style,
            data.background,
            data.language,
        )

        return {"response": explanation}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating explanation: {str(e)}")
