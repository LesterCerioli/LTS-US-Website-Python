import logging
from uuid import UUID
from datetime import date
from decimal import Decimal
from typing import List, Optional, Dict, Any
from app import exchange_rate_service
from app.database import db
from app.exchange_rate_service import ExchangeRateService


logger = logging.getLogger(__name__)


class CostService:
    
    def __init__(self, exchange_rate_service: Optional[ExchangeRateService] = None):
        
        self.exchange_rate_service = exchange_rate_service or ExchangeRateService()

    async def create_cost(
        self,
        due_date: date,
        amount: Decimal,
        currency: str,
        payment_nature: str,
        cost_nature_code: str,
        organization_id: UUID,
        converted_amount_brl: Optional[Decimal] = None,
        exchange_rate_month: Optional[str] = None,
        exchange_rate_value: Optional[Decimal] = None,
        description: Optional[str] = None,
        status: str = "pending"
    ) -> Optional[Dict[str, Any]]:
        
        logger.info(f"Creating cost for organization: {organization_id}")
        
        if amount <= 0:
            raise Exception("Cost amount must be greater than zero")
        
        if not currency or len(currency) != 3:
            raise Exception("Currency must be a 3-letter code")
        
        
        if currency != 'BRL' and (exchange_rate_month is None or exchange_rate_value is None):
            try:
                
                if exchange_rate_month is None:
                    exchange_rate_month = due_date.strftime("%Y-%m")
                
                
                exchange_rate = await self.exchange_rate_service.get_exchange_rate_for_period(
                    organization_id=organization_id,
                    year_month=exchange_rate_month,
                    base_currency=currency,
                    target_currency='BRL'
                )
                
                if exchange_rate:
                    exchange_rate_value = Decimal(str(exchange_rate['rate']))
                    logger.info(f"Found exchange rate for {exchange_rate_month}: {exchange_rate_value}")
                                        
                    if converted_amount_brl is None:
                        converted_amount_brl = amount * exchange_rate_value
                        logger.info(f"Calculated converted_amount_brl: {converted_amount_brl}")
                else:
                    
                    exchange_rate_for_date = await self.exchange_rate_service.get_exchange_rate_for_date(
                        organization_id=organization_id,
                        target_date=due_date,
                        base_currency=currency,
                        target_currency='BRL'
                    )
                    
                    if exchange_rate_for_date:
                        exchange_rate_month = exchange_rate_for_date['year_month']
                        exchange_rate_value = Decimal(str(exchange_rate_for_date['rate']))
                        logger.info(f"Found exchange rate for date {due_date}: {exchange_rate_value}")
                        
                        if converted_amount_brl is None:
                            converted_amount_brl = amount * exchange_rate_value
                    else:
                        logger.warning(f"No exchange rate found for {currency} to BRL for period {exchange_rate_month}")
                        
                        
            except Exception as e:
                logger.error(f"Error fetching exchange rate: {e}")
                
        
        
        if currency == 'BRL' and converted_amount_brl is None:
            converted_amount_brl = amount
        
        try:
            async with db.get_async_connection() as conn:
                cursor = conn.cursor()
                                
                org_query = """
                    SELECT id FROM public.organizations 
                    WHERE id = %s AND deleted_at IS NULL
                """
                cursor.execute(org_query, (str(organization_id),))
                if not cursor.fetchone():
                    raise Exception(f"Organization with ID {organization_id} not found")

                insert_query = """
                    INSERT INTO accounting.costs (
                        due_date, amount, currency, payment_nature, cost_nature_code,
                        organization_id, converted_amount_brl, exchange_rate_month,
                        exchange_rate_value, description, status, created_at, updated_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                    )
                    RETURNING *
                """
                
                cursor.execute(
                    insert_query,
                    (
                        due_date,
                        float(amount),
                        currency,
                        payment_nature,
                        cost_nature_code,
                        str(organization_id),
                        float(converted_amount_brl) if converted_amount_brl else None,
                        exchange_rate_month,
                        float(exchange_rate_value) if exchange_rate_value else None,
                        description,
                        status
                    )
                )
                
                created_cost = cursor.fetchone()
                conn.commit()
                
                if not created_cost:
                    raise Exception("Failed to create cost")
                
                logger.info(f"Cost created successfully")
                return dict(created_cost)
        
        except Exception as e:
            logger.error(f"Error creating cost: {e}")
            raise Exception(f"Database error creating cost: {str(e)}")

    async def get_cost_by_id(self, cost_id: UUID) -> Optional[Dict[str, Any]]:
        
        logger.info(f"Fetching cost by ID: {cost_id}")
    
        try:
            async with db.get_async_connection() as conn:
                cursor = conn.cursor()
                query = """
                    SELECT * FROM accounting.costs 
                    WHERE id = %s AND deleted_at IS NULL
                """
            
                cursor.execute(query, (str(cost_id),))
                cost = cursor.fetchone()
            
                if not cost:
                    logger.warning(f"Cost not found with ID: {cost_id}")
                    return None
            
                logger.info(f"Cost found: {cost_id}")
                return dict(cost)
        
        except Exception as e:
            logger.error(f"Error fetching cost: {e}")
            raise Exception(f"Database error fetching cost: {str(e)}")

    async def update_cost(
        self,
        cost_id: UUID,
        due_date: Optional[date] = None,
        amount: Optional[Decimal] = None,
        currency: Optional[str] = None,
        payment_nature: Optional[str] = None,
        cost_nature_code: Optional[str] = None,
        converted_amount_brl: Optional[Decimal] = None,
        exchange_rate_month: Optional[str] = None,
        exchange_rate_value: Optional[Decimal] = None,
        description: Optional[str] = None,
        status: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        
        logger.info(f"Updating cost with ID: {cost_id}")
        
        try:
            
            current_cost = await self.get_cost_by_id(cost_id)
            if not current_cost:
                return None
                        
            
            if (currency is not None and currency != 'BRL') or (due_date is not None and current_cost['currency'] != 'BRL'):
                target_currency = currency if currency is not None else current_cost['currency']
                target_date = due_date if due_date is not None else current_cost['due_date']
                                
                try:
                    if exchange_rate_month is None:
                        exchange_rate_month = target_date.strftime("%Y-%m")
                    
                    if exchange_rate_value is None:
                        exchange_rate = await self.exchange_rate_service.get_exchange_rate_for_period(
                            organization_id=UUID(current_cost['organization_id']),
                            year_month=exchange_rate_month,
                            base_currency=target_currency,
                            target_currency='BRL'
                        )
                        
                        if exchange_rate:
                            exchange_rate_value = Decimal(str(exchange_rate['rate']))
                            logger.info(f"Found exchange rate for update: {exchange_rate_value}")
                                                        
                            if converted_amount_brl is None and amount is not None:
                                converted_amount_brl = amount * exchange_rate_value
                except Exception as e:
                    logger.error(f"Error fetching exchange rate during update: {e}")
                    
        
            async with db.get_async_connection() as conn:
                cursor = conn.cursor()
                                
                check_query = """
                    SELECT id FROM accounting.costs 
                    WHERE id = %s AND deleted_at IS NULL
                """
                cursor.execute(check_query, (str(cost_id),))
                if not cursor.fetchone():
                    return None

                update_fields = []
                params = []
                
                if due_date is not None:
                    update_fields.append("due_date = %s")
                    params.append(due_date)
                
                if amount is not None:
                    if amount <= 0:
                        raise Exception("Cost amount must be greater than zero")
                    update_fields.append("amount = %s")
                    params.append(float(amount))
                
                if currency is not None:
                    if len(currency) != 3:
                        raise Exception("Currency must be a 3-letter code")
                    update_fields.append("currency = %s")
                    params.append(currency)
                
                if payment_nature is not None:
                    update_fields.append("payment_nature = %s")
                    params.append(payment_nature)
                
                if cost_nature_code is not None:
                    update_fields.append("cost_nature_code = %s")
                    params.append(cost_nature_code)
                
                if converted_amount_brl is not None:
                    update_fields.append("converted_amount_brl = %s")
                    params.append(float(converted_amount_brl))
                
                if exchange_rate_month is not None:
                    update_fields.append("exchange_rate_month = %s")
                    params.append(exchange_rate_month)
                
                if exchange_rate_value is not None:
                    update_fields.append("exchange_rate_value = %s")
                    params.append(float(exchange_rate_value))
                
                if description is not None:
                    update_fields.append("description = %s")
                    params.append(description)
                
                if status is not None:
                    update_fields.append("status = %s")
                    params.append(status)
                
                if not update_fields:
                    return await self.get_cost_by_id(cost_id)
                
                update_fields.append("updated_at = CURRENT_TIMESTAMP")
                params.append(str(cost_id))
                
                update_query = f"""
                    UPDATE accounting.costs 
                    SET {', '.join(update_fields)}
                    WHERE id = %s AND deleted_at IS NULL
                    RETURNING *
                """
                
                cursor.execute(update_query, params)
                updated_cost = cursor.fetchone()
                conn.commit()
                
                if not updated_cost:
                    return None
                
                logger.info(f"Cost updated successfully: {cost_id}")
                return dict(updated_cost)
                
        except Exception as e:
            logger.error(f"Error updating cost: {e}")
            raise Exception(f"Database error updating cost: {str(e)}")

    async def delete_cost(self, cost_id: UUID) -> bool:
        
        logger.info(f"Deleting cost with ID: {cost_id}")
        
        try:
            async with db.get_async_connection() as conn:
                cursor = conn.cursor()
                
                delete_query = """
                    UPDATE accounting.costs 
                    SET deleted_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s AND deleted_at IS NULL
                """
                
                cursor.execute(delete_query, (str(cost_id),))
                conn.commit()
                
                success = cursor.rowcount > 0
                
                if not success:
                    logger.warning(f"Cost not found or already deleted: {cost_id}")
                    return False
                
                logger.info(f"Cost deleted successfully: {cost_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error deleting cost: {e}")
            raise Exception(f"Database error deleting cost: {str(e)}")

    async def get_organization_costs(
        self, 
        organization_id: UUID,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        status: Optional[str] = None,
        cost_nature_code: Optional[str] = None,
        currency: Optional[str] = None,
        page: int = 1,
        page_size: int = 50
    ) -> Dict[str, Any]:
        
        logger.info(f"Fetching costs for organization: {organization_id}")
        
        try:
            async with db.get_async_connection() as conn:
                cursor = conn.cursor()
                
                conditions = ["organization_id = %s", "deleted_at IS NULL"]
                params = [str(organization_id)]
                
                if start_date:
                    conditions.append("due_date >= %s")
                    params.append(start_date)
                
                if end_date:
                    conditions.append("due_date <= %s")
                    params.append(end_date)
                
                if status:
                    conditions.append("status = %s")
                    params.append(status)
                
                if cost_nature_code:
                    conditions.append("cost_nature_code = %s")
                    params.append(cost_nature_code)
                
                if currency:
                    conditions.append("currency = %s")
                    params.append(currency)
                
                where_clause = " AND ".join(conditions)
                                
                count_query = f"""
                    SELECT COUNT(*) as total 
                    FROM accounting.costs 
                    WHERE {where_clause}
                """
                
                cursor.execute(count_query, params)
                count_result = cursor.fetchone()
                total_count = count_result['total'] if count_result else 0
                
                
                offset = (page - 1) * page_size
                
                base_query = f"""
                    SELECT * FROM accounting.costs 
                    WHERE {where_clause}
                    ORDER BY due_date DESC, created_at DESC
                """
                
                base_query += " LIMIT %s OFFSET %s"
                params.extend([page_size, offset])
                
                cursor.execute(base_query, params)
                costs = cursor.fetchall()
                
                costs_list = [dict(cost) for cost in costs]
                total_pages = (total_count + page_size - 1) // page_size if page_size > 0 else 1
                
                logger.info(f"Found {len(costs_list)} costs for organization {organization_id}")
                
                return {
                    "costs": costs_list,
                    "total_count": total_count,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": total_pages
                }
                
        except Exception as e:
            logger.error(f"Error fetching organization costs: {e}")
            raise Exception(f"Database error fetching costs: {str(e)}")

    async def update_cost_status(self, cost_id: UUID, status: str) -> bool:
        
        logger.info(f"Updating cost status: {cost_id} -> {status}")
        
        valid_statuses = ['pending', 'paid', 'overdue', 'cancelled']
        if status not in valid_statuses:
            raise Exception(f"Invalid status. Must be one of: {valid_statuses}")
        
        try:
            async with db.get_async_connection() as conn:
                cursor = conn.cursor()
                
                query = """
                    UPDATE accounting.costs 
                    SET status = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s AND deleted_at IS NULL
                """
                
                cursor.execute(query, (status, str(cost_id)))
                conn.commit()
                
                success = cursor.rowcount > 0
                
                if not success:
                    logger.warning(f"Cost not found or not updated: {cost_id}")
                    return False
                
                logger.info(f"Cost status updated successfully: {cost_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error updating cost status: {e}")
            raise Exception(f"Database error updating cost status: {str(e)}")

    async def update_exchange_rate_data(
        self,
        cost_id: UUID,
        converted_amount_brl: Decimal,
        exchange_rate_month: str,
        exchange_rate_value: Decimal
    ) -> bool:
        
        logger.info(f"Updating exchange rate for cost: {cost_id}")
        
        try:
            async with db.get_async_connection() as conn:
                cursor = conn.cursor()
                
                query = """
                    UPDATE accounting.costs 
                    SET 
                        converted_amount_brl = %s,
                        exchange_rate_month = %s,
                        exchange_rate_value = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s AND deleted_at IS NULL
                """
                
                cursor.execute(
                    query, 
                    (
                        float(converted_amount_brl),
                        exchange_rate_month,
                        float(exchange_rate_value),
                        str(cost_id)
                    )
                )
                conn.commit()
                
                success = cursor.rowcount > 0
                
                if not success:
                    logger.warning(f"Cost not found or not updated: {cost_id}")
                    return False
                
                logger.info(f"Exchange rate updated successfully: {cost_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error updating exchange rate: {e}")
            raise Exception(f"Database error updating exchange rate: {str(e)}")

    async def get_costs_by_exchange_rate_month(
        self,
        organization_id: UUID,
        exchange_rate_month: str
    ) -> List[Dict[str, Any]]:
        
        logger.info(f"Fetching costs by exchange rate month: {exchange_rate_month}")
        
        try:
            async with db.get_async_connection() as conn:
                cursor = conn.cursor()
                
                query = """
                    SELECT * FROM accounting.costs
                    WHERE 
                        organization_id = %s 
                        AND exchange_rate_month = %s 
                        AND deleted_at IS NULL
                    ORDER BY due_date
                """
                
                cursor.execute(query, (str(organization_id), exchange_rate_month))
                costs = cursor.fetchall()
                
                costs_list = [dict(cost) for cost in costs]
                logger.info(f"Found {len(costs_list)} costs for month {exchange_rate_month}")
                
                return costs_list
                
        except Exception as e:
            logger.error(f"Error fetching costs by exchange rate month: {e}")
            raise Exception(f"Database error fetching costs: {str(e)}")

    async def get_monthly_summary(
        self,
        organization_id: UUID,
        year: int,
        month: int
    ) -> Dict[str, Any]:
        
        logger.info(f"Fetching monthly summary for {year}-{month}")
        
        try:
            async with db.get_async_connection() as conn:
                cursor = conn.cursor()
                
                query = """
                    SELECT 
                        COUNT(*) as total_costs,
                        COALESCE(SUM(amount), 0) as total_amount,
                        COALESCE(AVG(amount), 0) as average_amount,
                        COALESCE(MIN(amount), 0) as min_amount,
                        COALESCE(MAX(amount), 0) as max_amount,
                        COUNT(DISTINCT currency) as distinct_currencies,
                        COUNT(DISTINCT cost_nature_code) as distinct_natures,
                        SUM(CASE WHEN status = 'paid' THEN 1 ELSE 0 END) as paid_count,
                        SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending_count,
                        SUM(CASE WHEN status = 'overdue' THEN 1 ELSE 0 END) as overdue_count
                    FROM accounting.costs
                    WHERE 
                        organization_id = %s
                        AND EXTRACT(YEAR FROM due_date) = %s
                        AND EXTRACT(MONTH FROM due_date) = %s
                        AND deleted_at IS NULL
                """
                
                cursor.execute(query, (str(organization_id), year, month))
                result = cursor.fetchone()
                
                if not result:
                    return {}
                
                logger.info(f"Monthly summary fetched for {year}-{month}")
                return dict(result)
                
        except Exception as e:
            logger.error(f"Error fetching monthly summary: {e}")
            raise Exception(f"Database error fetching monthly summary: {str(e)}")

    async def bulk_update_status(
        self,
        cost_ids: List[UUID],
        status: str
    ) -> int:
        
        logger.info(f"Bulk updating status for {len(cost_ids)} costs to {status}")
        
        if not cost_ids:
            return 0
        
        valid_statuses = ['pending', 'paid', 'overdue', 'cancelled']
        if status not in valid_statuses:
            raise Exception(f"Invalid status. Must be one of: {valid_statuses}")
        
        try:
            async with db.get_async_connection() as conn:
                cursor = conn.cursor()
                
                id_strings = [str(cost_id) for cost_id in cost_ids]
                
                update_query = """
                    UPDATE accounting.costs 
                    SET status = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ANY(%s::uuid[]) AND deleted_at IS NULL
                """
                
                cursor.execute(update_query, (status, id_strings))
                conn.commit()
                                
                count_query = """
                    SELECT COUNT(*) as updated_count
                    FROM accounting.costs
                    WHERE id = ANY(%s::uuid[]) AND status = %s AND deleted_at IS NULL
                """
                cursor.execute(count_query, (id_strings, status))
                count_result = cursor.fetchone()
                
                updated_count = count_result['updated_count'] if count_result else 0
                logger.info(f"Bulk update completed: {updated_count} costs updated")
                
                return updated_count
                
        except Exception as e:
            logger.error(f"Error in bulk update status: {e}")
            raise Exception(f"Database error in bulk update: {str(e)}")

    async def restore_cost(self, cost_id: UUID) -> Optional[Dict[str, Any]]:
        
        logger.info(f"Restoring cost: {cost_id}")
        
        try:
            async with db.get_async_connection() as conn:
                cursor = conn.cursor()
                
                restore_query = """
                    UPDATE accounting.costs 
                    SET deleted_at = NULL, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s AND deleted_at IS NOT NULL
                    RETURNING *
                """
                
                cursor.execute(restore_query, (str(cost_id),))
                restored_cost = cursor.fetchone()
                conn.commit()
                
                if not restored_cost:
                    logger.warning(f"Cost not found or not deleted: {cost_id}")
                    return None
                
                logger.info(f"Cost restored successfully: {cost_id}")
                return dict(restored_cost)
                
        except Exception as e:
            logger.error(f"Error restoring cost: {e}")
            raise Exception(f"Database error restoring cost: {str(e)}")

    async def get_organization_summary(
        self,
        organization_id: UUID,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict[str, Any]:
        
        logger.info(f"Fetching organization summary for {organization_id}")
        
        try:
            async with db.get_async_connection() as conn:
                cursor = conn.cursor()
                
                conditions = ["organization_id = %s", "deleted_at IS NULL"]
                params = [str(organization_id)]
                
                if start_date:
                    conditions.append("due_date >= %s")
                    params.append(start_date)
                if end_date:
                    conditions.append("due_date <= %s")
                    params.append(end_date)
                
                where_clause = " AND ".join(conditions)
                
                query = f"""
                    SELECT 
                        COUNT(*) as total_costs,
                        COALESCE(SUM(amount), 0) as total_amount,
                        COALESCE(SUM(CASE WHEN status = 'pending' THEN amount ELSE 0 END), 0) as pending_amount,
                        COALESCE(SUM(CASE WHEN status = 'paid' THEN amount ELSE 0 END), 0) as paid_amount,
                        COALESCE(SUM(CASE WHEN status = 'overdue' THEN amount ELSE 0 END), 0) as overdue_amount,
                        SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending_count,
                        SUM(CASE WHEN status = 'paid' THEN 1 ELSE 0 END) as paid_count,
                        SUM(CASE WHEN status = 'overdue' THEN 1 ELSE 0 END) as overdue_count,
                        COUNT(DISTINCT currency) as distinct_currencies,
                        COUNT(DISTINCT cost_nature_code) as distinct_natures,
                        COALESCE(SUM(converted_amount_brl), 0) as total_converted_brl
                    FROM accounting.costs
                    WHERE {where_clause}
                """
                
                cursor.execute(query, params)
                result = cursor.fetchone()
                
                if not result:
                    return {}
                
                return dict(result)
                
        except Exception as e:
            logger.error(f"Error fetching organization summary: {e}")
            raise Exception(f"Database error fetching summary: {str(e)}")

    async def get_costs_without_exchange_rate(self, organization_id: UUID) -> List[Dict[str, Any]]:
        
        logger.info(f"Fetching costs without exchange rate for organization: {organization_id}")
        
        try:
            async with db.get_async_connection() as conn:
                cursor = conn.cursor()
                
                query = """
                    SELECT * FROM accounting.costs
                    WHERE 
                        organization_id = %s 
                        AND (exchange_rate_month IS NULL OR exchange_rate_value IS NULL)
                        AND currency != 'BRL'
                        AND deleted_at IS NULL
                    ORDER BY due_date
                """
                
                cursor.execute(query, (str(organization_id),))
                costs = cursor.fetchall()
                
                costs_list = [dict(cost) for cost in costs]
                logger.info(f"Found {len(costs_list)} costs without exchange rate")
                
                return costs_list
                
        except Exception as e:
            logger.error(f"Error fetching costs without exchange rate: {e}")
            raise Exception(f"Database error fetching costs: {str(e)}")

    async def get_overdue_costs(self, organization_id: UUID, cutoff_date: Optional[date] = None) -> List[Dict[str, Any]]:
        
        logger.info(f"Fetching overdue costs for organization: {organization_id}")
        
        try:
            async with db.get_async_connection() as conn:
                cursor = conn.cursor()
                
                if cutoff_date is None:
                    from datetime import date as dt_date
                    cutoff_date = dt_date.today()
                
                query = """
                    SELECT * FROM accounting.costs
                    WHERE 
                        organization_id = %s 
                        AND status = 'pending'
                        AND due_date < %s
                        AND deleted_at IS NULL
                    ORDER BY due_date
                """
                
                cursor.execute(query, (str(organization_id), cutoff_date))
                costs = cursor.fetchall()
                
                costs_list = [dict(cost) for cost in costs]
                logger.info(f"Found {len(costs_list)} overdue costs")
                
                return costs_list
                
        except Exception as e:
            logger.error(f"Error fetching overdue costs: {e}")
            raise Exception(f"Database error fetching costs: {str(e)}")

    async def auto_update_exchange_rates_for_costs(self, organization_id: UUID) -> Dict[str, Any]:
        
        logger.info(f"Auto-updating exchange rates for costs in organization: {organization_id}")
        
        try:
            
            costs_without_rate = await self.get_costs_without_exchange_rate(organization_id)
            
            if not costs_without_rate:
                return {
                    "success": True,
                    "message": "No costs without exchange rate found",
                    "updated_count": 0
                }
            
            updated_count = 0
            failed_count = 0
            errors = []
            
            for cost in costs_without_rate:
                try:
                    cost_id = UUID(cost['id'])
                    due_date = cost['due_date']
                    currency = cost['currency']
                    amount = Decimal(str(cost['amount']))
                    
                    if currency == 'BRL':
                        
                        success = await self.update_cost(
                            cost_id=cost_id,
                            converted_amount_brl=amount,
                            exchange_rate_month=None,
                            exchange_rate_value=None
                        )
                        
                        if success:
                            updated_count += 1
                        else:
                            failed_count += 1
                            errors.append(f"Failed to update cost {cost_id} (BRL)")
                        continue
                    
                    
                    exchange_rate = await self.exchange_rate_service.get_exchange_rate_for_date(
                        organization_id=organization_id,
                        target_date=due_date,
                        base_currency=currency,
                        target_currency='BRL'
                    )
                    
                    if exchange_rate:
                        exchange_rate_month = exchange_rate['year_month']
                        exchange_rate_value = Decimal(str(exchange_rate['rate']))
                        converted_amount_brl = amount * exchange_rate_value
                                                
                        success = await self.update_exchange_rate_data(
                            cost_id=cost_id,
                            converted_amount_brl=converted_amount_brl,
                            exchange_rate_month=exchange_rate_month,
                            exchange_rate_value=exchange_rate_value
                        )
                        
                        if success:
                            updated_count += 1
                            logger.info(f"Updated exchange rate for cost {cost_id}")
                        else:
                            failed_count += 1
                            errors.append(f"Failed to update cost {cost_id}")
                    else:
                        failed_count += 1
                        errors.append(f"No exchange rate found for cost {cost_id} ({currency} on {due_date})")
                        
                except Exception as e:
                    failed_count += 1
                    errors.append(f"Error processing cost {cost['id']}: {str(e)}")
                    logger.error(f"Error processing cost {cost['id']}: {e}")
            
            return {
                "success": updated_count > 0,
                "updated_count": updated_count,
                "failed_count": failed_count,
                "total_processed": len(costs_without_rate),
                "errors": errors
            }
                
        except Exception as e:
            logger.error(f"Error in auto_update_exchange_rates_for_costs: {e}")
            return {
                "success": False,
                "error": str(e),
                "updated_count": 0,
                "failed_count": 0
            }


# Global instance
cost_service = CostService(exchange_rate_service=exchange_rate_service)