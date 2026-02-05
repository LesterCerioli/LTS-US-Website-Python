from abc import ABC, abstractmethod
from uuid import UUID
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class OrganizationServiceContract(ABC):
    """Contract for organization management services"""
    
    
    class OrganizationStatus(Enum):
        ACTIVE = "active"
        INACTIVE = "inactive"
        SUSPENDED = "suspended"
        PENDING = "pending"
    
    class OrganizationType(Enum):
        HOSPITAL = "hospital"
        CLINIC = "clinic"
        PRIVATE_PRACTICE = "private_practice"
        LABORATORY = "laboratory"
        PHARMACY = "pharmacy"
        OTHER = "other"
    
    class OrganizationCreateDTO:
        def __init__(
            self,
            name: str,
            cnpj: str,
            ein: str,
            organization_type: str,
            address: str,
            phone: str,
            email: str,
            website: Optional[str] = None,
            description: Optional[str] = None,
            subscription_id: Optional[UUID] = None,
            settings: Optional[Dict[str, Any]] = None
        ):
            self.name = name
            self.cnpj = cnpj
            self.ein = ein
            self.organization_type = organization_type
            self.address = address
            self.phone = phone
            self.email = email
            self.website = website
            self.description = description
            self.subscription_id = subscription_id
            self.settings = settings or {}
    
    class OrganizationUpdateDTO:
        def __init__(
            self,
            name: Optional[str] = None,
            organization_type: Optional[str] = None,
            address: Optional[str] = None,
            phone: Optional[str] = None,
            email: Optional[str] = None,
            website: Optional[str] = None,
            description: Optional[str] = None,
            subscription_id: Optional[UUID] = None,
            settings: Optional[Dict[str, Any]] = None,
            status: Optional[str] = None
        ):
            self.name = name
            self.organization_type = organization_type
            self.address = address
            self.phone = phone
            self.email = email
            self.website = website
            self.description = description
            self.subscription_id = subscription_id
            self.settings = settings
            self.status = status
    
    class OrganizationResponseDTO:
        def __init__(
            self,
            id: UUID,
            name: str,
            cnpj: str,
            ein: str,
            organization_type: str,
            address: str,
            phone: str,
            email: str,
            website: Optional[str],
            description: Optional[str],
            subscription_id: Optional[UUID],
            status: str,
            settings: Dict[str, Any],
            created_at: datetime,
            updated_at: datetime
        ):
            self.id = id
            self.name = name
            self.cnpj = cnpj
            self.ein = ein
            self.organization_type = organization_type
            self.address = address
            self.phone = phone
            self.email = email
            self.website = website
            self.description = description
            self.subscription_id = subscription_id
            self.status = status
            self.settings = settings
            self.created_at = created_at
            self.updated_at = updated_at
    
    class OrganizationDetailDTO:
        def __init__(
            self,
            id: UUID,
            name: str,
            cnpj: str,
            ein: str,
            organization_type: str,
            address: str,
            phone: str,
            email: str,
            website: Optional[str],
            description: Optional[str],
            subscription_id: Optional[UUID],
            status: str,
            settings: Dict[str, Any],
            created_at: datetime,
            updated_at: datetime,
            user_count: int,
            doctor_count: int,
            patient_count: int,
            appointment_count: int,
            subscription_info: Optional[Dict[str, Any]] = None
        ):
            self.id = id
            self.name = name
            self.cnpj = cnpj
            self.ein = ein
            self.organization_type = organization_type
            self.address = address
            self.phone = phone
            self.email = email
            self.website = website
            self.description = description
            self.subscription_id = subscription_id
            self.status = status
            self.settings = settings
            self.created_at = created_at
            self.updated_at = updated_at
            self.user_count = user_count
            self.doctor_count = doctor_count
            self.patient_count = patient_count
            self.appointment_count = appointment_count
            self.subscription_info = subscription_info or {}
    
    class OrganizationFilterDTO:
        def __init__(
            self,
            organization_type: Optional[str] = None,
            status: Optional[str] = None,
            subscription_id: Optional[UUID] = None,
            created_after: Optional[datetime] = None,
            created_before: Optional[datetime] = None,
            search_query: Optional[str] = None,
            page: int = 1,
            size: int = 100
        ):
            self.organization_type = organization_type
            self.status = status
            self.subscription_id = subscription_id
            self.created_after = created_after
            self.created_before = created_before
            self.search_query = search_query
            self.page = page
            self.size = size
    
    class OrganizationListDTO:
        def __init__(
            self,
            organizations: List['OrganizationServiceContract.OrganizationResponseDTO'],
            total: int,
            page: int,
            size: int,
            total_pages: int
        ):
            self.organizations = organizations
            self.total = total
            self.page = page
            self.size = size
            self.total_pages = total_pages
    
    @abstractmethod
    async def create(self, organization: 'OrganizationServiceContract.OrganizationCreateDTO') -> 'OrganizationServiceContract.OrganizationResponseDTO':
        """
        Create a new organization
        
        Args:
            organization: Organization data for creation
            
        Returns:
            OrganizationResponseDTO: Created organization with generated ID
            
        Raises:
            ValidationError: If organization data is invalid
            ConflictError: If organization with same CNPJ or EIN already exists
        """
        pass
    
    @abstractmethod
    async def get_by_id(self, organization_id: UUID) -> 'OrganizationServiceContract.OrganizationDetailDTO':
        """
        Get organization by ID
        
        Args:
            organization_id: UUID of the organization
            
        Returns:
            OrganizationDetailDTO: Found organization with complete details
            
        Raises:
            NotFoundError: If organization not found
        """
        pass
    
    @abstractmethod
    async def get_all(self, filter_dto: Optional['OrganizationServiceContract.OrganizationFilterDTO'] = None) -> 'OrganizationServiceContract.OrganizationListDTO':
        """
        Get all organizations with optional filtering
        
        Args:
            filter_dto: Optional filters for the query
            
        Returns:
            OrganizationListDTO: Paginated list of organizations
        """
        pass
    
    @abstractmethod
    async def get_by_name(self, name: str, filter_dto: Optional['OrganizationServiceContract.OrganizationFilterDTO'] = None) -> 'OrganizationServiceContract.OrganizationListDTO':
        """
        Get organizations by name
        
        Args:
            name: Organization name to search for (partial match supported)
            filter_dto: Optional additional filters
            
        Returns:
            OrganizationListDTO: Paginated list of organizations matching the name
        """
        pass
    
    @abstractmethod
    async def get_by_subscription(self, subscription_id: UUID, filter_dto: Optional['OrganizationServiceContract.OrganizationFilterDTO'] = None) -> 'OrganizationServiceContract.OrganizationListDTO':
        """
        Get organizations by subscription ID
        
        Args:
            subscription_id: UUID of the subscription
            filter_dto: Optional additional filters
            
        Returns:
            OrganizationListDTO: Paginated list of organizations with the specified subscription
            
        Raises:
            NotFoundError: If subscription not found
        """
        pass
    
    @abstractmethod
    async def update(self, organization_id: UUID, organization: 'OrganizationServiceContract.OrganizationUpdateDTO') -> 'OrganizationServiceContract.OrganizationResponseDTO':
        """
        Update an existing organization
        
        Args:
            organization_id: UUID of the organization to update
            organization: Updated organization data
            
        Returns:
            OrganizationResponseDTO: Updated organization
            
        Raises:
            NotFoundError: If organization not found
            ValidationError: If update data is invalid
            ConflictError: If update causes conflicts with existing data
        """
        pass
    
    @abstractmethod
    async def delete(self, organization_id: UUID) -> None:
        """
        Delete an organization
        
        Args:
            organization_id: UUID of the organization to delete
            
        Raises:
            NotFoundError: If organization not found
            BusinessRuleError: If organization has associated users, patients, or other dependencies
        """
        pass
    
    @abstractmethod
    async def get_by_cnpj(self, cnpj: str) -> 'OrganizationServiceContract.OrganizationResponseDTO':
        """
        Get organization by CNPJ
        
        Args:
            cnpj: CNPJ number (exact match)
            
        Returns:
            OrganizationResponseDTO: Found organization
            
        Raises:
            NotFoundError: If organization with CNPJ not found
        """
        pass
    
    @abstractmethod
    async def get_by_ein(self, ein: str) -> 'OrganizationServiceContract.OrganizationResponseDTO':
        """
        Get organization by EIN
        
        Args:
            ein: EIN number (exact match)
            
        Returns:
            OrganizationResponseDTO: Found organization
            
        Raises:
            NotFoundError: If organization with EIN not found
        """
        pass
    
    @abstractmethod
    async def search_organizations(self, query: str, filter_dto: Optional['OrganizationServiceContract.OrganizationFilterDTO'] = None) -> 'OrganizationServiceContract.OrganizationListDTO':
        """
        Search organizations by multiple criteria
        
        Args:
            query: Search term for name, address, CNPJ, etc.
            filter_dto: Optional additional filters
            
        Returns:
            OrganizationListDTO: Paginated list of matching organizations
        """
        pass
    
    @abstractmethod
    async def validate_cnpj(self, cnpj: str) -> dict:
        """
        Validate CNPJ format and check if it's available
        
        Args:
            cnpj: CNPJ number to validate
            
        Returns:
            dict: Validation result with status and details
            
        Raises:
            ValidationError: If CNPJ format is invalid
        """
        pass
    
    @abstractmethod
    async def validate_ein(self, ein: str) -> dict:
        """
        Validate EIN format and check if it's available
        
        Args:
            ein: EIN number to validate
            
        Returns:
            dict: Validation result with status and details
            
        Raises:
            ValidationError: If EIN format is invalid
        """
        pass
    
    @abstractmethod
    async def get_organization_statistics(self, organization_id: UUID) -> dict:
        """
        Get statistics for an organization
        
        Args:
            organization_id: UUID of the organization
            
        Returns:
            dict: Statistics including user count, patient count, appointment count, etc.
            
        Raises:
            NotFoundError: If organization not found
        """
        pass
    
    @abstractmethod
    async def get_organization_users(self, organization_id: UUID, filter_dto: Optional[dict] = None) -> List[dict]:
        """
        Get users belonging to an organization
        
        Args:
            organization_id: UUID of the organization
            filter_dto: Optional filters for users
            
        Returns:
            List[dict]: List of users in the organization
            
        Raises:
            NotFoundError: If organization not found
        """
        pass
    
    @abstractmethod
    async def get_organization_doctors(self, organization_id: UUID, filter_dto: Optional[dict] = None) -> List[dict]:
        """
        Get doctors belonging to an organization
        
        Args:
            organization_id: UUID of the organization
            filter_dto: Optional filters for doctors
            
        Returns:
            List[dict]: List of doctors in the organization
            
        Raises:
            NotFoundError: If organization not found
        """
        pass
    
    @abstractmethod
    async def get_organization_patients(self, organization_id: UUID, filter_dto: Optional[dict] = None) -> List[dict]:
        """
        Get patients belonging to an organization
        
        Args:
            organization_id: UUID of the organization
            filter_dto: Optional filters for patients
            
        Returns:
            List[dict]: List of patients in the organization
            
        Raises:
            NotFoundError: If organization not found
        """
        pass
    
    @abstractmethod
    async def update_organization_settings(self, organization_id: UUID, settings: dict) -> 'OrganizationServiceContract.OrganizationResponseDTO':
        """
        Update organization settings and configuration
        
        Args:
            organization_id: UUID of the organization
            settings: Settings data to update
            
        Returns:
            OrganizationResponseDTO: Updated organization
            
        Raises:
            NotFoundError: If organization not found
            ValidationError: If settings data is invalid
        """
        pass
    
    @abstractmethod
    async def get_organization_subscription(self, organization_id: UUID) -> dict:
        """
        Get organization's subscription information
        
        Args:
            organization_id: UUID of the organization
            
        Returns:
            dict: Subscription information including plan, status, expiration
            
        Raises:
            NotFoundError: If organization not found
        """
        pass
    
    @abstractmethod
    async def bulk_import_organizations(self, organizations: List['OrganizationServiceContract.OrganizationCreateDTO']) -> dict:
        """
        Bulk import organizations from external source
        
        Args:
            organizations: List of organization data to import
            
        Returns:
            dict: Import results with success/failure counts
            
        Raises:
            ValidationError: If any organization data is invalid
        """
        pass
    
    @abstractmethod
    async def export_organizations(self, filter_dto: Optional['OrganizationServiceContract.OrganizationFilterDTO'] = None, format: str = "csv") -> str:
        """
        Export organizations data
        
        Args:
            filter_dto: Optional filters for the export
            format: Export format (csv, json, pdf)
            
        Returns:
            str: Exported data as string or file path
            
        Raises:
            ValidationError: If export format is invalid
        """
        pass
    
    @abstractmethod
    async def deactivate_organization(self, organization_id: UUID, reason: Optional[str] = None) -> 'OrganizationServiceContract.OrganizationResponseDTO':
        """
        Deactivate an organization (soft delete)
        
        Args:
            organization_id: UUID of the organization to deactivate
            reason: Optional reason for deactivation
            
        Returns:
            OrganizationResponseDTO: Deactivated organization
            
        Raises:
            NotFoundError: If organization not found
        """
        pass
    
    @abstractmethod
    async def reactivate_organization(self, organization_id: UUID) -> 'OrganizationServiceContract.OrganizationResponseDTO':
        """
        Reactivate a previously deactivated organization
        
        Args:
            organization_id: UUID of the organization to reactivate
            
        Returns:
            OrganizationResponseDTO: Reactivated organization
            
        Raises:
            NotFoundError: If organization not found
        """
        pass