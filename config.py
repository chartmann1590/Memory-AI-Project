# config.py

import os
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO)

# Load environment variables from the .env file
load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "a_default_secret_key")
    FLASK_ENV = os.getenv("FLASK_ENV", "production")
    SQLALCHEMY_DATABASE_URI = os.getenv("SQLALCHEMY_DATABASE_URI", "sqlite:///site.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = os.getenv("SQLALCHEMY_TRACK_MODIFICATIONS", False)
    
    # Authentik SSO configuration
    AUTHENTIK_SSO_URL = os.getenv("AUTHENTIK_SSO_URL")
    AUTHENTIK_CLIENT_ID = os.getenv("AUTHENTIK_CLIENT_ID")
    AUTHENTIK_CLIENT_SECRET = os.getenv("AUTHENTIK_CLIENT_SECRET")
    AUTHENTIK_REDIRECT_URI = os.getenv("AUTHENTIK_REDIRECT_URI")

    #Ollama API
    OLLAMA_API_URL = os.getenv("OLLAMA_API_URL")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL")