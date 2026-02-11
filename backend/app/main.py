from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from app.routers import projects, auth

app = FastAPI()

app.include_router(auth.router)
app.include_router(projects.router)