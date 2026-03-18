from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker

# Dane z naszego docker-compose: user, hasło, host (localhost), port, nazwa bazy
SQLALCHEMY_DATABASE_URL = "postgresql://bully_admin:bully_password@localhost:5432/bully_db"

# Inicjalizacja silnika bazy danych
engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()