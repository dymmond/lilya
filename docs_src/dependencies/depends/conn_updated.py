from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

from lilya.dependencies import Depends, inject


engine = create_engine(
    "postgresql+psycopg2://user:password@localhost/dbname",
    pool_recycle=600,
    pool_pre_ping=True,
    echo=False,
    connect_args={
        "keepalives": 1,
        "keepalives_idle": 30,
        "keepalives_interval": 5,
        "keepalives_count": 3,
    },
)

Sessionlocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """
    Get the database session for the current request.
    """
    session = Sessionlocal()
    try:
        yield session
    finally:
        session.close()

@inject
def get_database_session(db = Depends(get_db)):
    """
    Get the database session for non-request contexts.
    """
    return db
