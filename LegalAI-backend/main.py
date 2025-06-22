# main.py
# This file contains the backend logic for the AI Legal Aid Assistant.
# To run this:
# 1. Install necessary libraries:
#    pip install "fastapi[all]" uvicorn python-multipart google-generativeai Pillow python-dotenv
# 2. Create a file named `.env` in the same directory as this main.py file.
# 3. In the .env file, add the following line (replace with your actual key):
#    GOOGLE_API_KEY="YOUR_API_KEY_HERE"
# 4. Save the main.py and .env files.
# 5. Run from your terminal:
#    uvicorn main:app --reload

import uvicorn
import re
import json
import os
import io
from fastapi import FastAPI, UploadFile, File, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Literal, Dict, Any
from datetime import datetime
from dotenv import load_dotenv

# --- Load Environment Variables ---
# This will load the GOOGLE_API_KEY from your .env file
load_dotenv()


# --- Gemini API Integration ---
import google.generativeai as genai
from PIL import Image

# Configure the Gemini API client
try:
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    if not GOOGLE_API_KEY:
        print("Warning: GOOGLE_API_KEY not found in .env file. API calls will fail.")
    genai.configure(api_key=GOOGLE_API_KEY)
except Exception as e:
    print(f"Error configuring Gemini API: {e}")


# --- Pydantic Models (Data Schemas) ---
class ChatMessage(BaseModel):
    id: int
    sender: Literal["user", "agent"]
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)

class Document(BaseModel):
    id: int
    name: str
    upload_date: datetime = Field(default_factory=datetime.now)
    summary: str
    extracted_data: Dict[str, Any]

class Case(BaseModel):
    id: int
    name: str
    created_at: datetime = Field(default_factory=datetime.now)
    documents: List[Document] = []
    chat_history: List[ChatMessage] = []

# --- Mock Database ---
DB: Dict[int, Case] = {}

def initialize_mock_db():
    """Populates the mock DB with some initial data for demonstration."""
    case_1 = Case(
        id=1,
        name="Parking Ticket on Elm St.",
        documents=[
            Document(
                id=101,
                name="parking_ticket.pdf",
                summary="A parking violation for an expired meter. Fine is $75, due by 2025-07-15.",
                extracted_data={"fine_amount": 75, "due_date": "2025-07-15", "violation": "Expired Meter"}
            )
        ],
        chat_history=[
            ChatMessage(id=1, sender="agent", content="Hello! I'm your case assistant. I see you've uploaded a parking ticket. How can I help you today?")
        ]
    )
    DB[1] = case_1

# --- FastAPI App Initialization ---
app = FastAPI(
    title="Legal Aid AI Agent API",
    description="API for managing legal cases and interacting with an AI assistant."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Helper Functions ---

def pii_redaction_service(text: str) -> str:
    """A simple PII redaction service using regex."""
    text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[REDACTED_EMAIL]', text)
    text = re.sub(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', '[REDACTED_PHONE]', text)
    text = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[REDACTED_SSN]', text)
    return text

def call_gemini_api_for_chat(prompt: str) -> str:
    """Makes a real call to the Google Gemini API for chat responses."""
    if not GOOGLE_API_KEY:
        return "Error: The AI assistant is not configured. Please set the GOOGLE_API_KEY in your .env file."
    try:
        print("\n--- Sending Prompt to Gemini ---")
        print(prompt)
        print("---------------------------------\n")
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Gemini API call failed: {e}")
        return "Sorry, I'm having trouble connecting to the AI service right now."

def call_gemini_api_for_document_parsing(file_content: bytes, filename: str) -> Dict[str, Any]:
    """Calls Gemini's multimodal capabilities to parse a document."""
    if not GOOGLE_API_KEY:
        return {"summary": "AI not configured.", "extracted_data": {}}
    
    try:
        image = Image.open(io.BytesIO(file_content))
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        
        prompt = """
        You are an expert data extractor for legal documents. Analyze the attached image of a document.
        First, provide a one-sentence summary of the document's purpose.
        Second, extract key information like dates, names, amounts, case numbers, and violation types.
        
        Return the information as a single, valid JSON object with two keys: "summary" and "extracted_data".
        The value for "extracted_data" should be another JSON object containing the extracted fields.
        
        Example response format:
        {
          "summary": "This is a court notice for a hearing.",
          "extracted_data": {
            "case_number": "CV-12345",
            "hearing_date": "2025-10-20",
            "fine_amount": 250
          }
        }
        """
        
        response = model.generate_content([prompt, image])
        
        json_response_text = response.text.strip().replace("```json", "").replace("```", "")
        data = json.loads(json_response_text)
        return data

    except Exception as e:
        print(f"Gemini document parsing failed: {e}")
        return {
            "summary": f"Could not automatically parse '{filename}'. Please review it manually.",
            "extracted_data": {"error": "AI parsing failed"}
        }

# --- API Endpoints ---
@app.on_event("startup")
async def startup_event():
    initialize_mock_db()

@app.get("/api/cases", response_model=List[Case])
async def get_all_cases():
    return list(DB.values())

@app.post("/api/cases", response_model=Case, status_code=201)
async def create_case(payload: Dict[str, str] = Body(...)):
    case_name = payload.get("name")
    if not case_name:
        raise HTTPException(status_code=400, detail="Case name is required.")
    new_id = max(DB.keys()) + 1 if DB else 1
    new_case = Case(
        id=new_id,
        name=case_name,
        chat_history=[
            ChatMessage(id=1, sender="agent", content=f"Hello! I've created your case '{case_name}'. How can I assist you?")
        ]
    )
    DB[new_id] = new_case
    return new_case

@app.post("/api/cases/{case_id}/chat")
async def chat_with_agent(case_id: int, payload: Dict[str, str] = Body(...)):
    user_query = payload.get("message")
    if case_id not in DB:
        raise HTTPException(status_code=404, detail="Case not found")
    if not user_query:
        raise HTTPException(status_code=400, detail="Message content is required.")
    case = DB[case_id]
    user_message_id = len(case.chat_history) + 1
    case.chat_history.append(ChatMessage(id=user_message_id, sender="user", content=user_query))
    redacted_query = pii_redaction_service(user_query)
    prompt_context = "You are a helpful and empathetic legal case assistant. Do not provide legal advice, but help the user understand their situation based on the information provided.\n\n"
    prompt_context += "--- Case Document Summaries ---\n"
    if case.documents:
        for doc in case.documents:
            prompt_context += f"Document '{doc.name}': {doc.summary}\n"
    else:
        prompt_context += "No documents have been uploaded for this case yet.\n"
    prompt_context += "\n--- Conversation History ---\n"
    for msg in case.chat_history:
        prompt_context += f"{msg.sender.capitalize()}: {msg.content}\n"
    prompt_context += f"\n--- New User Question ---\nUser: {redacted_query}\n\n---\n"
    prompt_context += "Based on all the information above, provide a helpful and concise answer to the new user question."
    agent_response_text = call_gemini_api_for_chat(prompt_context)
    agent_message_id = len(case.chat_history) + 1
    agent_message = ChatMessage(id=agent_message_id, sender="agent", content=agent_response_text)
    case.chat_history.append(agent_message)
    return agent_message

@app.post("/api/cases/{case_id}/documents", response_model=Document)
async def upload_document(case_id: int, file: UploadFile = File(...)):
    if case_id not in DB:
        raise HTTPException(status_code=404, detail="Case not found")
    
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image (e.g., PNG, JPG) for Vision API processing.")
        
    file_content = await file.read()
    parsing_result = call_gemini_api_for_document_parsing(file_content, file.filename)
    case = DB[case_id]
    new_doc_id = len(case.documents) + 101
    new_document = Document(
        id=new_doc_id,
        name=file.filename,
        summary=parsing_result.get("summary", "No summary provided."),
        extracted_data=parsing_result.get("extracted_data", {})
    )
    case.documents.append(new_document)
    agent_message_id = len(case.chat_history) + 1
    confirmation_message = ChatMessage(
        id=agent_message_id,
        sender="agent",
        content=f"Thank you. I have successfully processed the document: '{file.filename}'. You can now ask me questions about it."
    )
    case.chat_history.append(confirmation_message)
    return new_document

@app.get("/api/test-gemini")
async def test_gemini_connection():
    """An endpoint to explicitly test the connection to the Gemini API."""
    if not GOOGLE_API_KEY:
        raise HTTPException(status_code=500, detail="Gemini API key not found. Please create a .env file and add GOOGLE_API_KEY='your-key'.")
    
    try:
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        response = model.generate_content("Say 'Hello, World!'")
        
        if response.text:
            return {"status": "success", "message": "Gemini API connection is working!", "response": response.text}
        else:
            raise HTTPException(status_code=500, detail="Gemini API returned an empty response.")

    except Exception as e:
        print(f"Gemini test failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to connect to Gemini API. Error: {e}")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
