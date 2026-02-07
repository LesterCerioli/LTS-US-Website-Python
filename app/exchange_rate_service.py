import logging
from uuid import UUID
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional, Dict, Any
from app.database import db

logger = logging.getLogger(__name__)


class ExchangeRateService:
    """Exchange rate service implementation for accounting.exchange_rates table"""
    
    def __init__(self):
        pass

    async def create_exchange_rate(
        self,
        year_month: str,
        rate: Decimal,
        valid_from: date,
        valid_to: date,
        organization_id: UUID,
        base_currency: str = "USD",
        target_currency: str = "BRL",
        source: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        
        logger.info(f"Creating exchange rate for organization: {organization_id}, period: {year_month}")
        
        
        if rate <= 0:
            raise Exception("Exchange rate must be greater than zero")
        
        if base_currency == target_currency:
            raise Exception("Base and target currencies must be different")
        
        if valid_from > valid_to:
            raise Exception("Valid from date must be before or equal to valid to date")
        
        
        import re
        if not re.match(r'^\d{4}-\d{2}$', year_month):
            raise Exception("Year-month must be in format YYYY-MM")
        
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
                
                
                duplicate_check = """
                    SELECT id FROM accounting.exchange_rates 
                    WHERE year_month = %s 
                    AND base_currency = %s 
                    AND target_currency = %s 
                    AND organization_id = %s
                """
                cursor.execute(duplicate_check, (year_month, base_currency, target_currency, str(organization_id)))
                if cursor.fetchone():
                    raise Exception(f"Exchange rate for {year_month} ({base_currency}->{target_currency}) already exists for this organization")

                insert_query = """
                    INSERT INTO accounting.exchange_rates (
                        year_month, base_currency, target_currency, rate, source,
                        valid_from, valid_to, organization_id, created_at, updated_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                    )
                    RETURNING *
                """
                
                cursor.execute(
                    insert_query,
                    (
                        year_month,
                        base_currency,
                        target_currency,
                        float(rate),
                        source,
                        valid_from,
                        valid_to,
                        str(organization_id)
                    )
                )
                
                created_rate = cursor.fetchone()
                conn.commit()
                
                if not created_rate:
                    raise Exception("Failed to create exchange rate")
                
                logger.info(f"Exchange rate created successfully for {year_month}")
                return dict(created_rate)
        
        except Exception as e:
            logger.error(f"Error creating exchange rate: {e}")
            raise Exception(f"Database error creating exchange rate: {str(e)}")

    async def get_exchange_rate_by_id(self, rate_id: UUID) -> Optional[Dict[str, Any]]:
        """Get exchange rate by ID"""
        logger.info(f"Fetching exchange rate by ID: {rate_id}")
    
        try:
            async with db.get_async_connection() as conn:
                cursor = conn.cursor()
                query = """
                    SELECT * FROM accounting.exchange_rates 
                    WHERE id = %s
                """
            
                cursor.execute(query, (str(rate_id),))
                rate = cursor.fetchone()
            
                if not rate:
                    logger.warning(f"Exchange rate not found with ID: {rate_id}")
                    return None
            
                logger.info(f"Exchange rate found: {rate_id}")
                return dict(rate)
        
        except Exception as e:
            logger.error(f"Error fetching exchange rate: {e}")
            raise Exception(f"Database error fetching exchange rate: {str(e)}")

    async def update_exchange_rate(
        self,
        rate_id: UUID,
        year_month: Optional[str] = None,
        rate: Optional[Decimal] = None,
        valid_from: Optional[date] = None,
        valid_to: Optional[date] = None,
        base_currency: Optional[str] = None,
        target_currency: Optional[str] = None,
        source: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        
        logger.info(f"Updating exchange rate with ID: {rate_id}")
        
        try:
            async with db.get_async_connection() as conn:
                cursor = conn.cursor()
                
                
                check_query = """
                    SELECT id, organization_id FROM accounting.exchange_rates 
                    WHERE id = %s
                """
                cursor.execute(check_query, (str(rate_id),))
                existing_rate = cursor.fetchone()
                
                if not existing_rate:
                    logger.warning(f"Exchange rate not found with ID: {rate_id}")
                    return None

                update_fields = []
                params = []
                
                if year_month is not None:
                    
                    import re
                    if not re.match(r'^\d{4}-\d{2}$', year_month):
                        raise Exception("Year-month must be in format YYYY-MM")
                    update_fields.append("year_month = %s")
                    params.append(year_month)
                
                if rate is not None:
                    if rate <= 0:
                        raise Exception("Exchange rate must be greater than zero")
                    update_fields.append("rate = %s")
                    params.append(float(rate))
                
                if valid_from is not None:
                    update_fields.append("valid_from = %s")
                    params.append(valid_from)
                
                if valid_to is not None:
                    update_fields.append("valid_to = %s")
                    params.append(valid_to)
                
                if base_currency is not None:
                    update_fields.append("base_currency = %s")
                    params.append(base_currency)
                
                if target_currency is not None:
                    update_fields.append("target_currency = %s")
                    params.append(target_currency)
                
                if source is not None:
                    update_fields.append("source = %s")
                    params.append(source)
                
                
                if valid_from is not None and valid_to is not None:
                    if valid_from > valid_to:
                        raise Exception("Valid from date must be before or equal to valid to date")
                
                
                if base_currency is not None and target_currency is not None:
                    if base_currency == target_currency:
                        raise Exception("Base and target currencies must be different")
                
                if not update_fields:
                    return await self.get_exchange_rate_by_id(rate_id)
                
                
                if year_month is not None or base_currency is not None or target_currency is not None:
                    duplicate_check = """
                        SELECT id FROM accounting.exchange_rates 
                        WHERE year_month = %s 
                        AND base_currency = %s 
                        AND target_currency = %s 
                        AND organization_id = %s
                        AND id != %s
                    """
                    duplicate_params = [
                        year_month if year_month is not None else existing_rate['year_month'],
                        base_currency if base_currency is not None else existing_rate['base_currency'],
                        target_currency if target_currency is not None else existing_rate['target_currency'],
                        str(existing_rate['organization_id']),
                        str(rate_id)
                    ]
                    cursor.execute(duplicate_check, duplicate_params)
                    if cursor.fetchone():
                        raise Exception(f"Exchange rate for this period and currencies already exists for this organization")
                
                update_fields.append("updated_at = CURRENT_TIMESTAMP")
                params.append(str(rate_id))
                
                update_query = f"""
                    UPDATE accounting.exchange_rates 
                    SET {', '.join(update_fields)}
                    WHERE id = %s
                    RETURNING *
                """
                
                cursor.execute(update_query, params)
                updated_rate = cursor.fetchone()
                conn.commit()
                
                if not updated_rate:
                    return None
                
                logger.info(f"Exchange rate updated successfully: {rate_id}")
                return dict(updated_rate)
                
        except Exception as e:
            logger.error(f"Error updating exchange rate: {e}")
            raise Exception(f"Database error updating exchange rate: {str(e)}")

    async def delete_exchange_rate(self, rate_id: UUID) -> bool:
        
        logger.info(f"Deleting exchange rate with ID: {rate_id}")
        
        try:
            async with db.get_async_connection() as conn:
                cursor = conn.cursor()
                
                
                check_costs_query = """
                    SELECT COUNT(*) as cost_count FROM accounting.costs
                    WHERE exchange_rate_month = (
                        SELECT year_month FROM accounting.exchange_rates WHERE id = %s
                    )
                    AND organization_id = (
                        SELECT organization_id FROM accounting.exchange_rates WHERE id = %s
                    )
                    AND deleted_at IS NULL
                """
                cursor.execute(check_costs_query, (str(rate_id), str(rate_id)))
                result = cursor.fetchone()
                
                if result and result['cost_count'] > 0:
                    raise Exception("Cannot delete exchange rate because it is referenced by existing costs")
                
                delete_query = """
                    DELETE FROM accounting.exchange_rates 
                    WHERE id = %s
                """
                
                cursor.execute(delete_query, (str(rate_id),))
                conn.commit()
                
                success = cursor.rowcount > 0
                
                if not success:
                    logger.warning(f"Exchange rate not found: {rate_id}")
                    return False
                
                logger.info(f"Exchange rate deleted successfully: {rate_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error deleting exchange rate: {e}")
            raise Exception(f"Database error deleting exchange rate: {str(e)}")

    async def get_organization_exchange_rates(
        self, 
        organization_id: UUID,
        year_month: Optional[str] = None,
        base_currency: Optional[str] = None,
        target_currency: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        page: int = 1,
        page_size: int = 50
    ) -> Dict[str, Any]:
        
        logger.info(f"Fetching exchange rates for organization: {organization_id}")
        
        try:
            async with db.get_async_connection() as conn:
                cursor = conn.cursor()
                
                conditions = ["organization_id = %s"]
                params = [str(organization_id)]
                
                if year_month:
                    conditions.append("year_month = %s")
                    params.append(year_month)
                
                if base_currency:
                    conditions.append("base_currency = %s")
                    params.append(base_currency)
                
                if target_currency:
                    conditions.append("target_currency = %s")
                    params.append(target_currency)
                
                if date_from:
                    conditions.append("valid_to >= %s")
                    params.append(date_from)
                
                if date_to:
                    conditions.append("valid_from <= %s")
                    params.append(date_to)
                
                where_clause = " AND ".join(conditions)
                
                
                count_query = f"""
                    SELECT COUNT(*) as total 
                    FROM accounting.exchange_rates 
                    WHERE {where_clause}
                """
                
                cursor.execute(count_query, params)
                count_result = cursor.fetchone()
                total_count = count_result['total'] if count_result else 0
                
                
                offset = (page - 1) * page_size
                
                base_query = f"""
                    SELECT * FROM accounting.exchange_rates 
                    WHERE {where_clause}
                    ORDER BY year_month DESC, valid_from DESC, created_at DESC
                """
                
                base_query += " LIMIT %s OFFSET %s"
                params.extend([page_size, offset])
                
                cursor.execute(base_query, params)
                rates = cursor.fetchall()
                
                rates_list = [dict(rate) for rate in rates]
                total_pages = (total_count + page_size - 1) // page_size if page_size > 0 else 1
                
                logger.info(f"Found {len(rates_list)} exchange rates for organization {organization_id}")
                
                return {
                    "exchange_rates": rates_list,
                    "total_count": total_count,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": total_pages
                }
                
        except Exception as e:
            logger.error(f"Error fetching organization exchange rates: {e}")
            raise Exception(f"Database error fetching exchange rates: {str(e)}")

    async def get_exchange_rate_for_period(
        self,
        organization_id: UUID,
        year_month: str,
        base_currency: str = "USD",
        target_currency: str = "BRL"
    ) -> Optional[Dict[str, Any]]:
        """Get specific exchange rate for a period and currency pair"""
        logger.info(f"Fetching exchange rate for {year_month} ({base_currency}->{target_currency})")
        
        try:
            async with db.get_async_connection() as conn:
                cursor = conn.cursor()
                
                query = """
                    SELECT * FROM accounting.exchange_rates 
                    WHERE organization_id = %s 
                    AND year_month = %s 
                    AND base_currency = %s 
                    AND target_currency = %s
                """
                
                cursor.execute(query, (str(organization_id), year_month, base_currency, target_currency))
                rate = cursor.fetchone()
                
                if not rate:
                    logger.warning(f"Exchange rate not found for {year_month} ({base_currency}->{target_currency})")
                    return None
                
                logger.info(f"Exchange rate found for {year_month}")
                return dict(rate)
                
        except Exception as e:
            logger.error(f"Error fetching exchange rate for period: {e}")
            raise Exception(f"Database error fetching exchange rate: {str(e)}")

    async def get_exchange_rate_for_date(
        self,
        organization_id: UUID,
        target_date: date,
        base_currency: str = "USD",
        target_currency: str = "BRL"
    ) -> Optional[Dict[str, Any]]:
        
        logger.info(f"Fetching exchange rate for date: {target_date} ({base_currency}->{target_currency})")
        
        try:
            async with db.get_async_connection() as conn:
                cursor = conn.cursor()
                
                query = """
                    SELECT * FROM accounting.exchange_rates 
                    WHERE organization_id = %s 
                    AND base_currency = %s 
                    AND target_currency = %s
                    AND valid_from <= %s 
                    AND valid_to >= %s
                    ORDER BY year_month DESC, created_at DESC
                    LIMIT 1
                """
                
                cursor.execute(query, (str(organization_id), base_currency, target_currency, target_date, target_date))
                rate = cursor.fetchone()
                
                if not rate:
                    logger.warning(f"No exchange rate found for date {target_date}")
                    return None
                
                logger.info(f"Exchange rate found for date {target_date}")
                return dict(rate)
                
        except Exception as e:
            logger.error(f"Error fetching exchange rate for date: {e}")
            raise Exception(f"Database error fetching exchange rate: {str(e)}")

    async def get_latest_exchange_rate(
        self,
        organization_id: UUID,
        base_currency: str = "USD",
        target_currency: str = "BRL"
    ) -> Optional[Dict[str, Any]]:
        
        logger.info(f"Fetching latest exchange rate ({base_currency}->{target_currency})")
        
        try:
            async with db.get_async_connection() as conn:
                cursor = conn.cursor()
                
                query = """
                    SELECT * FROM accounting.exchange_rates 
                    WHERE organization_id = %s 
                    AND base_currency = %s 
                    AND target_currency = %s
                    ORDER BY year_month DESC, valid_from DESC, created_at DESC
                    LIMIT 1
                """
                
                cursor.execute(query, (str(organization_id), base_currency, target_currency))
                rate = cursor.fetchone()
                
                if not rate:
                    logger.warning(f"No exchange rate found for {base_currency}->{target_currency}")
                    return None
                
                logger.info(f"Latest exchange rate found for {base_currency}->{target_currency}")
                return dict(rate)
                
        except Exception as e:
            logger.error(f"Error fetching latest exchange rate: {e}")
            raise Exception(f"Database error fetching exchange rate: {str(e)}")

    async def get_available_periods(
        self,
        organization_id: UUID,
        base_currency: Optional[str] = None,
        target_currency: Optional[str] = None
    ) -> List[str]:
        
        logger.info(f"Fetching available periods for organization: {organization_id}")
        
        try:
            async with db.get_async_connection() as conn:
                cursor = conn.cursor()
                
                conditions = ["organization_id = %s"]
                params = [str(organization_id)]
                
                if base_currency:
                    conditions.append("base_currency = %s")
                    params.append(base_currency)
                
                if target_currency:
                    conditions.append("target_currency = %s")
                    params.append(target_currency)
                
                where_clause = " AND ".join(conditions)
                
                query = f"""
                    SELECT DISTINCT year_month 
                    FROM accounting.exchange_rates 
                    WHERE {where_clause}
                    ORDER BY year_month DESC
                """
                
                cursor.execute(query, params)
                periods = cursor.fetchall()
                
                period_list = [period['year_month'] for period in periods]
                logger.info(f"Found {len(period_list)} available periods")
                
                return period_list
                
        except Exception as e:
            logger.error(f"Error fetching available periods: {e}")
            raise Exception(f"Database error fetching periods: {str(e)}")

    async def get_available_currency_pairs(
        self,
        organization_id: UUID,
        year_month: Optional[str] = None
    ) -> List[Dict[str, str]]:
        
        logger.info(f"Fetching available currency pairs for organization: {organization_id}")
        
        try:
            async with db.get_async_connection() as conn:
                cursor = conn.cursor()
                
                conditions = ["organization_id = %s"]
                params = [str(organization_id)]
                
                if year_month:
                    conditions.append("year_month = %s")
                    params.append(year_month)
                
                where_clause = " AND ".join(conditions)
                
                query = f"""
                    SELECT DISTINCT base_currency, target_currency 
                    FROM accounting.exchange_rates 
                    WHERE {where_clause}
                    ORDER BY base_currency, target_currency
                """
                
                cursor.execute(query, params)
                pairs = cursor.fetchall()
                
                pair_list = [
                    {"base_currency": pair['base_currency'], "target_currency": pair['target_currency']}
                    for pair in pairs
                ]
                logger.info(f"Found {len(pair_list)} available currency pairs")
                
                return pair_list
                
        except Exception as e:
            logger.error(f"Error fetching available currency pairs: {e}")
            raise Exception(f"Database error fetching currency pairs: {str(e)}")

    async def batch_create_exchange_rates(
        self,
        rates_data: List[Dict[str, Any]],
        organization_id: UUID
    ) -> Dict[str, Any]:
        
        logger.info(f"Creating {len(rates_data)} exchange rates for organization: {organization_id}")
        
        if not rates_data:
            return {"created_count": 0, "failed_count": 0, "errors": []}
        
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
                
                created_count = 0
                failed_count = 0
                errors = []
                
                for i, rate_data in enumerate(rates_data):
                    try:
                        
                        required_fields = ['year_month', 'rate', 'valid_from', 'valid_to']
                        for field in required_fields:
                            if field not in rate_data or rate_data[field] is None:
                                errors.append(f"Rate {i}: Missing required field '{field}'")
                                failed_count += 1
                                continue
                        
                        
                        year_month = rate_data['year_month']
                        rate = Decimal(str(rate_data['rate']))
                        valid_from = rate_data['valid_from']
                        valid_to = rate_data['valid_to']
                        base_currency = rate_data.get('base_currency', 'USD')
                        target_currency = rate_data.get('target_currency', 'BRL')
                        source = rate_data.get('source')
                        
                        
                        if rate <= 0:
                            errors.append(f"Rate {i}: Exchange rate must be greater than zero")
                            failed_count += 1
                            continue
                        
                        if base_currency == target_currency:
                            errors.append(f"Rate {i}: Base and target currencies must be different")
                            failed_count += 1
                            continue
                        
                        if valid_from > valid_to:
                            errors.append(f"Rate {i}: Valid from date must be before or equal to valid to date")
                            failed_count += 1
                            continue
                        
                        
                        import re
                        if not re.match(r'^\d{4}-\d{2}$', year_month):
                            errors.append(f"Rate {i}: Year-month must be in format YYYY-MM")
                            failed_count += 1
                            continue
                        
                        
                        duplicate_check = """
                            SELECT id FROM accounting.exchange_rates 
                            WHERE year_month = %s 
                            AND base_currency = %s 
                            AND target_currency = %s 
                            AND organization_id = %s
                        """
                        cursor.execute(duplicate_check, (year_month, base_currency, target_currency, str(organization_id)))
                        if cursor.fetchone():
                            errors.append(f"Rate {i}: Exchange rate for {year_month} ({base_currency}->{target_currency}) already exists")
                            failed_count += 1
                            continue
                        
                        
                        insert_query = """
                            INSERT INTO accounting.exchange_rates (
                                year_month, base_currency, target_currency, rate, source,
                                valid_from, valid_to, organization_id, created_at, updated_at
                            ) VALUES (
                                %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                            )
                        """
                        
                        cursor.execute(
                            insert_query,
                            (
                                year_month,
                                base_currency,
                                target_currency,
                                float(rate),
                                source,
                                valid_from,
                                valid_to,
                                str(organization_id)
                            )
                        )
                        created_count += 1
                        
                    except Exception as e:
                        errors.append(f"Rate {i}: {str(e)}")
                        failed_count += 1
                
                conn.commit()
                
                logger.info(f"Batch create completed: {created_count} created, {failed_count} failed")
                
                return {
                    "created_count": created_count,
                    "failed_count": failed_count,
                    "errors": errors
                }
                
        except Exception as e:
            logger.error(f"Error in batch create exchange rates: {e}")
            raise Exception(f"Database error in batch create: {str(e)}")

    async def get_organization_summary(
        self,
        organization_id: UUID
    ) -> Dict[str, Any]:
        
        logger.info(f"Fetching exchange rate summary for organization: {organization_id}")
        
        try:
            async with db.get_async_connection() as conn:
                cursor = conn.cursor()
                
                
                stats_query = """
                    SELECT 
                        COUNT(*) as total_rates,
                        COUNT(DISTINCT year_month) as distinct_periods,
                        COUNT(DISTINCT base_currency) as distinct_base_currencies,
                        COUNT(DISTINCT target_currency) as distinct_target_currencies,
                        MIN(year_month) as earliest_period,
                        MAX(year_month) as latest_period,
                        MIN(rate) as min_rate,
                        MAX(rate) as max_rate,
                        AVG(rate) as avg_rate
                    FROM accounting.exchange_rates
                    WHERE organization_id = %s
                """
                
                cursor.execute(stats_query, (str(organization_id),))
                stats = cursor.fetchone()
                
                if not stats:
                    return {}
                
                
                pairs_query = """
                    SELECT 
                        base_currency,
                        target_currency,
                        COUNT(*) as rate_count,
                        MIN(year_month) as first_period,
                        MAX(year_month) as last_period
                    FROM accounting.exchange_rates
                    WHERE organization_id = %s
                    GROUP BY base_currency, target_currency
                    ORDER BY base_currency, target_currency
                """
                
                cursor.execute(pairs_query, (str(organization_id),))
                pairs = cursor.fetchall()
                
                return {
                    "statistics": dict(stats),
                    "currency_pairs": [dict(pair) for pair in pairs]
                }
                
        except Exception as e:
            logger.error(f"Error fetching exchange rate summary: {e}")
            raise Exception(f"Database error fetching summary: {str(e)}")



exchange_rate_service = ExchangeRateService()