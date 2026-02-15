from sqlalchemy import Column, Integer, Text, DateTime
from db import Base

class ProjectData(Base):
    __tablename__ = "PROJECT_DATA"

    id = Column(Integer, primary_key=True, index=True)
    ward = Column(Text)
    ward_no = Column(Integer)
    project_name = Column(Text)
    budget = Column(Text)
    deadline = Column(DateTime)
    responsible_person = Column(Text)
    contractor = Column(Text)
    body_text = Column(Text)