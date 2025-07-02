from fastapi import FastAPI
from pydantic import BaseModel
from openai import OpenAI
from config.openai_config import OPENAI_API_KEY, OPENAI_MODEL
from prompts.system_prompt import FINIVO_SYSTEM_PROMPT

client = OpenAI(api_key=OPENAI_API_KEY)

app = FastAPI()

class ChatRequest(BaseModel):
    message: str

@app.post("/chat")
def chat_endpoint(request: ChatRequest):
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": FINIVO_SYSTEM_PROMPT},
            {"role": "user", "content": request.message}
        ]
    )
    return {"response": response.choices[0].message.content}

def chat_with_finivo(user_message):
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": FINIVO_SYSTEM_PROMPT},
            {"role": "user", "content": user_message}
        ]
    )
    return response.choices[0].message.content
