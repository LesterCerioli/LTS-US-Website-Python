import logging
from uuid import UUID
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any, Callable
import aiohttp
import asyncio
from contextlib import asynccontextmanager
from app.database import db

logger = logging.getLogger(__name__)


class AwesomeAPISyncService:
    
    
    def __init__(self, sync_hour: int = 2, sync_minute: int = 0):
        
        self.BASE_API_URL = "https://economia.awesomeapi.com.br"
        self.DEFAULT_PAIR = "USD-BRL"
                
        self.sync_hour = sync_hour
        self.sync_minute = sync_minute
        self.sync_task: Optional[asyncio.Task] = None
        self.is_running = False
        self.scheduler_task: Optional[asyncio.Task] = None
                
        self.rate_cache: Dict[str, Dict] = {}
        self.cache_expiry = timedelta(minutes=5)
        
        
    async def _execute_sql(self, query: str, params: tuple) -> bool:
        
        try:
            async with db.get_async_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"SQL error executing query: {e}")
            logger.debug(f"Query: {query}, Params: {params}")
            return False
    
    async def _fetch_one_sql(self, query: str, params: tuple) -> Optional[Dict]:
        
        try:
            async with db.get_async_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                return cursor.fetchone()
        except Exception as e:
            logger.error(f"SQL error fetching one: {e}")
            return None
    
    async def _fetch_all_sql(self, query: str, params: tuple) -> List[Dict]:
        
        try:
            async with db.get_async_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"SQL error fetching all: {e}")
            return []
    
        
    async def _fetch_live_rate_from_api(self) -> Optional[Dict[str, Any]]:
        
        try:
            url = f"{self.BASE_API_URL}/last/{self.DEFAULT_PAIR}"
            
            logger.info(f"Fetching live rate from AwesomeAPI: {url}")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=30) as response:
                    if response.status == 200:
                        data = await response.json()
                        usdbrl = data.get("USDBRL")
                        if usdbrl:
                            
                            bid = Decimal(usdbrl.get("bid", "0"))
                            ask = Decimal(usdbrl.get("ask", "0"))
                            
                            rate = (bid + ask) / 2
                            
                            rate_data = {
                                'rate': rate,
                                'bid': bid,
                                'ask': ask,
                                'high': Decimal(usdbrl.get("high", "0")),
                                'low': Decimal(usdbrl.get("low", "0")),
                                'var_bid': Decimal(usdbrl.get("varBid", "0")),
                                'pct_change': Decimal(usdbrl.get("pctChange", "0")),
                                'timestamp': usdbrl.get("timestamp"),
                                'create_date': usdbrl.get("create_date"),
                                'code': usdbrl.get("code"),
                                'codein': usdbrl.get("codein"),
                                'name': usdbrl.get("name"),
                                'source': 'awesomeapi'
                            }
                                                        
                            cache_key = f"{datetime.now().strftime('%Y-%m-%d')}_USD_BRL"
                            self.rate_cache[cache_key] = {
                                'data': rate_data,
                                'timestamp': datetime.now()
                            }
                            
                            logger.info(f"Rate fetched: 1 USD = {rate} BRL")
                            return rate_data
                    else:
                        logger.error(f"AwesomeAPI returned status {response.status}")
                        return None
        except aiohttp.ClientError as e:
            logger.error(f"Network error fetching from AwesomeAPI: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching from AwesomeAPI: {e}")
            return None
    
        
    async def _store_exchange_rate(
        self,
        organization_id: UUID,
        rate_data: Dict[str, Any],
        force_update: bool = False
    ) -> bool:
                
        try:
            rate = rate_data['rate']
            today = date.today()
            year_month = today.strftime("%Y-%m")
                        
            check_query = """
                SELECT id, rate FROM accounting.exchange_rates 
                WHERE organization_id = %s 
                AND year_month = %s 
                AND base_currency = 'USD' 
                AND target_currency = 'BRL'
            """
            
            existing = await self._fetch_one_sql(
                check_query, 
                (str(organization_id), year_month)
            )
            
            if existing and not force_update:
                
                existing_rate = Decimal(str(existing['rate']))
                if abs((rate - existing_rate) / existing_rate) < 0.001:
                    logger.debug(f"Rate unchanged for {organization_id} in {year_month}")
                    return True
            
            
            valid_from = today.replace(day=1)
            if today.month == 12:
                valid_to = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                valid_to = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
            
            source = f"{rate_data.get('source', 'awesomeapi')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            if existing:
                
                update_query = """
                    UPDATE accounting.exchange_rates 
                    SET rate = %s, 
                        source = %s,
                        valid_from = %s,
                        valid_to = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """
                
                success = await self._execute_sql(
                    update_query,
                    (
                        float(rate),
                        source,
                        valid_from,
                        valid_to,
                        existing['id']
                    )
                )
                
                if success:
                    logger.info(f"Updated rate for org {organization_id}: {rate}")
                else:
                    logger.error(f"Failed to update rate for org {organization_id}")
                    
            else:
                
                insert_query = """
                    INSERT INTO accounting.exchange_rates (
                        id, year_month, base_currency, target_currency, 
                        rate, source, valid_from, valid_to, organization_id,
                        created_at, updated_at
                    ) VALUES (
                        gen_random_uuid(), %s, %s, %s, %s, %s, %s, %s, %s,
                        CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                    )
                """
                
                success = await self._execute_sql(
                    insert_query,
                    (
                        year_month,
                        'USD',
                        'BRL',
                        float(rate),
                        source,
                        valid_from,
                        valid_to,
                        str(organization_id)
                    )
                )
                
                if success:
                    logger.info(f"Inserted new rate for org {organization_id}: {rate}")
                else:
                    logger.error(f"Failed to insert rate for org {organization_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error storing exchange rate for {organization_id}: {e}")
            return False
    
    async def _get_all_active_organizations(self) -> List[Dict[str, Any]]:
        
        try:
            query = """
                SELECT id, name FROM public.organizations 
                WHERE deleted_at IS NULL
                ORDER BY created_at
            """
            
            orgs = await self._fetch_all_sql(query, ())
            logger.info(f"Found {len(orgs)} active organizations")
            return orgs
            
        except Exception as e:
            logger.error(f"Error fetching organizations: {e}")
            return []
    
        
    async def sync_for_organization(self, organization_id: UUID) -> Dict[str, Any]:
        
        start_time = datetime.now()
        
        try:
            logger.info(f"Starting sync for organization: {organization_id}")
            
            
            rate_data = await self._fetch_live_rate_from_api()
            
            if not rate_data:
                return {
                    'success': False,
                    'error': 'Failed to fetch rate from external API',
                    'organization_id': str(organization_id),
                    'timestamp': datetime.now().isoformat(),
                    'duration_seconds': (datetime.now() - start_time).total_seconds()
                }
            
            
            stored = await self._store_exchange_rate(organization_id, rate_data)
            
            if stored:
                return {
                    'success': True,
                    'organization_id': str(organization_id),
                    'rate': float(rate_data['rate']),
                    'bid': float(rate_data['bid']),
                    'ask': float(rate_data['ask']),
                    'timestamp': datetime.now().isoformat(),
                    'duration_seconds': (datetime.now() - start_time).total_seconds(),
                    'source': rate_data['source']
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to store rate in database',
                    'organization_id': str(organization_id),
                    'timestamp': datetime.now().isoformat(),
                    'duration_seconds': (datetime.now() - start_time).total_seconds()
                }
                
        except Exception as e:
            logger.error(f"Error in sync_for_organization: {e}")
            return {
                'success': False,
                'error': str(e),
                'organization_id': str(organization_id),
                'timestamp': datetime.now().isoformat(),
                'duration_seconds': (datetime.now() - start_time).total_seconds()
            }
    
    async def sync_all_organizations(self) -> Dict[str, Any]:
        
        start_time = datetime.now()
        logger.info("Starting sync for ALL organizations")
        
        try:
            
            rate_data = await self._fetch_live_rate_from_api()
            
            if not rate_data:
                return {
                    'success': False,
                    'error': 'Failed to fetch rate from external API',
                    'timestamp': datetime.now().isoformat(),
                    'duration_seconds': (datetime.now() - start_time).total_seconds()
                }
            
            
            organizations = await self._get_all_active_organizations()
            
            if not organizations:
                logger.warning("No active organizations found")
                return {
                    'success': True,
                    'message': 'No active organizations found',
                    'synced_count': 0,
                    'timestamp': datetime.now().isoformat(),
                    'duration_seconds': (datetime.now() - start_time).total_seconds()
                }
            
            
            synced_count = 0
            failed_count = 0
            results = []
            
            for org in organizations:
                org_id = UUID(org['id'])
                org_name = org['name']
                
                logger.info(f"Syncing for organization: {org_name} ({org_id})")
                
                
                stored = await self._store_exchange_rate(org_id, rate_data)
                
                if stored:
                    synced_count += 1
                    results.append({
                        'organization_id': str(org_id),
                        'organization_name': org_name,
                        'success': True,
                        'rate': float(rate_data['rate'])
                    })
                else:
                    failed_count += 1
                    results.append({
                        'organization_id': str(org_id),
                        'organization_name': org_name,
                        'success': False
                    })
                
                
                await asyncio.sleep(0.1)
            
            duration = (datetime.now() - start_time).total_seconds()
            logger.info(f"Sync completed: {synced_count} succeeded, {failed_count} failed in {duration:.2f}s")
            
            return {
                'success': synced_count > 0,
                'synced_count': synced_count,
                'failed_count': failed_count,
                'total_organizations': len(organizations),
                'rate': float(rate_data['rate']),
                'results': results,
                'timestamp': datetime.now().isoformat(),
                'duration_seconds': duration
            }
            
        except Exception as e:
            logger.error(f"Error in sync_all_organizations: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat(),
                'duration_seconds': (datetime.now() - start_time).total_seconds()
            }
    
        
    async def _calculate_next_run(self) -> datetime:
        
        now = datetime.now()
        next_run = now.replace(
            hour=self.sync_hour,
            minute=self.sync_minute,
            second=0,
            microsecond=0
        )
        
        
        if now >= next_run:
            next_run += timedelta(days=1)
        
        return next_run
    
    async def _scheduler_loop(self):
        
        logger.info("Starting exchange rate sync scheduler")
        
        while self.is_running:
            try:
                
                next_run = await self._calculate_next_run()
                wait_seconds = (next_run - datetime.now()).total_seconds()
                
                logger.info(f"Next sync scheduled for: {next_run} (in {wait_seconds:.0f} seconds)")
                
                
                if wait_seconds > 0:
                    await asyncio.sleep(wait_seconds)
                
                
                if not self.is_running:
                    break
                
                
                logger.info("Executing scheduled sync...")
                result = await self.sync_all_organizations()
                
                logger.info(f"Scheduled sync completed: {result}")
                
                
                await asyncio.sleep(60)
                
            except asyncio.CancelledError:
                logger.info("Scheduler cancelled")
                break
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                
                await asyncio.sleep(300)
    
    async def start_scheduler(self):
        
        if self.is_running:
            logger.warning("Scheduler is already running")
            return
        
        self.is_running = True
        self.scheduler_task = asyncio.create_task(self._scheduler_loop())
        logger.info(f"Exchange rate scheduler started. Sync at {self.sync_hour:02d}:{self.sync_minute:02d} daily")
    
    async def stop_scheduler(self):
        
        if not self.is_running:
            return
        
        self.is_running = False
        
        if self.scheduler_task:
            self.scheduler_task.cancel()
            try:
                await self.scheduler_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Exchange rate scheduler stopped")
    
    async def manual_sync_now(self) -> Dict[str, Any]:
        
        logger.info("Manual sync requested")
        return await self.sync_all_organizations()
    
    async def get_sync_status(self) -> Dict[str, Any]:
        
        return {
            'is_running': self.is_running,
            'sync_hour': self.sync_hour,
            'sync_minute': self.sync_minute,
            'next_run': (await self._calculate_next_run()).isoformat() if self.is_running else None,
            'cache_size': len(self.rate_cache)
        }
    
        
    async def get_current_rate(self, use_cache: bool = True) -> Optional[Dict[str, Any]]:
        
        if use_cache:
            cache_key = f"{datetime.now().strftime('%Y-%m-%d')}_USD_BRL"
            cached = self.rate_cache.get(cache_key)
            
            if cached:
                
                cache_age = datetime.now() - cached['timestamp']
                if cache_age < self.cache_expiry:
                    logger.debug("Returning cached rate")
                    return cached['data']
        
        
        return await self._fetch_live_rate_from_api()
    
    async def get_organization_rates(
        self, 
        organization_id: UUID,
        months_back: int = 6
    ) -> List[Dict[str, Any]]:
        
        try:
            
            cutoff_date = (datetime.now() - timedelta(days=30 * months_back)).replace(day=1)
            cutoff_month = cutoff_date.strftime("%Y-%m")
            
            query = """
                SELECT * FROM accounting.exchange_rates 
                WHERE organization_id = %s 
                AND year_month >= %s
                AND base_currency = 'USD' 
                AND target_currency = 'BRL'
                ORDER BY year_month DESC
            """
            
            rates = await self._fetch_all_sql(
                query, 
                (str(organization_id), cutoff_month)
            )
            
            return [dict(rate) for rate in rates]
            
        except Exception as e:
            logger.error(f"Error fetching organization rates: {e}")
            return []


@asynccontextmanager
async def lifespan_event_handler():
    
    service = AwesomeAPISyncService(sync_hour=2, sync_minute=0)
        
    await service.start_scheduler()
    
    try:
        yield service
    finally:
        
        await service.stop_scheduler()



awesomeapi_sync_service = AwesomeAPISyncService(sync_hour=2, sync_minute=0)