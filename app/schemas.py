import base64
from enum import Enum
import uuid
from pydantic import BaseModel, EmailStr, Field, validator, root_validator
from typing import Dict, Optional, List, Any, Union
from datetime import datetime, date
from uuid import UUID
import re


# ==================================================
#              AUTHENTICATION SCHEMAS
# ==================================================

class AuthTokenRequest(BaseModel):
    client_id: str
    client_secret: str


class TokenValidationRequest(BaseModel):
    token: str


class TokenValidationResponse(BaseModel):
    valid: bool
    message: str


class AuthenticatedRequest(BaseModel):
    token: str


class CredentialsValidationRequest(BaseModel):
    token: str
    cpf: Optional[str] = None
    crm_registry: Optional[str] = None
    identity: Optional[str] = None


class CredentialsValidationResponse(BaseModel):
    valid: bool


# ==================================================
#              ORGANIZATION SCHEMAS 
# ==================================================

class OrganizationBase(BaseModel):
    name: str
    address: Optional[str] = None
    cnpj: Optional[str] = None
    ein: Optional[str] = None


class OrganizationCreate(OrganizationBase):
    token: str


class OrganizationUpdate(BaseModel):
    token: str
    name: Optional[str] = None
    address: Optional[str] = None
    cnpj: Optional[str] = None
    ein: Optional[str] = None


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


class OrganizationDetailResponse(OrganizationResponse):
    statistics: dict = {}


class OrganizationListResponse(BaseModel):
    organizations: List[OrganizationResponse]
    total_count: int
    page: int
    page_size: int


class OrganizationFilter(BaseModel):
    token: str
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=1000)


class OrganizationSearchRequest(BaseModel):
    token: str
    query: str
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=1000)


class CNPJValidationRequest(BaseModel):
    token: str
    cnpj: str


class CNPJValidationResponse(BaseModel):
    cnpj: str
    is_valid_format: bool
    is_available: bool
    cleaned_cnpj: str


class EINValidationRequest(BaseModel):
    token: str
    ein: str


class EINValidationResponse(BaseModel):
    ein: str
    is_valid_format: bool
    is_available: bool
    cleaned_ein: str


class DeactivationRequest(BaseModel):
    token: str
    reason: Optional[str] = None


class ReactivationRequest(BaseModel):
    token: str


class OrganizationSettingsRequest(BaseModel):
    token: str
    settings: dict


class SubscriptionResponse(BaseModel):
    subscription_id: Optional[UUID] = None
    plan_name: Optional[str] = None
    status: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class UsersListResponse(BaseModel):
    users: List[dict]
    total_count: int


class CPFValidationRequest(BaseModel):
    token: str
    cpf: str


class CPFValidationResponse(BaseModel):
    cpf: str
    is_valid_format: bool
    is_available: bool
    cleaned_cpf: str


class SSNValidationRequest(BaseModel):
    token: str
    ssn: str


class SSNValidationResponse(BaseModel):
    ssn: str
    is_valid_format: bool
    is_available: bool
    cleaned_ssn: str


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str
    organization_name: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str
    role: str


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[str] = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


class UserResponse(BaseModel):
    id: UUID
    name: str
    email: str
    role: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ==================================================
#              PROJECT SCHEMAS 
# ==================================================

class ProjectBase(BaseModel):
    name: str
    code: str
    description: Optional[str] = None
    owner_username: str
    template_agile_method: str = "Scrum"


class ProjectCreate(ProjectBase):
    token: str
    settings: Optional[Dict[str, Any]] = Field(default_factory=dict)
    
    @validator('code')
    def validate_project_code(cls, v):
        import re
        pattern = r'^[A-Z0-9]{2,}-[A-Z0-9]{1,}$'
        if not re.match(pattern, v):
            raise ValueError('Project code must be in format like: PROJ-001, LTS-2024')
        return v
    
    @validator('template_agile_method')
    def validate_agile_method(cls, v):
        allowed_methods = ['Scrum', 'Kanban', 'Scrumban', 'XP', 'Lean']
        if v not in allowed_methods:
            raise ValueError(f'Agile method must be one of: {", ".join(allowed_methods)}')
        return v


class ProjectUpdate(BaseModel):
    token: str
    name: Optional[str] = None
    description: Optional[str] = None
    owner_username: Optional[str] = None
    template_agile_method: Optional[str] = None
    is_active: Optional[bool] = None
    settings: Optional[Dict[str, Any]] = None
    
    @validator('template_agile_method')
    def validate_agile_method(cls, v):
        if v is not None:
            allowed_methods = ['Scrum', 'Kanban', 'Scrumban', 'XP', 'Lean']
            if v not in allowed_methods:
                raise ValueError(f'Agile method must be one of: {", ".join(allowed_methods)}')
        return v


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
    total_count: int
    page: int
    page_size: int


class ProjectFilter(BaseModel):
    token: str
    organization_name: str
    active_only: bool = True
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=1000)


class ProjectSearchRequest(BaseModel):
    token: str
    organization_name: str
    query: str
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=1000)


class ProjectDeleteRequest(BaseModel):
    token: str
    organization_name: str
    project_code: str


class ProjectRestoreRequest(BaseModel):
    token: str
    organization_name: str
    project_code: str


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


# ==================================================
#          PROJECT MEMBER SCHEMAS 
# ==================================================

class ProjectMemberBase(BaseModel):
    username: str
    role: str = "Member"


class ProjectMemberCreate(ProjectMemberBase):
    token: str
    organization_name: str
    project_code: str
    
    @validator('role')
    def validate_role(cls, v):
        allowed_roles = ['Owner', 'Admin', 'Member', 'Viewer']
        if v not in allowed_roles:
            raise ValueError(f'Role must be one of: {", ".join(allowed_roles)}')
        return v


class ProjectMemberRemove(BaseModel):
    token: str
    organization_name: str
    project_code: str
    username: str


class ProjectMemberUpdate(BaseModel):
    token: str
    organization_name: str
    project_code: str
    username: str
    role: str
    
    @validator('role')
    def validate_role(cls, v):
        allowed_roles = ['Owner', 'Admin', 'Member', 'Viewer']
        if v not in allowed_roles:
            raise ValueError(f'Role must be one of: {", ".join(allowed_roles)}')
        return v


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
    total_count: int


# ==================================================
#          PROJECT STATISTICS SCHEMAS 
# ==================================================

class ProjectStatsRequest(BaseModel):
    token: str
    organization_name: str
    project_code: str


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


class ProjectActivityStats(BaseModel):
    date: date
    created_count: int
    completed_count: int


# ==================================================
#          PROJECT SETTINGS SCHEMAS 
# ==================================================

class ProjectSettingsUpdate(BaseModel):
    token: str
    organization_name: str
    project_code: str
    settings: Dict[str, Any]


class ProjectSettingsResponse(BaseModel):
    project_code: str
    settings: Dict[str, Any]
    updated_at: datetime


# ==================================================
#          AGILE/SPRINT SCHEMAS (opcional)
# ==================================================

class SprintBase(BaseModel):
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


class SprintCreate(SprintBase):
    token: str
    organization_name: str
    project_code: str


class SprintResponse(SprintBase):
    id: UUID
    project_id: UUID
    organization_id: UUID
    is_active: bool
    is_completed: bool
    actual_velocity: Optional[int] = None
    created_at: datetime
    updated_at: datetime


# ==================================================
#          WORK ITEM SCHEMAS (opcional)
# ==================================================

class WorkItemType(str, Enum):
    EPIC = "Epic"
    FEATURE = "Feature"
    USER_STORY = "User Story"
    TASK = "Task"
    BUG = "Bug"
    ISSUE = "Issue"


class WorkItemPriority(str, Enum):
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class WorkItemStatus(str, Enum):
    NEW = "New"
    IN_PROGRESS = "In Progress"
    REVIEW = "Review"
    DONE = "Done"
    CLOSED = "Closed"


class WorkItemBase(BaseModel):
    title: str
    description: Optional[str] = None
    type: WorkItemType
    priority: WorkItemPriority = WorkItemPriority.MEDIUM
    status: WorkItemStatus = WorkItemStatus.NEW
    assigned_to: Optional[str] = None
    story_points: Optional[int] = Field(None, ge=0, le=100)
    due_date: Optional[datetime] = None


class WorkItemCreate(WorkItemBase):
    token: str
    organization_name: str
    project_code: str
    parent_id: Optional[UUID] = None


class WorkItemResponse(WorkItemBase):
    id: UUID
    project_id: UUID
    organization_id: UUID
    identifier: str  # ex: PROJ-001
    type_id: UUID
    reporter_id: UUID
    reporter_username: Optional[str] = None
    epic_id: Optional[UUID] = None
    feature_id: Optional[UUID] = None
    original_estimate_hours: Optional[float] = None
    remaining_estimate_hours: Optional[float] = None
    completed_hours: Optional[float] = None
    tags: Optional[List[str]] = None
    attachments: Optional[List[Dict[str, Any]]] = None
    custom_fields: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None


# ==================================================
#          RESPONSE MESSAGE SCHEMAS 
# ==================================================

class SuccessResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    details: Optional[str] = None
    code: Optional[str] = None


class ProjectOperationResponse(SuccessResponse):
    project_code: str
    organization: str


class MemberOperationResponse(SuccessResponse):
    project_code: str
    username: str
    role: Optional[str] = None


# ==================================================
#              CREDENTIAL SCHEMAS 
# ==================================================

class CredentialBase(BaseModel):
    type: str = Field(..., description="Type of credential: 'Identifier' or 'Other'")
    email: EmailStr = Field(..., description="Email/login for the credential")
    password: str = Field(..., description="Password", min_length=4)
    description: Optional[str] = Field(None, description="Optional description")
    
    @validator('type')
    def validate_credential_type(cls, v):
        allowed_types = ['Identifier', 'Other']
        if v not in allowed_types:
            raise ValueError(f"Credential type must be one of: {', '.join(allowed_types)}")
        return v


class CredentialCreate(CredentialBase):
    token: str = Field(..., description="JWT authentication token")
    organization_name: str = Field(..., description="Organization name")


class CredentialUpdate(BaseModel):
    token: str = Field(..., description="JWT authentication token")
    organization_name: str = Field(..., description="Organization name")
    type: Optional[str] = Field(None, description="Type of credential")
    email: Optional[EmailStr] = Field(None, description="Email/login")
    password: Optional[str] = Field(None, description="Password", min_length=4)
    description: Optional[str] = Field(None, description="Description")
    
    @validator('type')
    def validate_credential_type(cls, v):
        if v is not None:
            allowed_types = ['Identifier', 'Other']
            if v not in allowed_types:
                raise ValueError(f"Credential type must be one of: {', '.join(allowed_types)}")
        return v


class CredentialResponse(BaseModel):
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


class CredentialListResponse(BaseModel):
    credentials: List[CredentialResponse]
    total_count: int
    page: int
    page_size: int
    organization_name: str


class CredentialFilter(BaseModel):
    token: str = Field(..., description="JWT authentication token")
    organization_name: str = Field(..., description="Organization name")
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=1000)


class CredentialSearchRequest(BaseModel):
    token: str = Field(..., description="JWT authentication token")
    organization_name: str = Field(..., description="Organization name")
    search_term: str = Field(..., description="Search term for email or description")
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=1000)


class EmailValidationRequest(BaseModel):
    token: str = Field(..., description="JWT authentication token")
    organization_name: str = Field(..., description="Organization name")
    email: EmailStr = Field(..., description="Email to validate")


class EmailValidationResponse(BaseModel):
    email: str
    organization_name: str
    is_available: bool
    exists: bool
    message: str


class CredentialStatsResponse(BaseModel):
    organization_name: str
    total_credentials: int
    distinct_types: int
    distinct_emails: int
    oldest_credential: Optional[datetime]
    newest_credential: Optional[datetime]
    by_type: Dict[str, int]


class CredentialDeleteRequest(BaseModel):
    token: str = Field(..., description="JWT authentication token")
    organization_name: str = Field(..., description="Organization name")
    credential_id: UUID = Field(..., description="Credential ID to delete")


# ==================================================
#              POST SCHEMAS 
# ==================================================

class PostBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    content: str
    scheduled_at: Optional[datetime] = None
    status: Optional[str] = Field("draft", pattern="^(draft|scheduled|published|archived)$")


class PostCreate(PostBase):
    user_id: Optional[uuid.UUID] = None
    organization_id: Optional[uuid.UUID] = None


class PostUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    content: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    status: Optional[str] = Field(None, pattern="^(draft|scheduled|published|archived)$")


class PostInDB(PostBase):
    id: uuid.UUID
    published_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    user_id: Optional[uuid.UUID] = None
    organization_id: Optional[uuid.UUID] = None
    
    class Config:
        from_attributes = True


class PostResponse(PostInDB):
    """Schema for post response"""
    pass


class PostStats(BaseModel):
    """Schema for post statistics"""
    total: int
    drafts: int
    scheduled: int
    published: int


# ==================================================
#              IMAGE SCHEMAS
# ==================================================

class ImageUpload(BaseModel):
    """Schema for image upload via base64"""
    base64_data: str = Field(..., description="Base64 encoded image data")
    mime_type: str = Field(..., description="Image MIME type (image/png, image/jpeg)")
    alt_text: Optional[str] = Field(None, max_length=200, description="Alternative text for the image")
    
    @validator('base64_data')
    def validate_base64_data(cls, v: str) -> str:
        """Validate base64 string"""
        try:
            # Remove data URL prefix if present
            if ',' in v:
                v = v.split(',')[1]  # CORREÇÃO: estava v.split('')[1]
            # Decode to ensure it's valid base64
            base64.b64decode(v, validate=True)
            return v
        except Exception as e:
            raise ValueError(f"Invalid base64 data: {str(e)}")
    
    @validator('mime_type')
    def validate_mime_type(cls, v: str) -> str:
        """Validate MIME type"""
        allowed_types = {'image/png', 'image/jpeg', 'image/jpg', 'image/gif', 'image/webp'}
        if v not in allowed_types:
            raise ValueError(f"Unsupported MIME type. Allowed: {', '.join(allowed_types)}")
        return v


class PostBaseWithImage(PostBase):
    """Extended post schema with base64 image support"""
    base64_image: Optional[str] = Field(None, description="Base64 encoded image")
    image_mime_type: Optional[str] = Field(None, description="Image MIME type")
    image_url: Optional[str] = Field(None, description="Optional external image URL")
    image_alt: Optional[str] = Field(None, max_length=200, description="Image alt text")
    
    @validator('base64_image')
    def validate_image_if_mime_provided(cls, v: Optional[str], values: Dict[str, Any]) -> Optional[str]:
        """Validate that if base64_image is provided, image_mime_type is also provided"""
        if v and not values.get('image_mime_type'):
            raise ValueError('image_mime_type is required when base64_image is provided')
        return v


class PostCreateWithImage(PostCreate):
    """Create post schema with image support"""
    organization_name: str = Field(..., description="Organization name for the post")
    base64_image: Optional[str] = Field(None, description="Base64 encoded image")
    image_mime_type: Optional[str] = Field(None, description="Image MIME type (image/png, image/jpeg)")
    image_alt: Optional[str] = Field(None, max_length=200, description="Image alt text")
    
    @validator('base64_image')
    def validate_image_if_mime_provided(cls, v: Optional[str], values: Dict[str, Any]) -> Optional[str]:
        """Validate that if base64_image is provided, image_mime_type is also provided"""
        if v and not values.get('image_mime_type'):
            raise ValueError('image_mime_type is required when base64_image is provided')
        return v


class PostResponseWithImage(PostResponse):
    """Response schema with image data"""
    base64_image: Optional[str] = Field(None, description="Base64 encoded image")
    image_mime_type: Optional[str] = Field(None, description="Image MIME type")
    image_alt: Optional[str] = Field(None, max_length=200, description="Image alt text")
    image_url: Optional[str] = Field(None, description="Optional external image URL")
    image_dimensions: Optional[str] = Field(None, description="Image dimensions (e.g., '1920x1080')")
    image_size_bytes: Optional[int] = Field(None, description="Image size in bytes")
    image_hash: Optional[str] = Field(None, description="Image hash for duplicate detection")
    has_image: bool = Field(False, description="Whether post has embedded image")
    image_data_url: Optional[str] = Field(None, description="Data URL for frontend display")
    
    class Config:
        from_attributes = True


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


# ==================================================
#          VALIDATION SCHEMAS
# ==================================================

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