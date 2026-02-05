import uuid
import re
import json
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
from app.database import db
from app.user_service import user_service

class ProjectService:
    def _validate_project_code(self, code: str) -> bool:
        
        pattern = r'^[A-Z0-9]{2,}-[A-Z0-9]{1,}$'
        return bool(re.match(pattern, code))
    
    def _get_organization_id_by_name(self, organization_name: str) -> Optional[str]:
        
        try:
            return user_service.get_organization_id_by_name(organization_name)
        except Exception as e:
            print(f"Error getting organization ID for '{organization_name}': {e}")
            return None
    
    def _get_user_id_by_username_or_email(self, username_or_email: str, organization_name: str) -> Optional[str]:
        
        try:
            org_id = self._get_organization_id_by_name(organization_name)
            if not org_id:
                return None
            
            with db.get_connection() as conn:
                with conn.cursor() as cursor:
                    
                    cursor.execute('''
                        SELECT id 
                        FROM public.users 
                        WHERE name = %s 
                          AND organization_id = %s
                          AND deleted_at IS NULL
                    ''', (username_or_email, org_id))
                    
                    result = cursor.fetchone()
                    if result:
                        return result['id']
                    
                    
                    cursor.execute('''
                        SELECT id 
                        FROM public.users 
                        WHERE email = %s 
                          AND organization_id = %s
                          AND deleted_at IS NULL
                    ''', (username_or_email, org_id))
                    
                    result = cursor.fetchone()
                    return result['id'] if result else None
                    
        except Exception as e:
            print(f"Error getting user ID for '{username_or_email}': {e}")
            return None
    
    def _prepare_settings_for_db(self, settings: Optional[Dict[str, Any]]) -> str:
        
        if not settings:
            return '{}'
        
        try:
            
            return json.dumps(settings, ensure_ascii=False)
        except (TypeError, ValueError) as e:
            print(f"Warning: Error converting settings to JSON: {e}")
            return '{}'
    
    def _parse_settings_from_db(self, settings_str: Optional[str]) -> Dict[str, Any]:
        
        if not settings_str:
            return {}
        
        try:
            
            return json.loads(settings_str)
        except (json.JSONDecodeError, TypeError) as e:
            print(f"Warning: Error parsing settings from DB: {e}")
            return {}
    
    def create_project(self, 
                      organization_name: str,
                      name: str,
                      code: str,
                      owner_username: str,
                      description: Optional[str] = None,
                      template_agile_method: str = 'Scrum',
                      settings: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        
        try:
            
            if not self._validate_project_code(code):
                print(f"ERROR: Invalid project code format: {code}")
                return None
            
            
            organization_id = self._get_organization_id_by_name(organization_name)
            if not organization_id:
                print(f"ERROR: Organization '{organization_name}' not found")
                return None
            
            owner_id = self._get_user_id_by_username_or_email(owner_username, organization_name)
            if not owner_id:
                print(f"ERROR: Owner '{owner_username}' not found in organization '{organization_name}'")
                return None
            
            
            project_id = str(uuid.uuid4())
            project_settings_json = self._prepare_settings_for_db(settings)
            
            print(f"DEBUG: Creating project with settings: {project_settings_json}")
            
            with db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        INSERT INTO boards.projects (
                            id, organization_id, name, code, description, 
                            owner_id, template_agile_method, settings
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                        RETURNING *
                    ''', (
                        project_id,
                        organization_id,
                        name,
                        code,
                        description,
                        owner_id,
                        template_agile_method,
                        project_settings_json
                    ))
                    
                    result = cursor.fetchone()
                    conn.commit()
                    
                    if result:
                        print(f"SUCCESS: Project '{code}' created in organization '{organization_name}'")
                        project_data = dict(result)
                        
                        project_data['settings'] = self._parse_settings_from_db(project_data.get('settings'))
                        project_data['owner_username'] = owner_username
                        return project_data
                    return None
                    
        except Exception as e:
            print(f"ERROR creating project '{code}': {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_project(self, organization_name: str, project_code: str) -> Optional[Dict[str, Any]]:
        
        try:
            organization_id = self._get_organization_id_by_name(organization_name)
            if not organization_id:
                return None
            
            with db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        SELECT 
                            p.*,
                            o.name as organization_name,
                            u.name as owner_name,
                            u.email as owner_email
                        FROM boards.projects p
                        LEFT JOIN public.organizations o ON p.organization_id = o.id
                        LEFT JOIN public.users u ON p.owner_id = u.id
                        WHERE p.organization_id = %s 
                          AND p.code = %s 
                          AND p.deleted_at IS NULL
                    ''', (organization_id, project_code))
                    
                    result = cursor.fetchone()
                    if result:
                        project_data = dict(result)
                        
                        project_data['settings'] = self._parse_settings_from_db(project_data.get('settings'))
                        
                        project_data['owner_username'] = project_data.get('owner_name') or project_data.get('owner_email')
                        return project_data
                    return None
                    
        except Exception as e:
            print(f"ERROR getting project '{project_code}': {e}")
            return None
    
    def get_all_projects(self, 
                        organization_name: str,
                        active_only: bool = True,
                        limit: int = 100,
                        offset: int = 0) -> List[Dict[str, Any]]:
        
        try:
            organization_id = self._get_organization_id_by_name(organization_name)
            if not organization_id:
                return []
            
            with db.get_connection() as conn:
                with conn.cursor() as cursor:
                    query = '''
                        SELECT 
                            p.*,
                            u.name as owner_name,
                            u.email as owner_email,
                            COUNT(DISTINCT wi.id) as work_item_count
                        FROM boards.projects p
                        LEFT JOIN public.users u ON p.owner_id = u.id
                        LEFT JOIN boards.work_items wi ON p.id = wi.project_id 
                            AND p.organization_id = wi.organization_id 
                            AND wi.deleted_at IS NULL
                        WHERE p.organization_id = %s 
                          AND p.deleted_at IS NULL
                    '''
                    
                    params = [organization_id]
                    
                    if active_only:
                        query += ' AND p.is_active = true'
                    
                    query += '''
                        GROUP BY p.id, u.name, u.email
                        ORDER BY p.created_at DESC
                        LIMIT %s OFFSET %s
                    '''
                    
                    params.extend([limit, offset])
                    
                    cursor.execute(query, params)
                    results = cursor.fetchall()
                    
                    projects = []
                    for row in results:
                        project_data = dict(row)
                        
                        project_data['settings'] = self._parse_settings_from_db(project_data.get('settings'))
                        
                        project_data['owner_username'] = project_data.get('owner_name') or project_data.get('owner_email')
                        projects.append(project_data)
                    
                    return projects
                    
        except Exception as e:
            print(f"ERROR getting projects for '{organization_name}': {e}")
            return []
    
    def update_project(self,
                      organization_name: str,
                      project_code: str,
                      updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        
        try:
            organization_id = self._get_organization_id_by_name(organization_name)
            if not organization_id:
                return None
            
            
            allowed_fields = {
                'name', 'description', 'owner_username', 
                'template_agile_method', 'is_active', 'settings'
            }
            
            set_clauses = []
            params = []
            
            
            if 'owner_username' in updates:
                owner_id = self._get_user_id_by_username_or_email(updates['owner_username'], organization_name)
                if not owner_id:
                    print(f"ERROR: New owner '{updates['owner_username']}' not found")
                    return None
                set_clauses.append("owner_id = %s")
                params.append(owner_id)
                
                updates = updates.copy()
                del updates['owner_username']
            
            
            if 'settings' in updates:
                settings_json = self._prepare_settings_for_db(updates['settings'])
                set_clauses.append("settings = %s::jsonb")
                params.append(settings_json)
                del updates['settings']
            
            
            for field, value in updates.items():
                if field in allowed_fields:
                    set_clauses.append(f"{field} = %s")
                    params.append(value)
            
            if not set_clauses:
                print("WARNING: No valid fields to update")
                return None
            
            
            set_clauses.append("updated_at = CURRENT_TIMESTAMP")
            
            
            params.append(organization_id)
            params.append(project_code)
            
            with db.get_connection() as conn:
                with conn.cursor() as cursor:
                    query = f'''
                        UPDATE boards.projects 
                        SET {', '.join(set_clauses)}
                        WHERE organization_id = %s 
                          AND code = %s 
                          AND deleted_at IS NULL
                        RETURNING *
                    '''
                    
                    cursor.execute(query, params)
                    result = cursor.fetchone()
                    conn.commit()
                    
                    if result:
                        print(f"SUCCESS: Project '{project_code}' updated")
                        project_data = dict(result)
                        
                        project_data['settings'] = self._parse_settings_from_db(project_data.get('settings'))
                        return project_data
                    return None
                    
        except Exception as e:
            print(f"ERROR updating project '{project_code}': {e}")
            return None
    
    def delete_project(self, organization_name: str, project_code: str) -> bool:
        
        try:
            organization_id = self._get_organization_id_by_name(organization_name)
            if not organization_id:
                return False
            
            with db.get_connection() as conn:
                with conn.cursor() as cursor:
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
                        print(f"SUCCESS: Project '{project_code}' soft deleted")
                        return True
                    print(f"WARNING: Project '{project_code}' not found or already deleted")
                    return False
                    
        except Exception as e:
            print(f"ERROR deleting project '{project_code}': {e}")
            return False
    
    def restore_project(self, organization_name: str, project_code: str) -> bool:
        
        try:
            organization_id = self._get_organization_id_by_name(organization_name)
            if not organization_id:
                return False
            
            with db.get_connection() as conn:
                with conn.cursor() as cursor:
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
                        print(f"SUCCESS: Project '{project_code}' restored")
                        return True
                    print(f"WARNING: Project '{project_code}' not found or not deleted")
                    return False
                    
        except Exception as e:
            print(f"ERROR restoring project '{project_code}': {e}")
            return False
    
    def add_project_member(self,
                          organization_name: str,
                          project_code: str,
                          username: str,
                          role: str = 'Member') -> bool:
        
        try:
            organization_id = self._get_organization_id_by_name(organization_name)
            if not organization_id:
                return False
            
            
            user_id = self._get_user_id_by_username_or_email(username, organization_name)
            if not user_id:
                print(f"ERROR: User '{username}' not found")
                return False
            
            
            project = self.get_project(organization_name, project_code)
            if not project:
                print(f"ERROR: Project '{project_code}' not found")
                return False
            
            with db.get_connection() as conn:
                with conn.cursor() as cursor:
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
                    ''', (project['id'], user_id, organization_id, role))
                    
                    result = cursor.fetchone()
                    conn.commit()
                    
                    if result:
                        print(f"SUCCESS: User '{username}' added to project '{project_code}' as {role}")
                        return True
                    return False
                    
        except Exception as e:
            print(f"ERROR adding member '{username}' to project '{project_code}': {e}")
            return False
    
    def remove_project_member(self,
                             organization_name: str,
                             project_code: str,
                             username: str) -> bool:
        
        try:
            organization_id = self._get_organization_id_by_name(organization_name)
            if not organization_id:
                return False
            
            
            user_id = self._get_user_id_by_username_or_email(username, organization_name)
            if not user_id:
                print(f"ERROR: User '{username}' not found")
                return False
            
            
            project = self.get_project(organization_name, project_code)
            if not project:
                print(f"ERROR: Project '{project_code}' not found")
                return False
            
            with db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        UPDATE boards.project_members 
                        SET left_at = CURRENT_TIMESTAMP
                        WHERE project_id = %s 
                          AND user_id = %s 
                          AND organization_id = %s
                          AND left_at IS NULL
                        RETURNING project_id
                    ''', (project['id'], user_id, organization_id))
                    
                    result = cursor.fetchone()
                    conn.commit()
                    
                    if result:
                        print(f"SUCCESS: User '{username}' removed from project '{project_code}'")
                        return True
                    print(f"WARNING: User '{username}' not found in project '{project_code}'")
                    return False
                    
        except Exception as e:
            print(f"ERROR removing member '{username}' from project '{project_code}': {e}")
            return False
    
    def get_project_members(self,
                           organization_name: str,
                           project_code: str) -> List[Dict[str, Any]]:
        
        try:
            organization_id = self._get_organization_id_by_name(organization_name)
            if not organization_id:
                return []
            
            project = self.get_project(organization_name, project_code)
            if not project:
                return []
            
            with db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        SELECT 
                            pm.*,
                            u.name,
                            u.email,
                            u.full_name
                        FROM boards.project_members pm
                        JOIN public.users u ON pm.user_id = u.id
                        WHERE pm.project_id = %s 
                          AND pm.organization_id = %s
                          AND pm.left_at IS NULL
                          AND u.deleted_at IS NULL
                        ORDER BY pm.joined_at
                    ''', (project['id'], organization_id))
                    
                    results = cursor.fetchall()
                    return [dict(row) for row in results]
                    
        except Exception as e:
            print(f"ERROR getting members for project '{project_code}': {e}")
            return []
    
    def get_project_stats(self, organization_name: str, project_code: str) -> Optional[Dict[str, Any]]:
        
        try:
            organization_id = self._get_organization_id_by_name(organization_name)
            if not organization_id:
                return None
            
            project = self.get_project(organization_name, project_code)
            if not project:
                return None
            
            with db.get_connection() as conn:
                with conn.cursor() as cursor:
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
                    ''', (project['id'], organization_id))
                    
                    result = cursor.fetchone()
                    return dict(result) if result else {}
                    
        except Exception as e:
            print(f"ERROR getting stats for project '{project_code}': {e}")
            return None
    
    def search_projects(self,
                       organization_name: str,
                       query: str,
                       limit: int = 50) -> List[Dict[str, Any]]:
        
        try:
            organization_id = self._get_organization_id_by_name(organization_name)
            if not organization_id:
                return []
            
            search_pattern = f"%{query}%"
            
            with db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        SELECT 
                            p.*,
                            u.name as owner_name,
                            u.email as owner_email
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
                    
                    projects = []
                    for row in results:
                        project_data = dict(row)
                        
                        project_data['settings'] = self._parse_settings_from_db(project_data.get('settings'))
                        
                        project_data['owner_username'] = project_data.get('owner_name') or project_data.get('owner_email')
                        projects.append(project_data)
                    
                    return projects
                    
        except Exception as e:
            print(f"ERROR searching projects with query '{query}': {e}")
            return []

    def get_raw_projects(self,
                        organization_name: Optional[str] = None,
                        limit: int = 1000,
                        offset: int = 0) -> List[Dict[str, Any]]:

        try:
            with db.get_connection() as conn:
                with conn.cursor() as cursor:
                    query = '''
                        SELECT
                            id,
                            organization_id,
                            name,
                            code,
                            description,
                            owner_id,
                            template_agile_method,
                            is_active,
                            created_at,
                            updated_at,
                            deleted_at
                            
                        FROM boards.projects
                    '''
                    params = []
                    if organization_name:
                        organization_id = self._get_organization_id_by_name(organization_name)
                        if not organization_id:
                            print(f"WARNING: Organization '{organization_name}' not found")
                            return []
                        query += ' WHERE organization_id = %s'
                        params.append(organization_id)
                    query += '''
                        ORDER BY organization_id, created_at DESC
                        LIMIT %s OFFSET %s
                    '''
                    params.extend([limit, offset])
                    cursor.execute(query, params)
                    results = cursor.fetchall()

                    projects = []
                    for row in results:
                        project_data = dict(row)
                        
                        projects.append(project_data)
                    print(f"DEBUG: Retrieved {len(projects)} raw projects")
                    return projects
        except Exception as e:
            print(f"ERROR getting raw projects: {e}")
            import traceback
            traceback.print_exc()
            return []


project_service = ProjectService()
