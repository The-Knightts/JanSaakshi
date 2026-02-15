from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from db import get_db
from models import ProjectData

app = FastAPI()


@app.get("/")
def root():
    return {"message": "JanSaakshi running"}


# ==============================
# GET ALL PROJECTS
# ==============================
@app.get("/projects")
def get_all_projects(db: Session = Depends(get_db)):
    projects = db.query(ProjectData).all()
    return projects


# ==============================
# GET PROJECTS BY WARD
# ==============================
@app.get("/ward/{ward_no}")
def get_ward_projects(ward_no: int, db: Session = Depends(get_db)):
    projects = db.query(ProjectData).filter(ProjectData.ward_no == ward_no).all()
    return projects