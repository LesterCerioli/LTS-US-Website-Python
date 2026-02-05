import logging
from uuid import UUID, uuid4
from datetime import datetime
from typing import List, Optional, Dict, Any
from venv import logger

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.database import db


class OrganizationService:
    """Organization service implementation with native PostgreSQL queries"""
    
    
    class OrganizationCreateDTO:
        def __init__(
            self,
            name: str,
            address: Optional[str] = None,
            cnpj: Optional[str] = None,
            ein: Optional[str] = None
        ):
            self.name = name
            self.address = address
            self.cnpj = cnpj
            self.ein = ein

    class OrganizationUpdateDTO:
        def __init__(
            self,
            name: Optional[str] = None,
            address: Optional[str] = None,
            cnpj: Optional[str] = None,
            ein: Optional[str] = None
        ):
            self.name = name
            self.address = address
            self.cnpj = cnpj
            self.ein = ein

    class OrganizationResponseDTO:
        def __init__(
            self,
            id: UUID,
            name: str,
            address: str,
            cnpj: str,
            ein: str,
            created_at: datetime,
            updated_at: datetime
        ):
            self.id = id
            self.name = name
            self.address = address
            self.cnpj = cnpj
            self.ein = ein
            self.created_at = created_at
            self.updated_at = updated_at

    class OrganizationDetailDTO:
        def __init__(
            self,
            id: UUID,
            name: str,
            address: str,
            cnpj: str,
            ein: str,
            created_at: datetime,
            updated_at: datetime,
            statistics: Dict[str, Any]
        ):
            self.id = id
            self.name = name
            self.address = address
            self.cnpj = cnpj
            self.ein = ein
            self.created_at = created_at
            self.updated_at = updated_at
            self.statistics = statistics

    class OrganizationFilterDTO:
        def __init__(
            self,
            page: int = 1,
            page_size: int = 100
        ):
            self.page = page
            self.page_size = page_size

    class OrganizationListDTO:
        def __init__(
            self,
            organizations: List['OrganizationService.OrganizationResponseDTO'],
            total_count: int,
            page: int,
            page_size: int,
            total_pages: int
        ):
            self.organizations = organizations
            self.total_count = total_count
            self.page = page
            self.page_size = page_size
            self.total_pages = total_pages

    def __init__(self):
        
        pass

    def create(self, organization: 'OrganizationService.OrganizationCreateDTO') -> 'OrganizationService.OrganizationResponseDTO':
        """
        Create a new organization
        """
        
        if not organization.name or not organization.name.strip():
            raise Exception("Organization name cannot be empty")

        try:
            with db.get_connection() as conn:
                with conn.cursor() as cursor:
                    if organization.cnpj:
                        existing_cnpj_query = """
                            SELECT id FROM public.organizations 
                            WHERE cnpj = %s AND deleted_at IS NULL
                        """
                        cursor.execute(existing_cnpj_query, (organization.cnpj,))
                        if cursor.fetchone():
                            raise Exception(f"Organization with CNPJ {organization.cnpj} already exists")

                    if organization.ein:
                        existing_ein_query = """
                            SELECT id FROM public.organizations 
                            WHERE ein = %s AND deleted_at IS NULL
                        """
                        cursor.execute(existing_ein_query, (organization.ein,))
                        if cursor.fetchone():
                            raise Exception(f"Organization with EIN {organization.ein} already exists")
                    organization_id = uuid4()
                    insert_query = """
                        INSERT INTO public.organizations (
                            id, name, address, cnpj, ein, created_at, updated_at
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s
                        )
                        RETURNING *
                                        
                    """
                    now = datetime.utcnow()
                    cursor.execute(
                        insert_query,
                        (
                            str(organization_id),
                            organization.name,
                            organization.address,
                            organization.cnpj,
                            organization.ein,
                            now,
                            now
                        )
                    )
                    created_org = cursor.fetchone()
                    conn.commit()
                     
                    if not created_org:
                        raise Exception("Failed to create organization")
                    
                    
                    return self._map_to_response_dto(created_org)
        
        except Exception as e:
            logger.error(f"Error creating organization: {e}")
            raise Exception(f"Database error creating organization: {str(e)}")
                                            
    def get_by_id(self, organization_id: UUID) -> 'OrganizationService.OrganizationDetailDTO':
        """
        Get organization by ID
        """
        logger.info(f"Fetching organization by ID: {organization_id}")
    
        try:
            with db.get_connection() as conn:
                with conn.cursor() as cursor:
                    query = """
                        SELECT * FROM public.organizations 
                        WHERE id = %s AND deleted_at IS NULL
                    """
                
                    cursor.execute(query, (str(organization_id),))
                    organization = cursor.fetchone()
                
                    if not organization:
                        logger.warning(f"Organization not found with ID: {organization_id}")
                        raise Exception(f"Organization with ID {organization_id} not found")
                
                    logger.info(f"Organization found: {organization['name']}")
                    return self._map_to_detail_dto(organization)
                
        except Exception as e:
            logger.error(f"Error fetching organization: {e}")
            raise Exception(f"Database error fetching organization: {str(e)}")
           

    def search_organizations(self, query: str, filter_dto: Optional['OrganizationService.OrganizationFilterDTO'] = None) -> 'OrganizationService.OrganizationListDTO':
        """
        Search organizations by multiple criteria
        """
        logger.info(f"Searching organizations with query: {query}")
    
        if not query or not query.strip():
            raise Exception("Search query cannot be empty")
    
        try:
            with db.get_connection() as conn:
                with conn.cursor() as cursor:
                    base_query = """
                        SELECT * FROM public.organizations 
                        WHERE deleted_at IS NULL AND (
                            name ILIKE %s 
                            OR address ILIKE %s 
                            OR cnpj ILIKE %s 
                            OR ein ILIKE %s
                        )
                    """
                    count_query = """
                        SELECT COUNT(*) as total FROM public.organizations 
                        WHERE deleted_at IS NULL AND (
                            name ILIKE %s 
                            OR address ILIKE %s 
                            OR cnpj ILIKE %s 
                            OR ein ILIKE %s
                        )
                    """
                
                    search_param = f"%{query}%"
                    params = [search_param, search_param, search_param, search_param]
                                    
                    cursor.execute(count_query, params)
                    count_result = cursor.fetchone()
                    total_count = count_result['total'] if count_result else 0
                
                    
                    page = filter_dto.page if filter_dto else 1
                    page_size = filter_dto.page_size if filter_dto else 100
                    offset = (page - 1) * page_size
                
                    if filter_dto and filter_dto.page and filter_dto.page_size:
                        base_query += " LIMIT %s OFFSET %s"
                        params.extend([page_size, offset])
                    
                    
                    cursor.execute(base_query, params)
                    organizations = cursor.fetchall()
                
                    organizations_dto = [self._map_to_response_dto(org) for org in organizations]
                    total_pages = (total_count + page_size - 1) // page_size if page_size > 0 else 1
                
                    logger.info(f"Found {len(organizations_dto)} organizations with query: {query}")
                    return self.OrganizationListDTO(
                        organizations=organizations_dto,
                        total_count=total_count,
                        page=page,
                        page_size=page_size,
                        total_pages=total_pages
                    )
                
        except Exception as e:
            logger.error(f"Error searching organizations: {e}")
            raise Exception(f"Database error searching organizations: {str(e)}")
    
    def get_by_name(self, name: str, filter_dto: Optional['OrganizationService.OrganizationFilterDTO'] = None) -> 'OrganizationService.OrganizationListDTO':
        """
        Get organizations by name
        """
        logger.info(f"Fetching organizations by name: {name}")
        
        if not name or not name.strip():
            raise Exception("Organization name cannot be empty")
        try:
            with db.get_connection() as conn:
                with conn.cursor() as cursor:
                    base_query = """
                        SELECT * FROM public.organizations 
                        WHERE name ILIKE %s AND deleted_at IS NULL
                    """
                    
                    count_query = """
                        SELECT COUNT(*) as total FROM public.organizations 
                        WHERE name ILIKE %s AND deleted_at IS NULL
                    """
                    search_param = f"%{name}%"
                    params = [search_param]
                    
                    cursor.execute(count_query, params)
                    count_result = cursor.fetchone()
                    total_count = count_result['total'] if count_result else 0
                    
                    page = filter_dto.page if filter_dto else 1
                    page_size = filter_dto.page_size if filter_dto else 100
                    offset = (page - 1) * page_size
                    
                    if filter_dto and filter_dto.page and filter_dto.page_size:
                        base_query += " LIMIT %s OFFSET %s"
                        params.extend([page_size, offset])
                        
                    cursor.execute(base_query, params)
                    organizations = cursor.fetchall()
                    
                    organizations_dto = [self._map_to_response_dto(org) for org in organizations]
                    total_pages = (total_count + page_size - 1) // page_size if page_size > 0 else 1
                    
                    logger.info(f"Found {len(organizations_dto)} organizations with name: {name}")
                    return self.OrganizationListDTO(
                        organizations=organizations_dto,
                        total_count=total_count,
                        page=page,
                        page_size=page_size,
                        total_pages=total_pages
                    )

        except Exception as e:  
            logger.error(f"Error fetching organizations by name: {e}")
            raise Exception(f"Database error fetching organizations: {str(e)}")
        
    def update(self, organization_id: UUID, organization: 'OrganizationService.OrganizationUpdateDTO') -> 'OrganizationService.OrganizationResponseDTO':
        """
        Update an existing organization
        """
        logger.info(f"Updating organization with ID: {organization_id}")
        
        try:
            with db.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Check if organization exists
                    check_query = """
                        SELECT id FROM public.organizations 
                        WHERE id = %s AND deleted_at IS NULL
                    """
                    cursor.execute(check_query, (str(organization_id),))
                    if not cursor.fetchone():
                        raise Exception(f"Organization with ID {organization_id} not found")

                    update_fields = []
                    params = []
                    
                    
                    if organization.cnpj:
                        conflict_query = """
                            SELECT id FROM public.organizations 
                            WHERE cnpj = %s AND id != %s AND deleted_at IS NULL
                        """
                        cursor.execute(conflict_query, (organization.cnpj, str(organization_id)))
                        if cursor.fetchone():
                            raise Exception(f"Organization with CNPJ {organization.cnpj} already exists")
                        update_fields.append("cnpj = %s")
                        params.append(organization.cnpj)
                    
                    
                    if organization.ein:
                        conflict_query = """
                            SELECT id FROM public.organizations 
                            WHERE ein = %s AND id != %s AND deleted_at IS NULL
                        """
                        cursor.execute(conflict_query, (organization.ein, str(organization_id)))
                        if cursor.fetchone():
                            raise Exception(f"Organization with EIN {organization.ein} already exists")
                        update_fields.append("ein = %s")
                        params.append(organization.ein)
                    
                    
                    if organization.name is not None:
                        update_fields.append("name = %s")
                        params.append(organization.name)
                    
                    if organization.address is not None:
                        update_fields.append("address = %s")
                        params.append(organization.address)
                    
                    if not update_fields:
                        return self.get_by_id(organization_id)
                    
                    update_fields.append("updated_at = %s")
                    params.append(datetime.utcnow())
                                        
                    params.append(str(organization_id))
                    
                    
                    update_query = f"""
                        UPDATE public.organizations 
                        SET {', '.join(update_fields)}
                        WHERE id = %s AND deleted_at IS NULL
                        RETURNING *
                    """
                    
                    cursor.execute(update_query, params)
                    updated_org = cursor.fetchone()
                    conn.commit()
                    
                    if not updated_org:
                        raise Exception(f"Organization with ID {organization_id} not found")
                    
                    logger.info(f"Organization updated successfully: {organization_id}")
                    return self._map_to_response_dto(updated_org)
                    
        except Exception as e:
            logger.error(f"Error updating organization: {e}")
            raise Exception(f"Database error updating organization: {str(e)}")
    
    def delete(self, organization_id: UUID) -> None:
        """
        Delete an organization (soft delete)
        """
        logger.info(f"Deleting organization with ID: {organization_id}")
        
        try:
            with db.get_connection() as conn:
                with conn.cursor() as cursor:
                    
                    check_query = """
                        SELECT id FROM public.organizations 
                        WHERE id = %s AND deleted_at IS NULL
                    """
                    cursor.execute(check_query, (str(organization_id),))
                    if not cursor.fetchone():
                        raise Exception(f"Organization with ID {organization_id} not found")

                    
                    users_query = """
                        SELECT COUNT(*) as count FROM public.users 
                        WHERE organization_id = %s AND deleted_at IS NULL
                    """
                    cursor.execute(users_query, (str(organization_id),))
                    user_count = cursor.fetchone()['count']
                    
                    if user_count > 0:
                        raise Exception("Cannot delete organization with associated users")

                    
                    patients_query = """
                        SELECT COUNT(*) as count FROM public.patients 
                        WHERE organization_id = %s AND deleted_at IS NULL
                    """
                    cursor.execute(patients_query, (str(organization_id),))
                    patient_count = cursor.fetchone()['count']
                    
                    if patient_count > 0:
                        raise Exception("Cannot delete organization with associated patients")

                    
                    delete_query = """
                        UPDATE public.organizations 
                        SET deleted_at = %s 
                        WHERE id = %s AND deleted_at IS NULL
                    """
                    
                    cursor.execute(delete_query, (datetime.utcnow(), str(organization_id)))
                    
                    if cursor.rowcount == 0:
                        raise Exception(f"Organization with ID {organization_id} not found")
                    
                    conn.commit()
                    logger.info(f"Organization deleted successfully: {organization_id}")
                    
        except Exception as e:
            logger.error(f"Error deleting organization: {e}")
            raise Exception(f"Database error deleting organization: {str(e)}")  
    
    def get_by_cnpj(self, cnpj: str) -> 'OrganizationService.OrganizationResponseDTO':
        """
        Get organization by CNPJ
        """
        logger.info(f"Fetching organization by CNPJ: {cnpj}")
        if not cnpj or not cnpj.strip():
            raise Exception("CNPJ cannot be empty")
        try:
            with db.get_connection() as conn:
                with conn.cursor() as cursor:
                    query = """
                        SELECT * FROM public.organizations 
                        WHERE cnpj = %s AND deleted_at IS NULL
                    """
                    cursor.execute(query, (cnpj,))
                    organization = cursor.fetchone()
                    
                    if not organization:
                        logger.warning(f"Organization not found with CNPJ: {cnpj}")
                        raise Exception(f"Organization with CNPJ {cnpj} not found")
                    
                    logger.info(f"Organization found: {organization['name']}")
                    return self._map_to_response_dto(organization)
        except Exception as e:
            logger.error(f"Error fetching organization by CNPJ: {e}")
            raise Exception(f"Database error fetching organization: {str(e)}")
      
    def get_by_ein(self, ein: str) -> 'OrganizationService.OrganizationResponseDTO':
        """
        Get organization by EIN
        """
        logger.info(f"Fetching organization by EIN: {ein}")
        
        if not ein or not ein.strip():
            raise Exception("EIN cannot be empty")
        
        try:
            with db.get_connection() as conn:
                with conn.cursor() as cursor:
                    query = """
                        SELECT * FROM public.organizations 
                        WHERE ein = %s AND deleted_at IS NULL
                    """
                    cursor.execute(query, (ein,))
                    organization = cursor.fetchone()
                    
                    if not organization:
                        logger.warning(f"Organization not found with EIN: {ein}")
                        raise Exception(f"Organization with EIN {ein} not found")
                    
                    logger.info(f"Organization found: {organization['name']}")
                    return self._map_to_response_dto(organization)
        except Exception as e:
            logger.error(f"Error fetching organization by EIN: {e}")
            raise Exception(f"Database error fetching organization: {str(e)}")
        
    def search_organizations(self, query: str, filter_dto: Optional['OrganizationService.OrganizationFilterDTO'] = None) -> 'OrganizationService.OrganizationListDTO':
        """
        Search organizations by multiple criteria
        """
        logger.info(f"Searching organizations with query: {query}")
        
        if not query or not query.strip():
            raise Exception("Search query cannot be empty")
        try:
            with db.get_connection() as conn:
                with conn.cursor() as cursor:
                    base_query = """
                        SELECT * FROM public.organizations 
                        WHERE deleted_at IS NULL AND (
                            name ILIKE %s 
                            OR address ILIKE %s 
                            OR cnpj ILIKE %s 
                            OR ein ILIKE %s
                        )
                    """
                    count_query = """
                        SELECT COUNT(*) as total FROM public.organizations 
                         WHERE deleted_at IS NULL AND (
                             name ILIKE %s 
                            OR address ILIKE %s 
                            OR cnpj ILIKE %s 
                            OR ein ILIKE %s
                         )
                    """
                    search_param = f"%{query}%"
                    params = [search_param, search_param, search_param, search_param]
                    
                    cursor.execute(count_query, params)
                    count_result = cursor.fetchone()
                    total_count = count_result['total'] if count_result else 0
                    
                    page = filter_dto.page if filter_dto else 1
                    page_size = filter_dto.page_size if filter_dto else 100
                    offset = (page - 1) * page_size
                    
                    if filter_dto and filter_dto.page and filter_dto.page_size:
                        base_query += " LIMIT %s OFFSET %s"
                        params.extend([page_size, offset])
                        
                    cursor.execute(base_query, params)
                    organizations = cursor.fetchall()
                    
                    organizations_dto = [self._map_to_response_dto(org) for org in organizations]
                    total_pages = (total_count + page_size - 1) // page_size if page_size > 0 else 1
                    
                    logger.info(f"Found {len(organizations_dto)} organizations with query: {query}")
                    return self.OrganizationListDTO(
                        organizations=organizations_dto,
                        total_count=total_count,
                        page=page,
                        page_size=page_size,
                        total_pages=total_pages
                    )
                    
        except Exception as e:
            logger.error(f"Error searching organizations: {e}")
            raise Exception(f"Database error searching organizations: {str(e)}")

    def validate_cnpj(self, cnpj: str) -> dict:
        """
        Validate CNPJ format and check if it's available
        """
        logger.info(f"Validating CNPJ: {cnpj}")
        
        if not cnpj or not cnpj.strip():
            raise Exception("CNPJ cannot be empty")

        try:
            with db.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Clean CNPJ
                    cleaned_cnpj = ''.join(filter(str.isdigit, cnpj))
                    if len(cleaned_cnpj) != 14:
                        raise Exception("CNPJ must have 14 digits")

                    
                    existing_query = """
                        SELECT id FROM public.organizations 
                        WHERE cnpj = %s AND deleted_at IS NULL
                    """
                    cursor.execute(existing_query, (cnpj,))
                    is_available = not cursor.fetchone()

                    return {
                        "cnpj": cnpj,
                        "is_valid_format": True,
                        "is_available": is_available,
                        "cleaned_cnpj": cleaned_cnpj
                    }
                    
        except Exception as e:
            logger.error(f"Error validating CNPJ: {e}")
            raise Exception(f"Database error validating CNPJ: {str(e)}")

    def validate_ein(self, ein: str) -> dict:
        """
        Validate EIN format and check if it's available
        """
        logger.info(f"Validating EIN: {ein}")
        
        if not ein or not ein.strip():
            raise Exception("EIN cannot be empty")

        try:
            with db.get_connection() as conn:
                with conn.cursor() as cursor:
                    
                    cleaned_ein = ''.join(filter(str.isdigit, ein))
                    if len(cleaned_ein) != 9:
                        raise Exception("EIN must have 9 digits")

                    
                    existing_query = """
                        SELECT id FROM public.organizations 
                        WHERE ein = %s AND deleted_at IS NULL
                    """
                    cursor.execute(existing_query, (ein,))
                    is_available = not cursor.fetchone()

                    return {
                        "ein": ein,
                        "is_valid_format": True,
                        "is_available": is_available,
                        "cleaned_ein": cleaned_ein
                    }
                    
        except Exception as e:
            logger.error(f"Error validating EIN: {e}")
            raise Exception(f"Database error validating EIN: {str(e)}")

    def deactivate_organization(self, organization_id: UUID, reason: Optional[str] = None) -> 'OrganizationService.OrganizationResponseDTO':
        """
        Deactivate an organization (soft delete)
        """
        logger.info(f"Deactivating organization with ID: {organization_id}")
        
        try:
            with db.get_connection() as conn:
                with conn.cursor() as cursor:
                    
                    check_query = """
                        SELECT id FROM public.organizations 
                        WHERE id = %s AND deleted_at IS NULL
                    """
                    cursor.execute(check_query, (str(organization_id),))
                    if not cursor.fetchone():
                        raise Exception(f"Organization with ID {organization_id} not found")

                    
                    deactivate_query = """
                        UPDATE public.organizations 
                        SET deleted_at = %s 
                        WHERE id = %s AND deleted_at IS NULL
                        RETURNING *
                    """
                    
                    cursor.execute(deactivate_query, (datetime.utcnow(), str(organization_id)))
                    deactivated_org = cursor.fetchone()
                    conn.commit()
                    
                    if not deactivated_org:
                        raise Exception(f"Organization with ID {organization_id} not found")
                    
                    logger.info(f"Organization deactivated successfully: {organization_id}")
                    return self._map_to_response_dto(deactivated_org)
                    
        except Exception as e:
            logger.error(f"Error deactivating organization: {e}")
            raise Exception(f"Database error deactivating organization: {str(e)}")

    def reactivate_organization(self, organization_id: UUID) -> 'OrganizationService.OrganizationResponseDTO':
        """
        Reactivate a previously deactivated organization
        """
        logger.info(f"Reactivating organization with ID: {organization_id}")
        
        try:
            with db.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Check if organization exists
                    check_query = "SELECT * FROM public.organizations WHERE id = %s"
                    cursor.execute(check_query, (str(organization_id),))
                    organization = cursor.fetchone()
                    
                    if not organization:
                        raise Exception(f"Organization with ID {organization_id} not found")

                    
                    reactivate_query = """
                        UPDATE public.organizations 
                        SET deleted_at = NULL, updated_at = %s
                        WHERE id = %s
                        RETURNING *
                    """
                    
                    cursor.execute(reactivate_query, (datetime.utcnow(), str(organization_id)))
                    reactivated_org = cursor.fetchone()
                    conn.commit()
                    
                    if not reactivated_org:
                        raise Exception(f"Organization with ID {organization_id} not found")
                    
                    logger.info(f"Organization reactivated successfully: {organization_id}")
                    return self._map_to_response_dto(reactivated_org)
                    
        except Exception as e:
            logger.error(f"Error reactivating organization: {e}")
            raise Exception(f"Database error reactivating organization: {str(e)}")

    def get_organization_statistics(self, organization_id: UUID) -> dict:
        """Get statistics for an organization"""
        logger.info(f"Fetching statistics for organization: {organization_id}")
        
        try:
            with db.get_connection() as conn:
                with conn.cursor() as cursor:
                    
                    user_query = """
                        SELECT COUNT(*) as count FROM public.users 
                        WHERE organization_id = %s AND deleted_at IS NULL
                    """
                    cursor.execute(user_query, (str(organization_id),))
                    user_count = cursor.fetchone()['count']

                    
                    doctor_query = """
                        SELECT COUNT(*) as count FROM public.doctors 
                        WHERE organization_id = %s AND deleted_at IS NULL
                    """
                    cursor.execute(doctor_query, (str(organization_id),))
                    doctor_count = cursor.fetchone()['count']

                    
                    patient_query = """
                        SELECT COUNT(*) as count FROM public.patients 
                        WHERE organization_id = %s AND deleted_at IS NULL
                    """
                    cursor.execute(patient_query, (str(organization_id),))
                    patient_count = cursor.fetchone()['count']

                    
                    appointment_query = """
                        SELECT COUNT(*) as count FROM public.appointments 
                        WHERE organization_id = %s AND deleted_at IS NULL
                    """
                    cursor.execute(appointment_query, (str(organization_id),))
                    appointment_count = cursor.fetchone()['count']

                    return {
                        "user_count": user_count,
                        "doctor_count": doctor_count,
                        "patient_count": patient_count,
                        "appointment_count": appointment_count
                    }
                    
        except Exception as e:
            logger.error(f"Error fetching organization statistics: {e}")
            raise Exception(f"Database error fetching statistics: {str(e)}")

    def get_all_organizations(self, filter_dto: Optional['OrganizationService.OrganizationFilterDTO'] = None) -> 'OrganizationService.OrganizationListDTO':
        """
        Get all organizations with pagination - optimized for high performance
        
        """
        logger.info(f"Fetching all organizations with pagination - page: {filter_dto.page if filter_dto else 1}, page_size: {filter_dto.page_size if filter_dto else 100}")
        try:
            
            with db.get_connection() as conn:
                with conn.cursor() as cursor:
                    base_query = """
                        SELECT * FROM public.organizations 
                        WHERE deleted_at IS NULL
                        ORDER BY created_at DESC, id
                    """
                    count_query= """
                        SELECT COUNT(*) as total FROM public.organizations 
                        WHERE deleted_at IS NULL
                    """
                    
                    cursor.execute(count_query)
                    count_result = cursor.fetchone()
                    total_count = count_result['total'] if count_result else 0
                    
                    page = filter_dto.page if filter_dto else 1
                    page_size = filter_dto.page_size if filter_dto else 100
                    offset = (page - 1) * page_size
                    
                    paginated_query = base_query + " LIMIT %s OFFSET %s"
                    logger.info(f"Executing pagonated query with limit={page_size}, offset={offset}")
                    
                    cursor.execute(paginated_query, (page_size, offset))
                    organizations = cursor.fetchall()
                    organizations_dto = [self._map_to_response_dto(org) for org in organizations]
                    total_pages = (total_count + page_size - 1) // page_size if page_size > 0 else 1
                
                    logger.info(f"Successfully fetched {len(organizations_dto)} organizations (page {page} of {total_pages}, total: {total_count})")
                    
                    return self.OrganizationListDTO(
                        organizations=organizations_dto,
                        total_count=total_count,
                        page=page,
                        page_size=page_size,
                        total_pages=total_pages
                    )
                    

        except Exception as e:
            logger.error(f"Error fetching all organizations: {e}")
            raise Exception(f"Database error fetching organizations: {str(e)}")
    
    def _map_to_response_dto(self, db_result) -> 'OrganizationService.OrganizationResponseDTO':
        """Map database result to OrganizationResponseDTO"""
        logger.debug("Mapping database result to response DTO")
        return self.OrganizationResponseDTO(
            id=UUID(db_result['id']),
            name=db_result['name'],
            address=db_result['address'],
            cnpj=db_result['cnpj'],
            ein=db_result['ein'],
            created_at=db_result['created_at'],
            updated_at=db_result['updated_at']
        )

    def _map_to_detail_dto(self, db_result) -> 'OrganizationService.OrganizationDetailDTO':
        """Map database result to OrganizationDetailDTO"""
        logger.debug("Mapping database result to detail DTO")
        base_data = self._map_to_response_dto(db_result)
                
        stats = self.get_organization_statistics(base_data.id)
        
        return self.OrganizationDetailDTO(
            id=base_data.id,
            name=base_data.name,
            address=base_data.address,
            cnpj=base_data.cnpj,
            ein=base_data.ein,
            created_at=base_data.created_at,
            updated_at=base_data.updated_at,
            statistics=stats
        )


organization_service = OrganizationService()