from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import(
    projects, 
    auth, 
    users, 
    project_members, 
    project_applications, 
    notifications, 
    comments, 
    media_versions,
    music_cues,
    cue_audio_versions,
    player
)


app = FastAPI()

app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(users.router)
app.include_router(users.public_router)
app.include_router(project_members.router)
app.include_router(project_applications.router)
app.include_router(notifications.router)
app.include_router(comments.router)
app.include_router(media_versions.router)
app.include_router(music_cues.router)
app.include_router(cue_audio_versions.router)
app.include_router(player.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)