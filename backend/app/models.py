# SQLAlchemy ORM model for the Member table.

from sqlalchemy import Column, Date, Integer, String

from app.database import Base


class Member(Base):
    __tablename__ = "members"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    firstname = Column(String, nullable=False, index=True)
    lastname = Column(String, nullable=False, index=True)
    father_name = Column(String, nullable=False)
    mother_name = Column(String, nullable=False)
    intercessor_name = Column(String, nullable=False)
    date_of_birth = Column(Date, nullable=False)