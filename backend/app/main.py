from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from app.routers import projects, auth, users, project_members, project_applications, notifications, comments

app = FastAPI()

app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(users.router)
app.include_router(users.public_router)
app.include_router(project_members.router)
app.include_router(project_applications.router)
app.include_router(notifications.router)
app.include_router(comments.router)
