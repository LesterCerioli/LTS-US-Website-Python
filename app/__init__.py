# app/__init__.py
"""
Medical App User Management Microservice - Python
"""

__version__ = "1.0.0"
__author__ = "Medical App Team"
__description__ = "User management microservice with FastAPI and PostgreSQL"


from app.config import config
from app.database import db, Database

from app import schemas
from app import crud
from app import auth_service  # Importa o módulo auth_service
from app import user_service
from app import organization_service
from app import project_service
from app import image_service
from app import awesomeapi_sync_service
from app import exchange_rate_service
from app import cost_service


from app.auth_service import auth_token_service  # CORRIGIDO: auth_token_service com underscore


__all__ = [
    "config",
    "db",
    "Database",
    "schemas",
    "crud",
    "auth_service",  
    "auth_token_service",  
    "user_service",
    "organization_service",
    "project_service",
    "image_service",
    "awesomeapi_sync_service",
    "exchange_rate_service",
    "cost_service",
]