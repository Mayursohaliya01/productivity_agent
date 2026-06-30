"""Check setup and seed demo user."""
import logging
from backend.database import SessionLocal, engine, Base
from backend import models, auth

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create tables
Base.metadata.create_all(bind=engine)
logger.info("Tables created successfully")

db = SessionLocal()
try:
    user = db.query(models.User).filter(models.User.username == 'Mayur').first()
    if user:
        db.delete(user)
        db.commit()
        logger.info("Deleted existing Mayur user")
    
    user = models.User(
        email='mayur@demo.com',
        username='Mayur',
        hashed_password=auth.hash_password('demo123')
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info(f"User Mayur created with id={user.id}")
    
    # Verify login works
    pw_ok = auth.verify_password('demo123', user.hashed_password)
    logger.info(f"Password verification: {pw_ok}")
    
    # Test API call
    import requests
    resp = requests.post(
        'http://localhost:8001/auth/login',
        json={'username': 'Mayur', 'password': 'demo123'},
        timeout=5
    )
    logger.info(f"Login API status: {resp.status_code}")
    if resp.status_code == 200:
        logger.info(f"Login response: {resp.json()}")
    else:
        logger.info(f"Login error: {resp.text}")
except Exception as e:
    logger.error(f"Error: {e}")
finally:
    db.close()