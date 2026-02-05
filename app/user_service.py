import bcrypt
from typing import Optional, Dict, Any, List
from app.database import db

class UserService:
    def hash_password(self, password: str) -> str:
        """Generates a secure hash for the password using bcrypt"""
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed_password.decode('utf-8')
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verifies if plain password matches the bcrypt hash"""
        try:
            return bcrypt.checkpw(
                plain_password.encode('utf-8'),
                hashed_password.encode('utf-8')
            )
        except (ValueError, TypeError):
            return False
    
    def get_organization_id_by_name(self, organization_name: str) -> Optional[str]:
        """Gets organization ID by name (case-insensitive with debug)"""
        print(f"DEBUG: Searching for organization name: '{organization_name}'")
        return db.get_organization_id(organization_name)
    
    def get_organization_id_exact(self, organization_name: str) -> Optional[str]:
        """Exact match for organization name (including spaces)"""
        try:
            print(f"DEBUG: Exact search for: '{organization_name}'")
            with db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT id FROM public.organizations WHERE name = %s",
                        (organization_name,)
                    )
                    result = cursor.fetchone()
                    print(f"DEBUG: Exact match result: {result}")
                    return result['id'] if result else None
        except Exception as e:
            print(f"Error fetching organization (exact): {e}")
            return None
    
    def get_organization_id_trim(self, organization_name: str) -> Optional[str]:
        """Trimmed match for organization name"""
        try:
            print(f"DEBUG: Trimmed search for: '{organization_name}'")
            with db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT id FROM public.organizations WHERE TRIM(name) = TRIM(%s)",
                        (organization_name,)
                    )
                    result = cursor.fetchone()
                    print(f"DEBUG: Trimmed match result: {result}")
                    return result['id'] if result else None
        except Exception as e:
            print(f"Error fetching organization (trim): {e}")
            return None
    
    def get_all_organizations(self) -> List[Dict[str, Any]]:
        """Get all organizations for debugging"""
        try:
            with db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT id, name FROM public.organizations")
                    results = cursor.fetchall()
                    org_list = [dict(result) for result in results]
                    print(f"DEBUG: All organizations in DB: {org_list}")
                    return org_list
        except Exception as e:
            print(f"Error fetching organizations: {e}")
            return []
    
    def organization_exists(self, organization_name: str) -> bool:
        """Checks if organization exists"""
        return db.organization_exists(organization_name)
    
    def authenticate_user(self, email: str, password: str, organization_name: str) -> Optional[Dict[str, Any]]:
        """Authenticates user by verifying password against stored hash"""
        try:
            print(f"DEBUG: Authenticating user for org: '{organization_name}'")
                        
            if not self.organization_exists(organization_name):
                print(f"DEBUG: Organization '{organization_name}' does not exist")
                return None
            
            org_id = self.get_organization_id_by_name(organization_name)
            if not org_id:
                print(f"DEBUG: Could not get ID for organization '{organization_name}'")
                return None
            
            print(f"DEBUG: Organization ID found: {org_id}")
            
            user_data = db.get_user_by_email_and_org(email, org_id)
            if not user_data:
                print(f"DEBUG: User with email '{email}' not found in organization {org_id}")
                return None
            
            if not self.verify_password(password, user_data['password']):
                print("DEBUG: Password verification failed")
                return None
            
            user_data.pop('password', None)
            print("DEBUG: Authentication successful")
            return user_data
                    
        except Exception as e:
            print(f"Authentication error: {e}")
            return None
        
    def authenticate_user_by_role(self, email: str, password: str, role: str) -> Optional[Dict[str, Any]]:
        """Authenticates user by verifying password and role against stored data"""
        try:
            print(f"DEBUG: Authenticating user: {email} with role: {role}")
            user_data = self.get_user_by_email(email)
            if not user_data:
                print(f"DEBUG: User with email '{email}' not found")
                return None
            if user_data['role'] != role:
                print(f"DEBUG: Role mismatch. Expected: {role}, Found: {user_data['role']}")
                return None
            if not self.verify_password(password, user_data['password']):
                print("DEBUG: Password verification failed")
                return None
            user_data.pop('password', None)
            user_data.pop('organization_id', None)
            print("DEBUG: Authentication successful by role")
            return user_data
        except Exception as e:
            print(f"Authentication error: {e}")
            return None
        
    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Finds user by email across all organizations"""
        try:
            with db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute('''
                                   SELECT id, name, email, password, role, organization_id, created_at
                                   FROM public.users 
                                   WHERE email = %s AND deleted_at IS NULL
                    ''', (email,))
                    result = cursor.fetchone()
                    return dict(result) if result else None
        except Exception as e:
            print(f"Error fetching user by email: {e}")
            return None
             
    
    def create_user(self, name: str, email: str, password: str, 
                   role: str, organization_name: str) -> Optional[Dict[str, Any]]:
        """Creates a new user with organization validation"""
        try:
            print(f"DEBUG: Creating user for organization: '{organization_name}'")
            print(f"DEBUG: User details - Name: {name}, Email: {email}, Role: {role}")
                        
            all_orgs = self.get_all_organizations()
                        
            org_id = self.get_organization_id_exact(organization_name)
            if not org_id:
                org_id = self.get_organization_id_trim(organization_name)
            if not org_id:
                org_id = self.get_organization_id_by_name(organization_name)
            
            print(f"DEBUG: Final organization ID found: {org_id}")
            
            if not org_id:
                org_names = [org['name'] for org in all_orgs]
                error_msg = f"Organization '{organization_name}' not found. Available organizations: {org_names}"
                print(f"VALIDATION ERROR: {error_msg}")
                raise ValueError(error_msg)
            
            hashed_password = self.hash_password(password)
            print("DEBUG: Password hashed successfully")
                        
            user_data = {
                'name': name,
                'email': email,
                'password': hashed_password,
                'role': role,
                'organization_id': org_id
            }
            
            print(f"DEBUG: Attempting to create user with data: {user_data}")
            result = db.create_user(user_data)
            
            if result:
                print(f"DEBUG: User created successfully: {result}")
                
                result.pop('password', None)
                result.pop('organization_id', None)
            else:
                print("DEBUG: User creation failed - possibly duplicate email")
            
            return result
            
        except ValueError as e:
            print(f"VALIDATION ERROR: {e}")
            return None
        except Exception as e:
            print(f"ERROR creating user: {e}")
            return None

    

    def reset_password_by_email(self, email: str, new_password: str) -> bool:
        """Logic to update the database"""
        try:
            
            user_data = self.get_user_by_email(email)
            if not user_data:
                return False

            
            from app.user_service import user_service 
            hashed_password = user_service.hash_password(new_password)

            
            with db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        UPDATE public.users 
                        SET password = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE email = %s AND deleted_at IS NULL
                    ''', (hashed_password, email))
                    
                    return cursor.rowcount > 0  # Returns True if a row was updated
        except Exception as e:
            print(f"Error in crud reset_password: {e}")
            return False



user_service = UserService()