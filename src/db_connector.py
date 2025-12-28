import os
import urllib
import time
import logging
import pandas as pd
from functools import lru_cache
from typing import Optional, Tuple
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Configure logging for diagnostics
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('DatabaseConnector')


class QueryDiagnostics:
    """Utility class for query performance diagnostics."""
    
    def __init__(self):
        self.query_times = []
        self.slow_query_threshold = 1.0  # seconds
    
    def log_query(self, query_name: str, duration: float, row_count: int):
        """Logs query execution details."""
        self.query_times.append({
            'query': query_name,
            'duration': duration,
            'rows': row_count,
            'timestamp': time.time()
        })
        
        if duration > self.slow_query_threshold:
            logger.warning(f"SLOW QUERY: {query_name} took {duration:.3f}s ({row_count} rows)")
        else:
            logger.debug(f"Query: {query_name} completed in {duration:.3f}s ({row_count} rows)")
    
    def get_stats(self) -> dict:
        """Returns query statistics."""
        if not self.query_times:
            return {'total_queries': 0, 'avg_duration': 0, 'slow_queries': 0}
        
        durations = [q['duration'] for q in self.query_times]
        return {
            'total_queries': len(self.query_times),
            'avg_duration': sum(durations) / len(durations),
            'max_duration': max(durations),
            'slow_queries': sum(1 for d in durations if d > self.slow_query_threshold)
        }


class DatabaseConnector:
    # Class-level cache for expensive queries
    _cache = {}
    _cache_timestamps = {}
    _cache_ttl = 300  # 5 minutes default TTL
    
    def __init__(self, enable_diagnostics: bool = True, enable_audit: bool = True):
        load_dotenv()
        self.conn_str = os.getenv('DB_CONN_STR')
        if not self.conn_str:
            raise ValueError("DB_CONN_STR not found in .env variables")
        self.engine = self._create_db_engine()
        self.diagnostics = QueryDiagnostics() if enable_diagnostics else None
        
        # Initialize audit logging
        self._audit = None
        if enable_audit:
            try:
                from src.security.audit import SecurityAuditLog, AuditEventType
                self._audit = SecurityAuditLog()
                self._audit.log(
                    AuditEventType.SESSION_START,
                    details={"component": "DatabaseConnector"}
                )
            except ImportError:
                logger.debug("Audit logging not available")
        
        logger.info("DatabaseConnector initialized successfully")

    def _create_db_engine(self):
        """
        Creates SQLAlchemy engine with optimized connection pooling.
        
        Pool settings:
        - pool_pre_ping: Verify connections before use (handles stale connections)
        - pool_size: Base number of persistent connections (default: 5)
        - max_overflow: Additional connections allowed during peak (default: 10)
        - pool_recycle: Recycle connections after N seconds to prevent stale (default: 3600)
        - pool_timeout: Seconds to wait for connection from pool (default: 30)
        """
        try:
            engine = create_engine(
                self.conn_str,
                pool_pre_ping=True,           # Verify connections before use
                pool_size=5,                   # Base pool size
                max_overflow=10,               # Extra connections during peak
                pool_recycle=3600,             # Recycle connections every hour
                pool_timeout=30,               # Wait 30s for connection from pool
                echo=False,                    # Set True for SQL debugging
            )
            logger.info(
                f"Database engine created with pool: "
                f"size=5, max_overflow=10, recycle=3600s"
            )
            return engine
        except Exception as e:
            logger.error(f"Error creating engine: {e}")
            raise

    def get_connection(self):
        """Returns a raw connection object"""
        return self.engine.connect()

    def _get_from_cache(self, cache_key: str) -> Optional[pd.DataFrame]:
        """Retrieves data from cache if valid."""
        if cache_key in self._cache:
            timestamp = self._cache_timestamps.get(cache_key, 0)
            if time.time() - timestamp < self._cache_ttl:
                logger.debug(f"Cache HIT for: {cache_key}")
                return self._cache[cache_key].copy()
            else:
                # Cache expired
                del self._cache[cache_key]
                del self._cache_timestamps[cache_key]
                logger.debug(f"Cache EXPIRED for: {cache_key}")
        return None
    
    def _set_cache(self, cache_key: str, data: pd.DataFrame):
        """Stores data in cache."""
        self._cache[cache_key] = data.copy()
        self._cache_timestamps[cache_key] = time.time()
        logger.debug(f"Cache SET for: {cache_key} ({len(data)} rows)")
    
    def clear_cache(self, cache_key: str = None):
        """Clears cache - all or specific key."""
        if cache_key:
            self._cache.pop(cache_key, None)
            self._cache_timestamps.pop(cache_key, None)
            logger.info(f"Cache cleared for: {cache_key}")
        else:
            self._cache.clear()
            self._cache_timestamps.clear()
            logger.info("All cache cleared")

    def execute_query(self, query: str, params=None, query_name: str = "unnamed") -> pd.DataFrame:
        """
        Executes a SQL query and returns the result as a pandas DataFrame.
        Includes diagnostics logging for performance monitoring.
        """
        start_time = time.time()
        try:
            with self.engine.connect() as connection:
                df = pd.read_sql(text(query), connection, params=params)
                
                # Log diagnostics
                duration = time.time() - start_time
                if self.diagnostics:
                    self.diagnostics.log_query(query_name, duration, len(df))
                
                return df
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Query execution failed ({query_name}): {e} (after {duration:.3f}s)")
            return pd.DataFrame() # Return empty DF on failure

    def test_connection(self) -> bool:
        """Tests the database connection."""
        start_time = time.time()
        try:
            with self.engine.connect() as connection:
                result = connection.execute(text("SELECT 1"))
                duration = time.time() - start_time
                logger.info(f"Connection test successful ({duration:.3f}s)")
                return result.scalar() == 1
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False

    def get_historical_data(self, use_cache: bool = True, date_from: str = None, date_to: str = None) -> pd.DataFrame:
        """
        Fetches historical production data aggregated by week.
        Joins CtiZlecenieElem with CtiZlecenieNag and CDN.Towary.
        Strictly filters for Raw Materials (CZE_Typ IN (1, 2)).
        
        PERFORMANCE: Uses date range filtering when provided to reduce data transfer.
        
        Args:
            use_cache: If True, returns cached data if available (default: True)
            date_from: Optional start date filter (YYYY-MM-DD format)
            date_to: Optional end date filter (YYYY-MM-DD format)
            
        Note on NOLOCK: Used for read-only reporting queries. 
        Risk: May read uncommitted data (dirty reads). 
        Benefit: Does not block production ERP operations.
        """
        # Create cache key based on date range
        cache_key = f"historical_data_{date_from}_{date_to}" if (date_from or date_to) else "historical_data"
        
        if use_cache:
            cached = self._get_from_cache(cache_key)
            if cached is not None:
                return cached
        
        # Build query with optional date filters for performance
        base_query = """
        SELECT 
            DATEPART(ISO_WEEK, n.CZN_DataRealizacji) as Week,
            YEAR(n.CZN_DataRealizacji) as Year,
            e.CZE_TwrId as TowarId,
            SUM(e.CZE_Ilosc) as Quantity
        FROM dbo.CtiZlecenieElem e WITH (NOLOCK)
        JOIN dbo.CtiZlecenieNag n WITH (NOLOCK) ON e.CZE_CZNId = n.CZN_ID
        JOIN CDN.Towary t WITH (NOLOCK) ON e.CZE_TwrId = t.Twr_TwrId
        WHERE n.CZN_DataRealizacji IS NOT NULL 
          AND e.CZE_Typ IN (1, 2)
          AND t.Twr_Typ != 2
        """
        
        params = {}
        
        # Add date range filters if provided (PERFORMANCE OPTIMIZATION)
        if date_from:
            base_query += " AND n.CZN_DataRealizacji >= :date_from"
            params['date_from'] = date_from
        if date_to:
            base_query += " AND n.CZN_DataRealizacji <= :date_to"
            params['date_to'] = date_to
            
        base_query += """
        GROUP BY YEAR(n.CZN_DataRealizacji), DATEPART(ISO_WEEK, n.CZN_DataRealizacji), e.CZE_TwrId
        ORDER BY Year, Week
        """
        
        df = self.execute_query(base_query, params=params if params else None, query_name="get_historical_data")
        
        if not df.empty:
            self._set_cache(cache_key, df)
        
        return df


    def get_current_stock(self, use_cache: bool = True) -> pd.DataFrame:
        """
        Fetches current stock levels from TwrZasoby/Towary.
        Only includes items that are defined as Raw Materials in production orders (CZE_Typ IN (1, 2)).
        Excludes explicit Services (Twr_Typ = 2).
        
        Args:
            use_cache: If True, returns cached data if available (default: True)
        """
        cache_key = "current_stock"
        
        if use_cache:
            cached = self._get_from_cache(cache_key)
            if cached is not None:
                return cached
        
        query = """
        SELECT 
            t.Twr_TwrId as TowarId,
            t.Twr_Kod as Code,
            t.Twr_Nazwa as Name,
            ISNULL(SUM(z.TwZ_Ilosc), 0) as StockLevel,
            (SELECT COUNT(*) FROM dbo.CtiZlecenieElem e WHERE e.CZE_TwrId = t.Twr_TwrId AND e.CZE_Typ IN (1, 2)) as UsageCount
        FROM CDN.Towary t
        LEFT JOIN CDN.TwrZasoby z ON t.Twr_TwrId = z.TwZ_TwrId
        WHERE t.Twr_TwrId IN (
            SELECT DISTINCT CZE_TwrId 
            FROM dbo.CtiZlecenieElem 
            WHERE CZE_Typ IN (1, 2)
        )
        AND t.Twr_Typ != 2
        GROUP BY t.Twr_TwrId, t.Twr_Kod, t.Twr_Nazwa
        ORDER BY UsageCount DESC
        """
        df = self.execute_query(query, query_name="get_current_stock")
        
        if not df.empty:
            self._set_cache(cache_key, df)
        
        return df

    def get_product_usage_stats(self, raw_material_id: int) -> pd.DataFrame:
        """
        Returns stats on which Final Products use this Raw Material.
        Joins:
        - CtiZlecenieElem (Input Material - Typ 1, 2)
        - CtiZlecenieNag (Production Order)
        - CDN.Towary (Final Product) via CtiZlecenieNag.CZN_TwrId
        """
        query = """
        SELECT TOP 20
            t_final.Twr_TwrId as FinalProductId,
            t_final.Twr_Nazwa as FinalProductName,
            t_final.Twr_Kod as FinalProductCode,
            COUNT(DISTINCT n.CZN_ID) as OrderCount,
            SUM(e.CZE_Ilosc) as TotalUsage
        FROM dbo.CtiZlecenieElem e WITH (NOLOCK)
        JOIN dbo.CtiZlecenieNag n WITH (NOLOCK) ON e.CZE_CZNId = n.CZN_ID
        JOIN CDN.Towary t_final WITH (NOLOCK) ON n.CZN_TwrId = t_final.Twr_TwrId
        WHERE e.CZE_TwrId = :raw_material_id
          AND e.CZE_Typ IN (1, 2)
        GROUP BY t_final.Twr_TwrId, t_final.Twr_Nazwa, t_final.Twr_Kod
        ORDER BY TotalUsage DESC
        """
        return self.execute_query(query, params={"raw_material_id": raw_material_id}, 
                                  query_name=f"get_product_usage_stats({raw_material_id})")

    def get_product_bom(self, final_product_id: int) -> pd.DataFrame:
        """
        Fetches the Bill of Materials (BOM) for a given Final Product.
        Joins:
        - CtiTechnolNag (Technology Header) - finds active tech for this product
        - CtiTechnolElem (Technology Elements) - ingredients
        - CDN.Towary (Ingredient Details)
        Filters for Ingredients (CTE_Typ IN (1, 2)).
        """
        # Note: CTE_Typ 1,2 = Raw Materials
        # CTN_Status = 1 usually means Valid/Active (assumption, or we pick the latest)
        query = """
        SELECT TOP 100
            elem_t.Twr_Kod as IngredientCode,
            elem_t.Twr_Nazwa as IngredientName,
            e.CTE_Ilosc as QuantityPerUnit,
            elem_t.Twr_JM as Unit,
            e.CTE_Typ as Type
        FROM dbo.CtiTechnolNag n WITH (NOLOCK)
        JOIN dbo.CtiTechnolElem e WITH (NOLOCK) ON n.CTN_ID = e.CTE_CTNId
        JOIN CDN.Towary elem_t WITH (NOLOCK) ON e.CTE_TwrId = elem_t.Twr_TwrId
        WHERE n.CTN_TwrId = :final_product_id
          AND e.CTE_Typ IN (1, 2)
        -- Order by latest technology (highest ID or Date if available, simple max ID here)
        ORDER BY n.CTN_ID DESC, e.CTE_Lp ASC
        """
        return self.execute_query(query, params={"final_product_id": final_product_id},
                                  query_name=f"get_product_bom({final_product_id})")

    def get_products_with_technology(self, use_cache: bool = True) -> pd.DataFrame:
        """
        Fetches list of Final Products that have a defined technology (BOM).
        Used for the 'Final Product Analysis' AI mode.
        
        Args:
            use_cache: If True, returns cached data if available (default: True)
        """
        cache_key = "products_with_technology"
        
        if use_cache:
            cached = self._get_from_cache(cache_key)
            if cached is not None:
                return cached
        
        query = """
        SELECT DISTINCT 
            t.Twr_TwrId as FinalProductId,
            t.Twr_Kod as Code,
            t.Twr_Nazwa as Name
        FROM dbo.CtiTechnolNag n WITH (NOLOCK)
        JOIN CDN.Towary t WITH (NOLOCK) ON n.CTN_TwrId = t.Twr_TwrId
        ORDER BY t.Twr_Nazwa
        """
        df = self.execute_query(query, query_name="get_products_with_technology")
        
        if not df.empty:
            self._set_cache(cache_key, df)
        
        return df

    def get_bom_with_stock(self, final_product_id: int, technology_id: int = None) -> pd.DataFrame:
        """
        Fetches BOM for a product along with current stock levels of ingredients.
        Used for AI generation to advise on purchasing.
        Strictly filters ingredients by CTI Type 1, 2 AND CDN Type != 2.
        
        Args:
            final_product_id: ID of the final product
            technology_id: Optional specific technology ID. If None, uses all technologies for product.
        """
        # Build query with optional technology filter (parameterized to prevent SQL injection)
        base_query = """
        SELECT 
            elem_t.Twr_Kod as IngredientCode,
            elem_t.Twr_Nazwa as IngredientName,
            e.CTE_Ilosc as QuantityPerUnit,
            elem_t.Twr_JM as Unit,
            ISNULL(SUM(z.TwZ_Ilosc), 0) as CurrentStock
        FROM dbo.CtiTechnolNag n WITH (NOLOCK)
        JOIN dbo.CtiTechnolElem e WITH (NOLOCK) ON n.CTN_ID = e.CTE_CTNId
        JOIN CDN.Towary elem_t WITH (NOLOCK) ON e.CTE_TwrId = elem_t.Twr_TwrId
        LEFT JOIN CDN.TwrZasoby z WITH (NOLOCK) ON elem_t.Twr_TwrId = z.TwZ_TwrId
        WHERE n.CTN_TwrId = :final_product_id
          AND e.CTE_Typ IN (1, 2)
          AND elem_t.Twr_Typ != 2
        """
        
        params = {"final_product_id": final_product_id}
        
        if technology_id is not None:
            base_query += " AND n.CTN_ID = :technology_id"
            params["technology_id"] = int(technology_id)
        
        base_query += """
        GROUP BY elem_t.Twr_Kod, elem_t.Twr_Nazwa, e.CTE_Ilosc, elem_t.Twr_JM
        ORDER BY e.CTE_Ilosc DESC
        """
        
        return self.execute_query(base_query, params=params,
                                  query_name=f"get_bom_with_stock({final_product_id})")
    
    def get_diagnostics_stats(self) -> dict:
        """Returns query performance statistics."""
        if self.diagnostics:
            return self.diagnostics.get_stats()
        return {}
    
    def check_and_create_indexes(self) -> dict:
        """
        Checks for recommended indexes and returns SQL statements to create them.
        Does NOT automatically create indexes - returns recommendations only.
        """
        recommended_indexes = [
            {
                'name': 'IX_CtiZlecenieElem_TwrId_Typ',
                'table': 'dbo.CtiZlecenieElem',
                'columns': 'CZE_TwrId, CZE_Typ',
                'sql': 'CREATE INDEX IX_CtiZlecenieElem_TwrId_Typ ON dbo.CtiZlecenieElem(CZE_TwrId, CZE_Typ)',
                'reason': 'Improves raw material filtering performance'
            },
            {
                'name': 'IX_CtiZlecenieNag_DataRealizacji',
                'table': 'dbo.CtiZlecenieNag',
                'columns': 'CZN_DataRealizacji',
                'sql': 'CREATE INDEX IX_CtiZlecenieNag_DataRealizacji ON dbo.CtiZlecenieNag(CZN_DataRealizacji)',
                'reason': 'Improves historical data queries by date'
            },
            {
                'name': 'IX_CtiTechnolElem_CTNId',
                'table': 'dbo.CtiTechnolElem',
                'columns': 'CTE_CTNId',
                'sql': 'CREATE INDEX IX_CtiTechnolElem_CTNId ON dbo.CtiTechnolElem(CTE_CTNId)',
                'reason': 'Improves BOM lookup performance'
            },
            {
                'name': 'IX_CtiTechnolNag_TwrId',
                'table': 'dbo.CtiTechnolNag',
                'columns': 'CTN_TwrId',
                'sql': 'CREATE INDEX IX_CtiTechnolNag_TwrId ON dbo.CtiTechnolNag(CTN_TwrId)',
                'reason': 'Improves technology lookup by product'
            }
        ]
        
        # Check which indexes already exist
        check_query = """
        SELECT i.name as IndexName, t.name as TableName
        FROM sys.indexes i
        JOIN sys.tables t ON i.object_id = t.object_id
        WHERE i.name IN ('IX_CtiZlecenieElem_TwrId_Typ', 'IX_CtiZlecenieNag_DataRealizacji', 
                         'IX_CtiTechnolElem_CTNId', 'IX_CtiTechnolNag_TwrId')
        """
        
        existing_indexes = set()
        try:
            df = self.execute_query(check_query, query_name="check_indexes")
            if not df.empty:
                existing_indexes = set(df['IndexName'].tolist())
        except Exception as e:
            logger.warning(f"Could not check existing indexes: {e}")
        
        result = {
            'existing': [],
            'missing': [],
            'create_sql': []
        }
        
        for idx in recommended_indexes:
            if idx['name'] in existing_indexes:
                result['existing'].append(idx['name'])
            else:
                result['missing'].append(idx)
                result['create_sql'].append(idx['sql'])
        
        return result
