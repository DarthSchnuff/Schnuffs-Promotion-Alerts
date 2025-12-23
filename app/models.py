from sqlalchemy import Column, Integer, String, Boolean
from app.database import Base


class Streamer(Base):
    __tablename__ = "streamers"

    id = Column(Integer, primary_key=True)
    login = Column(String, unique=True, nullable=False)
    is_live = Column(Boolean, default=False)
