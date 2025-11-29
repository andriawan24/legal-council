from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class UserInput(BaseModel):
    query: str

@app.post("/deliberate")
async def deliberate(user_input: UserInput):
    # This will eventually interact with Cloud SQL for vector search
    # and Vertex AI for the debate loop.
    return {"message": f"Received query: {user_input.query}. Deliberation not yet implemented."}

@app.get("/")
async def root():
    return {"message": "Legal Council API is running."}
