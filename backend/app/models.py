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
    # Added after the first release, so they stay nullable at the DB level:
    # rows created before they existed have no value to backfill with. The
    # API still requires them on create/update.
    place_of_birth = Column(String, nullable=True)
    godfather_name = Column(String, nullable=True)
    godmother_name = Column(String, nullable=True)
    baptizing_priest = Column(String, nullable=True)
    place_of_baptism = Column(String, nullable=True)
    date_of_baptism = Column(Date, nullable=True)