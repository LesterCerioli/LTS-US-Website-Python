from typing import Optional, Dict, Any, List
from app import credential_service
from app.database import db
from app.image_service import ImageService
from app.user_service import UserService
from app.project_service import ProjectService
import uuid
from datetime import datetime

class UserCRUD:
    def __init__(self):
        self.user_service = UserService()  # Instância local
    
    def create_user(self, name: str, email: str, password: str, 
                   role: str, organization_name: str) -> Optional[Dict[str, Any]]:
        """Creates a new user with organization validation"""
        try:
            result = self.user_service.create_user(name, email, password, role, organization_name)
            if result:
                # Remove sensitive data before returning
                result.pop('password', None)
                result.pop('organization_id', None)
            return result
            
        except Exception as e:
            print(f"Error creating user: {e}")
            return None
    
    def authenticate_user(self, email: str, password: str, role: str) -> Optional[Dict[str, Any]]:
        """Authenticates user using the service layer"""
        try:
            auth_result = self.user_service.authenticate_user_by_role(email, password, role)
            return auth_result
        except Exception as e:
            print(f"Authentication error: {e}")
            return None
    
    def change_user_password(self, user_id: str, current_password: str, 
                           new_password: str, organization_name: str) -> bool:
        """Changes user password with validation"""
        try:
            
            org_id = self.user_service.get_organization_id_by_name(organization_name)
            if not org_id:
                return False
                
            
            user = db.get_user_by_id(user_id)
            if not user or user.get('organization_id') != org_id:
                return False
            
            
            if not self.user_service.verify_password(current_password, user['password']):
                return False
            
            
            new_hashed_password = self.user_service.hash_password(new_password)
            
            
            with db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        UPDATE public.users 
                        SET password = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s AND organization_id = %s
                    ''', (new_hashed_password, user_id, org_id))
                    
                    conn.commit()
                    return cursor.rowcount > 0
                    
        except Exception as e:
            print(f"Error changing password: {e}")
            return False
    
    def get_user_by_id(self, user_id: str, organization_name: str) -> Optional[Dict[str, Any]]:
        """Get user by ID with organization validation"""
        try:
            org_id = self.user_service.get_organization_id_by_name(organization_name)
            if not org_id:
                return None
            
            user = db.get_user_by_id(user_id)
            if user and user.get('organization_id') == org_id:
                user.pop('password', None)
                user.pop('organization_id', None)
                return user
            return None
            
        except Exception as e:
            print(f"Error getting user: {e}")
            return None
    
    def get_organization_users(self, organization_name: str) -> Optional[Dict[str, Any]]:
        """Get all users in an organization"""
        try:
            org_id = self.user_service.get_organization_id_by_name(organization_name)
            if not org_id:
                return None
            
            users = db.get_organization_users(org_id)
            if users:
                for user in users:
                    user.pop('password', None)
                    user.pop('organization_id', None)
            return users
            
        except Exception as e:
            print(f"Error getting organization users: {e}")
            return None
    
    def update_user(self, user_id: str, update_data: Dict[str, Any], organization_name: str) -> Optional[Dict[str, Any]]:
        """Update user information"""
        try:
            org_id = self.user_service.get_organization_id_by_name(organization_name)
            if not org_id:
                return None
            
            
            user = db.get_user_by_id(user_id)
            if not user or user.get('organization_id') != org_id:
                return None
            
            # Constrói query dinâmica
            set_clauses = []
            values = []
            for field, value in update_data.items():
                if field in ['name', 'email', 'role']:
                    set_clauses.append(f"{field} = %s")
                    values.append(value)
            
            if not set_clauses:
                return None
            
            values.extend([user_id, org_id])
            
            with db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(f'''
                        UPDATE public.users 
                        SET {', '.join(set_clauses)}, updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s AND organization_id = %s
                        RETURNING id, name, email, role, created_at, updated_at
                    ''', values)
                    
                    result = cursor.fetchone()
                    conn.commit()
                    return dict(result) if result else None
                    
        except Exception as e:
            print(f"Error updating user: {e}")
            return None
    
    def delete_user(self, user_id: str, organization_name: str) -> bool:
        """Soft delete a user"""
        try:
            org_id = self.user_service.get_organization_id_by_name(organization_name)
            if not org_id:
                return False
            
            with db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        UPDATE public.users 
                        SET deleted_at = CURRENT_TIMESTAMP
                        WHERE id = %s AND organization_id = %s
                    ''', (user_id, org_id))
                    
                    conn.commit()
                    return cursor.rowcount > 0
                    
        except Exception as e:
            print(f"Error deleting user: {e}")
            return False

    def reset_password_by_email(self, email: str, new_password: str) -> bool:
        """Logic to update the database - returns True if successful"""
        try:
            # We use the service to hash because it has the bcrypt logic
            from app.user_service import user_service 
            hashed_password = user_service.hash_password(new_password)

            with db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        UPDATE public.users 
                        SET password = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE email = %s AND deleted_at IS NULL
                    ''', (hashed_password, email))
                    
                    return cursor.rowcount > 0  # This must be indented!
        except Exception as e:
            print(f"Error in crud reset_password: {e}")
            return False

class ProjectCRUD:
    def __init__(self):
        self.project_service = ProjectService()

    def create_project(self,
                      organization_name: str,
                      name: str,
                      code: str,
                      owner_username: str,
                      description: str,
                      template_agile_method: str,
                      settings: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        try:
            # Obter organization_id
            with db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        SELECT id FROM public.organizations 
                        WHERE name = %s AND deleted_at IS NULL
                    ''', (organization_name,))
                    org_result = cursor.fetchone()
                    
                    if not org_result:
                        print(f"ERROR: Organization '{organization_name}' not found")
                        return None
                    
                    organization_id = org_result['id']
                    
                    # Obter owner_id
                    cursor.execute('''
                        SELECT u.id FROM public.users u
                        JOIN public.user_organizations uo ON u.id = uo.user_id
                        WHERE u.username = %s 
                          AND uo.organization_id = %s
                          AND u.deleted_at IS NULL
                          AND uo.left_at IS NULL
                    ''', (owner_username, organization_id))
                    
                    owner_result = cursor.fetchone()
                    if not owner_result:
                        print(f"ERROR: Owner '{owner_username}' not found")
                        return None
                    
                    owner_id = owner_result['id']
                    
                    # Validar código
                    if not self.project_service._validate_project_code(code):
                        print(f"ERROR: Invalid project code: {code}")
                        return None
                    
                    # Verificar se código já existe
                    cursor.execute('''
                        SELECT id FROM boards.projects 
                        WHERE organization_id = %s AND code = %s AND deleted_at IS NULL
                    ''', (organization_id, code))
                    
                    if cursor.fetchone():
                        print(f"ERROR: Project code '{code}' already exists")
                        return None
                    
                    # Inserir projeto
                    project_id = str(uuid.uuid4())
                    project_settings = settings or {}
                    
                    cursor.execute('''
                        INSERT INTO boards.projects (
                            id, organization_id, name, code, description, 
                            owner_id, template_agile_method, settings
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING 
                            id, organization_id, name, code, description,
                            owner_id, template_agile_method, is_active,
                            created_at, updated_at, deleted_at, settings
                    ''', (
                        project_id, organization_id, name, code, description,
                        owner_id, template_agile_method, project_settings
                    ))
                    
                    result = cursor.fetchone()
                    conn.commit()
                    
                    if result:
                        print(f"SUCCESS: Project '{code}' created")
                        result_dict = dict(result)
                        result_dict['message'] = f"Project '{code}' created successfully"
                        return result_dict
                    return None
                    
        except Exception as e:
            print(f"CRUD Error creating project: {e}")
            return None
    
    def get_project(self, organization_name: str, project_code: str) -> Optional[Dict[str, Any]]:
        try:
            with db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        SELECT 
                            p.id, p.organization_id, p.name, p.code, p.description,
                            p.owner_id, p.template_agile_method, p.is_active,
                            p.created_at, p.updated_at, p.deleted_at, p.settings,
                            o.name as organization_name,
                            u.username as owner_username
                        FROM boards.projects p
                        LEFT JOIN public.organizations o ON p.organization_id = o.id
                        LEFT JOIN public.users u ON p.owner_id = u.id
                        WHERE o.name = %s 
                          AND p.code = %s 
                          AND p.deleted_at IS NULL
                    ''', (organization_name, project_code))
                    
                    result = cursor.fetchone()
                    
                    if result:
                        print(f"CRUD: Retrieved project '{project_code}'")
                        return dict(result)
                    else:
                        print(f"CRUD: Project '{project_code}' not found")
                        return None
                    
        except Exception as e:
            print(f"CRUD Error getting project: {e}")
            return None
    
    def get_all_projects(self,
                        organization_name: str,
                        active_only: bool = True,
                        limit: int = 100,
                        offset: int = 0) -> List[Dict[str, Any]]:
        try:
            with db.get_connection() as conn:
                with conn.cursor() as cursor:
                    query = '''
                        SELECT 
                            p.id, p.organization_id, p.name, p.code, p.description,
                            p.owner_id, p.template_agile_method, p.is_active,
                            p.created_at, p.updated_at, p.deleted_at, p.settings,
                            u.username as owner_username,
                            COUNT(DISTINCT wi.id) as work_item_count,
                            COUNT(DISTINCT pm.user_id) as member_count
                        FROM boards.projects p
                        LEFT JOIN public.users u ON p.owner_id = u.id
                        LEFT JOIN boards.work_items wi ON p.id = wi.project_id 
                            AND p.organization_id = wi.organization_id 
                            AND wi.deleted_at IS NULL
                        LEFT JOIN boards.project_members pm ON p.id = pm.project_id 
                            AND p.organization_id = pm.organization_id 
                            AND pm.left_at IS NULL
                        WHERE p.organization_id = (
                            SELECT id FROM public.organizations 
                            WHERE name = %s AND deleted_at IS NULL
                        )
                        AND p.deleted_at IS NULL
                    '''
                    
                    params = [organization_name]
                    
                    if active_only:
                        query += ' AND p.is_active = true'
                    
                    query += '''
                        GROUP BY p.id, p.organization_id, p.name, p.code, p.description,
                                 p.owner_id, p.template_agile_method, p.is_active,
                                 p.created_at, p.updated_at, p.deleted_at, p.settings,
                                 u.username
                        ORDER BY p.created_at DESC
                        LIMIT %s OFFSET %s
                    '''
                    
                    params.extend([limit, offset])
                    
                    cursor.execute(query, params)
                    results = cursor.fetchall()
                    
                    print(f"CRUD: Retrieved {len(results)} projects")
                    return [dict(row) for row in results]
                    
        except Exception as e:
            print(f"CRUD Error getting projects: {e}")
            return []
    
    def update_project(self,
                      organization_name: str,
                      project_code: str,
                      updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            with db.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Primeiro obter organization_id
                    cursor.execute('''
                        SELECT id FROM public.organizations 
                        WHERE name = %s AND deleted_at IS NULL
                    ''', (organization_name,))
                    org_result = cursor.fetchone()
                    
                    if not org_result:
                        return None
                    
                    organization_id = org_result['id']
                    
                    # Verificar se projeto existe
                    cursor.execute('''
                        SELECT id FROM boards.projects 
                        WHERE organization_id = %s AND code = %s AND deleted_at IS NULL
                    ''', (organization_id, project_code))
                    
                    if not cursor.fetchone():
                        return None
                    
                    # Processar owner_username se fornecido
                    if 'owner_username' in updates:
                        cursor.execute('''
                            SELECT u.id FROM public.users u
                            JOIN public.user_organizations uo ON u.id = uo.user_id
                            WHERE u.username = %s 
                              AND uo.organization_id = %s
                              AND u.deleted_at IS NULL
                              AND uo.left_at IS NULL
                        ''', (updates['owner_username'], organization_id))
                        
                        owner_result = cursor.fetchone()
                        if not owner_result:
                            return None
                        
                        updates['owner_id'] = owner_result['id']
                        del updates['owner_username']
                    
                    # Construir query dinâmica
                    allowed_fields = {
                        'name', 'description', 'owner_id', 
                        'template_agile_method', 'is_active', 'settings'
                    }
                    
                    set_clauses = []
                    params = []
                    
                    for field, value in updates.items():
                        if field in allowed_fields:
                            set_clauses.append(f"{field} = %s")
                            params.append(value)
                    
                    if not set_clauses:
                        return None
                    
                    set_clauses.append("updated_at = CURRENT_TIMESTAMP")
                    params.extend([organization_id, project_code])
                    
                    query = f'''
                        UPDATE boards.projects 
                        SET {', '.join(set_clauses)}
                        WHERE organization_id = %s 
                          AND code = %s 
                          AND deleted_at IS NULL
                        RETURNING 
                            id, organization_id, name, code, description,
                            owner_id, template_agile_method, is_active,
                            created_at, updated_at, deleted_at, settings
                    '''
                    
                    cursor.execute(query, params)
                    result = cursor.fetchone()
                    conn.commit()
                    
                    if result:
                        print(f"CRUD: Updated project '{project_code}'")
                        result_dict = dict(result)
                        result_dict['message'] = f"Project '{project_code}' updated"
                        return result_dict
                    return None
                    
        except Exception as e:
            print(f"CRUD Error updating project: {e}")
            return None
    
    def delete_project(self, organization_name: str, project_code: str) -> Dict[str, Any]:
        try:
            with db.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Obter organization_id
                    cursor.execute('''
                        SELECT id FROM public.organizations 
                        WHERE name = %s AND deleted_at IS NULL
                    ''', (organization_name,))
                    org_result = cursor.fetchone()
                    
                    if not org_result:
                        return {
                            'success': False,
                            'message': f"Organization '{organization_name}' not found",
                            'project_code': project_code
                        }
                    
                    organization_id = org_result['id']
                    
                    # Soft delete
                    cursor.execute('''
                        UPDATE boards.projects 
                        SET deleted_at = CURRENT_TIMESTAMP,
                            is_active = false,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE organization_id = %s 
                          AND code = %s 
                          AND deleted_at IS NULL
                        RETURNING id
                    ''', (organization_id, project_code))
                    
                    result = cursor.fetchone()
                    conn.commit()
                    
                    if result:
                        return {
                            'success': True,
                            'message': f"Project '{project_code}' deleted",
                            'project_code': project_code
                        }
                    else:
                        return {
                            'success': False,
                            'message': f"Project '{project_code}' not found",
                            'project_code': project_code
                        }
                    
        except Exception as e:
            print(f"CRUD Error deleting project: {e}")
            return {
                'success': False,
                'message': f"Error: {str(e)}",
                'project_code': project_code
            }
    
    def restore_project(self, organization_name: str, project_code: str) -> Dict[str, Any]:
        try:
            with db.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Obter organization_id
                    cursor.execute('''
                        SELECT id FROM public.organizations 
                        WHERE name = %s AND deleted_at IS NULL
                    ''', (organization_name,))
                    org_result = cursor.fetchone()
                    
                    if not org_result:
                        return {
                            'success': False,
                            'message': f"Organization '{organization_name}' not found",
                            'project_code': project_code
                        }
                    
                    organization_id = org_result['id']
                    
                    # Restaurar projeto
                    cursor.execute('''
                        UPDATE boards.projects 
                        SET deleted_at = NULL,
                            is_active = true,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE organization_id = %s 
                          AND code = %s 
                          AND deleted_at IS NOT NULL
                        RETURNING id
                    ''', (organization_id, project_code))
                    
                    result = cursor.fetchone()
                    conn.commit()
                    
                    if result:
                        return {
                            'success': True,
                            'message': f"Project '{project_code}' restored",
                            'project_code': project_code
                        }
                    else:
                        return {
                            'success': False,
                            'message': f"Project '{project_code}' not found or not deleted",
                            'project_code': project_code
                        }
                    
        except Exception as e:
            print(f"CRUD Error restoring project: {e}")
            return {
                'success': False,
                'message': f"Error: {str(e)}",
                'project_code': project_code
            }
    
    def add_project_member(self,
                          organization_name: str,
                          project_code: str,
                          username: str,
                          role: str = 'Member') -> Dict[str, Any]:
        try:
            with db.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Obter organization_id
                    cursor.execute('''
                        SELECT id FROM public.organizations 
                        WHERE name = %s AND deleted_at IS NULL
                    ''', (organization_name,))
                    org_result = cursor.fetchone()
                    
                    if not org_result:
                        return {
                            'success': False,
                            'message': f"Organization '{organization_name}' not found",
                            'project_code': project_code,
                            'username': username,
                            'role': role
                        }
                    
                    organization_id = org_result['id']
                    
                    # Obter project_id
                    cursor.execute('''
                        SELECT id FROM boards.projects 
                        WHERE organization_id = %s AND code = %s AND deleted_at IS NULL
                    ''', (organization_id, project_code))
                    
                    project_result = cursor.fetchone()
                    if not project_result:
                        return {
                            'success': False,
                            'message': f"Project '{project_code}' not found",
                            'project_code': project_code,
                            'username': username,
                            'role': role
                        }
                    
                    project_id = project_result['id']
                    
                    # Obter user_id
                    cursor.execute('''
                        SELECT u.id FROM public.users u
                        JOIN public.user_organizations uo ON u.id = uo.user_id
                        WHERE u.username = %s 
                          AND uo.organization_id = %s
                          AND u.deleted_at IS NULL
                          AND uo.left_at IS NULL
                    ''', (username, organization_id))
                    
                    user_result = cursor.fetchone()
                    if not user_result:
                        return {
                            'success': False,
                            'message': f"User '{username}' not found",
                            'project_code': project_code,
                            'username': username,
                            'role': role
                        }
                    
                    user_id = user_result['id']
                    
                    # Adicionar membro
                    cursor.execute('''
                        INSERT INTO boards.project_members 
                        (project_id, user_id, organization_id, role, joined_at)
                        VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
                        ON CONFLICT (project_id, user_id, organization_id) 
                        DO UPDATE SET 
                            role = EXCLUDED.role,
                            left_at = NULL,
                            joined_at = CASE 
                                WHEN boards.project_members.left_at IS NOT NULL 
                                THEN CURRENT_TIMESTAMP 
                                ELSE boards.project_members.joined_at 
                            END
                        RETURNING project_id
                    ''', (project_id, user_id, organization_id, role))
                    
                    result = cursor.fetchone()
                    conn.commit()
                    
                    if result:
                        return {
                            'success': True,
                            'message': f"User '{username}' added to project",
                            'project_code': project_code,
                            'username': username,
                            'role': role
                        }
                    else:
                        return {
                            'success': False,
                            'message': f"Failed to add user '{username}'",
                            'project_code': project_code,
                            'username': username,
                            'role': role
                        }
                    
        except Exception as e:
            print(f"CRUD Error adding member: {e}")
            return {
                'success': False,
                'message': f"Error: {str(e)}",
                'project_code': project_code,
                'username': username,
                'role': role
            }
    
    def remove_project_member(self,
                             organization_name: str,
                             project_code: str,
                             username: str) -> Dict[str, Any]:
        try:
            with db.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Obter organization_id
                    cursor.execute('''
                        SELECT id FROM public.organizations 
                        WHERE name = %s AND deleted_at IS NULL
                    ''', (organization_name,))
                    org_result = cursor.fetchone()
                    
                    if not org_result:
                        return {
                            'success': False,
                            'message': f"Organization '{organization_name}' not found",
                            'project_code': project_code,
                            'username': username
                        }
                    
                    organization_id = org_result['id']
                    
                    # Obter project_id
                    cursor.execute('''
                        SELECT id FROM boards.projects 
                        WHERE organization_id = %s AND code = %s AND deleted_at IS NULL
                    ''', (organization_id, project_code))
                    
                    project_result = cursor.fetchone()
                    if not project_result:
                        return {
                            'success': False,
                            'message': f"Project '{project_code}' not found",
                            'project_code': project_code,
                            'username': username
                        }
                    
                    project_id = project_result['id']
                    
                    # Obter user_id
                    cursor.execute('''
                        SELECT u.id FROM public.users u
                        JOIN public.user_organizations uo ON u.id = uo.user_id
                        WHERE u.username = %s 
                          AND uo.organization_id = %s
                          AND u.deleted_at IS NULL
                          AND uo.left_at IS NULL
                    ''', (username, organization_id))
                    
                    user_result = cursor.fetchone()
                    if not user_result:
                        return {
                            'success': False,
                            'message': f"User '{username}' not found",
                            'project_code': project_code,
                            'username': username
                        }
                    
                    user_id = user_result['id']
                    
                    # Remover membro
                    cursor.execute('''
                        UPDATE boards.project_members 
                        SET left_at = CURRENT_TIMESTAMP
                        WHERE project_id = %s 
                          AND user_id = %s 
                          AND organization_id = %s
                          AND left_at IS NULL
                        RETURNING project_id
                    ''', (project_id, user_id, organization_id))
                    
                    result = cursor.fetchone()
                    conn.commit()
                    
                    if result:
                        return {
                            'success': True,
                            'message': f"User '{username}' removed from project",
                            'project_code': project_code,
                            'username': username
                        }
                    else:
                        return {
                            'success': False,
                            'message': f"User '{username}' not found in project",
                            'project_code': project_code,
                            'username': username
                        }
                    
        except Exception as e:
            print(f"CRUD Error removing member: {e}")
            return {
                'success': False,
                'message': f"Error: {str(e)}",
                'project_code': project_code,
                'username': username
            }
    
    def get_project_members(self,
                           organization_name: str,
                           project_code: str) -> List[Dict[str, Any]]:
        try:
            with db.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Obter organization_id
                    cursor.execute('''
                        SELECT id FROM public.organizations 
                        WHERE name = %s AND deleted_at IS NULL
                    ''', (organization_name,))
                    org_result = cursor.fetchone()
                    
                    if not org_result:
                        return []
                    
                    organization_id = org_result['id']
                    
                    # Obter project_id
                    cursor.execute('''
                        SELECT id FROM boards.projects 
                        WHERE organization_id = %s AND code = %s AND deleted_at IS NULL
                    ''', (organization_id, project_code))
                    
                    project_result = cursor.fetchone()
                    if not project_result:
                        return []
                    
                    project_id = project_result['id']
                    
                    # Buscar membros
                    cursor.execute('''
                        SELECT 
                            pm.*,
                            u.username,
                            u.email,
                            u.full_name,
                            u.avatar_url
                        FROM boards.project_members pm
                        JOIN public.users u ON pm.user_id = u.id
                        WHERE pm.project_id = %s 
                          AND pm.organization_id = %s
                          AND pm.left_at IS NULL
                          AND u.deleted_at IS NULL
                        ORDER BY pm.joined_at
                    ''', (project_id, organization_id))
                    
                    results = cursor.fetchall()
                    return [dict(row) for row in results]
                    
        except Exception as e:
            print(f"CRUD Error getting members: {e}")
            return []
    
    def get_project_stats(self, organization_name: str, project_code: str) -> Dict[str, Any]:
        try:
            with db.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Obter organization_id e project_id
                    cursor.execute('''
                        SELECT p.id, p.organization_id
                        FROM boards.projects p
                        JOIN public.organizations o ON p.organization_id = o.id
                        WHERE o.name = %s 
                          AND p.code = %s 
                          AND p.deleted_at IS NULL
                    ''', (organization_name, project_code))
                    
                    project_result = cursor.fetchone()
                    if not project_result:
                        return {
                            'success': False,
                            'message': f"Project '{project_code}' not found",
                            'project_code': project_code
                        }
                    
                    project_id = project_result['id']
                    organization_id = project_result['organization_id']
                    
                    # Buscar estatísticas
                    cursor.execute('''
                        SELECT 
                            COUNT(DISTINCT wi.id) as total_work_items,
                            COUNT(DISTINCT CASE WHEN wi.status = 'New' THEN wi.id END) as new_count,
                            COUNT(DISTINCT CASE WHEN wi.status = 'In Progress' THEN wi.id END) as in_progress_count,
                            COUNT(DISTINCT CASE WHEN wi.status IN ('Done', 'Closed') THEN wi.id END) as completed_count,
                            COUNT(DISTINCT pm.user_id) as member_count,
                            MIN(wi.created_at) as first_activity,
                            MAX(wi.updated_at) as last_activity
                        FROM boards.projects p
                        LEFT JOIN boards.work_items wi ON p.id = wi.project_id 
                            AND p.organization_id = wi.organization_id 
                            AND wi.deleted_at IS NULL
                        LEFT JOIN boards.project_members pm ON p.id = pm.project_id 
                            AND p.organization_id = pm.organization_id 
                            AND pm.left_at IS NULL
                        WHERE p.id = %s 
                          AND p.organization_id = %s
                        GROUP BY p.id
                    ''', (project_id, organization_id))
                    
                    stats_result = cursor.fetchone()
                    
                    if stats_result:
                        return {
                            'success': True,
                            'project_code': project_code,
                            'stats': dict(stats_result)
                        }
                    else:
                        return {
                            'success': True,
                            'project_code': project_code,
                            'stats': {}
                        }
                    
        except Exception as e:
            print(f"CRUD Error getting stats: {e}")
            return {
                'success': False,
                'message': f"Error: {str(e)}",
                'project_code': project_code
            }
    
    def search_projects(self,
                       organization_name: str,
                       query: str,
                       limit: int = 50) -> Dict[str, Any]:
        try:
            with db.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Obter organization_id
                    cursor.execute('''
                        SELECT id FROM public.organizations 
                        WHERE name = %s AND deleted_at IS NULL
                    ''', (organization_name,))
                    org_result = cursor.fetchone()
                    
                    if not org_result:
                        return {
                            'success': False,
                            'message': f"Organization '{organization_name}' not found",
                            'query': query,
                            'count': 0,
                            'results': []
                        }
                    
                    organization_id = org_result['id']
                    search_pattern = f"%{query}%"
                    
                    # Buscar projetos
                    cursor.execute('''
                        SELECT 
                            p.id, p.organization_id, p.name, p.code, p.description,
                            p.owner_id, p.template_agile_method, p.is_active,
                            p.created_at, p.updated_at, p.deleted_at, p.settings,
                            u.username as owner_username
                        FROM boards.projects p
                        LEFT JOIN public.users u ON p.owner_id = u.id
                        WHERE p.organization_id = %s 
                          AND p.deleted_at IS NULL
                          AND (p.name ILIKE %s OR p.code ILIKE %s)
                        ORDER BY 
                            CASE 
                                WHEN p.code ILIKE %s THEN 1
                                WHEN p.name ILIKE %s THEN 2
                                ELSE 3
                            END,
                            p.created_at DESC
                        LIMIT %s
                    ''', (organization_id, search_pattern, search_pattern, 
                          search_pattern, search_pattern, limit))
                    
                    results = cursor.fetchall()
                    
                    return {
                        'success': True,
                        'query': query,
                        'count': len(results),
                        'results': [dict(row) for row in results]
                    }
                    
        except Exception as e:
            print(f"CRUD Error searching projects: {e}")
            return {
                'success': False,
                'message': f"Error: {str(e)}",
                'query': query,
                'count': 0,
                'results': []
            }
    
    def validate_project_code(self, organization_name: str, code: str) -> Dict[str, Any]:
        try:
            # Validar formato
            if not self.project_service._validate_project_code(code):
                return {
                    'success': False,
                    'valid': False,
                    'message': f"Invalid format: {code}",
                    'code': code
                }
            
            with db.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Verificar se organização existe
                    cursor.execute('''
                        SELECT id FROM public.organizations 
                        WHERE name = %s AND deleted_at IS NULL
                    ''', (organization_name,))
                    org_result = cursor.fetchone()
                    
                    if not org_result:
                        return {
                            'success': False,
                            'valid': False,
                            'message': f"Organization '{organization_name}' not found",
                            'code': code
                        }
                    
                    organization_id = org_result['id']
                    
                    # Verificar se código já existe
                    cursor.execute('''
                        SELECT EXISTS (
                            SELECT 1 FROM boards.projects 
                            WHERE organization_id = %s 
                              AND code = %s 
                              AND deleted_at IS NULL
                        ) as exists
                    ''', (organization_id, code))
                    
                    result = cursor.fetchone()
                    
                    if result['exists']:
                        return {
                            'success': True,
                            'valid': False,
                            'message': f"Code '{code}' already exists",
                            'code': code,
                            'available': False
                        }
                    else:
                        return {
                            'success': True,
                            'valid': True,
                            'message': f"Code '{code}' is available",
                            'code': code,
                            'available': True
                        }
                    
        except Exception as e:
            print(f"CRUD Error validating code: {e}")
            return {
                'success': False,
                'valid': False,
                'message': f"Error: {str(e)}",
                'code': code
            }
            
class CredentialCRUD:
    def __init__(self):
        self.service = credential_service
    
    def create_credential(self, 
                         organization_name: str,
                         type: str, 
                         email: str, 
                         password: str, 
                         description: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Create a new credential"""
        try:
            result = self.service.create_credential(
                organization_name=organization_name,
                type=type,
                email=email,
                password=password,
                description=description
            )
            
            if result:
                print(f"CRUD: Credential created successfully for email: {email}")
            else:
                print(f"CRUD: Failed to create credential for email: {email}")
                
            return result
            
        except Exception as e:
            print(f"CRUD Error creating credential: {e}")
            return None
    
    def get_credential(self, credential_id: str, organization_name: str) -> Optional[Dict[str, Any]]:
        """Get credential by ID"""
        try:
            result = self.service.get_credential_by_id(credential_id, organization_name)
            
            if result:
                print(f"CRUD: Retrieved credential {credential_id}")
            else:
                print(f"CRUD: Credential {credential_id} not found in organization '{organization_name}'")
                
            return result
            
        except Exception as e:
            print(f"CRUD Error getting credential: {e}")
            return None
    
    def get_all_credentials(self, 
                           organization_name: str,
                           limit: int = 100, 
                           offset: int = 0) -> List[Dict[str, Any]]:
        """Get all credentials for an organization"""
        try:
            credentials = self.service.get_all_credentials(organization_name, limit, offset)
            
            print(f"CRUD: Retrieved {len(credentials)} credentials for organization '{organization_name}'")
            return credentials
            
        except Exception as e:
            print(f"CRUD Error getting all credentials: {e}")
            return []
    
    def update_credential(self, 
                         credential_id: str, 
                         organization_name: str,
                         updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update a credential"""
        try:
            result = self.service.update_credential(credential_id, organization_name, updates)
            
            if result:
                print(f"CRUD: Credential {credential_id} updated successfully")
            else:
                print(f"CRUD: Failed to update credential {credential_id}")
                
            return result
            
        except Exception as e:
            print(f"CRUD Error updating credential: {e}")
            return None
    
    def delete_credential(self, credential_id: str, organization_name: str) -> Dict[str, Any]:
        """Delete a credential"""
        try:
            success = self.service.delete_credential(credential_id, organization_name)
            
            if success:
                return {
                    'success': True,
                    'message': f"Credential deleted successfully",
                    'credential_id': credential_id,
                    'organization_name': organization_name
                }
            else:
                return {
                    'success': False,
                    'message': f"Credential not found or doesn't belong to organization",
                    'credential_id': credential_id,
                    'organization_name': organization_name
                }
                    
        except Exception as e:
            print(f"CRUD Error deleting credential: {e}")
            return {
                'success': False,
                'message': f"Error: {str(e)}",
                'credential_id': credential_id,
                'organization_name': organization_name
            }
    
    def search_credentials(self, 
                          organization_name: str,
                          search_term: str, 
                          limit: int = 50, 
                          offset: int = 0) -> Dict[str, Any]:
        """Search credentials"""
        try:
            result = self.service.search_credentials(organization_name, search_term, limit, offset)
            
            if 'error' in result:
                return {
                    'success': False,
                    'message': result['error'],
                    'search_term': search_term,
                    'organization_name': organization_name,
                    'results': [],
                    'total_count': 0
                }
            
            return {
                'success': True,
                'message': f"Found {result['total_count']} credentials matching '{search_term}'",
                'search_term': search_term,
                'organization_name': organization_name,
                'results': result['results'],
                'total_count': result['total_count']
            }
            
        except Exception as e:
            print(f"CRUD Error searching credentials: {e}")
            return {
                'success': False,
                'message': f"Error: {str(e)}",
                'search_term': search_term,
                'organization_name': organization_name,
                'results': [],
                'total_count': 0
            }
    
    def validate_email(self, organization_name: str, email: str) -> Dict[str, Any]:
        """Validate email availability"""
        try:
            result = self.service.validate_email(organization_name, email)
            
            if 'error' in result:
                return {
                    'success': False,
                    'email': email,
                    'organization_name': organization_name,
                    'is_available': False,
                    'exists': False,
                    'error': result['error']
                }
            
            return {
                'success': True,
                'email': email,
                'organization_name': organization_name,
                'is_available': result['is_available'],
                'exists': result['exists'],
                'message': result['message']
            }
            
        except Exception as e:
            print(f"CRUD Error validating email: {e}")
            return {
                'success': False,
                'email': email,
                'organization_name': organization_name,
                'is_available': False,
                'exists': False,
                'error': str(e)
            }
    
    def get_stats(self, organization_name: str) -> Dict[str, Any]:
        """Get credential statistics"""
        try:
            stats = self.service.get_credential_stats(organization_name)
            
            if 'error' in stats:
                return {
                    'success': False,
                    'error': stats['error'],
                    'stats': {}
                }
            
            return {
                'success': True,
                'message': f"Retrieved credential statistics for '{organization_name}'",
                'stats': stats
            }
            
        except Exception as e:
            print(f"CRUD Error getting stats: {e}")
            return {
                'success': False,
                'error': str(e),
                'stats': {}
            }
            
class PostCRUD:
    def __init__(self):
        pass

    async def create_post(self,
                         organization_name: str,
                         title: str,
                         content: str,
                         user_id: Optional[str] = None,
                         scheduled_at: Optional[datetime] = None,
                         status: str = 'draft',
                         
                         
                         base64_image: Optional[str] = None,
                         image_mime_type: Optional[str] = None,
                         image_alt: Optional[str] = None,
                                                  
                         slug: Optional[str] = None,
                         excerpt: Optional[str] = None,
                         category: Optional[str] = None,
                         read_time_minutes: Optional[int] = None,
                         image_url: Optional[str] = None,
                         badge_text: Optional[str] = None,
                         badge_variant: str = 'default',
                         featured: bool = False,
                         seo_title: Optional[str] = None,
                         seo_description: Optional[str] = None,
                         meta_keywords: Optional[List[List[str]]] = None
                         ) -> Optional[Dict[str, Any]]:
        
        
        try:
            async with db.get_async_connection() as conn:
                async with conn.cursor() as cursor:
                    
                    await cursor.execute('''
                        SELECT id FROM public.organizations 
                        WHERE name = %s AND deleted_at IS NULL
                    ''', (organization_name,))
                    org_result = await cursor.fetchone()
                    
                    if not org_result:
                        print(f"ERROR: Organization '{organization_name}' not found")
                        return None
                    
                    organization_id = org_result['id']

                    
                    if not user_id:
                        await cursor.execute('''
                            SELECT u.id FROM public.users u
                            JOIN public.user_organizations uo ON u.id = uo.user_id
                            WHERE uo.organization_id = %s 
                              AND u.deleted_at IS NULL
                              AND uo.left_at IS NULL
                            LIMIT 1
                        ''', (organization_id,))
                        user_result = await cursor.fetchone()
                        if not user_result:
                            print(f"ERROR: No users found in organization '{organization_name}'")
                            return None
                        user_id = user_result['id']

                    
                    await cursor.execute('''
                        SELECT 1 FROM public.user_organizations 
                        WHERE user_id = %s 
                          AND organization_id = %s
                          AND left_at IS NULL
                    ''', (user_id, organization_id))
                    
                    if not await cursor.fetchone():
                        print(f"ERROR: User '{user_id}' not found in organization")
                        return None

                    
                    processed_image_data = None
                    if base64_image and image_mime_type:
                        try:
                            
                            image_info = await ImageService.validate_and_process_image(
                                base64_image, 
                                image_mime_type
                            )
                            processed_image_data = {
                                'base64_image': image_info['base64_data'],
                                'image_mime_type': image_info['mime_type'],
                                'image_alt': image_alt or ''
                            }
                        except Exception as e:
                            print(f"ERROR: Image validation failed: {e}")
                            return None

                    
                    published_at = None
                    if scheduled_at:
                        if scheduled_at > datetime.utcnow():
                            status = 'scheduled'
                        else:
                            status = 'published'
                            published_at = scheduled_at
                    elif status == 'published':
                        published_at = datetime.utcnow()

                    
                    if not slug:
                        slug = self._generate_slug(title)

                    
                    post_id = str(uuid.uuid4())
                    
                    
                    fields = []
                    values = []
                    placeholders = []
                                        
                    fields.extend(['id', 'organization_id', 'title', 'content', 'status', 'user_id'])
                    values.extend([post_id, organization_id, title, content, status, user_id])
                    placeholders.extend(['%s'] * 6)
                                        
                    optional_fields = [
                        ('scheduled_at', scheduled_at),
                        ('published_at', published_at),
                        ('slug', slug),
                        ('excerpt', excerpt),
                        ('category', category),
                        ('read_time_minutes', read_time_minutes),
                        ('image_url', image_url),
                        ('image_alt', image_alt),
                        ('badge_text', badge_text),
                        ('badge_variant', badge_variant),
                        ('featured', featured),
                        ('seo_title', seo_title),
                        ('seo_description', seo_description),
                        ('meta_keywords', meta_keywords),
                        ('base64_image', processed_image_data['base64_image'] if processed_image_data else None),
                        ('image_mime_type', processed_image_data['image_mime_type'] if processed_image_data else None)
                    ]
                    
                    for field_name, field_value in optional_fields:
                        if field_value is not None:
                            fields.append(field_name)
                            values.append(field_value)
                            placeholders.append('%s')
                                        
                    fields.extend(['created_at', 'updated_at'])
                    values.extend([datetime.utcnow(), datetime.utcnow()])
                    placeholders.extend(['%s', '%s'])
                    
                    query = f'''
                        INSERT INTO public.posts ({', '.join(fields)})
                        VALUES ({', '.join(placeholders)})
                        RETURNING *
                    '''
                    
                    await cursor.execute(query, values)
                    result = await cursor.fetchone()
                    await conn.commit()
                    
                    if result:
                        post_dict = dict(result)
                        
                        post_dict['has_image'] = bool(post_dict.get('base64_image'))
                        if post_dict.get('base64_image'):
                            post_dict['image_data_url'] = ImageService.create_data_url(
                                post_dict['base64_image'],
                                post_dict['image_mime_type']
                            )
                        print(f"SUCCESS: Post '{title}' created with status '{status}'")
                        return post_dict
                    return None
                    
        except Exception as e:
            print(f"CRUD Error creating post: {e}")
            return None

    async def get_post(self, 
                      organization_name: str, 
                      post_id: str) -> Optional[Dict[str, Any]]:
        
        
        try:
            async with db.get_async_connection() as conn:
                async with conn.cursor() as cursor:
                    
                    await cursor.execute('''
                        SELECT id FROM public.organizations 
                        WHERE name = %s AND deleted_at IS NULL
                    ''', (organization_name,))
                    org_result = await cursor.fetchone()
                    
                    if not org_result:
                        print(f"ERROR: Organization '{organization_name}' not found")
                        return None
                    
                    organization_id = org_result['id']

                    await cursor.execute('''
                        SELECT 
                            p.*,
                            u.username,
                            u.email as user_email
                        FROM public.posts p
                        LEFT JOIN public.users u ON p.user_id = u.id
                        WHERE p.organization_id = %s 
                          AND p.id = %s 
                          AND p.deleted_at IS NULL
                    ''', (organization_id, post_id))
                    
                    result = await cursor.fetchone()
                    
                    if result:
                        post_dict = dict(result)
                        
                        post_dict['has_image'] = bool(post_dict.get('base64_image'))
                        if post_dict.get('base64_image'):
                            post_dict['image_data_url'] = ImageService.create_data_url(
                                post_dict['base64_image'],
                                post_dict['image_mime_type']
                            )
                        print(f"CRUD: Retrieved post '{post_id}'")
                        return post_dict
                    else:
                        print(f"CRUD: Post '{post_id}' not found")
                        return None
                    
        except Exception as e:
            print(f"CRUD Error getting post: {e}")
            return None

    async def get_all_posts(self,
                           organization_name: str,
                           status: Optional[str] = None,
                           user_id: Optional[str] = None,
                           search: Optional[str] = None,
                           start_date: Optional[datetime] = None,
                           end_date: Optional[datetime] = None,
                           has_image: Optional[bool] = None,
                           include_deleted: bool = False,
                           limit: int = 100,
                           offset: int = 0) -> List[Dict[str, Any]]:
        
        try:
            async with db.get_async_connection() as conn:
                async with conn.cursor() as cursor:
                    
                    await cursor.execute('''
                        SELECT id FROM public.organizations 
                        WHERE name = %s AND deleted_at IS NULL
                    ''', (organization_name,))
                    org_result = await cursor.fetchone()
                    
                    if not org_result:
                        print(f"ERROR: Organization '{organization_name}' not found")
                        return []
                    
                    organization_id = org_result['id']

                    
                    query = '''
                        SELECT 
                            p.*,
                            u.username,
                            u.email as user_email
                        FROM public.posts p
                        LEFT JOIN public.users u ON p.user_id = u.id
                        WHERE p.organization_id = %s
                    '''
                    params = [organization_id]

                    if not include_deleted:
                        query += ' AND p.deleted_at IS NULL'
                    
                    if status:
                        query += ' AND p.status = %s'
                        params.append(status)
                    
                    if user_id:
                        query += ' AND p.user_id = %s'
                        params.append(user_id)
                    
                    if search:
                        query += ' AND (p.title ILIKE %s OR p.content ILIKE %s OR p.excerpt ILIKE %s)'
                        search_pattern = f"%{search}%"
                        params.extend([search_pattern, search_pattern, search_pattern])
                    
                    if start_date:
                        query += ' AND p.created_at >= %s'
                        params.append(start_date)
                    
                    if end_date:
                        query += ' AND p.created_at <= %s'
                        params.append(end_date)
                    
                    if has_image is not None:
                        if has_image:
                            query += ' AND p.base64_image IS NOT NULL'
                        else:
                            query += ' AND p.base64_image IS NULL'

                    query += ' ORDER BY p.created_at DESC LIMIT %s OFFSET %s'
                    params.extend([limit, offset])

                    await cursor.execute(query, params)
                    results = await cursor.fetchall()
                                        
                    processed_results = []
                    for row in results:
                        post_dict = dict(row)
                        post_dict['has_image'] = bool(post_dict.get('base64_image'))
                        if post_dict.get('base64_image'):
                            post_dict['image_data_url'] = ImageService.create_data_url(
                                post_dict['base64_image'],
                                post_dict['image_mime_type']
                            )
                        processed_results.append(post_dict)
                    
                    print(f"CRUD: Retrieved {len(processed_results)} posts")
                    return processed_results
                    
        except Exception as e:
            print(f"CRUD Error getting all posts: {e}")
            return []

    async def update_post(self,
                         organization_name: str,
                         post_id: str,
                         updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        
        try:
            async with db.get_async_connection() as conn:
                async with conn.cursor() as cursor:
                    
                    await cursor.execute('''
                        SELECT id FROM public.organizations 
                        WHERE name = %s AND deleted_at IS NULL
                    ''', (organization_name,))
                    org_result = await cursor.fetchone()
                    
                    if not org_result:
                        print(f"ERROR: Organization '{organization_name}' not found")
                        return None
                    
                    organization_id = org_result['id']

                    
                    await cursor.execute('''
                        SELECT id FROM public.posts 
                        WHERE organization_id = %s 
                          AND id = %s 
                          AND deleted_at IS NULL
                    ''', (organization_id, post_id))
                    
                    if not await cursor.fetchone():
                        print(f"CRUD: Post '{post_id}' not found")
                        return None

                    
                    if 'base64_image' in updates and updates.get('image_mime_type'):
                        try:
                            image_info = await ImageService.validate_and_process_image(
                                updates['base64_image'],
                                updates['image_mime_type']
                            )
                            updates['base64_image'] = image_info['base64_data']
                            updates['image_mime_type'] = image_info['mime_type']
                        except Exception as e:
                            print(f"ERROR: Image validation failed: {e}")
                            return None

                    
                    allowed_fields = {
                        'title', 'content', 'scheduled_at', 'status',
                        'slug', 'excerpt', 'category', 'read_time_minutes',
                        'image_url', 'image_alt', 'badge_text', 'badge_variant',
                        'featured', 'seo_title', 'seo_description', 'meta_keywords',
                        'base64_image', 'image_mime_type'
                    }
                    
                    set_clauses = []
                    params = []
                    
                    for field, value in updates.items():
                        if field in allowed_fields and value is not None:
                            if field == 'status' and value == 'published':
                                
                                set_clauses.append("published_at = CURRENT_TIMESTAMP")
                            set_clauses.append(f"{field} = %s")
                            params.append(value)
                    
                    if not set_clauses:
                        return None
                    
                    set_clauses.append("updated_at = CURRENT_TIMESTAMP")
                    params.extend([organization_id, post_id])

                    query = f'''
                        UPDATE public.posts 
                        SET {', '.join(set_clauses)}
                        WHERE organization_id = %s 
                          AND id = %s 
                          AND deleted_at IS NULL
                        RETURNING *
                    '''
                    
                    await cursor.execute(query, params)
                    result = await cursor.fetchone()
                    await conn.commit()
                    
                    if result:
                        post_dict = dict(result)
                        post_dict['has_image'] = bool(post_dict.get('base64_image'))
                        if post_dict.get('base64_image'):
                            post_dict['image_data_url'] = ImageService.create_data_url(
                                post_dict['base64_image'],
                                post_dict['image_mime_type']
                            )
                        print(f"CRUD: Updated post '{post_id}'")
                        return post_dict
                    return None
                    
        except Exception as e:
            print(f"CRUD Error updating post: {e}")
            return None

    async def delete_post(self, organization_name: str, post_id: str) -> bool:
        
        try:
            async with db.get_async_connection() as conn:
                async with conn.cursor() as cursor:
                    
                    await cursor.execute('''
                        SELECT id FROM public.organizations 
                        WHERE name = %s AND deleted_at IS NULL
                    ''', (organization_name,))
                    org_result = await cursor.fetchone()
                    
                    if not org_result:
                        print(f"ERROR: Organization '{organization_name}' not found")
                        return False
                    
                    organization_id = org_result['id']

                    
                    await cursor.execute('''
                        UPDATE public.posts 
                        SET deleted_at = CURRENT_TIMESTAMP,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE organization_id = %s 
                          AND id = %s 
                          AND deleted_at IS NULL
                        RETURNING id
                    ''', (organization_id, post_id))
                    
                    result = await cursor.fetchone()
                    await conn.commit()
                    
                    if result:
                        print(f"CRUD: Deleted post '{post_id}'")
                        return True
                    else:
                        print(f"CRUD: Post '{post_id}' not found")
                        return False
                    
        except Exception as e:
            print(f"CRUD Error deleting post: {e}")
            return False

    async def restore_post(self, organization_name: str, post_id: str) -> bool:
        
        try:
            async with db.get_async_connection() as conn:
                async with conn.cursor() as cursor:
                    
                    await cursor.execute('''
                        SELECT id FROM public.organizations 
                        WHERE name = %s AND deleted_at IS NULL
                    ''', (organization_name,))
                    org_result = await cursor.fetchone()
                    
                    if not org_result:
                        print(f"ERROR: Organization '{organization_name}' not found")
                        return False
                    
                    organization_id = org_result['id']

                    
                    await cursor.execute('''
                        UPDATE public.posts 
                        SET deleted_at = NULL,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE organization_id = %s 
                          AND id = %s 
                          AND deleted_at IS NOT NULL
                        RETURNING id
                    ''', (organization_id, post_id))
                    
                    result = await cursor.fetchone()
                    await conn.commit()
                    
                    if result:
                        print(f"CRUD: Restored post '{post_id}'")
                        return True
                    else:
                        print(f"CRUD: Post '{post_id}' not found or not deleted")
                        return False
                    
        except Exception as e:
            print(f"CRUD Error restoring post: {e}")
            return False

    async def upload_post_image(self,
                               organization_name: str,
                               post_id: str,
                               base64_image: str,
                               mime_type: str,
                               alt_text: Optional[str] = None) -> Optional[Dict[str, Any]]:
        
        try:
            
            image_info = await ImageService.validate_and_process_image(base64_image, mime_type)
            
            async with db.get_async_connection() as conn:
                async with conn.cursor() as cursor:
                    
                    await cursor.execute('''
                        SELECT id FROM public.organizations 
                        WHERE name = %s AND deleted_at IS NULL
                    ''', (organization_name,))
                    org_result = await cursor.fetchone()
                    
                    if not org_result:
                        print(f"ERROR: Organization '{organization_name}' not found")
                        return None
                    
                    organization_id = org_result['id']

                    
                    await cursor.execute('''
                        UPDATE public.posts 
                        SET base64_image = %s,
                            image_mime_type = %s,
                            image_url = NULL,
                            image_alt = COALESCE(%s, image_alt),
                            updated_at = CURRENT_TIMESTAMP
                        WHERE organization_id = %s 
                          AND id = %s 
                          AND deleted_at IS NULL
                        RETURNING *
                    ''', (image_info['base64_data'], 
                          image_info['mime_type'], 
                          alt_text,
                          organization_id, 
                          post_id))
                    
                    result = await cursor.fetchone()
                    await conn.commit()
                    
                    if result:
                        post_dict = dict(result)
                        post_dict['has_image'] = True
                        post_dict['image_data_url'] = ImageService.create_data_url(
                            post_dict['base64_image'],
                            post_dict['image_mime_type']
                        )
                        print(f"CRUD: Uploaded image for post '{post_id}'")
                        return post_dict
                    else:
                        print(f"CRUD: Post '{post_id}' not found")
                        return None
                    
        except Exception as e:
            print(f"CRUD Error uploading post image: {e}")
            return None

    async def remove_post_image(self,
                               organization_name: str,
                               post_id: str) -> Optional[Dict[str, Any]]:
        
        try:
            async with db.get_async_connection() as conn:
                async with conn.cursor() as cursor:
                    
                    await cursor.execute('''
                        SELECT id FROM public.organizations 
                        WHERE name = %s AND deleted_at IS NULL
                    ''', (organization_name,))
                    org_result = await cursor.fetchone()
                    
                    if not org_result:
                        print(f"ERROR: Organization '{organization_name}' not found")
                        return None
                    
                    organization_id = org_result['id']

                    
                    await cursor.execute('''
                        UPDATE public.posts 
                        SET base64_image = NULL,
                            image_mime_type = NULL,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE organization_id = %s 
                          AND id = %s 
                          AND deleted_at IS NULL
                        RETURNING *
                    ''', (organization_id, post_id))
                    
                    result = await cursor.fetchone()
                    await conn.commit()
                    
                    if result:
                        post_dict = dict(result)
                        post_dict['has_image'] = False
                        print(f"CRUD: Removed image from post '{post_id}'")
                        return post_dict
                    else:
                        print(f"CRUD: Post '{post_id}' not found")
                        return None
                    
        except Exception as e:
            print(f"CRUD Error removing post image: {e}")
            return None

    async def get_post_image(self,
                            organization_name: str,
                            post_id: str,
                            as_data_url: bool = True) -> Optional[Dict[str, Any]]:
        
        try:
            async with db.get_async_connection() as conn:
                async with conn.cursor() as cursor:
                    
                    await cursor.execute('''
                        SELECT id FROM public.organizations 
                        WHERE name = %s AND deleted_at IS NULL
                    ''', (organization_name,))
                    org_result = await cursor.fetchone()
                    
                    if not org_result:
                        print(f"ERROR: Organization '{organization_name}' not found")
                        return None
                    
                    organization_id = org_result['id']

                    await cursor.execute('''
                        SELECT base64_image, image_mime_type, image_alt
                        FROM public.posts 
                        WHERE organization_id = %s 
                          AND id = %s 
                          AND base64_image IS NOT NULL
                          AND deleted_at IS NULL
                    ''', (organization_id, post_id))
                    
                    result = await cursor.fetchone()
                    
                    if result:
                        image_data = dict(result)
                        if as_data_url:
                            image_data['data_url'] = ImageService.create_data_url(
                                image_data['base64_image'],
                                image_data['image_mime_type']
                            )
                        return image_data
                    else:
                        print(f"CRUD: Image not found for post '{post_id}'")
                        return None
                    
        except Exception as e:
            print(f"CRUD Error getting post image: {e}")
            return None

    async def publish_post(self, organization_name: str, post_id: str) -> Optional[Dict[str, Any]]:
        
        try:
            async with db.get_async_connection() as conn:
                async with conn.cursor() as cursor:
                    
                    await cursor.execute('''
                        SELECT id FROM public.organizations 
                        WHERE name = %s AND deleted_at IS NULL
                    ''', (organization_name,))
                    org_result = await cursor.fetchone()
                    
                    if not org_result:
                        print(f"ERROR: Organization '{organization_name}' not found")
                        return None
                    
                    organization_id = org_result['id']

                    await cursor.execute('''
                        UPDATE public.posts 
                        SET status = 'published',
                            published_at = CURRENT_TIMESTAMP,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE organization_id = %s 
                          AND id = %s 
                          AND status != 'published'
                          AND deleted_at IS NULL
                        RETURNING *
                    ''', (organization_id, post_id))
                    
                    result = await cursor.fetchone()
                    await conn.commit()
                    
                    if result:
                        post_dict = dict(result)
                        post_dict['has_image'] = bool(post_dict.get('base64_image'))
                        if post_dict.get('base64_image'):
                            post_dict['image_data_url'] = ImageService.create_data_url(
                                post_dict['base64_image'],
                                post_dict['image_mime_type']
                            )
                        print(f"CRUD: Published post '{post_id}'")
                        return post_dict
                    else:
                        print(f"CRUD: Post '{post_id}' not found or already published")
                        return None
                    
        except Exception as e:
            print(f"CRUD Error publishing post: {e}")
            return None

    async def schedule_post(self, 
                           organization_name: str, 
                           post_id: str, 
                           scheduled_at: datetime) -> Optional[Dict[str, Any]]:
        
        try:
            async with db.get_async_connection() as conn:
                async with conn.cursor() as cursor:
                    
                    await cursor.execute('''
                        SELECT id FROM public.organizations 
                        WHERE name = %s AND deleted_at IS NULL
                    ''', (organization_name,))
                    org_result = await cursor.fetchone()
                    
                    if not org_result:
                        print(f"ERROR: Organization '{organization_name}' not found")
                        return None
                    
                    organization_id = org_result['id']

                    await cursor.execute('''
                        UPDATE public.posts 
                        SET status = 'scheduled',
                            scheduled_at = %s,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE organization_id = %s 
                          AND id = %s 
                          AND deleted_at IS NULL
                        RETURNING *
                    ''', (scheduled_at, organization_id, post_id))
                    
                    result = await cursor.fetchone()
                    await conn.commit()
                    
                    if result:
                        post_dict = dict(result)
                        post_dict['has_image'] = bool(post_dict.get('base64_image'))
                        if post_dict.get('base64_image'):
                            post_dict['image_data_url'] = ImageService.create_data_url(
                                post_dict['base64_image'],
                                post_dict['image_mime_type']
                            )
                        print(f"CRUD: Scheduled post '{post_id}' for {scheduled_at}")
                        return post_dict
                    else:
                        print(f"CRUD: Post '{post_id}' not found")
                        return None
                    
        except Exception as e:
            print(f"CRUD Error scheduling post: {e}")
            return None

    async def get_scheduled_posts_ready(self, organization_name: str) -> List[Dict[str, Any]]:
        
        try:
            async with db.get_async_connection() as conn:
                async with conn.cursor() as cursor:
                    
                    await cursor.execute('''
                        SELECT id FROM public.organizations 
                        WHERE name = %s AND deleted_at IS NULL
                    ''', (organization_name,))
                    org_result = await cursor.fetchone()
                    
                    if not org_result:
                        print(f"ERROR: Organization '{organization_name}' not found")
                        return []
                    
                    organization_id = org_result['id']

                    await cursor.execute('''
                        SELECT 
                            p.*,
                            u.username,
                            u.email as user_email
                        FROM public.posts p
                        LEFT JOIN public.users u ON p.user_id = u.id
                        WHERE p.organization_id = %s 
                          AND p.status = 'scheduled'
                          AND p.scheduled_at <= CURRENT_TIMESTAMP
                          AND p.deleted_at IS NULL
                        ORDER BY p.scheduled_at ASC
                    ''', (organization_id,))
                    
                    results = await cursor.fetchall()
                    
                    
                    processed_results = []
                    for row in results:
                        post_dict = dict(row)
                        post_dict['has_image'] = bool(post_dict.get('base64_image'))
                        if post_dict.get('base64_image'):
                            post_dict['image_data_url'] = ImageService.create_data_url(
                                post_dict['base64_image'],
                                post_dict['image_mime_type']
                            )
                        processed_results.append(post_dict)
                    
                    print(f"CRUD: Retrieved {len(processed_results)} scheduled posts ready for publishing")
                    return processed_results
                    
        except Exception as e:
            print(f"CRUD Error getting scheduled posts: {e}")
            return []

    async def publish_scheduled_posts(self, organization_name: str) -> Dict[str, Any]:
        
        try:
            scheduled_posts = await self.get_scheduled_posts_ready(organization_name)
            
            if not scheduled_posts:
                return {
                    'success': True,
                    'message': "No scheduled posts ready for publishing",
                    'published_count': 0
                }
            
            published_count = 0
            async with db.get_async_connection() as conn:
                async with conn.cursor() as cursor:
                    for post in scheduled_posts:
                        await cursor.execute('''
                            UPDATE public.posts 
                            SET status = 'published',
                                published_at = CURRENT_TIMESTAMP,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE id = %s
                        ''', (post['id'],))
                        published_count += 1
                    
                    await conn.commit()
            
            return {
                'success': True,
                'message': f"Published {published_count} scheduled posts",
                'published_count': published_count
            }
                    
        except Exception as e:
            print(f"CRUD Error publishing scheduled posts: {e}")
            return {
                'success': False,
                'message': f"Error: {str(e)}",
                'published_count': 0
            }

    async def get_post_stats(self, organization_name: str) -> Dict[str, Any]:
        
        try:
            async with db.get_async_connection() as conn:
                async with conn.cursor() as cursor:
                    
                    await cursor.execute('''
                        SELECT id FROM public.organizations 
                        WHERE name = %s AND deleted_at IS NULL
                    ''', (organization_name,))
                    org_result = await cursor.fetchone()
                    
                    if not org_result:
                        return {
                            'success': False,
                            'message': f"Organization '{organization_name}' not found",
                            'stats': {}
                        }
                    
                    organization_id = org_result['id']

                    
                    await cursor.execute('''
                        SELECT 
                            COUNT(*) as total,
                            COUNT(CASE WHEN status = 'draft' THEN 1 END) as drafts,
                            COUNT(CASE WHEN status = 'scheduled' THEN 1 END) as scheduled,
                            COUNT(CASE WHEN status = 'published' THEN 1 END) as published,
                            COUNT(CASE WHEN deleted_at IS NOT NULL THEN 1 END) as deleted,
                            COUNT(CASE WHEN base64_image IS NOT NULL THEN 1 END) as with_images,
                            MIN(created_at) as oldest,
                            MAX(created_at) as newest
                        FROM public.posts 
                        WHERE organization_id = %s
                    ''', (organization_id,))
                    
                    basic_stats = await cursor.fetchone()
                    
                    
                    await cursor.execute('''
                        SELECT 
                            TO_CHAR(created_at, 'YYYY-MM') as month,
                            COUNT(*) as count
                        FROM public.posts 
                        WHERE organization_id = %s 
                          AND created_at >= CURRENT_DATE - INTERVAL '12 months'
                        GROUP BY TO_CHAR(created_at, 'YYYY-MM')
                        ORDER BY month DESC
                    ''', (organization_id,))
                    
                    monthly_stats = await cursor.fetchall()
                    
                    
                    await cursor.execute('''
                        SELECT 
                            COUNT(DISTINCT user_id) as active_users,
                            COUNT(*) as total_posts
                        FROM public.posts 
                        WHERE organization_id = %s 
                          AND deleted_at IS NULL
                    ''', (organization_id,))
                    
                    user_stats = await cursor.fetchone()
                    
                    stats_dict = dict(basic_stats) if basic_stats else {}
                    stats_dict['posts_by_month'] = {row['month']: row['count'] for row in monthly_stats}
                    
                    if user_stats and user_stats['active_users'] > 0:
                        stats_dict['avg_posts_per_user'] = user_stats['total_posts'] / user_stats['active_users']
                    else:
                        stats_dict['avg_posts_per_user'] = 0.0
                    
                    return {
                        'success': True,
                        'message': "Post statistics retrieved",
                        'stats': stats_dict
                    }
                    
        except Exception as e:
            print(f"CRUD Error getting post stats: {e}")
            return {
                'success': False,
                'message': f"Error: {str(e)}",
                'stats': {}
            }

    async def search_posts(self,
                          organization_name: str,
                          query: str,
                          search_in_title: bool = True,
                          search_in_content: bool = True,
                          search_in_excerpt: bool = True,
                          has_image: Optional[bool] = None,
                          limit: int = 50,
                          offset: int = 0) -> Dict[str, Any]:
        
        try:
            async with db.get_async_connection() as conn:
                async with conn.cursor() as cursor:
                    
                    await cursor.execute('''
                        SELECT id FROM public.organizations 
                        WHERE name = %s AND deleted_at IS NULL
                    ''', (organization_name,))
                    org_result = await cursor.fetchone()
                    
                    if not org_result:
                        return {
                            'success': False,
                            'message': f"Organization '{organization_name}' not found",
                            'query': query,
                            'count': 0,
                            'results': []
                        }
                    
                    organization_id = org_result['id']
                    search_pattern = f"%{query}%"
                    
                    
                    search_conditions = []
                    params = [organization_id]
                    
                    search_fields = []
                    if search_in_title:
                        search_fields.append('p.title')
                    if search_in_content:
                        search_fields.append('p.content')
                    if search_in_excerpt:
                        search_fields.append('p.excerpt')
                    
                    if search_fields:
                        like_conditions = []
                        for field in search_fields:
                            like_conditions.append(f"{field} ILIKE %s")
                            params.append(search_pattern)
                        search_conditions.append(f"({' OR '.join(like_conditions)})")
                    
                    if has_image is not None:
                        if has_image:
                            search_conditions.append('p.base64_image IS NOT NULL')
                        else:
                            search_conditions.append('p.base64_image IS NULL')
                    
                    if not search_conditions:
                        return {
                            'success': False,
                            'message': "No search criteria specified",
                            'query': query,
                            'count': 0,
                            'results': []
                        }
                    
                    search_query = ' AND '.join(search_conditions)
                    
                    
                    await cursor.execute(f'''
                        SELECT COUNT(*) as total
                        FROM public.posts p
                        WHERE p.organization_id = %s 
                          AND p.deleted_at IS NULL
                          AND {search_query}
                    ''', params)
                    
                    total_result = await cursor.fetchone()
                    total_count = total_result['total'] if total_result else 0
                    
                    
                    params_with_pagination = params.copy()
                    params_with_pagination.extend([limit, offset])
                    
                    await cursor.execute(f'''
                        SELECT 
                            p.*,
                            u.username,
                            u.email as user_email
                        FROM public.posts p
                        LEFT JOIN public.users u ON p.user_id = u.id
                        WHERE p.organization_id = %s 
                          AND p.deleted_at IS NULL
                          AND {search_query}
                        ORDER BY 
                            CASE 
                                WHEN p.title ILIKE %s THEN 1
                                WHEN p.content ILIKE %s THEN 2
                                WHEN p.excerpt ILIKE %s THEN 3
                                ELSE 4
                            END,
                            p.created_at DESC
                        LIMIT %s OFFSET %s
                    ''', params_with_pagination)
                    
                    results = await cursor.fetchall()
                    
                    
                    processed_results = []
                    for row in results:
                        post_dict = dict(row)
                        post_dict['has_image'] = bool(post_dict.get('base64_image'))
                        if post_dict.get('base64_image'):
                            post_dict['image_data_url'] = ImageService.create_data_url(
                                post_dict['base64_image'],
                                post_dict['image_mime_type']
                            )
                        processed_results.append(post_dict)
                    
                    return {
                        'success': True,
                        'query': query,
                        'count': len(processed_results),
                        'total_count': total_count,
                        'results': processed_results
                    }
                    
        except Exception as e:
            print(f"CRUD Error searching posts: {e}")
            return {
                'success': False,
                'message': f"Error: {str(e)}",
                'query': query,
                'count': 0,
                'results': []
            }

    async def bulk_publish_posts(self,
                                organization_name: str,
                                post_ids: List[str]) -> Dict[str, Any]:
        
        
        try:
            if not post_ids:
                return {
                    'success': False,
                    'message': "No post IDs provided",
                    'published_count': 0
                }
            
            async with db.get_async_connection() as conn:
                async with conn.cursor() as cursor:
                    
                    await cursor.execute('''
                        SELECT id FROM public.organizations 
                        WHERE name = %s AND deleted_at IS NULL
                    ''', (organization_name,))
                    org_result = await cursor.fetchone()
                    
                    if not org_result:
                        return {
                            'success': False,
                            'message': f"Organization '{organization_name}' not found",
                            'published_count': 0
                        }
                    
                    organization_id = org_result['id']

                    
                    published_count = 0
                    for post_id in post_ids:
                        await cursor.execute('''
                            UPDATE public.posts 
                            SET status = 'published',
                                published_at = CURRENT_TIMESTAMP,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE organization_id = %s 
                              AND id = %s 
                              AND status != 'published'
                              AND deleted_at IS NULL
                        ''', (organization_id, post_id))
                        
                        if cursor.rowcount > 0:
                            published_count += 1
                    
                    await conn.commit()
                    
                    return {
                        'success': True,
                        'message': f"Published {published_count} of {len(post_ids)} posts",
                        'published_count': published_count,
                        'total_requested': len(post_ids)
                    }
                    
        except Exception as e:
            print(f"CRUD Error bulk publishing posts: {e}")
            return {
                'success': False,
                'message': f"Error: {str(e)}",
                'published_count': 0
            }

    async def bulk_delete_posts(self,
                               organization_name: str,
                               post_ids: List[str]) -> Dict[str, Any]:
        
        
        try:
            if not post_ids:
                return {
                    'success': False,
                    'message': "No post IDs provided",
                    'deleted_count': 0
                }
            
            async with db.get_async_connection() as conn:
                async with conn.cursor() as cursor:
                    # Get organization_id
                    await cursor.execute('''
                        SELECT id FROM public.organizations 
                        WHERE name = %s AND deleted_at IS NULL
                    ''', (organization_name,))
                    org_result = await cursor.fetchone()
                    
                    if not org_result:
                        return {
                            'success': False,
                            'message': f"Organization '{organization_name}' not found",
                            'deleted_count': 0
                        }
                    
                    organization_id = org_result['id']

                    
                    deleted_count = 0
                    for post_id in post_ids:
                        await cursor.execute('''
                            UPDATE public.posts 
                            SET deleted_at = CURRENT_TIMESTAMP,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE organization_id = %s 
                              AND id = %s 
                              AND deleted_at IS NULL
                        ''', (organization_id, post_id))
                        
                        if cursor.rowcount > 0:
                            deleted_count += 1
                    
                    await conn.commit()
                    
                    return {
                        'success': True,
                        'message': f"Deleted {deleted_count} of {len(post_ids)} posts",
                        'deleted_count': deleted_count,
                        'total_requested': len(post_ids)
                    }
                    
        except Exception as e:
            print(f"CRUD Error bulk deleting posts: {e}")
            return {
                'success': False,
                'message': f"Error: {str(e)}",
                'deleted_count': 0
            }

    async def bulk_update_images(self,
                                organization_name: str,
                                updates: List[Dict[str, Any]]) -> Dict[str, Any]:
        
        try:
            if not updates:
                return {
                    'success': False,
                    'message': "No updates provided",
                    'updated_count': 0
                }
            
            async with db.get_async_connection() as conn:
                async with conn.cursor() as cursor:
                    
                    await cursor.execute('''
                        SELECT id FROM public.organizations 
                        WHERE name = %s AND deleted_at IS NULL
                    ''', (organization_name,))
                    org_result = await cursor.fetchone()
                    
                    if not org_result:
                        return {
                            'success': False,
                            'message': f"Organization '{organization_name}' not found",
                            'updated_count': 0
                        }
                    
                    organization_id = org_result['id']

                    updated_count = 0
                    for update in updates:
                        post_id = update.get('post_id')
                        base64_image = update.get('base64_image')
                        mime_type = update.get('image_mime_type')
                        alt_text = update.get('image_alt')
                        
                        if not all([post_id, base64_image, mime_type]):
                            continue
                        
                        
                        try:
                            image_info = await ImageService.validate_and_process_image(base64_image, mime_type)
                            
                            await cursor.execute('''
                                UPDATE public.posts 
                                SET base64_image = %s,
                                    image_mime_type = %s,
                                    image_alt = COALESCE(%s, image_alt),
                                    updated_at = CURRENT_TIMESTAMP
                                WHERE organization_id = %s 
                                  AND id = %s 
                                  AND deleted_at IS NULL
                            ''', (image_info['base64_data'],
                                  image_info['mime_type'],
                                  alt_text,
                                  organization_id,
                                  post_id))
                            
                            if cursor.rowcount > 0:
                                updated_count += 1
                                
                        except Exception as e:
                            print(f"ERROR: Failed to update image for post {post_id}: {e}")
                            continue
                    
                    await conn.commit()
                    
                    return {
                        'success': True,
                        'message': f"Updated images for {updated_count} of {len(updates)} posts",
                        'updated_count': updated_count,
                        'total_requested': len(updates)
                    }
                    
        except Exception as e:
            print(f"CRUD Error bulk updating images: {e}")
            return {
                'success': False,
                'message': f"Error: {str(e)}",
                'updated_count': 0
            }

    def _generate_slug(self, title: str) -> str:
        
        import re
        
        slug = title.lower()
        
        slug = re.sub(r'[^\w\s-]', '', slug)
        slug = re.sub(r'[-\s]+', '-', slug)
        
        slug = slug.strip('-')
        return slug





post_crud = PostCRUD()
user_crud = UserCRUD()
project_crud = ProjectCRUD()