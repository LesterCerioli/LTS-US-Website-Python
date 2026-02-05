from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid
from app.database import db

class CredentialService:
    def __init__(self):
        self.db = db
    
    def _get_organization_id_by_name(self, organization_name: str) -> Optional[str]:
        """Gets organization ID by name using the same logic as UserService"""
        try:
            print(f"DEBUG: Searching for organization: '{organization_name}'")
            
            
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT id FROM public.organizations WHERE name = %s AND deleted_at IS NULL",
                        (organization_name,)
                    )
                    result = cursor.fetchone()
                    
                    if result:
                        print(f"DEBUG: Exact match found - ID: {result['id']}, Name: '{organization_name}'")
                        return result['id']
                    
                    
                    cursor.execute(
                        "SELECT id, name FROM public.organizations WHERE LOWER(TRIM(name)) = LOWER(TRIM(%s)) AND deleted_at IS NULL",
                        (organization_name,)
                    )
                    result = cursor.fetchone()
                    
                    if result:
                        print(f"DEBUG: Case-insensitive match found - ID: {result['id']}, Name in DB: '{result['name']}'")
                        return result['id']
                    
                    
                    cursor.execute("SELECT id, name FROM public.organizations WHERE deleted_at IS NULL")
                    all_orgs = cursor.fetchall()
                    print(f"DEBUG: Available organizations: {[dict(org) for org in all_orgs]}")
                    
                    return None
                        
        except Exception as e:
            print(f"Error fetching organization: {e}")
            return None
    
    def _organization_exists(self, organization_name: str) -> bool:
        """Checks if an organization exists"""
        return self.db.organization_exists(organization_name)
    
    def _get_all_organizations(self) -> List[Dict[str, Any]]:
        """Get all organizations for debugging"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT id, name FROM public.organizations WHERE deleted_at IS NULL")
                    results = cursor.fetchall()
                    org_list = [dict(result) for result in results]
                    print(f"DEBUG: All organizations in DB: {org_list}")
                    return org_list
        except Exception as e:
            print(f"Error fetching organizations: {e}")
            return []
    
    def create_credential(self, 
                         organization_name: str,
                         type: str, 
                         email: str, 
                         password: str, 
                         description: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Create a new credential
        
        Args:
            organization_name: Organization name
            type: Credential type ('Identifier' or 'Other')
            email: Email/login
            password: Password
            description: Optional description
            
        Returns:
            Dictionary with created credential data or None on error
        """
        try:
            print(f"DEBUG: Creating credential for organization: '{organization_name}'")
            print(f"DEBUG: Credential details - Type: {type}, Email: {email}")
            
            
            if type not in ['Identifier', 'Other']:
                error_msg = f"Invalid credential type: {type}. Must be 'Identifier' or 'Other'"
                print(f"VALIDATION ERROR: {error_msg}")
                raise ValueError(error_msg)
            
            
            org_id = self._get_organization_id_by_name(organization_name)
            
            if not org_id:
                all_orgs = self._get_all_organizations()
                org_names = [org['name'] for org in all_orgs]
                error_msg = f"Organization '{organization_name}' not found. Available organizations: {org_names}"
                print(f"VALIDATION ERROR: {error_msg}")
                raise ValueError(error_msg)
            
            print(f"DEBUG: Organization ID found: {org_id}")
            
            
            email_check = self.validate_email(organization_name, email)
            if not email_check.get('is_available', True):
                error_msg = f"Email '{email}' already exists in organization '{organization_name}'"
                print(f"VALIDATION ERROR: {error_msg}")
                raise ValueError(error_msg)
            
            
            credential_id = str(uuid.uuid4())
            
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        INSERT INTO public.credentials (
                            id, organization_id, type, email, password, description, 
                            created_at, updated_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                        RETURNING 
                            id, organization_id, type, email, password, description,
                            created_at, updated_at
                    ''', (
                        credential_id, 
                        org_id,
                        type, 
                        email, 
                        password, 
                        description
                    ))
                    
                    result = cursor.fetchone()
                    conn.commit()
                    
                    if result:
                        result_dict = dict(result)
                        print(f"SUCCESS: Credential created for email: {email} in organization: {organization_name}")
                        print(f"DEBUG: Created credential: {result_dict}")
                        return result_dict
                    
                    print("DEBUG: Credential creation failed - no result returned")
                    return None
                    
        except ValueError as e:
            print(f"VALIDATION ERROR creating credential: {e}")
            return None
        except Exception as e:
            print(f"ERROR creating credential: {e}", exc_info=True)
            return None
    
    def get_credential_by_id(self, credential_id: str, organization_name: str) -> Optional[Dict[str, Any]]:
        """
        Get credential by ID with organization validation
        
        Args:
            credential_id: Credential UUID
            organization_name: Organization name
            
        Returns:
            Dictionary with credential data or None if not found
        """
        try:
            print(f"DEBUG: Getting credential {credential_id} for organization: '{organization_name}'")
            
            
            org_id = self._get_organization_id_by_name(organization_name)
            if not org_id:
                print(f"DEBUG: Organization '{organization_name}' not found")
                return None
            
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        SELECT 
                            c.id, c.organization_id, c.type, c.email, c.password, c.description,
                            c.created_at, c.updated_at,
                            o.name as organization_name
                        FROM public.credentials c
                        LEFT JOIN public.organizations o ON c.organization_id = o.id
                        WHERE c.id = %s AND c.organization_id = %s
                    ''', (credential_id, org_id))
                    
                    result = cursor.fetchone()
                    
                    if result:
                        result_dict = dict(result)
                        print(f"DEBUG: Found credential: {result_dict}")
                        return result_dict
                    
                    print(f"DEBUG: Credential {credential_id} not found in organization {organization_name}")
                    return None
                    
        except Exception as e:
            print(f"ERROR getting credential by ID: {e}")
            return None
    
    def get_all_credentials(self, 
                           organization_name: str,
                           limit: int = 100, 
                           offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get all credentials for an organization with pagination
        
        Args:
            organization_name: Organization name
            limit: Limit per page
            offset: Offset for pagination
            
        Returns:
            List of credential dictionaries
        """
        try:
            print(f"DEBUG: Getting all credentials for organization: '{organization_name}'")
            
            
            org_id = self._get_organization_id_by_name(organization_name)
            if not org_id:
                print(f"DEBUG: Organization '{organization_name}' not found")
                return []
            
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        SELECT 
                            c.id, c.organization_id, c.type, c.email, c.password, c.description,
                            c.created_at, c.updated_at,
                            o.name as organization_name
                        FROM public.credentials c
                        LEFT JOIN public.organizations o ON c.organization_id = o.id
                        WHERE c.organization_id = %s
                        ORDER BY c.created_at DESC
                        LIMIT %s OFFSET %s
                    ''', (org_id, limit, offset))
                    
                    results = cursor.fetchall()
                    credentials = [dict(row) for row in results]
                    
                    print(f"DEBUG: Found {len(credentials)} credentials for organization '{organization_name}'")
                    return credentials
                    
        except Exception as e:
            print(f"ERROR getting all credentials: {e}")
            return []
    
    def update_credential(self, 
                         credential_id: str, 
                         organization_name: str,
                         updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Update a credential
        
        Args:
            credential_id: Credential UUID
            organization_name: Organization name
            updates: Dictionary with fields to update
            
        Returns:
            Dictionary with updated credential data or None if not found
        """
        try:
            print(f"DEBUG: Updating credential {credential_id} for organization: '{organization_name}'")
            print(f"DEBUG: Update data: {updates}")
            
            
            org_id = self._get_organization_id_by_name(organization_name)
            if not org_id:
                print(f"DEBUG: Organization '{organization_name}' not found")
                return None
            
            
            if 'type' in updates and updates['type'] not in ['Identifier', 'Other']:
                error_msg = f"Invalid credential type: {updates['type']}. Must be 'Identifier' or 'Other'"
                print(f"VALIDATION ERROR: {error_msg}")
                raise ValueError(error_msg)
            
            
            if 'email' in updates:
                email_check = self.validate_email(organization_name, updates['email'])
                if not email_check.get('is_available', True):
                    
                    existing = self.get_credential_by_id(credential_id, organization_name)
                    if not existing or existing['email'] != updates['email']:
                        error_msg = f"Email '{updates['email']}' already exists in organization '{organization_name}'"
                        print(f"VALIDATION ERROR: {error_msg}")
                        raise ValueError(error_msg)
            
            
            set_clauses = []
            params = []
            
            allowed_fields = ['type', 'email', 'password', 'description']
            
            for field, value in updates.items():
                if field in allowed_fields:
                    set_clauses.append(f"{field} = %s")
                    params.append(value)
            
            if not set_clauses:
                print("DEBUG: No valid fields to update")
                return None
            
            set_clauses.append("updated_at = CURRENT_TIMESTAMP")
            params.extend([credential_id, org_id])
            
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(f'''
                        UPDATE public.credentials 
                        SET {', '.join(set_clauses)}
                        WHERE id = %s AND organization_id = %s
                        RETURNING 
                            id, organization_id, type, email, password, description,
                            created_at, updated_at
                    ''', params)
                    
                    result = cursor.fetchone()
                    conn.commit()
                    
                    if result:
                        result_dict = dict(result)
                        print(f"SUCCESS: Credential {credential_id} updated")
                        print(f"DEBUG: Updated credential: {result_dict}")
                        return result_dict
                    
                    print(f"DEBUG: Credential {credential_id} not found or not updated")
                    return None
                    
        except ValueError as e:
            print(f"VALIDATION ERROR updating credential: {e}")
            return None
        except Exception as e:
            print(f"ERROR updating credential: {e}")
            return None
    
    def delete_credential(self, credential_id: str, organization_name: str) -> bool:
        """
        Delete a credential
        
        Args:
            credential_id: Credential UUID
            organization_name: Organization name
            
        Returns:
            True if deleted, False otherwise
        """
        try:
            print(f"DEBUG: Deleting credential {credential_id} from organization: '{organization_name}'")
            
            
            org_id = self._get_organization_id_by_name(organization_name)
            if not org_id:
                print(f"DEBUG: Organization '{organization_name}' not found")
                return False
            
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        DELETE FROM public.credentials 
                        WHERE id = %s AND organization_id = %s
                        RETURNING id
                    ''', (credential_id, org_id))
                    
                    result = cursor.fetchone()
                    conn.commit()
                    
                    if result:
                        print(f"SUCCESS: Credential {credential_id} deleted from organization: {organization_name}")
                        return True
                    
                    print(f"DEBUG: Credential {credential_id} not found in organization {organization_name}")
                    return False
                    
        except Exception as e:
            print(f"ERROR deleting credential: {e}")
            return False
    
    def search_credentials(self, 
                          organization_name: str,
                          search_term: str, 
                          limit: int = 50, 
                          offset: int = 0) -> Dict[str, Any]:
        """
        Search credentials by email or description within an organization
        
        Args:
            organization_name: Organization name
            search_term: Search term
            limit: Limit per page
            offset: Offset for pagination
            
        Returns:
            Dictionary with search results
        """
        try:
            print(f"DEBUG: Searching credentials in organization '{organization_name}' for: '{search_term}'")
            
            
            org_id = self._get_organization_id_by_name(organization_name)
            if not org_id:
                error_msg = f"Organization '{organization_name}' not found"
                print(f"DEBUG: {error_msg}")
                return {
                    'results': [],
                    'total_count': 0,
                    'search_term': search_term,
                    'organization_name': organization_name,
                    'error': error_msg
                }
            
            search_pattern = f"%{search_term}%"
            
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        SELECT 
                            c.id, c.organization_id, c.type, c.email, c.password, c.description,
                            c.created_at, c.updated_at,
                            o.name as organization_name
                        FROM public.credentials c
                        LEFT JOIN public.organizations o ON c.organization_id = o.id
                        WHERE c.organization_id = %s 
                          AND (c.email ILIKE %s OR c.description ILIKE %s)
                        ORDER BY c.created_at DESC
                        LIMIT %s OFFSET %s
                    ''', (org_id, search_pattern, search_pattern, limit, offset))
                    
                    results = cursor.fetchall()
                    
                    cursor.execute('''
                        SELECT COUNT(*) as total
                        FROM public.credentials 
                        WHERE organization_id = %s 
                          AND (email ILIKE %s OR description ILIKE %s)
                    ''', (org_id, search_pattern, search_pattern))
                    
                    total_result = cursor.fetchone()
                    total_count = total_result['total'] if total_result else 0
                    
                    response = {
                        'results': [dict(row) for row in results],
                        'total_count': total_count,
                        'search_term': search_term,
                        'organization_name': organization_name,
                        'limit': limit,
                        'offset': offset
                    }
                    
                    print(f"DEBUG: Found {total_count} results for search term '{search_term}'")
                    return response
                    
        except Exception as e:
            print(f"ERROR searching credentials: {e}")
            return {
                'results': [],
                'total_count': 0,
                'search_term': search_term,
                'organization_name': organization_name,
                'limit': limit,
                'offset': offset,
                'error': str(e)
            }
    
    def validate_email(self, organization_name: str, email: str) -> Dict[str, Any]:
        """
        Validate email availability within an organization
        
        Args:
            organization_name: Organization name
            email: Email to validate
            
        Returns:
            Dictionary with validation results
        """
        try:
            print(f"DEBUG: Validating email '{email}' in organization '{organization_name}'")
            
            
            org_id = self._get_organization_id_by_name(organization_name)
            if not org_id:
                error_msg = f"Organization '{organization_name}' not found"
                print(f"DEBUG: {error_msg}")
                return {
                    'email': email,
                    'is_available': False,
                    'exists': False,
                    'organization_name': organization_name,
                    'error': error_msg
                }
            
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        SELECT EXISTS (
                            SELECT 1 FROM public.credentials 
                            WHERE organization_id = %s AND email = %s
                        ) as exists
                    ''', (org_id, email))
                    
                    result = cursor.fetchone()
                    
                    response = {
                        'email': email,
                        'is_available': not result['exists'],
                        'exists': result['exists'],
                        'organization_name': organization_name,
                        'message': f"Email '{email}' is {'not available' if result['exists'] else 'available'} in organization '{organization_name}'"
                    }
                    
                    print(f"DEBUG: Email validation result: {response}")
                    return response
                    
        except Exception as e:
            print(f"ERROR validating email: {e}")
            return {
                'email': email,
                'is_available': False,
                'exists': False,
                'organization_name': organization_name,
                'error': str(e)
            }
    
    def get_credential_stats(self, organization_name: str) -> Dict[str, Any]:
        """
        Get credential statistics for an organization
        
        Args:
            organization_name: Organization name
            
        Returns:
            Dictionary with statistics
        """
        try:
            print(f"DEBUG: Getting credential stats for organization: '{organization_name}'")
            
            
            org_id = self._get_organization_id_by_name(organization_name)
            if not org_id:
                error_msg = f"Organization '{organization_name}' not found"
                print(f"DEBUG: {error_msg}")
                return {
                    'organization_name': organization_name,
                    'error': error_msg,
                    'total_credentials': 0,
                    'by_type': {}
                }
            
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        SELECT 
                            COUNT(*) as total_credentials,
                            COUNT(DISTINCT type) as distinct_types,
                            COUNT(DISTINCT email) as distinct_emails,
                            MIN(created_at) as oldest_credential,
                            MAX(created_at) as newest_credential
                        FROM public.credentials
                        WHERE organization_id = %s
                    ''', (org_id,))
                    
                    stats_result = cursor.fetchone()
                    
                    cursor.execute('''
                        SELECT 
                            type,
                            COUNT(*) as count
                        FROM public.credentials 
                        WHERE organization_id = %s
                        GROUP BY type
                        ORDER BY count DESC
                    ''', (org_id,))
                    
                    type_results = cursor.fetchall()
                    
                    response = {
                        'organization_name': organization_name,
                        'total_credentials': stats_result['total_credentials'] if stats_result else 0,
                        'distinct_types': stats_result['distinct_types'] if stats_result else 0,
                        'distinct_emails': stats_result['distinct_emails'] if stats_result else 0,
                        'oldest_credential': stats_result['oldest_credential'],
                        'newest_credential': stats_result['newest_credential'],
                        'by_type': {row['type']: row['count'] for row in type_results}
                    }
                    
                    print(f"DEBUG: Credential stats: {response}")
                    return response
                    
        except Exception as e:
            print(f"ERROR getting credential stats: {e}")
            return {
                'organization_name': organization_name,
                'error': str(e),
                'total_credentials': 0,
                'by_type': {}
            }


credential_service = CredentialService()