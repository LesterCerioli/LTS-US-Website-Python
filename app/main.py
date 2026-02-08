import asyncio
import base64
from datetime import date, datetime
from decimal import Decimal
import token
from typing import List, Dict, Any, Optional
from urllib import request
from uuid import UUID
import uuid

from fastapi import FastAPI, File, Form, HTTPException, Depends, UploadFile, logger, Header, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
from enum import Enum as PyEnum

from app import cost_service, exchange_rate_service, organization_service, schemas
from app.awesome_api_sync_service import awesomeapi_sync_service
from app.auth_service import auth_token_service

from app.database import db
from app.crud import user_crud




import jwt
import logging

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Lucas Technology Service - Core Microservice",
    description="API from Core microservice",
    version="1.0.1",
    author="Lucas Technology Service"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://lts-us-website.vercel.app"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    db.init_db()
    await awesomeapi_sync_service.start_scheduler()
    logger.info("Exchange rate sync service started")
    
@app.on_event("shutdown")
async def shutdown_event():
    
    await awesomeapi_sync_service.stop_scheduler()
    logger.info("Exchange rate sync service stopped")

async def validate_token_from_body(token: str) -> Dict[str, Any]:
    
    if not token:
        raise HTTPException(status_code=401, detail="Token is required")
    
    if not auth_token_service.validate_token(token):
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    
    try:
        decoded_token = jwt.decode(token, auth_token_service.jwt_secret, algorithms=["HS256"])
        return {
            "client_id": decoded_token.get("client_id"),
            "token": token
        }
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Token validation failed: {str(e)}")

# =============================================================================
# USER MODELS
# =============================================================================

class AuthenticatedUserCreate(BaseModel):
    token: str
    name: str
    email: str
    password: str
    role: str
    organization_name: str


class AuthenticatedPasswordReset(BaseModel):
    token: str
    email: str
    new_password: str

class AuthenticatedUserLogin(BaseModel):
    token: str
    email: str
    password: str
    role: str

class AuthenticatedRequest(BaseModel):
    token: str
    organization_name: str

class AuthenticatedUserUpdate(BaseModel):
    token: str
    name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None

class AuthenticatedPasswordChange(BaseModel):
    token: str
    current_password: str
    new_password: str

class AuthenticatedDeleteRequest(BaseModel):
    token: str
    organization_name: str

class HealthCheckRequest(BaseModel):
    token: str

class RootRequest(BaseModel):
    token: str

# =============================================================================
# ORGANIZATION MODELS
# =============================================================================

class OrganizationStatisticsResponse(BaseModel):
    organization: Dict[str, Any]
    total_logs: int
    success_count: int
    error_count: int
    pending_count: int
    avg_duration_ms: float
    min_duration_ms: float
    max_duration_ms: float
    median_duration_ms: float
    p95_duration_ms: float
    last_log_date: Optional[datetime]
    first_log_date: Optional[datetime]
    unique_services: int
    unique_operations: int
    success_rate: float
    error_rate: float
    availability: float

class OrganizationOverviewResponse(BaseModel):
    organization_id: UUID
    organization_name: str
    total_logs: int
    success_count: int
    error_count: int
    avg_duration_ms: float
    last_activity: datetime
    success_rate: float
    error_rate: float
    health_score: float

class OrganizationServicesResponse(BaseModel):
    service_name: str
    total_requests: int
    success_count: int
    error_count: int
    avg_duration_ms: float
    last_request: datetime
    success_rate: float
    error_rate: float

class OrganizationCreateRequest(BaseModel):
    token: str
    name: str
    address: Optional[str] = None
    cnpj: Optional[str] = None
    ein: Optional[str] = None

class OrganizationUpdateRequest(BaseModel):
    token: str
    name: Optional[str] = None
    address: Optional[str] = None
    cnpj: Optional[str] = None
    ein: Optional[str] = None

class OrganizationFilterRequest(BaseModel):
    token: str
    page: int = Field(1, ge=1)
    size: int = Field(100, ge=1, le=1000)

class OrganizationSearchRequest(BaseModel):
    token: str
    query: str
    page: int = Field(1, ge=1)
    size: int = Field(100, ge=1, le=1000)

class OrganizationValidationRequest(BaseModel):
    token: str
    cnpj: Optional[str] = None
    ein: Optional[str] = None

class OrganizationDeactivateRequest(BaseModel):
    token: str
    reason: Optional[str] = None

class OrganizationResponse(BaseModel):
    id: UUID
    name: str
    address: Optional[str]
    cnpj: Optional[str]
    ein: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class OrganizationDetailResponse(BaseModel):
    id: UUID
    name: str
    address: Optional[str]
    cnpj: Optional[str]
    ein: Optional[str]
    created_at: datetime
    updated_at: datetime
    statistics: Dict[str, Any]

    class Config:
        from_attributes = True

class OrganizationListResponse(BaseModel):
    organizations: List[OrganizationResponse]
    total: int
    page: int
    size: int
    total_pages: int

    class Config:
        from_attributes = True

class OrganizationValidationResponse(BaseModel):
    cnpj: Optional[str] = None
    ein: Optional[str] = None
    is_valid_format: bool
    is_available: bool
    cleaned_cnpj: Optional[str] = None
    cleaned_ein: Optional[str] = None

class OrganizationDeleteRequest(BaseModel):
    
    token: str


# =============================================================================
# PROJECT MODELS
# =============================================================================

class ProjectBase(BaseModel):
    name: str
    code: str
    description: Optional[str] = None
    owner_username: str
    template_agile_method: str = "Scrum"

class ProjectCreateRequest(BaseModel):
    token: str
    organization_name: str
    name: str
    code: str
    description: Optional[str] = None
    owner_username: str
    template_agile_method: str = "Scrum"
    settings: Optional[Dict[str, Any]] = Field(default_factory=dict)

class ProjectUpdateRequest(BaseModel):
    token: str
    name: Optional[str] = None
    description: Optional[str] = None
    owner_username: Optional[str] = None
    template_agile_method: Optional[str] = None
    is_active: Optional[bool] = None
    settings: Optional[Dict[str, Any]] = None

class ProjectResponse(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    code: str
    description: Optional[str]
    owner_id: UUID
    owner_username: Optional[str] = None
    template_agile_method: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None
    settings: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True

class ProjectDetailResponse(ProjectResponse):
    organization_name: Optional[str] = None
    work_item_count: Optional[int] = 0
    member_count: Optional[int] = 0
    last_activity: Optional[datetime] = None

class ProjectListResponse(BaseModel):
    projects: List[ProjectResponse]
    total: int
    page: int
    size: int
    total_pages: int

    class Config:
        from_attributes = True

class ProjectFilterRequest(BaseModel):
    token: str
    organization_name: str
    active_only: bool = True
    page: int = Field(1, ge=1)
    size: int = Field(50, ge=1, le=1000)

class ProjectSearchRequest(BaseModel):
    token: str
    organization_name: str
    query: str
    page: int = Field(1, ge=1)
    size: int = Field(50, ge=1, le=1000)

class ProjectDeleteRequest(BaseModel):
    token: str
    organization_name: str

class ProjectRestoreRequest(BaseModel):
    token: str
    organization_name: str

class ProjectCodeValidationRequest(BaseModel):
    token: str
    organization_name: str
    code: str

class ProjectCodeValidationResponse(BaseModel):
    code: str
    is_valid_format: bool
    is_available: bool
    cleaned_code: str
    suggested_format: Optional[str] = None

class ProjectMemberCreateRequest(BaseModel):
    token: str
    organization_name: str
    username: str
    role: str = "Member"

class ProjectMemberRemoveRequest(BaseModel):
    token: str
    organization_name: str
    username: str

class ProjectMemberUpdateRequest(BaseModel):
    token: str
    organization_name: str
    username: str
    role: str

class ProjectMemberResponse(BaseModel):
    project_id: UUID
    user_id: UUID
    username: str
    email: str
    full_name: Optional[str] = None
    role: str
    joined_at: datetime
    left_at: Optional[datetime] = None

class ProjectMemberListResponse(BaseModel):
    members: List[ProjectMemberResponse]
    total: int
    page: int
    size: int

class ProjectStatsRequest(BaseModel):
    token: str
    organization_name: str

class ProjectStatsResponse(BaseModel):
    project_code: str
    total_work_items: int = 0
    new_items: int = 0
    in_progress_items: int = 0
    completed_items: int = 0
    member_count: int = 0
    first_activity: Optional[datetime] = None
    last_activity: Optional[datetime] = None
    completion_percentage: float = 0.0

class ProjectSettingsUpdateRequest(BaseModel):
    token: str
    organization_name: str
    settings: Dict[str, Any]

class ProjectSettingsResponse(BaseModel):
    project_code: str
    settings: Dict[str, Any]
    updated_at: datetime

# =============================================================================
# WORK ITEM MODELS
# =============================================================================

class WorkItemType(str, PyEnum):
    EPIC = "Epic"
    FEATURE = "Feature"
    USER_STORY = "User Story"
    TASK = "Task"
    BUG = "Bug"
    ISSUE = "Issue"

class WorkItemPriority(str, PyEnum):
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"

class WorkItemStatus(str, PyEnum):
    NEW = "New"
    IN_PROGRESS = "In Progress"
    REVIEW = "Review"
    DONE = "Done"
    CLOSED = "Closed"

class WorkItemCreateRequest(BaseModel):
    token: str
    organization_name: str
    project_code: str
    title: str
    description: Optional[str] = None
    type: WorkItemType
    priority: WorkItemPriority = WorkItemPriority.MEDIUM
    status: WorkItemStatus = WorkItemStatus.NEW
    assigned_to: Optional[str] = None
    story_points: Optional[int] = Field(None, ge=0, le=100)
    due_date: Optional[datetime] = None
    parent_id: Optional[UUID] = None

class WorkItemResponse(BaseModel):
    id: UUID
    project_id: UUID
    organization_id: UUID
    identifier: str
    title: str
    description: Optional[str]
    type: WorkItemType
    priority: WorkItemPriority
    status: WorkItemStatus
    assigned_to: Optional[str]
    story_points: Optional[int]
    due_date: Optional[datetime]
    reporter_id: UUID
    reporter_username: Optional[str] = None
    original_estimate_hours: Optional[float] = None
    remaining_estimate_hours: Optional[float] = None
    completed_hours: Optional[float] = None
    tags: Optional[List[str]] = None
    created_at: datetime
    updated_at: datetime

# =============================================================================
# SPRINT MODELS
# =============================================================================

class SprintCreateRequest(BaseModel):
    token: str
    organization_name: str
    project_code: str
    name: str
    goal: Optional[str] = None
    start_date: datetime
    end_date: datetime
    velocity_target: Optional[int] = None

    @validator('end_date')
    def validate_dates(cls, v, values):
        if 'start_date' in values and v <= values['start_date']:
            raise ValueError('End date must be after start date')
        return v

class SprintResponse(BaseModel):
    id: UUID
    project_id: UUID
    organization_id: UUID
    name: str
    goal: Optional[str]
    start_date: datetime
    end_date: datetime
    velocity_target: Optional[int]
    is_active: bool
    is_completed: bool
    actual_velocity: Optional[int] = None
    created_at: datetime
    updated_at: datetime

# =============================================================================
# PROJECT OPERATION RESPONSE MODELS
# =============================================================================

class ProjectOperationResponse(BaseModel):
    success: bool
    message: str
    project_code: str
    organization: str
    data: Optional[Dict[str, Any]] = None

class MemberOperationResponse(BaseModel):
    success: bool
    message: str
    project_code: str
    username: str
    role: Optional[str] = None
    organization: str
    data: Optional[Dict[str, Any]] = None

class SuccessResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None

class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    details: Optional[str] = None
    code: Optional[str] = None


class ProjectListRequest(BaseModel):
    token: str
    organization_name: Optional[str] = None
    limit: Optional[int] = Field(1000, ge=1, le=10000)
    offset: Optional[int] = Field(0, ge=0)
    include_deleted: Optional[bool] = False

class RawProjectResponse(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    code: str
    description: Optional[str]
    owner_id: UUID
    template_agile_method: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None
    

class RawProjectListResponse(BaseModel):
    success: bool = True
    count: int
    total_count: Optional[int] = None
    projects: List[RawProjectResponse]
    limit: int
    offset: int
    organization_name: Optional[str] = None
    include_deleted: bool
    
    
# =============================================================================
# CREDENTIAL MODELS (Adicione após os modelos de Project)
# =============================================================================

class CredentialCreateRequest(BaseModel):
    token: str
    organization_name: str
    type: str
    email: str
    password: str
    description: Optional[str] = None

class CredentialUpdateRequest(BaseModel):
    token: str
    organization_name: str
    type: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    description: Optional[str] = None

class CredentialResponseModel(BaseModel):
    id: UUID
    organization_id: Optional[UUID] = None
    organization_name: Optional[str] = None
    type: str
    email: str
    password: str
    description: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class CredentialListResponseModel(BaseModel):
    credentials: List[CredentialResponseModel]
    total: int
    page: int
    size: int
    total_pages: int
    organization_name: str

class CredentialSearchRequest(BaseModel):
    token: str
    organization_name: str
    search_term: str
    page: int = Field(1, ge=1)
    size: int = Field(50, ge=1, le=1000)

class EmailValidationRequest(BaseModel):
    token: str
    organization_name: str
    email: str

class EmailValidationResponse(BaseModel):
    email: str
    organization_name: str
    is_available: bool
    exists: bool
    message: str

class CredentialDeleteRequest(BaseModel):
    token: str
    organization_name: str
    credential_id: UUID

class CredentialStatsResponse(BaseModel):
    organization_name: str
    total_credentials: int
    distinct_types: int
    distinct_emails: int
    oldest_credential: Optional[datetime]
    newest_credential: Optional[datetime]
    by_type: Dict[str, int]
    
    
# =============================================================================
# IMAGE MODELS (Novos modelos para imagens)
# =============================================================================

class ImageUploadRequest(BaseModel):
    """Schema for image upload request"""
    token: str
    organization_name: str
    base64_data: str = Field(..., description="Base64 encoded image data")
    mime_type: str = Field(..., description="Image MIME type (image/png, image/jpeg)")
    alt_text: Optional[str] = Field(None, max_length=200, description="Alternative text for the image")

class ImageFileUploadRequest(BaseModel):
    """Schema for image file upload request"""
    token: str
    organization_name: str
    alt_text: Optional[str] = Field(None, max_length=200, description="Alternative text for the image")

class ImageResponse(BaseModel):
    """Response schema for image operations"""
    success: bool
    message: str
    image_info: Optional[Dict[str, Any]] = None
    data_url: Optional[str] = None
    thumbnail: Optional[str] = None
    duplicates_found: Optional[int] = 0

class ImageStatsResponse(BaseModel):
    """Schema for image statistics response"""
    total_posts_with_images: int
    total_posts_without_images: int
    total_storage_bytes: int
    total_storage_mb: float
    image_types_distribution: List[Dict[str, Any]]
    size_statistics: Dict[str, Any]
    recent_images: List[Dict[str, Any]]
    storage_percentage: float

class ImageCleanupResponse(BaseModel):
    """Schema for image cleanup response"""
    success: bool
    cleaned_count: int
    total_space_freed_bytes: int
    total_space_freed_mb: float
    cleaned_posts: List[Dict[str, Any]]

class BulkImageUpdateRequest(BaseModel):
    """Schema for bulk image metadata update"""
    token: str
    organization_name: str
    updates: List[Dict[str, Any]] = Field(..., description="List of image updates")

class BulkImageUpdateResponse(BaseModel):
    """Schema for bulk image update response"""
    success: bool
    updated_count: int
    failed_count: int
    failed_posts: List[Dict[str, Any]]
    total_processed: int

class DuplicateImageResponse(BaseModel):
    """Schema for duplicate image detection response"""
    image_hash: str
    duplicate_count: int
    duplicates: List[Dict[str, Any]]

class ImageValidationResponse(BaseModel):
    """Schema for image validation response"""
    valid: bool
    error: Optional[str] = None
    status_code: Optional[int] = None
    image_info: Optional[Dict[str, Any]] = None
    data_url: Optional[str] = None
    thumbnail: Optional[str] = None
    thumbnail_data_url: Optional[str] = None

class ImageOptimizationResponse(BaseModel):
    """Schema for image optimization response"""
    original_size: int
    optimized_size: int
    reduction_percentage: float
    base64_data: str
    data_url: str

class PostImageUploadResponse(BaseModel):
    """Response for post image upload"""
    success: bool
    message: str
    post_id: UUID
    image_info: Dict[str, Any]
    data_url: str
    duplicates_found: int
    
# =============================================================================
# EXCHANGE RATE MODELS (REVISADOS E COMPLETOS)
# =============================================================================

class ExchangeRateCreateRequest(BaseModel):
    token: str
    organization_id: UUID
    year_month: str
    rate: float
    valid_from: date
    valid_to: date
    base_currency: str = "USD"
    target_currency: str = "BRL"
    source: Optional[str] = None

class ExchangeRateUpdateRequest(BaseModel):
    token: str
    year_month: Optional[str] = None
    rate: Optional[float] = None
    valid_from: Optional[date] = None
    valid_to: Optional[date] = None
    base_currency: Optional[str] = None
    target_currency: Optional[str] = None
    source: Optional[str] = None

# ExchangeRateResponse DEVE vir ANTES de ExchangeRateListResponse
class ExchangeRateResponse(BaseModel):
    id: UUID
    year_month: str
    base_currency: str
    target_currency: str
    rate: float
    source: Optional[str]
    valid_from: date
    valid_to: date
    organization_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Agora podemos definir ExchangeRateListResponse que usa ExchangeRateResponse
class ExchangeRateListResponse(BaseModel):
    exchange_rates: List[ExchangeRateResponse]
    total_count: int
    page: int
    page_size: int
    total_pages: int

class ExchangeRatePeriodRequest(BaseModel):
    token: str
    organization_id: UUID
    year_month: str
    base_currency: str = "USD"
    target_currency: str = "BRL"

class ExchangeRateDateRequest(BaseModel):
    token: str
    organization_id: UUID
    target_date: date
    base_currency: str = "USD"
    target_currency: str = "BRL"

class ExchangeRateBatchCreateRequest(BaseModel):
    token: str
    organization_id: UUID
    rates_data: List[Dict[str, Any]]

class ExchangeRateBatchCreateResponse(BaseModel):
    created_count: int
    failed_count: int
    errors: List[str]

class ExchangeRateSummaryResponse(BaseModel):
    statistics: Dict[str, Any]
    currency_pairs: List[Dict[str, Any]]

# =============================================================================
# COST MODELS (REVISADOS E COMPLETOS)
# =============================================================================

class CostCreateRequest(BaseModel):
    token: str
    organization_id: UUID
    due_date: date
    amount: float
    currency: str
    payment_nature: str
    cost_nature_code: str
    converted_amount_brl: Optional[float] = None
    exchange_rate_month: Optional[str] = None
    exchange_rate_value: Optional[float] = None
    description: Optional[str] = None
    status: str = "pending"

class CostUpdateRequest(BaseModel):
    token: str
    due_date: Optional[date] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    payment_nature: Optional[str] = None
    cost_nature_code: Optional[str] = None
    converted_amount_brl: Optional[float] = None
    exchange_rate_month: Optional[str] = None
    exchange_rate_value: Optional[float] = None
    description: Optional[str] = None
    status: Optional[str] = None

# CostResponse DEVE vir ANTES de CostListResponse
class CostResponse(BaseModel):
    id: UUID
    due_date: date
    amount: float
    currency: str
    payment_nature: str
    cost_nature_code: str
    organization_id: UUID
    converted_amount_brl: Optional[float]
    exchange_rate_month: Optional[str]
    exchange_rate_value: Optional[float]
    description: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Agora podemos definir CostListResponse que usa CostResponse
class CostListResponse(BaseModel):
    costs: List[CostResponse]
    total_count: int
    page: int
    page_size: int
    total_pages: int

class CostSummaryResponse(BaseModel):
    total_costs: int
    total_amount: float
    pending_amount: float
    paid_amount: float
    overdue_amount: float
    pending_count: int
    paid_count: int
    overdue_count: int
    distinct_currencies: int
    distinct_natures: int
    total_converted_brl: float

class CostMonthlySummaryResponse(BaseModel):
    total_costs: int
    total_amount: float
    average_amount: float
    min_amount: float
    max_amount: float
    distinct_currencies: int
    distinct_natures: int
    paid_count: int
    pending_count: int
    overdue_count: int

class CostStatusUpdateRequest(BaseModel):
    token: str
    organization_id: UUID
    status: str

class CostBulkStatusUpdateRequest(BaseModel):
    token: str
    organization_id: UUID
    cost_ids: List[UUID]
    status: str

class CostExchangeRateUpdateRequest(BaseModel):
    token: str
    organization_id: UUID
    converted_amount_brl: float
    exchange_rate_month: str
    exchange_rate_value: float

class CostAutoUpdateExchangeRatesResponse(BaseModel):
    success: bool
    updated_count: int
    failed_count: int
    total_processed: int
    errors: List[str]

class CostFilterRequest(BaseModel):
    token: str
    organization_id: UUID
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[str] = None
    cost_nature_code: Optional[str] = None
    currency: Optional[str] = None
    page: int = 1
    page_size: int = 50

# =============================================================================
# AWESOME API SYNC MODELS (REVISADOS E COMPLETOS)
# =============================================================================

class AwesomeAPISyncRequest(BaseModel):
    token: str
    organization_id: UUID

class AwesomeAPISyncResponse(BaseModel):
    success: bool
    organization_id: Optional[str] = None
    rate: Optional[float] = None
    bid: Optional[float] = None
    ask: Optional[float] = None
    timestamp: Optional[str] = None
    duration_seconds: Optional[float] = None
    source: Optional[str] = None
    error: Optional[str] = None

class AwesomeAPISyncAllResponse(BaseModel):
    success: bool
    synced_count: int
    failed_count: int
    total_organizations: int
    rate: Optional[float] = None
    results: List[Dict[str, Any]]
    timestamp: str
    duration_seconds: float
    error: Optional[str] = None

class AwesomeAPISyncStatusResponse(BaseModel):
    is_running: bool
    sync_hour: int
    sync_minute: int
    next_run: Optional[str] = None
    cache_size: int

class AwesomeAPIManualSyncResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None

# =============================================================================
# AUTHENTICATION ENDPOINTS
# =============================================================================

@app.post("/auth/token", tags=["auth"])
async def generate_auth_token(auth_request: schemas.AuthTokenRequest):
    """
    Generate JWT authentication token
    
    - **client_id**: Client identifier
    - **client_secret**: Client secret
    """
    try:
        if not auth_request.client_id or not auth_request.client_secret:
            raise HTTPException(
                status_code=400,
                detail="Both 'client_id' and 'client_secret' are required"
            )
        result = auth_token_service.generate_token(
            auth_request.client_id,
            auth_request.client_secret
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))

@app.post("/auth/validate", tags=["auth"])
async def validate_auth_token(validate_request: schemas.TokenValidationRequest):
    """
    Validate JWT authentication token
    
    - **token**: JWT token to validate
    """
    is_valid = auth_token_service.validate_token(validate_request.token)
    if not is_valid:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return {"valid": True, "message": "Token is valid"}

@app.get("/auth/token/{client_id}", tags=["auth"])
async def get_valid_token(client_id: str):
    """Get valid token for client_id"""
    token = auth_token_service.get_valid_token(client_id)
    if not token:
        raise HTTPException(status_code=404, detail="No valid token found")
    return {"token": token}

@app.delete("/auth/cleanup", tags=["auth"])
async def cleanup_tokens():
    """Clean up expired tokens (admin endpoint)"""
    deleted_count = auth_token_service.cleanup_expired_tokens()
    return {"message": f"Cleaned up {deleted_count} expired tokens"}

# =============================================================================
# ORGANIZATION ENDPOINTS
# =============================================================================

@app.post("/organizations", response_model=OrganizationResponse, tags=["organizations"])
async def create_organization(request: OrganizationCreateRequest):
    """
    Create a new organization
    
    - **token**: JWT token in request body
    - **name**: Organization name (required)
    - **address**: Organization address (optional)
    - **cnpj**: CNPJ number (optional)
    - **ein**: EIN number (optional)
    """
    try:
        logger.info(f"Starting organization creation for name: {request.name}")
        await validate_token_from_body(request.token)
        logger.info("Token validated successfully")
        
        from app.organization_service import organization_service
        
        organization_dto = organization_service.OrganizationCreateDTO(
            name=request.name,
            address=request.address,
            cnpj=request.cnpj,
            ein=request.ein
        )
        
        logger.info(f"Organization DTO created: name={request.name}, has_cnpj={bool(request.cnpj)}, has_ein={bool(request.ein)}")
        
        result = organization_service.create(organization_dto)
        logger.info(f"Organization created successfully with ID: {result.id}")
        
        return OrganizationResponse(
            id=result.id,
            name=result.name,
            address=result.address,
            cnpj=result.cnpj,
            ein=result.ein,
            created_at=result.created_at,
            updated_at=result.updated_at
        )
    except Exception as e:
        logger.error(f"Error creating organization: {str(e)}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/organizations/name/{name}", response_model=OrganizationListResponse, tags=["organizations"])
async def get_organizations_by_name(
    name: str,
    token: str = Header(..., description="JWT token"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(100, ge=1, le=1000, description="Page size")
):
    """
    Get organizations by name (partial match)
    
    - **name**: Organization name (partial match)
    - **token**: JWT token in Header
    - **page**: Page number (default: 1)
    - **size**: Page size (default: 100, max: 1000)
    """
    try:
        await validate_token_from_body(token)
        from app.organization_service import organization_service
        filter_dto = organization_service.OrganizationFilterDTO(
            page=page,
            page_size=size
        )
        result = organization_service.get_by_name(name, filter_dto)
        
        return OrganizationListResponse(
            organizations=[
                OrganizationResponse(
                    id=org.id,
                    name=org.name,
                    address=org.address,
                    cnpj=org.cnpj,
                    ein=org.ein,
                    created_at=org.created_at,
                    updated_at=org.updated_at
                )
                for org in result.organizations
            ],
            total=result.total_count,  # CORRIGIDO: 'otal' para 'total'
            page=result.page,
            size=result.page_size,
            total_pages=result.total_pages
        )
    except Exception as e:
        logger.error(f"Error fetching organizations by name: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/organizations/cnpj/{cnpj}", response_model=OrganizationResponse, tags=["organizations"])
async def get_organization_by_cnpj(
    cnpj: str,
    token: str = Header(..., description="JWT token")
):
    """
    Get organization by CNPJ
    
    - **cnpj**: CNPJ number
    - **token**: JWT token in Header
    """
    try:
        await validate_token_from_body(token)
        from app.organization_service import organization_service
        result = organization_service.get_by_cnpj(cnpj)
        return OrganizationResponse(
            id=result.id,
            name=result.name,
            address=result.address,
            cnpj=result.cnpj,
            ein=result.ein,
            created_at=result.created_at,
            updated_at=result.updated_at
        )
    except Exception as e:
        logger.error(f"Error fetching organization by CNPJ: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))

@app.get("/organizations/ein/{ein}", response_model=OrganizationResponse, tags=["organizations"])
async def get_organization_by_ein(
    ein: str,
    token: str = Header(..., description="JWT token")
):
    """
    Get organization by EIN
    
    - **ein**: EIN number
    - **token**: JWT token in Header
    """
    try:
        await validate_token_from_body(token)
        from app.organization_service import organization_service
        result = organization_service.get_by_ein(ein)
        
        return OrganizationResponse(
            id=result.id,
            name=result.name,
            address=result.address,
            cnpj=result.cnpj,
            ein=result.ein,
            created_at=result.created_at,
            updated_at=result.updated_at
        )
    except Exception as e:
        logger.error(f"Error fetching organization by EIN: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))

@app.post("/organizations/search", response_model=OrganizationListResponse, tags=["organizations"])
async def search_organizations(request: OrganizationSearchRequest):
    """
    Search organizations by multiple criteria
    
    - **token**: JWT token in request body
    - **query**: Search query (searches in name, address, CNPJ, EIN)
    - **page**: Page number (default: 1)
    - **size**: Page size (default: 100, max: 1000)
    """
    try:
        await validate_token_from_body(request.token)
        from app.organization_service import organization_service
        filter_dto = organization_service.OrganizationFilterDTO(
            page=request.page,
            page_size=request.size
        )
        
        result = organization_service.search_organizations(request.query, filter_dto)
        
        return OrganizationListResponse(
            organizations=[
                OrganizationResponse(
                    id=org.id,
                    name=org.name,
                    address=org.address,
                    cnpj=org.cnpj,
                    ein=org.ein,
                    created_at=org.created_at,
                    updated_at=org.updated_at
                )
                for org in result.organizations
            ],
            total=result.total_count,
            page=result.page,
            size=result.page_size,
            total_pages=result.total_pages
        )
    except Exception as e:
        logger.error(f"Error searching organizations: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/organizations/validate", response_model=OrganizationValidationResponse, tags=["organizations"])
async def validate_organization_data(request: OrganizationValidationRequest):
    """
    Validate CNPJ or EIN format and availability
    
    - **token**: JWT token in request body
    - **cnpj**: CNPJ number to validate (optional)
    - **ein**: EIN number to validate (optional)
    """
    try:
        await validate_token_from_body(request.token)
        from app.organization_service import organization_service
        
        if request.cnpj and request.ein:
            raise HTTPException(status_code=400, detail="Provide either CNPJ or EIN, not both")
        
        if request.cnpj:
            result = organization_service.validate_cnpj(request.cnpj)
            return OrganizationValidationResponse(
                cnpj=result["cnpj"],
                is_valid_format=result["is_valid_format"],
                is_available=result["is_available"],
                cleaned_cnpj=result["cleaned_cnpj"]
            )
        elif request.ein:
            result = organization_service.validate_ein(request.ein)
            return OrganizationValidationResponse(
                ein=result["ein"],
                is_valid_format=result["is_valid_format"],
                is_available=result["is_available"],
                cleaned_ein=result["cleaned_ein"]
            )
        else:
            raise HTTPException(status_code=400, detail="Either CNPJ or EIN must be provided")
    except Exception as e:
        logger.error(f"Error validating organization data: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/organizations", response_model=OrganizationListResponse, tags=["organizations"])
async def get_all_organizations(
    token: str = Header(..., description="JWT token"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(100, ge=1, le=1000, description="Page size")
):
    """
    Get all organizations with pagination
    
    - **token**: JWT token in Header
    - **page**: Page number (default: 1)
    - **size**: Page size (default: 100, max: 1000)
    """
    try:
        await validate_token_from_body(token)
        from app.organization_service import organization_service
        filter_dto = organization_service.OrganizationFilterDTO(
            page=page,
            page_size=size
        )
        result = organization_service.get_all_organizations(filter_dto)
        
        return OrganizationListResponse(
            organizations=[
                OrganizationResponse(
                    id=org.id,
                    name=org.name,
                    address=org.address,
                    cnpj=org.cnpj,
                    ein=org.ein,
                    created_at=org.created_at,
                    updated_at=org.updated_at
                )
                for org in result.organizations
            ],
            total=result.total_count,
            page=result.page,
            size=result.page_size,
            total_pages=result.total_pages
        )
    except Exception as e:
        logger.error(f"Error fetching all organizations: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

# =============================================================================
# USER ENDPOINTS
# =============================================================================

@app.post("/users/register", response_model=schemas.UserResponse, tags=["users"])
async def register_user(user: AuthenticatedUserCreate):
    """
    Register a new user (Requires authentication token in body)
    
    - **token**: JWT token in request body
    - **name**: User's full name
    - **email**: User's email (must be unique per organization)
    - **password**: User's password
    - **role**: User's role (admin, user, etc.)
    - **organization_name**: Organization name
    """
    
    token_data = await validate_token_from_body(user.token)
    print(f"Register user request from client: {token_data['client_id']}")
    
    
    user_data = user.dict()
    user_data.pop('token')
    
    result = user_crud.create_user(
        name=user_data['name'],
        email=user_data['email'],
        password=user_data['password'],
        role=user_data['role'],
        organization_name=user_data['organization_name']
    )
    
    if not result:
        raise HTTPException(
            status_code=400,
            detail="Failed to create user. Organization may not exist or email already registered."
        )
    
    return result

@app.post("/users/login", response_model=schemas.UserResponse, tags=["users"])
async def login_user(login: AuthenticatedUserLogin):
    """
    Authenticate user (Requires authentication token in body)
    
    - **token**: JWT token in request body
    - **email**: User's email
    - **password**: User's password
    - **role**: User's role
    """
    
    token_data = await validate_token_from_body(login.token)
    print(f"Login attempt from client: {token_data['client_id']}")
    
    
    login_data = login.dict()
    login_data.pop('token')
    
    result = user_crud.authenticate_user(
        email=login_data['email'],
        password=login_data['password'],
        role=login_data['role']
    )
    
    if not result:
        raise HTTPException(status_code=401, detail="Invalid credentials or organization")
    
    return result

@app.post("/users/{user_id}", response_model=schemas.UserResponse, tags=["users"])
async def get_user(user_id: str, request: AuthenticatedRequest):
    """
    Get user by ID (Requires authentication token in body)
    
    - **token**: JWT token in request body
    - **user_id**: User UUID
    - **organization_name**: Organization name for validation
    """
    
    token_data = await validate_token_from_body(request.token)
    
    result = user_crud.get_user_by_id(user_id, request.organization_name)
    
    if not result:
        raise HTTPException(
            status_code=404,
            detail="User not found or doesn't belong to this organization"
        )
    
    return result

@app.post("/users", response_model=List[schemas.UserResponse], tags=["users"])
async def get_organization_users(request: AuthenticatedRequest):
    """
    Get all users in an organization (Requires authentication token in body)
    
    - **token**: JWT token in request body
    - **organization_name**: Organization name
    """
    
    token_data = await validate_token_from_body(request.token)
    
    result = user_crud.get_organization_users(request.organization_name)
    
    if result is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    return result

@app.put("/users/{user_id}", response_model=schemas.UserResponse, tags=["users"])
async def update_user(user_id: str, request: AuthenticatedUserUpdate, organization_name: str):
    """
    Update user information (Requires authentication token in body)
    
    - **token**: JWT token in request body
    - **user_id**: User UUID
    - **organization_name**: Organization name for validation
    """
    
    token_data = await validate_token_from_body(request.token)
    
    
    update_data = request.dict(exclude_unset=True)
    update_data.pop('token')
    
    result = user_crud.update_user(
        user_id,
        update_data,
        organization_name
    )
    
    if not result:
        raise HTTPException(status_code=404, detail="User not found or update failed")
    
    return result

@app.post("/users/{user_id}/change-password", tags=["users"])
async def change_password(user_id: str, request: AuthenticatedPasswordChange, organization_name: str):
    """
    Change user password (Requires authentication token in body)
    
    - **token**: JWT token in request body
    - **user_id**: User UUID
    - **current_password**: Current password
    - **new_password**: New password
    - **organization_name**: Organization name for validation
    """
    
    token_data = await validate_token_from_body(request.token)
    
    
    password_data = request.dict()
    password_data.pop('token')
    
    success = user_crud.change_user_password(
        user_id=user_id,
        current_password=password_data['current_password'],
        new_password=password_data['new_password'],
        organization_name=organization_name
    )
    
    if not success:
        raise HTTPException(
            status_code=400,
            detail="Password change failed. Invalid current password or user not found."
        )
    
    return {"message": "Password changed successfully"}

@app.delete("/users/{user_id}", tags=["users"])
async def delete_user(user_id: str, request: AuthenticatedDeleteRequest):
    """
    Delete a user (soft delete) (Requires authentication token in body)
    
    - **token**: JWT token in request body
    - **user_id**: User UUID
    - **organization_name**: Organization name for validation
    """
    
    token_data = await validate_token_from_body(request.token)
    
    success = user_crud.delete_user(user_id, request.organization_name)
    
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"message": "User deleted successfully"}


@app.post("/users/reset-password", tags=["users"])
async def reset_password(request: AuthenticatedPasswordReset):
    """
    Reset user password by email (Requires authentication token in body)
    
    - **token**: JWT token in request body
    - **email**: User's email
    - **new_password**: New password
    - **organization_name**: Organization name
    """
    
    token_data = await validate_token_from_body(request.token)
    
    
    from app.user_service import user_service
    
    
    success = user_service.reset_password_by_email(
        email=request.email,
        new_password=request.new_password
    )

    if not success:
        raise HTTPException(
            status_code=404, 
            detail="User not found or password reset failed"
        )

    return {"message": f"Password for {request.email} has been reset successfully."}


# =============================================================================
# PROJECT ENDPOINTS
# =============================================================================

@app.post("/projects", response_model=ProjectResponse, tags=["projects"])
async def create_project(request: ProjectCreateRequest):
    """
    Create a new project
    
    - **token**: JWT token in request body
    - **organization_name**: Organization name
    - **name**: Project name
    - **code**: Project code (must be unique per organization)
    - **description**: Project description
    - **owner_username**: Username of project owner
    - **template_agile_method**: Agile methodology (default: Scrum)
    - **settings**: Project settings dictionary
    """
    try:
        
        token_data = await validate_token_from_body(request.token)
        print(f"Creating project for client: {token_data['client_id']}")
                
        from app.project_service import project_service
                
        result = project_service.create_project(
            name=request.name,
            code=request.code,
            description=request.description,
            owner_username=request.owner_username,
            template_agile_method=request.template_agile_method,
            settings=request.settings,
            organization_name=request.organization_name
        )
        
        if not result:
            raise HTTPException(
                status_code=400,
                detail="Failed to create project. Organization may not exist, user not found, or project code already in use."
            )
        
        return result
        
    except ValueError as e:
        print(f"Validation error creating project: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"Error creating project: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/projects/{project_code}", response_model=ProjectDetailResponse, tags=["projects"])
async def get_project_by_code(
    project_code: str,
    organization_name: str,
    token: str = Header(..., description="JWT token")
):
    """
    Get project by code
    
    - **project_code**: Project code
    - **organization_name**: Organization name
    - **token**: JWT token in Header
    """
    try:
        # Validate token
        await validate_token_from_body(token)
        
        # Import project service
        from app.project_service import project_service
        
        # Get project using service method
        result = project_service.get_project_by_code(
            project_code=project_code,
            organization_name=organization_name
        )
        
        if not result:
            raise HTTPException(
                status_code=404,
                detail="Project not found"
            )
        
        return result
        
    except Exception as e:
        print(f"Error fetching project: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/projects", response_model=ProjectListResponse, tags=["projects"])
async def get_organization_projects(
    organization_name: str,
    token: str = Header(..., description="JWT token"),
    active_only: bool = Query(True, description="Show only active projects"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(50, ge=1, le=1000, description="Page size")
):
    """
    Get all projects in an organization
    
    - **organization_name**: Organization name
    - **token**: JWT token in Header
    - **active_only**: Show only active projects (default: True)
    - **page**: Page number (default: 1)
    - **size**: Page size (default: 50, max: 1000)
    """
    try:
        
        await validate_token_from_body(token)
                
        from app.project_service import project_service
                
        result = project_service.get_organization_projects(
            organization_name=organization_name,
            active_only=active_only,
            page=page,
            page_size=size
        )
        
        return ProjectListResponse(
            projects=result['projects'],
            total=result['total'],
            page=page,
            size=size,
            total_pages=result['total_pages']
        )
        
    except Exception as e:
        print(f"Error fetching organization projects: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.put("/projects/{project_code}", response_model=ProjectResponse, tags=["projects"])
async def update_project(
    project_code: str,
    request: ProjectUpdateRequest,
    organization_name: str = Query(..., description="Organization name")
):
    """
    Update project information
    
    - **project_code**: Project code
    - **organization_name**: Organization name (query parameter)
    - **token**: JWT token in request body
    - **name**: New project name (optional)
    - **description**: New description (optional)
    - **owner_username**: New owner username (optional)
    - **template_agile_method**: New agile method (optional)
    - **is_active**: Active status (optional)
    - **settings**: New settings (optional)
    """
    try:
        
        token_data = await validate_token_from_body(request.token)
        print(f"Updating project for client: {token_data['client_id']}")
                
        from app.project_service import project_service
                
        update_data = {}
        if request.name is not None:
            update_data['name'] = request.name
        if request.description is not None:
            update_data['description'] = request.description
        if request.owner_username is not None:
            update_data['owner_username'] = request.owner_username
        if request.template_agile_method is not None:
            update_data['template_agile_method'] = request.template_agile_method
        if request.is_active is not None:
            update_data['is_active'] = request.is_active
        if request.settings is not None:
            update_data['settings'] = request.settings
        
        
        result = project_service.update_project(
            project_code=project_code,
            organization_name=organization_name,
            update_data=update_data
        )
        
        if not result:
            raise HTTPException(
                status_code=404,
                detail="Project not found or update failed"
            )
        
        return result
        
    except ValueError as e:
        print(f"Validation error updating project: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error updating project: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.delete("/projects/{project_code}", response_model=ProjectOperationResponse, tags=["projects"])
async def delete_project(
    project_code: str,
    request: ProjectDeleteRequest
):
    """
    Soft delete a project
    
    - **project_code**: Project code
    - **token**: JWT token in request body
    - **organization_name**: Organization name
    """
    try:
        
        token_data = await validate_token_from_body(request.token)
        print(f"Deleting project for client: {token_data['client_id']}")
        
        
        from app.project_service import project_service
                
        success = project_service.delete_project(
            project_code=project_code,
            organization_name=request.organization_name
        )
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail="Project not found"
            )
        
        return ProjectOperationResponse(
            success=True,
            message="Project deleted successfully",
            project_code=project_code,
            organization=request.organization_name
        )
        
    except Exception as e:
        print(f"Error deleting project: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/projects/{project_code}/restore", response_model=ProjectOperationResponse, tags=["projects"])
async def restore_project(
    project_code: str,
    request: ProjectRestoreRequest
):
    """
    Restore a soft-deleted project
    
    - **project_code**: Project code
    - **token**: JWT token in request body
    - **organization_name**: Organization name
    """
    try:
        
        token_data = await validate_token_from_body(request.token)
        print(f"Restoring project for client: {token_data['client_id']}")
                
        from app.project_service import project_service
                
        success = project_service.restore_project(
            project_code=project_code,
            organization_name=request.organization_name
        )
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail="Project not found or already active"
            )
        
        return ProjectOperationResponse(
            success=True,
            message="Project restored successfully",
            project_code=project_code,
            organization=request.organization_name
        )
        
    except Exception as e:
        print(f"Error restoring project: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/projects/validate-code", response_model=ProjectCodeValidationResponse, tags=["projects"])
async def validate_project_code(request: ProjectCodeValidationRequest):
    """
    Validate project code format and availability
    
    - **token**: JWT token in request body
    - **organization_name**: Organization name
    - **code**: Project code to validate
    """
    try:
        
        await validate_token_from_body(request.token)
                
        from app.project_service import project_service
                
        result = project_service.validate_project_code(
            code=request.code,
            organization_name=request.organization_name
        )
        
        return ProjectCodeValidationResponse(**result)
        
    except Exception as e:
        print(f"Error validating project code: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/projects/search", response_model=ProjectListResponse, tags=["projects"])
async def search_projects(request: ProjectSearchRequest):
    """
    Search projects in an organization
    
    - **token**: JWT token in request body
    - **organization_name**: Organization name
    - **query**: Search query
    - **page**: Page number (default: 1)
    - **size**: Page size (default: 50, max: 1000)
    """
    try:
        
        await validate_token_from_body(request.token)
                
        from app.project_service import project_service
                
        result = project_service.search_projects(
            organization_name=request.organization_name,
            query=request.query,
            page=request.page,
            page_size=request.size
        )
        
        return ProjectListResponse(
            projects=result['projects'],
            total=result['total'],
            page=request.page,
            size=request.size,
            total_pages=result['total_pages']
        )
        
    except Exception as e:
        print(f"Error searching projects: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/projects/{project_code}/stats", response_model=ProjectStatsResponse, tags=["projects"])
async def get_project_statistics(
    project_code: str,
    organization_name: str,
    token: str = Header(..., description="JWT token")
):
    """
    Get project statistics
    
    - **project_code**: Project code
    - **organization_name**: Organization name
    - **token**: JWT token in Header
    """
    try:
        
        await validate_token_from_body(token)
                
        from app.project_service import project_service
                
        stats = project_service.get_project_statistics(
            project_code=project_code,
            organization_name=organization_name
        )
        
        return ProjectStatsResponse(**stats)
        
    except Exception as e:
        print(f"Error fetching project statistics: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# =============================================================================
# PROJECT MEMBERS ENDPOINTS
# =============================================================================

@app.post("/projects/{project_code}/members", response_model=ProjectMemberResponse, tags=["project-members"])
async def add_project_member(
    project_code: str,
    request: ProjectMemberCreateRequest
):
    """
    Add member to project
    
    - **project_code**: Project code
    - **token**: JWT token in request body
    - **organization_name**: Organization name
    - **username**: Username to add
    - **role**: Member role (Owner, Admin, Member, Viewer)
    """
    try:
        
        token_data = await validate_token_from_body(request.token)
        print(f"Adding project member for client: {token_data['client_id']}")
        
        
        from app.project_service import project_service
                
        result = project_service.add_project_member(
            project_code=project_code,
            organization_name=request.organization_name,
            username=request.username,
            role=request.role
        )
        
        if not result:
            raise HTTPException(
                status_code=400,
                detail="Failed to add member. User may not exist or already a member."
            )
        
        return result
        
    except ValueError as e:
        print(f"Validation error adding project member: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error adding project member: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/projects/{project_code}/members", response_model=ProjectMemberListResponse, tags=["project-members"])
async def get_project_members(
    project_code: str,
    organization_name: str,
    token: str = Header(..., description="JWT token"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(50, ge=1, le=1000, description="Page size")
):
    """
    Get all project members
    
    - **project_code**: Project code
    - **organization_name**: Organization name
    - **token**: JWT token in Header
    - **page**: Page number (default: 1)
    - **size**: Page size (default: 50, max: 1000)
    """
    try:
        
        await validate_token_from_body(token)
                
        from app.project_service import project_service
                
        result = project_service.get_project_members(
            project_code=project_code,
            organization_name=organization_name,
            page=page,
            page_size=size
        )
        
        return ProjectMemberListResponse(
            members=result['members'],
            total=result['total'],
            page=page,
            size=size
        )
        
    except Exception as e:
        print(f"Error fetching project members: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.put("/projects/{project_code}/members/{username}", response_model=ProjectMemberResponse, tags=["project-members"])
async def update_project_member_role(
    project_code: str,
    username: str,
    request: ProjectMemberUpdateRequest
):
    """
    Update project member role
    
    - **project_code**: Project code
    - **username**: Username to update
    - **token**: JWT token in request body
    - **organization_name**: Organization name
    - **role**: New role
    """
    try:
        
        token_data = await validate_token_from_body(request.token)
        print(f"Updating project member role for client: {token_data['client_id']}")
                
        from app.project_service import project_service
                
        result = project_service.update_project_member_role(
            project_code=project_code,
            organization_name=request.organization_name,
            username=username,
            role=request.role
        )
        
        if not result:
            raise HTTPException(
                status_code=404,
                detail="Member not found or update failed"
            )
        
        return result
        
    except ValueError as e:
        print(f"Validation error updating project member: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error updating project member: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.delete("/projects/{project_code}/members/{username}", response_model=MemberOperationResponse, tags=["project-members"])
async def remove_project_member(
    project_code: str,
    username: str,
    request: ProjectMemberRemoveRequest
):
    """
    Remove member from project
    
    - **project_code**: Project code
    - **username**: Username to remove
    - **token**: JWT token in request body
    - **organization_name**: Organization name
    """
    try:
        
        token_data = await validate_token_from_body(request.token)
        print(f"Removing project member for client: {token_data['client_id']}")
        
        
        from app.project_service import project_service
        
        
        success = project_service.remove_project_member(
            project_code=project_code,
            organization_name=request.organization_name,
            username=username
        )
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail="Member not found"
            )
        
        return MemberOperationResponse(
            success=True,
            message="Member removed successfully",
            project_code=project_code,
            username=username,
            organization=request.organization_name
        )
        
    except Exception as e:
        print(f"Error removing project member: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.put("/projects/{project_code}/settings", response_model=ProjectSettingsResponse, tags=["projects"])
async def update_project_settings(
    project_code: str,
    request: ProjectSettingsUpdateRequest
):
    """
    Update project settings
    
    - **project_code**: Project code
    - **token**: JWT token in request body
    - **organization_name**: Organization name
    - **settings**: New settings dictionary
    """
    try:
        # Validate token
        token_data = await validate_token_from_body(request.token)
        print(f"Updating project settings for client: {token_data['client_id']}")
        
        # Import project service
        from app.project_service import project_service
        
        # Update settings using service method
        result = project_service.update_project_settings(
            project_code=project_code,
            organization_name=request.organization_name,
            settings=request.settings
        )
        
        if not result:
            raise HTTPException(
                status_code=404,
                detail="Project not found or update failed"
            )
        
        return result
        
    except Exception as e:
        print(f"Error updating project settings: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# =============================================================================
# WORK ITEM ENDPOINTS
# =============================================================================

@app.post("/projects/{project_code}/work-items", response_model=WorkItemResponse, tags=["work-items"])
async def create_work_item(
    project_code: str,
    request: WorkItemCreateRequest
):
    """
    Create a new work item
    
    - **project_code**: Project code
    - **token**: JWT token in request body
    - **organization_name**: Organization name
    - **title**: Work item title
    - **description**: Work item description
    - **type**: Work item type (Epic, Feature, User Story, Task, Bug, Issue)
    - **priority**: Priority (Critical, High, Medium, Low)
    - **status**: Status (New, In Progress, Review, Done, Closed)
    - **assigned_to**: Username of assignee
    - **story_points**: Story points estimate
    - **due_date**: Due date
    - **parent_id**: Parent work item ID (optional)
    """
    try:
        
        token_data = await validate_token_from_body(request.token)
        print(f"Creating work item for client: {token_data['client_id']}")
        
        
        from app.project_service import project_service
        
        
        result = project_service.create_work_item(
            project_code=project_code,
            organization_name=request.organization_name,
            title=request.title,
            description=request.description,
            type=request.type,
            priority=request.priority,
            status=request.status,
            assigned_to=request.assigned_to,
            story_points=request.story_points,
            due_date=request.due_date,
            parent_id=request.parent_id
        )
        
        if not result:
            raise HTTPException(
                status_code=400,
                detail="Failed to create work item. Project may not exist or user not found."
            )
        
        return result
        
    except ValueError as e:
        print(f"Validation error creating work item: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"Error creating work item: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/projects/{project_code}/work-items/{work_item_id}", response_model=WorkItemResponse, tags=["work-items"])
async def get_work_item(
    project_code: str,
    work_item_id: UUID,
    organization_name: str,
    token: str = Header(..., description="JWT token")
):
    """
    Get work item by ID
    
    - **project_code**: Project code
    - **work_item_id**: Work item UUID
    - **organization_name**: Organization name
    - **token**: JWT token in Header
    """
    try:
        # Validate token
        await validate_token_from_body(token)
        
        # Import project service
        from app.project_service import project_service
        
        # Get work item using service method
        result = project_service.get_work_item(
            project_code=project_code,
            work_item_id=work_item_id,
            organization_name=organization_name
        )
        
        if not result:
            raise HTTPException(
                status_code=404,
                detail="Work item not found"
            )
        
        return result
        
    except Exception as e:
        print(f"Error fetching work item: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# =============================================================================
# SPRINT ENDPOINTS
# =============================================================================

@app.post("/projects/{project_code}/sprints", response_model=SprintResponse, tags=["sprints"])
async def create_sprint(
    project_code: str,
    request: SprintCreateRequest
):
    """
    Create a new sprint
    
    - **project_code**: Project code
    - **token**: JWT token in request body
    - **organization_name**: Organization name
    - **name**: Sprint name
    - **goal**: Sprint goal
    - **start_date**: Sprint start date
    - **end_date**: Sprint end date
    - **velocity_target**: Velocity target (optional)
    """
    try:
        # Validate token
        token_data = await validate_token_from_body(request.token)
        print(f"Creating sprint for client: {token_data['client_id']}")
        
        # Import project service
        from app.project_service import project_service
        
        # Create sprint using service method
        result = project_service.create_sprint(
            project_code=project_code,
            organization_name=request.organization_name,
            name=request.name,
            goal=request.goal,
            start_date=request.start_date,
            end_date=request.end_date,
            velocity_target=request.velocity_target
        )
        
        if not result:
            raise HTTPException(
                status_code=400,
                detail="Failed to create sprint. Project may not exist."
            )
        
        return result
        
    except ValueError as e:
        print(f"Validation error creating sprint: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"Error creating sprint: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/projects-raw", response_model=RawProjectListResponse, tags=["projects"])
async def get_raw_projects_list(
    token: str = Header(..., description="JWT token"),
    organization_name: Optional[str] = Query(None, description="Filter by organization name"),
    limit: int = Query(1000, ge=1, le=10000, description="Maximum number of projects"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    include_deleted: bool = Query(False, description="Include deleted projects")
):
    """
    GET raw projects list (admin/debug endpoint)
    """
    try:
        
        await validate_token_from_body(token)
        
        
        from app.project_service import project_service
        
        
        raw_projects = project_service.get_raw_projects(
            organization_name=organization_name,
            limit=limit,
            offset=offset
        )
        
        
        if not include_deleted:
            raw_projects = [p for p in raw_projects if p.get('deleted_at') is None]
        
        
        project_responses = []
        for project in raw_projects:
            try:
                project_responses.append(RawProjectResponse(
                    id=project.get('id'),
                    organization_id=project.get('organization_id'),
                    name=project.get('name'),
                    code=project.get('code'),
                    description=project.get('description'),
                    owner_id=project.get('owner_id'),
                    template_agile_method=project.get('template_agile_method'),
                    is_active=project.get('is_active', False),
                    created_at=project.get('created_at'),
                    updated_at=project.get('updated_at'),
                    deleted_at=project.get('deleted_at')
                    # NÃO INCLUIR settings porque o método não retorna
                ))
            except Exception:
                continue
        
        
        return RawProjectListResponse(
            count=len(project_responses),
            total_count=None,
            projects=project_responses,
            limit=limit,
            offset=offset,
            organization_name=organization_name,
            include_deleted=include_deleted
        )
        
    except Exception as e:
        print(f"Error getting raw projects list: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# CREDENTIAL ENDPOINTS (Adicione após os endpoints de Projects)
# =============================================================================

@app.post("/credentials", response_model=CredentialResponseModel, tags=["credentials"])
async def create_credential(request: CredentialCreateRequest):
    """
    Create a new credential
    
    - **token**: JWT token in request body
    - **organization_name**: Organization name
    - **type**: Credential type ('Identifier' or 'Other')
    - **email**: Email/login for the credential
    - **password**: Password
    - **description**: Optional description
    """
    try:
        
        token_data = await validate_token_from_body(request.token)
        print(f"Creating credential for client: {token_data['client_id']}")
        
        
        from app.credential_service import credential_service
        
        
        if request.type not in ['Identifier', 'Other']:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid credential type: {request.type}. Must be 'Identifier' or 'Other'"
            )
        
        # Create credential using service method
        result = credential_service.create_credential(
            organization_name=request.organization_name,
            type=request.type,
            email=request.email,
            password=request.password,
            description=request.description
        )
        
        if not result:
            raise HTTPException(
                status_code=400,
                detail="Failed to create credential. Organization may not exist, invalid data, or duplicate email."
            )
        
        return CredentialResponseModel(**result)
        
    except ValueError as e:
        print(f"Validation error creating credential: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error creating credential: {str(e)}")
        import traceback
        traceback.print_exc()  # Adicione esta linha para debug
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/credentials", response_model=CredentialListResponseModel, tags=["credentials"])
async def get_all_credentials(
    organization_name: str = Query(..., description="Organization name"),
    token: str = Header(..., description="JWT token"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(50, ge=1, le=1000, description="Page size")
):
    """
    Get all credentials for an organization with pagination
    
    - **organization_name**: Organization name (query parameter)
    - **token**: JWT token in Header
    - **page**: Page number (default: 1)
    - **size**: Page size (default: 50, max: 1000)
    """
    try:
        
        await validate_token_from_body(token)
                
        from app.credential_service import credential_service
                
        offset = (page - 1) * size
                
        credentials = credential_service.get_all_credentials(
            organization_name=organization_name,
            limit=size, 
            offset=offset
        )
                
        all_credentials = credential_service.get_all_credentials(
            organization_name=organization_name,
            limit=10000, 
            offset=0
        )
        total = len(all_credentials)
        
        return CredentialListResponseModel(
            credentials=[
                CredentialResponseModel(**cred) for cred in credentials
            ],
            total=total,
            page=page,
            size=size,
            total_pages=(total + size - 1) // size if size > 0 else 0,
            organization_name=organization_name
        )
        
    except Exception as e:
        print(f"Error fetching credentials: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/credentials/{credential_id}", response_model=CredentialResponseModel, tags=["credentials"])
async def get_credential_by_id(
    credential_id: UUID,
    organization_name: str = Query(..., description="Organization name"),
    token: str = Header(..., description="JWT token")
):
    """
    Get credential by ID with organization validation
    
    - **credential_id**: Credential UUID
    - **organization_name**: Organization name (query parameter)
    - **token**: JWT token in Header
    """
    try:
        
        await validate_token_from_body(token)
                
        from app.credential_service import credential_service
                
        result = credential_service.get_credential_by_id(
            credential_id=str(credential_id),
            organization_name=organization_name
        )
        
        if not result:
            raise HTTPException(
                status_code=404,
                detail="Credential not found or doesn't belong to this organization"
            )
        
        return CredentialResponseModel(**result)
        
    except Exception as e:
        print(f"Error fetching credential: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.put("/credentials/{credential_id}", response_model=CredentialResponseModel, tags=["credentials"])
async def update_credential(
    credential_id: UUID,
    request: CredentialUpdateRequest
):
    """
    Update credential information
    
    - **credential_id**: Credential UUID
    - **token**: JWT token in request body
    - **organization_name**: Organization name
    - **type**: New credential type (optional)
    - **email**: New email (optional)
    - **password**: New password (optional)
    - **description**: New description (optional)
    """
    try:
        
        token_data = await validate_token_from_body(request.token)
        print(f"Updating credential for client: {token_data['client_id']}")
                
        from app.credential_service import credential_service
                
        update_data = {}
        if request.type is not None:
            update_data['type'] = request.type
        if request.email is not None:
            update_data['email'] = request.email
        if request.password is not None:
            update_data['password'] = request.password
        if request.description is not None:
            update_data['description'] = request.description
                
        result = credential_service.update_credential(
            credential_id=str(credential_id),
            organization_name=request.organization_name,
            updates=update_data
        )
        
        if not result:
            raise HTTPException(
                status_code=404,
                detail="Credential not found or doesn't belong to this organization"
            )
        
        return CredentialResponseModel(**result)
        
    except ValueError as e:
        print(f"Validation error updating credential: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"Error updating credential: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.delete("/credentials/{credential_id}", response_model=SuccessResponse, tags=["credentials"])
async def delete_credential(
    credential_id: UUID,
    request: CredentialDeleteRequest
):
    """
    Delete a credential
    
    - **credential_id**: Credential UUID
    - **token**: JWT token in request body
    - **organization_name**: Organization name
    """
    try:
        
        token_data = await validate_token_from_body(request.token)
        print(f"Deleting credential for client: {token_data['client_id']}")
                
        from app.credential_service import credential_service
                
        success = credential_service.delete_credential(
            credential_id=str(credential_id),
            organization_name=request.organization_name
        )
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail="Credential not found or doesn't belong to this organization"
            )
        
        return SuccessResponse(
            success=True,
            message="Credential deleted successfully",
            data={
                "credential_id": str(credential_id),
                "organization_name": request.organization_name
            }
        )
        
    except Exception as e:
        print(f"Error deleting credential: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/credentials/search", response_model=CredentialListResponseModel, tags=["credentials"])
async def search_credentials(request: CredentialSearchRequest):
    """
    Search credentials by email or description within an organization
    
    - **token**: JWT token in request body
    - **organization_name**: Organization name
    - **search_term**: Search term
    - **page**: Page number (default: 1)
    - **size**: Page size (default: 50, max: 1000)
    """
    try:
        
        await validate_token_from_body(request.token)
                
        from app.credential_service import credential_service
                
        offset = (request.page - 1) * request.size
                
        result = credential_service.search_credentials(
            organization_name=request.organization_name,
            search_term=request.search_term,
            limit=request.size,
            offset=offset
        )
        
        if 'error' in result:
            raise HTTPException(status_code=400, detail=result['error'])
        
        return CredentialListResponseModel(
            credentials=[
                CredentialResponseModel(**cred) for cred in result['results']
            ],
            total=result['total_count'],
            page=request.page,
            size=request.size,
            total_pages=(result['total_count'] + request.size - 1) // request.size if request.size > 0 else 0,
            organization_name=request.organization_name
        )
        
    except Exception as e:
        print(f"Error searching credentials: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/credentials/validate-email", response_model=EmailValidationResponse, tags=["credentials"])
async def validate_email(request: EmailValidationRequest):
    """
    Validate email availability within an organization
    
    - **token**: JWT token in request body
    - **organization_name**: Organization name
    - **email**: Email to validate
    """
    try:
        
        await validate_token_from_body(request.token)
                
        from app.credential_service import credential_service
                
        result = credential_service.validate_email(
            organization_name=request.organization_name,
            email=request.email
        )
        
        if 'error' in result:
            raise HTTPException(status_code=400, detail=result['error'])
        
        return EmailValidationResponse(**result)
        
    except Exception as e:
        print(f"Error validating email: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/credentials/stats", response_model=CredentialStatsResponse, tags=["credentials"])
async def get_credential_statistics(
    organization_name: str = Query(..., description="Organization name"),
    token: str = Header(..., description="JWT token")
):
    """
    Get credential statistics for an organization
    
    - **organization_name**: Organization name (query parameter)
    - **token**: JWT token in Header
    """
    try:
        
        await validate_token_from_body(token)
                
        from app.credential_service import credential_service
                
        stats = credential_service.get_credential_stats(organization_name)
        
        if 'error' in stats:
            raise HTTPException(status_code=400, detail=stats['error'])
        
        return CredentialStatsResponse(**stats)
        
    except Exception as e:
        print(f"Error getting credential statistics: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/credentials/by-type/{type}", response_model=CredentialListResponseModel, tags=["credentials"])
async def get_credentials_by_type(
    type: str,
    organization_name: str = Query(..., description="Organization name"),
    token: str = Header(..., description="JWT token"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(50, ge=1, le=1000, description="Page size")
):
    """
    Get credentials by type within an organization
    
    - **type**: Credential type ('Identifier' or 'Other')
    - **organization_name**: Organization name (query parameter)
    - **token**: JWT token in Header
    - **page**: Page number (default: 1)
    - **size**: Page size (default: 50, max: 1000)
    """
    try:
        
        await validate_token_from_body(token)
                
        if type not in ['Identifier', 'Other']:
            raise HTTPException(status_code=400, detail="Invalid credential type")
        
        
        from app.credential_service import credential_service
        
        
        all_credentials = credential_service.get_all_credentials(
            organization_name=organization_name,
            limit=10000, 
            offset=0
        )
        
        filtered = [cred for cred in all_credentials if cred['type'] == type]
        
        
        offset = (page - 1) * size
        total = len(filtered)
        paginated = filtered[offset:offset + size]
        
        return CredentialListResponseModel(
            credentials=[
                CredentialResponseModel(**cred) for cred in paginated
            ],
            total=total,
            page=page,
            size=size,
            total_pages=(total + size - 1) // size if size > 0 else 0,
            organization_name=organization_name
        )
        
    except Exception as e:
        print(f"Error fetching credentials by type: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


# =============================================================================
# IMAGE ENDPOINTS (Novos endpoints para imagens)
# =============================================================================

@app.post("/organizations/{organization_name}/posts/{post_id}/image/upload-file", 
          response_model=PostImageUploadResponse,
          tags=["images"])
async def upload_post_image_file(
    organization_name: str,
    post_id: UUID,
    token: str = Form(...),
    alt_text: Optional[str] = Form(None),
    image: UploadFile = File(...),
    optimize: bool = Form(True),
    check_duplicates: bool = Form(True)
):
    """
    Upload image for a post from file
    
    - **organization_name**: Organization name
    - **post_id**: Post UUID
    - **token**: JWT token in form data
    - **alt_text**: Alternative text for image (optional)
    - **image**: Image file (PNG, JPEG, GIF, WebP)
    - **optimize**: Optimize image if > 1MB (default: True)
    - **check_duplicates**: Check for duplicate images (default: True)
    """
    try:
        
        await validate_token_from_body(token)
                      
        
        contents = await image.read()
        base64_data = base64.b64encode(contents).decode('utf-8')
        
        
        image_info = await image_service.validate_and_process_image(
            base64_data, 
            image.content_type
        )
        
        
        if alt_text:
            image_info['image_alt'] = alt_text
        
        
        if optimize and image_info['size_bytes'] > 1 * 1024 * 1024:
            image_info['base64_data'] = await image_service.optimize_image_size(
                image_info['base64_data'],
                target_size_kb=500
            )
        
        
        duplicates = []
        if check_duplicates:
            duplicates = await image_service.find_duplicate_image(
                image_info['image_hash'],
                exclude_post_id=post_id
            )
        
        
        saved = await image_service.save_image_to_post(post_id, image_info)
        
        if not saved:
            raise HTTPException(status_code=404, detail="Post não encontrado")
        
        return PostImageUploadResponse(
            success=True,
            message="Imagem enviada com sucesso",
            post_id=post_id,
            image_info={
                "mime_type": image_info['mime_type'],
                "size_bytes": image_info['size_bytes'],
                "dimensions": image_info['processed_dimensions'],
                "hash": image_info['image_hash']
            },
            data_url=image_service.create_data_url(
                image_info['base64_data'],
                image_info['mime_type']
            ),
            duplicates_found=len(duplicates)
        )
        
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/organizations/{organization_name}/posts/{post_id}/image/upload-base64", 
          response_model=PostImageUploadResponse,
          tags=["images"])
async def upload_post_image_base64(
    organization_name: str,
    post_id: UUID,
    request: ImageUploadRequest
):
    """
    Upload image for a post using base64 string
    
    - **organization_name**: Organization name
    - **post_id**: Post UUID
    - **token**: JWT token
    - **base64_data**: Base64 encoded image data
    - **mime_type**: Image MIME type (image/png, image/jpeg)
    - **alt_text**: Alternative text for image (optional)
    """
    try:
        
        await validate_token_from_body(request.token)
        
        
        image_info = await image_service.validate_and_process_image(
            request.base64_data,
            request.mime_type
        )
        
        
        if request.alt_text:
            image_info['image_alt'] = request.alt_text
        
        
        duplicates = await image_service.find_duplicate_image(
            image_info['image_hash'],
            exclude_post_id=post_id
        )
        
        
        saved = await image_service.save_image_to_post(post_id, image_info)
        
        if not saved:
            raise HTTPException(status_code=404, detail="Post não encontrado")
        
        return PostImageUploadResponse(
            success=True,
            message="Imagem enviada com sucesso",
            post_id=post_id,
            image_info={
                "mime_type": image_info['mime_type'],
                "size_bytes": image_info['size_bytes'],
                "dimensions": image_info['processed_dimensions'],
                "hash": image_info['image_hash']
            },
            data_url=image_service.create_data_url(
                image_info['base64_data'],
                image_info['mime_type']
            ),
            duplicates_found=len(duplicates)
        )
        
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/organizations/{organization_name}/posts/{post_id}/image", 
         response_model=ImageResponse,
         tags=["images"])
async def get_post_image(
    organization_name: str,
    post_id: UUID,
    token: str = Header(..., description="JWT token"),
    include_metadata: bool = Query(False),
    thumbnail: bool = Query(False),
    as_data_url: bool = Query(True)
):
    """
    Get image for a post
    
    - **organization_name**: Organization name
    - **post_id**: Post UUID
    - **token**: JWT token in header
    - **include_metadata**: Include metadata (size, dimensions, hash)
    - **thumbnail**: Generate thumbnail (300px max)
    - **as_data_url**: Return as data URL
    """
    try:
        
        await validate_token_from_body(token)
        
        
        image_data = await image_service.get_post_image(
            post_id, 
            include_metadata
        )
        
        if not image_data:
            raise HTTPException(status_code=404, detail="Imagem não encontrada")
        
        
        thumbnail_base64 = None
        if thumbnail:
            thumbnail_base64 = await image_service.generate_image_thumbnail(
                image_data['base64_image'],
                max_dimension=300
            )
        
        
        data_url = None
        if as_data_url:
            data_url = image_service.create_data_url(
                image_data['base64_image'],
                image_data['image_mime_type']
            )
        
        return ImageResponse(
            success=True,
            message="Imagem recuperada com sucesso",
            image_info=image_data,
            data_url=data_url,
            thumbnail=thumbnail_base64
        )
        
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/organizations/{organization_name}/posts/{post_id}/image/raw", 
         tags=["images"])
async def get_post_image_raw(
    organization_name: str,
    post_id: UUID,
    token: str = Header(..., description="JWT token")
):
    """
    Get post image as raw binary
    
    - **organization_name**: Organization name
    - **post_id**: Post UUID
    - **token**: JWT token in header
    """
    try:
        
        await validate_token_from_body(token)
        
        
        image_data = await image_service.get_post_image(
            post_id, 
            include_metadata=False
        )
        
        if not image_data:
            raise HTTPException(status_code=404, detail="Imagem não encontrada")
        
        
        image_bytes = base64.b64decode(image_data['base64_image'])
                
        return Response(
            content=image_bytes,
            media_type=image_data['image_mime_type'],
            headers={
                "Content-Disposition": f"inline; filename=\"post_{post_id}.{image_data['image_mime_type'].split('/')[1]}\""
            }
        )
        
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/organizations/{organization_name}/posts/{post_id}/image", 
            response_model=SuccessResponse,
            tags=["images"])
async def delete_post_image(
    organization_name: str,
    post_id: UUID,
    token: str = Header(..., description="JWT token")
):
    """
    Remove image from post
    
    - **organization_name**: Organization name
    - **post_id**: Post UUID
    - **token**: JWT token in header
    """
    try:
        
        await validate_token_from_body(token)
                
        removed = await image_service.remove_post_image(post_id)
        
        if not removed:
            raise HTTPException(status_code=404, detail="Imagem não encontrada")
        
        return SuccessResponse(
            success=True,
            message="Imagem removida com sucesso"
        )
        
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/organizations/{organization_name}/images/stats", 
         response_model=ImageStatsResponse,
         tags=["images"])
async def get_image_statistics(
    organization_name: str,
    token: str = Header(..., description="JWT token")
):
    """
    Get image statistics for organization
    
    - **organization_name**: Organization name
    - **token**: JWT token in header
    """
    try:
        
        await validate_token_from_body(token)
                
        stats = await image_service.get_image_statistics(uuid.UUID(organization_name))
        
        return ImageStatsResponse(**stats)
        
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/organizations/{organization_name}/posts/by-image-status", 
         response_model=List[Dict[str, Any]],
         tags=["images"])
async def get_posts_by_image_status(
    organization_name: str,
    token: str = Header(..., description="JWT token"),
    has_image: bool = Query(True)
):
    """
    Get posts filtered by image status
    
    - **organization_name**: Organization name
    - **token**: JWT token in header
    - **has_image**: Filter by image presence (true = with images, false = without images)
    """
    try:
        
        await validate_token_from_body(token)
                
        posts = await image_service.get_posts_by_image_status(
            uuid.UUID(organization_name), 
            has_image
        )
        
        return posts
        
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/organizations/{organization_name}/images/bulk/update-metadata", 
          response_model=BulkImageUpdateResponse,
          tags=["images"])
async def bulk_update_image_metadata(
    organization_name: str,
    request: BulkImageUpdateRequest
):
    """
    Bulk update image metadata
    
    - **organization_name**: Organization name
    - **token**: JWT token
    - **updates**: List of image updates with post_id and metadata
    """
    try:
        
        await validate_token_from_body(request.token)
                
        result = await image_service.bulk_update_image_metadata(request.updates)
        
        return BulkImageUpdateResponse(**result)
        
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/organizations/{organization_name}/images/cleanup", 
          response_model=ImageCleanupResponse,
          tags=["images"])
async def cleanup_orphaned_images(
    organization_name: str,
    token: str = Header(..., description="JWT token"),
    days_threshold: int = Query(30, ge=1, le=365)
):
    """
    Clean up orphaned images (deleted posts)
    
    - **organization_name**: Organization name
    - **token**: JWT token in header
    - **days_threshold**: Days since deletion (default: 30)
    """
    try:
        
        await validate_token_from_body(token)
                
        result = await image_service.cleanup_orphaned_images(
            uuid.UUID(organization_name), 
            days_threshold
        )
        
        return ImageCleanupResponse(**result)
        
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/images/validate", 
          response_model=ImageValidationResponse,
          tags=["images"])
async def validate_image(
    request: ImageUploadRequest
):
    """
    Validate image without saving to database
    
    - **token**: JWT token
    - **organization_name**: Organization name (not used, but required for consistency)
    - **base64_data**: Base64 encoded image data
    - **mime_type**: Image MIME type
    - **alt_text**: Alternative text (optional)
    """
    try:
        
        await validate_token_from_body(request.token)
                
        result = await image_service.validate_and_process_image(
            request.base64_data,
            request.mime_type
        )
        
        # Gerar thumbnail
        thumbnail = await image_service.generate_image_thumbnail(
            result['base64_data']
        )
        
        return ImageValidationResponse(
            valid=True,
            image_info=result,
            data_url=image_service.create_data_url(
                result['base64_data'],
                result['mime_type']
            ),
            thumbnail=thumbnail,
            thumbnail_data_url=image_service.create_data_url(
                thumbnail,
                result['mime_type']
            )
        )
        
    except HTTPException as e:
        return ImageValidationResponse(
            valid=False,
            error=e.detail,
            status_code=e.status_code
        )
    except Exception as e:
        return ImageValidationResponse(
            valid=False,
            error=str(e)
        )

@app.post("/images/optimize", 
          response_model=ImageOptimizationResponse,
          tags=["images"])
async def optimize_image(
    request: ImageUploadRequest,
    target_size_kb: int = Query(500, ge=10, le=5000)
):
    """
    Optimize image size
    
    - **token**: JWT token
    - **organization_name**: Organization name (not used)
    - **base64_data**: Base64 encoded image data
    - **mime_type**: Image MIME type
    - **alt_text**: Alternative text (optional)
    - **target_size_kb**: Target size in KB (default: 500)
    """
    try:
        
        await validate_token_from_body(request.token)
        
        
        image_info = await image_service.validate_and_process_image(
            request.base64_data,
            request.mime_type
        )
        
        
        optimized = await image_service.optimize_image_size(
            image_info['base64_data'],
            target_size_kb
        )
        
        return ImageOptimizationResponse(
            original_size=image_info['size_bytes'],
            optimized_size=len(base64.b64decode(optimized)),
            reduction_percentage=round(
                (1 - len(base64.b64decode(optimized)) / image_info['size_bytes']) * 100,
                2
            ),
            base64_data=optimized,
            data_url=image_service.create_data_url(
                optimized,
                image_info['mime_type']
            )
        )
        
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/images/batch/optimize", 
          response_model=Dict[str, Any],
          tags=["images"])
async def batch_optimize_images(
    token: str = Header(..., description="JWT token"),
    images: List[Dict[str, Any]] = Body(...),
    target_size_kb: int = Query(500, ge=10, le=5000)
):
    """
    Optimize multiple images in batch
    
    - **token**: JWT token in header
    - **images**: List of images with base64_data
    - **target_size_kb**: Target size in KB
    """
    try:
        
        await validate_token_from_body(token)
        
        optimized_images = []
        failed_images = []
        
        for img_data in images:
            try:
                base64_data = img_data.get('base64_data')
                if not base64_data:
                    failed_images.append({
                        'id': img_data.get('id'),
                        'error': 'Missing base64_data'
                    })
                    continue
                
                
                optimized = await image_service.optimize_image_size(
                    base64_data,
                    target_size_kb
                )
                
                optimized_images.append({
                    'id': img_data.get('id'),
                    'original_size': len(base64.b64decode(base64_data)),
                    'optimized_size': len(base64.b64decode(optimized)),
                    'reduction_percentage': round(
                        (1 - len(base64.b64decode(optimized)) / len(base64.b64decode(base64_data))) * 100,
                        2
                    ),
                    'base64_data': optimized
                })
            except Exception as e:
                failed_images.append({
                    'id': img_data.get('id'),
                    'error': str(e)
                })
        
        return {
            'success': True,
            'optimized_count': len(optimized_images),
            'failed_count': len(failed_images),
            'optimized_images': optimized_images,
            'failed_images': failed_images
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


        organization_id = org.organizations[0].id
# =============================================================================
# EXCHANGE RATE ENDPOINTS (CORRIGIDOS)
# =============================================================================

@app.post("/exchange-rates", response_model=schemas.ExchangeRateResponse, tags=["exchange-rates"])
async def create_exchange_rate(request: ExchangeRateCreateRequest):
    """
    Create a new exchange rate
    
    - **token**: JWT token in request body
    - **organization_id**: Organization UUID
    - **year_month**: Year and month in format YYYY-MM
    - **rate**: Exchange rate value
    - **valid_from**: Start date of validity
    - **valid_to**: End date of validity
    - **base_currency**: Base currency code (default: USD)
    - **target_currency**: Target currency code (default: BRL)
    - **source**: Source of the exchange rate
    """
    try:
        token_data = await validate_token_from_body(request.token)
        logger.info(f"Creating exchange rate for organization: {request.organization_id}")
        
        result = await exchange_rate_service.create_exchange_rate(
            year_month=request.year_month,
            rate=Decimal(str(request.rate)),
            valid_from=request.valid_from,
            valid_to=request.valid_to,
            organization_id=request.organization_id,  # Já é UUID
            base_currency=request.base_currency,
            target_currency=request.target_currency,
            source=request.source
        )
        if not result:
            raise HTTPException(status_code=400, detail="Failed to create exchange rate")
        return schemas.ExchangeRateResponse(**result)
    except Exception as e:
        logger.error(f"Error creating exchange rate: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    
@app.post("/exchange-rates/organization/list", response_model=ExchangeRateListResponse, tags=["exchange-rates"])
async def get_organization_exchange_rates(request: CostFilterRequest):
    """
    Get exchange rates for an organization with filtering
    
    - **token**: JWT token in request body
    - **organization_id**: Organization UUID
    - **start_date**: Start date filter (optional)
    - **end_date**: End date filter (optional)
    - **page**: Page number (default: 1)
    - **page_size**: Page size (default: 50)
    """
    try:
        await validate_token_from_body(token)
        return await exchange_rate_service.get_organization_exchange_rate(
            organization_id=request.organization_id,  # Já é UUID
            year_month=None,
            base_currency=None,
            target_currency=None,
            date_from=request.start_date,
            date_to=request.end_date,
            page=request.page,
            page_size=request.page_size
        )
        return ExchangeRateListResponse(
            exchange_rates=[ExchangeRateResponse(**rate) for rate in result['exchange_rates']],
            total_count=result['total_count'],
            page=result['page'],
            page_size=result['page_size'],
            total_pages=result['total_pages']
        )
    except Exception as e:
        logger.error(f"Error fetching organization exchange rates: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    
@app.post("/exchange-rates/period", response_model=schemas.ExchangeRateResponse, tags=["exchange-rates"])
async def get_exchange_rate_for_period(request: ExchangeRatePeriodRequest):
    """
    Get exchange rate for specific period
    
    - **token**: JWT token in request body
    - **organization_id**: Organization UUID
    - **year_month**: Year and month in format YYYY-MM
    - **base_currency**: Base currency code (default: USD)
    - **target_currency**: Target currency code (default: BRL)
    """
    try:
        
        await validate_token_from_body(request.token)
                
        result = await exchange_rate_service.get_exchange_rate_for_period(
            organization_id=request.organization_id,  # Já é UUID
            year_month=request.year_month,
            base_currency=request.base_currency,
            target_currency=request.target_currency
        )
        
        if not result:
            raise HTTPException(status_code=404, detail="Exchange rate not found for specified period")
        
        return schemas.ExchangeRateResponse(**result)
        
    except Exception as e:
        logger.error(f"Error fetching exchange rate for period: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    
                                                                                              
# =============================================================================
# COST ENDPOINTS (CORRIGIDOS)
# =============================================================================

@app.post("/costs", response_model=CostResponse, tags=["costs"])
async def create_cost(request: CostCreateRequest):
    """
    Create a new cost
    
    - **token**: JWT token in request body
    - **organization_id**: Organization UUID
    - **due_date**: Due date
    - **amount**: Cost amount
    - **currency**: Currency code (3 letters)
    - **payment_nature**: Payment nature
    - **cost_nature_code**: Cost nature code
    - **converted_amount_brl**: Converted amount in BRL (optional, auto-calculated)
    - **exchange_rate_month**: Exchange rate month (optional, auto-filled)
    - **exchange_rate_value**: Exchange rate value (optional, auto-filled)
    - **description**: Description (optional)
    - **status**: Status (default: pending)
    """
    try: 
        token_data = await validate_token_from_body(request.token)
        logger.info(f"Creating cost for organization: {request.organization_id}")
        result = await cost_service.create_cost(
            due_date=request.due_date,
            amount=Decimal(str(request.amount)),
            currency=request.currency,
            payment_nature=request.payment_nature,
            cost_nature_code=request.cost_nature_code,
            organization_id=request.organization_id,  # Já é UUID
            converted_amount_brl=Decimal(str(request.converted_amount_brl)) if request.converted_amount_brl else None,
            exchange_rate_month=request.exchange_rate_month,
            exchange_rate_value=Decimal(str(request.exchange_rate_value)) if request.exchange_rate_value else None,
            description=request.description,
            status=request.status

        )
        if not result:
            raise HTTPException(status_code=400, detail="Failed to create cost")
        return CostResponse(**result)
    
    except  Exception as e:
        logger.error(f"Error creating cost: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    
@app.get("/costs/organization/list", response_model=CostListResponse, tags=["costs"])
async def get_organization_costs(
    organization_id: UUID = Query(..., description="Organization UUID"),
    token: str = Header(..., description="JWT token"),
    start_date: Optional[date] = Query(None, description="Start date filter (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date filter (YYYY-MM-DD)"),
    status: Optional[str] = Query(None, description="Status filter"),
    cost_nature_code: Optional[str] = Query(None, description="Cost nature code filter"),
    currency: Optional[str] = Query(None, description="Currency filter"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Page size")
):
    """
    Get costs for an organization with filtering (GET version)
    
    - **organization_id**: Organization UUID (query parameter)
    - **token**: JWT token in Header
    - **start_date**: Start date filter (optional)
    - **end_date**: End date filter (optional)
    - **status**: Status filter (optional)
    - **cost_nature_code**: Cost nature code filter (optional)
    - **currency**: Currency filter (optional)
    - **page**: Page number (default: 1)
    - **page_size**: Page size (default: 50, max: 100)
    """
    try:
        
        await validate_token_from_body(token)
                
        result = await cost_service.get_organization_costs(
            organization_id=organization_id,
            start_date=start_date,
            end_date=end_date,
            status=status,
            cost_nature_code=cost_nature_code,
            currency=currency,
            page=page,
            page_size=page_size
        )
        
        return CostListResponse(
            costs=[CostResponse(**cost) for cost in result['costs']],
            total_count=result['total_count'],
            page=result['page'],
            page_size=result['page_size'],
            total_pages=result['total_pages']
        )
        
    except Exception as e:
        logger.error(f"Error fetching organization costs: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
      
# =============================================================================
# AWESOME API SYNC ENDPOINTS (CORRIGIDOS)
# =============================================================================

@app.post("/awesome-api/sync/organization", response_model=AwesomeAPISyncResponse, tags=["awesome-api"])
async def sync_awesome_api_for_organization(request: AwesomeAPISyncRequest):
    """
    Sync Awesome API exchange rate for specific organization
    
    - **token**: JWT token in request body
    - **organization_id**: Organization UUID
    """
    try:
        
        await validate_token_from_body(request.token)
        
        
        result = await awesomeapi_sync_service.sync_for_organization(request.organization_id)
        
        return AwesomeAPISyncResponse(**result)
        
    except Exception as e:
        logger.error(f"Error syncing Awesome API for organization: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/awesome-api/organization/rates", response_model=List[Dict[str, Any]], tags=["awesome-api"])
async def get_organization_awesome_api_rates(
    organization_id: UUID = Query(..., description="Organization UUID"),
    token: str = Header(..., description="JWT token"),
    months_back: int = Query(6, ge=1, le=24, description="Number of months back to fetch")
):
    """
    Get Awesome API rates for organization
    
    - **organization_id**: Organization UUID (query parameter)
    - **token**: JWT token in Header
    - **months_back**: Number of months back to fetch (default: 6)
    """
    try:
        
        await validate_token_from_body(token)
                
        rates = await awesomeapi_sync_service.get_organization_rates(organization_id, months_back)
        
        return rates
        
    except Exception as e:
        logger.error(f"Error getting organization rates: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/awesome-api/current-rate", response_model=Dict[str, Any], tags=["awesome-api"])
async def get_current_dollar_rate(
    use_cache: bool = Query(True, description="Use cached rate if available"),
    token: str = Header(..., description="JWT token")
):
    """
    Get current USD-BRL exchange rate from Awesome API
    
    - **use_cache**: Use cached rate if available (default: True)
    - **token**: JWT token in Header
    """
    try:
        
        await validate_token_from_body(token)
                
        rate_data = await awesomeapi_sync_service.get_current_rate(use_cache=use_cache)
        
        if not rate_data:
            raise HTTPException(
                status_code=503, 
                detail="Unable to fetch current exchange rate from Awesome API"
            )
        
        return {
            "success": True,
            "data": rate_data,
            "timestamp": datetime.now().isoformat(),
            "source": "awesomeapi"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting current dollar rate: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
# =============================================================================
# MONITORING ENDPOINTS
# =============================================================================

@app.post("/health")
async def health_check(request: HealthCheckRequest):
    """
    Health check endpoint (Requires authentication token in body)
    
    - **token**: JWT token in request body
    """
    token_data = await validate_token_from_body(request.token)
    
    return {
        "status": "healthy",
        "service": "user-microservice",
        "version": "1.0.0",
        "authenticated_client": token_data['client_id']
    }

@app.post("/")
async def root(request: RootRequest):
    """
    Root endpoint with API information (Requires authentication token in body)
    
    - **token**: JWT token in request body
    """
    token_data = await validate_token_from_body(request.token)
    
    return {
        "message": "User Microservice API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc",
        "authenticated_client": token_data['client_id']
    }

@app.get("/docs", include_in_schema=False)
async def get_docs():
    """Documentation endpoint (no authentication required)"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/docs")

@app.get("/redoc", include_in_schema=False)
async def get_redoc():
    """ReDoc endpoint (no authentication required)"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/redoc")