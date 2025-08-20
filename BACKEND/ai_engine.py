from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage
import os
from dotenv import load_dotenv
import json
import re
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

def get_llm():
    try:
        return ChatOpenAI(
            model_name="llama3-8b-8192",  # Or "llama3-8b-8192", etc.
            openai_api_base="https://api.groq.com/openai/v1",
            openai_api_key=os.getenv("OPENAI_API_KEY"),  # You will set this in .env
            temperature=0.7,
            max_tokens=1024
        )
    except Exception as e :
        logger.error(f"ERROR intializing LLM: {str(e)}")
        raise Exception(f"Failed to initialize AI model: {str(e)}")

def generate_tutoring_response(subject,level,question,learning_style,background,language):
    """Generate a personalised tutoring response based on user preferences.

    Args:
        subject (str) : the academic subject
        level (str) : learning level (Beginner , Intermediate , Advanced)
        question (str) : User's specific question
        learning_style (str) : preferred learning style (Visual , Textbased , Hands-on)
        background (str) : User's background knowledge
        language (str) : preferred language for response

    Returns :
        str: Formated tutoring response
    """
    try:
        llm = get_llm()

        prompt = _create_tutoring_prompt(subject, level, question ,learning_style, background, language)

        logger.info(f"Generating tutoring response for subject:{subject} , level : {level}")
        response = llm([HumanMessage(content=prompt)])

        return _format_tutoring_response(response.content, learning_style)

    except Exception as e :
        logger.error(f"ERROR generating tutoring response: {str(e)}")
        raise Exception(f"Failed to generate tutoring response {str(e)}")


def _create_tutoring_prompt(subject, level, question, learning_style, background, language):
    """helper function to create a well-structured tutoring prompt"""

    prompt = f"""
    You are an expert tutor in {subject} at the {level} level,

    STUDENT PROFILE:
    - Background knowledge : {background}
    - Learning style preference : {learning_style}
    - language preference : {language}   

    Question:
    {question}

    INSTRUCTIONS:
    1. Provide a clear educational explanation that directly addresses the question
    2. Tailor your explanation to a {background} student at {level} level
    3. use {language} as the primary language
    4. Format your response with appropriate markdown for readability

    LEARNING STYLE ADAPTATIONS:
    - for Visual learners : Include descriptions of visual concepts,diagrams or mental models
    - For Text-based learners: Provide clear, structured explanations with defined concepts 
    - For Hands-on learners : Include practical examples , exercises or applications \

    Your explanation should be educational , accurate and engaging.
    """

    return prompt

def _format_tutoring_response(content, learning_style):
    """Helper function to format the tutoring response based on learning style"""

    if learning_style == "Visual":
        return content + "\n\n*Note: Visualize these concepts as you read for better retention*"
    elif learning_style == "Hands-on":
        return content + "\n\n*Tip: Try working through the examples yourself to reinforce your learning.*"
    else:
        return content