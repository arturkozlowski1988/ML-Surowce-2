import os
import urllib
import time
import logging
from logging.handlers import RotatingFileHandler
import pandas as pd
from functools import lru_cache
from typing import Optional, Tuple
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Ensure logs directory exists
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

# Configure logging for diagnostics with both console and file handlers
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('DatabaseConnector')

# Add RotatingFileHandler for persistent logging (5MB max per file, 5 backup files)
file_handler = RotatingFileHandler(
    os.path.join(LOG_DIR, 'db_connector.log'),
    maxBytes=5*1024*1024,  # 5MB
    backupCount=5,
    encoding='utf-8'
)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
file_handler.setLevel(logging.DEBUG)
logger.addHandler(file_handler)


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
    
    def __init__(self, enable_diagnostics: bool = True, enable_audit: bool = True, database_name: str = None):
        load_dotenv()
        self.conn_str = os.getenv('DB_CONN_STR')
        if not self.conn_str:
            raise ValueError("DB_CONN_STR not found in .env variables")
        
        # Multi-database support: replace database in connection string if specified
        if database_name:
            # Replace database name in connection string (supports both cdn_test and cdn_mietex)
            import re
            self.conn_str = re.sub(r'/cdn_\w+\?', f'/{database_name}?', self.conn_str)
            self.database_name = database_name
        else:
            # Extract database name from connection string
            import re
            match = re.search(r'/([^/?]+)\?', self.conn_str)
            self.database_name = match.group(1) if match else 'unknown'
        
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
                    details={"component": "DatabaseConnector", "database": self.database_name}
                )
            except ImportError:
                logger.debug("Audit logging not available")
        
        logger.info(f"DatabaseConnector initialized for database: {self.database_name}")

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
    
    def dispose(self):
        """
        Releases all database connections and disposes the engine.
        Call this when switching databases to free up resources.
        """
        if self.engine:
            self.engine.dispose()
            self.clear_database_cache()  # Also clear this database's cache
            logger.info(f"Engine disposed for database: {self.database_name}")

    def _get_cache_key(self, base_key: str) -> str:
        """Creates database-specific cache key."""
        return f"{self.database_name}_{base_key}"
    
    def _get_from_cache(self, cache_key: str) -> Optional[pd.DataFrame]:
        """Retrieves data from cache if valid. Uses database-specific key."""
        full_key = self._get_cache_key(cache_key)
        if full_key in self._cache:
            timestamp = self._cache_timestamps.get(full_key, 0)
            if time.time() - timestamp < self._cache_ttl:
                logger.debug(f"Cache HIT for: {full_key}")
                return self._cache[full_key].copy()
            else:
                # Cache expired
                del self._cache[full_key]
                del self._cache_timestamps[full_key]
                logger.debug(f"Cache EXPIRED for: {full_key}")
        return None
    
    def _set_cache(self, cache_key: str, data: pd.DataFrame):
        """Stores data in cache with database-specific key."""
        full_key = self._get_cache_key(cache_key)
        self._cache[full_key] = data.copy()
        self._cache_timestamps[full_key] = time.time()
        logger.debug(f"Cache SET for: {full_key} ({len(data)} rows)")
    
    def clear_cache(self, cache_key: str = None):
        """Clears cache - all or specific key (with database prefix)."""
        if cache_key:
            full_key = self._get_cache_key(cache_key)
            self._cache.pop(full_key, None)
            self._cache_timestamps.pop(full_key, None)
            logger.info(f"Cache cleared for: {full_key}")
        else:
            self._cache.clear()
            self._cache_timestamps.clear()
            logger.info("All cache cleared")
    
    def clear_database_cache(self):
        """Clears all cache entries for current database."""
        prefix = f"{self.database_name}_"
        keys_to_remove = [k for k in self._cache.keys() if k.startswith(prefix)]
        for key in keys_to_remove:
            self._cache.pop(key, None)
            self._cache_timestamps.pop(key, None)
        logger.info(f"Cleared {len(keys_to_remove)} cache entries for database: {self.database_name}")

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


    def get_warehouses(self, use_cache: bool = True, only_with_stock: bool = True) -> pd.DataFrame:
        """
        Fetches list of available warehouses with stock counts.
        
        Args:
            use_cache: If True, returns cached data if available (default: True)
            only_with_stock: If True, returns only warehouses with stock > 0 (default: True)
        
        Returns:
            DataFrame with columns: MagId, Symbol, Name, ProductCount, TotalStock
        """
        cache_key = f"warehouses_{only_with_stock}"
        
        if use_cache:
            cached = self._get_from_cache(cache_key)
            if cached is not None:
                return cached
        
        query = """
        SELECT 
            m.Mag_MagId as MagId,
            m.Mag_Symbol as Symbol,
            m.Mag_Nazwa as Name,
            COUNT(DISTINCT z.TwZ_TwrId) as ProductCount,
            ISNULL(SUM(z.TwZ_Ilosc), 0) as TotalStock
        FROM CDN.Magazyny m WITH (NOLOCK)
        LEFT JOIN CDN.TwrZasoby z WITH (NOLOCK) ON m.Mag_MagId = z.TwZ_MagId
        GROUP BY m.Mag_MagId, m.Mag_Symbol, m.Mag_Nazwa
        """
        
        if only_with_stock:
            query += " HAVING SUM(z.TwZ_Ilosc) > 0"
        
        query += " ORDER BY m.Mag_Symbol"
        
        df = self.execute_query(query, query_name="get_warehouses")
        
        if not df.empty:
            self._set_cache(cache_key, df)
        
        return df

    def get_current_stock(self, use_cache: bool = True, warehouse_ids: list = None) -> pd.DataFrame:
        """
        Fetches current stock levels from TwrZasoby/Towary.
        Only includes items that are defined as Raw Materials in production orders (CZE_Typ IN (1, 2)).
        Excludes explicit Services (Twr_Typ = 2).
        
        Args:
            use_cache: If True, returns cached data if available (default: True)
            warehouse_ids: Optional list of warehouse IDs to filter by. If None, returns global stock.
        """
        # Create cache key based on warehouse filter
        warehouse_key = "_".join(map(str, sorted(warehouse_ids))) if warehouse_ids else "all"
        cache_key = f"current_stock_{warehouse_key}"
        
        if use_cache:
            cached = self._get_from_cache(cache_key)
            if cached is not None:
                return cached
        
        # Build query with optional warehouse filter
        if warehouse_ids:
            warehouse_list = ",".join(map(str, warehouse_ids))
            query = f"""
            SELECT 
                t.Twr_TwrId as TowarId,
                t.Twr_Kod as Code,
                t.Twr_Nazwa as Name,
                ISNULL(SUM(z.TwZ_Ilosc), 0) as StockLevel,
                (SELECT COUNT(*) FROM dbo.CtiZlecenieElem e WHERE e.CZE_TwrId = t.Twr_TwrId AND e.CZE_Typ IN (1, 2)) as UsageCount
            FROM CDN.Towary t
            LEFT JOIN CDN.TwrZasoby z ON t.Twr_TwrId = z.TwZ_TwrId AND z.TwZ_MagId IN ({warehouse_list})
            WHERE t.Twr_TwrId IN (
                SELECT DISTINCT CZE_TwrId 
                FROM dbo.CtiZlecenieElem 
                WHERE CZE_Typ IN (1, 2)
            )
            AND t.Twr_Typ != 2
            GROUP BY t.Twr_TwrId, t.Twr_Kod, t.Twr_Nazwa
            ORDER BY UsageCount DESC
            """
        else:
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

    def get_bom_with_stock(self, final_product_id: int, technology_id: int = None, warehouse_ids: list = None) -> pd.DataFrame:
        """
        Fetches BOM for a product along with current stock levels of ingredients.
        Used for AI generation to advise on purchasing.
        Strictly filters ingredients by CTI Type 1, 2 AND CDN Type != 2.
        
        Args:
            final_product_id: ID of the final product
            technology_id: Optional specific technology ID. If None, uses all technologies for product.
            warehouse_ids: Optional list of warehouse IDs to filter stock by. If None, uses all warehouses.
        """
        # Build warehouse filter for JOIN condition
        warehouse_filter = ""
        if warehouse_ids:
            warehouse_list = ",".join(map(str, warehouse_ids))
            warehouse_filter = f" AND z.TwZ_MagId IN ({warehouse_list})"
        
        # Build query with optional technology and warehouse filters
        base_query = f"""
        SELECT 
            elem_t.Twr_Kod as IngredientCode,
            elem_t.Twr_Nazwa as IngredientName,
            e.CTE_Ilosc as QuantityPerUnit,
            elem_t.Twr_JM as Unit,
            ISNULL(SUM(z.TwZ_Ilosc), 0) as CurrentStock
        FROM dbo.CtiTechnolNag n WITH (NOLOCK)
        JOIN dbo.CtiTechnolElem e WITH (NOLOCK) ON n.CTN_ID = e.CTE_CTNId
        JOIN CDN.Towary elem_t WITH (NOLOCK) ON e.CTE_TwrId = elem_t.Twr_TwrId
        LEFT JOIN CDN.TwrZasoby z WITH (NOLOCK) ON elem_t.Twr_TwrId = z.TwZ_TwrId{warehouse_filter}
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
    
    def get_bom_with_warehouse_breakdown(self, final_product_id: int, technology_id: int = None) -> pd.DataFrame:
        """
        Fetches BOM for a product with stock breakdown per warehouse.
        Used by AI to provide recommendations considering stock in other warehouses.
        
        Args:
            final_product_id: ID of the final product
            technology_id: Optional specific technology ID
            
        Returns:
            DataFrame with columns: IngredientCode, IngredientName, QuantityPerUnit, Unit,
                                   MagSymbol, MagName, StockInWarehouse, TotalStock
        """
        tech_filter = ""
        params = {"final_product_id": int(final_product_id)}  # Convert to Python int for ODBC compatibility
        
        if technology_id is not None:
            tech_filter = " AND n.CTN_ID = :technology_id"
            params["technology_id"] = int(technology_id)
        
        query = f"""
        WITH BomItems AS (
            SELECT DISTINCT
                elem_t.Twr_TwrId as IngredientId,
                elem_t.Twr_Kod as IngredientCode,
                elem_t.Twr_Nazwa as IngredientName,
                e.CTE_Ilosc as QuantityPerUnit,
                elem_t.Twr_JM as Unit
            FROM dbo.CtiTechnolNag n WITH (NOLOCK)
            JOIN dbo.CtiTechnolElem e WITH (NOLOCK) ON n.CTN_ID = e.CTE_CTNId
            JOIN CDN.Towary elem_t WITH (NOLOCK) ON e.CTE_TwrId = elem_t.Twr_TwrId
            WHERE n.CTN_TwrId = :final_product_id
              AND e.CTE_Typ IN (1, 2)
              AND elem_t.Twr_Typ != 2
              {tech_filter}
        )
        SELECT 
            b.IngredientCode,
            b.IngredientName,
            b.QuantityPerUnit,
            b.Unit,
            m.Mag_Symbol as MagSymbol,
            m.Mag_Nazwa as MagName,
            ISNULL(z.TwZ_Ilosc, 0) as StockInWarehouse,
            (SELECT ISNULL(SUM(z2.TwZ_Ilosc), 0) FROM CDN.TwrZasoby z2 WHERE z2.TwZ_TwrId = b.IngredientId) as TotalStock
        FROM BomItems b
        LEFT JOIN CDN.TwrZasoby z WITH (NOLOCK) ON b.IngredientId = z.TwZ_TwrId
        LEFT JOIN CDN.Magazyny m WITH (NOLOCK) ON z.TwZ_MagId = m.Mag_MagId
        WHERE z.TwZ_Ilosc > 0 OR z.TwZ_Ilosc IS NULL
        ORDER BY b.IngredientCode, m.Mag_Symbol
        """
        
        return self.execute_query(query, params=params,
                                  query_name=f"get_bom_with_warehouse_breakdown({final_product_id})")
    
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
    
    def get_vendor_delivery_stats(self, vendor_id: int = None, use_cache: bool = True) -> pd.DataFrame:
        """
        Analyzes vendor delivery performance based on CDN.TraNag (document headers).
        Calculates average delivery delays for supplier evaluation.
        
        Args:
            vendor_id: Optional specific vendor ID to analyze. If None, returns all vendors.
            use_cache: If True, returns cached data if available (default: True)
            
        Returns:
            DataFrame with columns:
            - VendorId, VendorCode, VendorName
            - DeliveryCount: Number of deliveries
            - AvgDelayDays: Average delay in days (positive = late, negative = early)
            - OnTimePercent: Percentage of on-time deliveries
            - Rating: A/B/C/D based on performance
        """
        cache_key = f"vendor_stats_{vendor_id or 'all'}"
        
        if use_cache:
            cached = self._get_from_cache(cache_key)
            if cached is not None:
                return cached
        
        # Query for delivery performance
        # TrN_TypDokumentu = 301 is PZ (Przyjęcie Zewnętrzne / External Receipt)
        # TrN_DataOtrz = Receipt date, TrN_DataDoc = Document date (expected)
        vendor_filter = ""
        params = {}
        if vendor_id is not None:
            vendor_filter = "AND t.TrN_KnTId = :vendor_id"
            params["vendor_id"] = vendor_id
        
        query = f"""
        SELECT 
            k.Knt_KntId as VendorId,
            k.Knt_Kod as VendorCode,
            k.Knt_Nazwa1 as VendorName,
            COUNT(*) as DeliveryCount,
            AVG(DATEDIFF(day, t.TrN_DataDoc, t.TrN_DataOtrz)) as AvgDelayDays,
            SUM(CASE WHEN DATEDIFF(day, t.TrN_DataDoc, t.TrN_DataOtrz) <= 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as OnTimePercent
        FROM CDN.TraNag t WITH (NOLOCK)
        JOIN CDN.Kontrahenci k WITH (NOLOCK) ON t.TrN_KnTId = k.Knt_KntId
        WHERE t.TrN_TypDokumentu = 301  -- PZ (przyjęcie zewnętrzne)
          AND t.TrN_DataOtrz IS NOT NULL
          AND t.TrN_DataDoc IS NOT NULL
          {vendor_filter}
        GROUP BY k.Knt_KntId, k.Knt_Kod, k.Knt_Nazwa1
        HAVING COUNT(*) >= 3  -- Minimum 3 deliveries for meaningful stats
        ORDER BY AvgDelayDays ASC
        """
        
        df = self.execute_query(query, params=params if params else None, 
                               query_name="get_vendor_delivery_stats")
        
        if not df.empty:
            # Add rating based on performance
            def calculate_rating(row):
                if row['AvgDelayDays'] <= 0 and row['OnTimePercent'] >= 90:
                    return 'A'
                elif row['AvgDelayDays'] <= 3 and row['OnTimePercent'] >= 70:
                    return 'B'
                elif row['AvgDelayDays'] <= 7 and row['OnTimePercent'] >= 50:
                    return 'C'
                else:
                    return 'D'
            
            df['Rating'] = df.apply(calculate_rating, axis=1)
            df['AvgDelayDays'] = df['AvgDelayDays'].round(1)
            df['OnTimePercent'] = df['OnTimePercent'].round(1)
            
            self._set_cache(cache_key, df)
        
        return df
    
    def get_product_delivery_info(self, product_id: int = None, use_cache: bool = True) -> pd.DataFrame:
        """
        Fetches delivery information from CtiDelivery table.
        Includes vendor info, delivery times, costs, and order limits.
        
        Args:
            product_id: Optional specific product ID. If None, returns all.
            use_cache: If True, returns cached data if available
            
        Returns:
            DataFrame with columns:
            - ProductId, ProductCode, ProductName
            - VendorId, VendorCode, VendorName
            - IsDefaultVendor
            - DeliveryTime_Min/Optimum/Max (in days)
            - DeliveryCost_Min/Optimum/Max
            - ProductionTime_Min/Optimum/Max
            - MinOrderQty, MaxOrderQty
            - Currency
        """
        cache_key = f"delivery_info_{product_id or 'all'}"
        
        if use_cache:
            cached = self._get_from_cache(cache_key)
            if cached is not None:
                return cached
        
        product_filter = ""
        params = {}
        if product_id is not None:
            product_filter = "AND cd.CD_TwrId = :product_id"
            params["product_id"] = product_id
        
        query = f"""
        SELECT 
            cd.CD_TwrId AS ProductId,
            t.Twr_Kod AS ProductCode,
            t.Twr_Nazwa AS ProductName,
            cd.CD_KntId AS VendorId,
            k.Knt_Kod AS VendorCode,
            k.Knt_Nazwa1 AS VendorName,
            cd.CD_DefaultProvider AS IsDefaultVendor,
            cd.CD_MinDeliveryTime AS DeliveryTime_Min,
            cd.CD_OptimumDeliveryTime AS DeliveryTime_Optimum,
            cd.CD_MaxDeliveryTime AS DeliveryTime_Max,
            cd.CD_MinDeliveryCost AS DeliveryCost_Min,
            cd.CD_OptimumDeliveryCost AS DeliveryCost_Optimum,
            cd.CD_MaxDeliveryCost AS DeliveryCost_Max,
            cd.CD_MinProductionTime AS ProductionTime_Min,
            cd.CD_OptimumProductionTime AS ProductionTime_Optimum,
            cd.CD_MaxProductionTime AS ProductionTime_Max,
            cd.CD_MinAmount AS MinOrderQty,
            cd.CD_MaxAmount AS MaxOrderQty,
            cd.CD_Currency AS Currency,
            cd.CD_Price AS UnitPrice
        FROM dbo.CtiDelivery cd
        LEFT JOIN CDN.Towary t ON cd.CD_TwrId = t.Twr_TwrId
        LEFT JOIN CDN.Kontrahenci k ON cd.CD_KntId = k.Knt_KntId
        WHERE 1=1 {product_filter}
        ORDER BY cd.CD_DefaultProvider DESC, t.Twr_Kod
        """
        
        df = self.execute_query(query, params=params if params else None,
                               query_name="get_product_delivery_info")
        
        if not df.empty:
            self._set_cache(cache_key, df)
        
        return df
    
    def get_product_lead_times(self, product_id: int = None, use_cache: bool = True) -> pd.DataFrame:
        """
        Fetches product lead times from CtiTwrCzasy table.
        Contains delivery and production times at product level (not vendor-specific).
        
        Args:
            product_id: Optional specific product ID. If None, returns all.
            use_cache: If True, returns cached data
            
        Returns:
            DataFrame with columns:
            - ProductId, ProductCode, ProductName
            - LeadTime_Min/Optimum/Max (delivery, in days)
            - LeadTime_Type (1=hours, 2=days, 3=weeks)
            - LeadCost_Min/Optimum/Max
            - ProdTime_Min/Optimum/Max (production)
            - ProdCost_Min/Optimum/Max
        """
        cache_key = f"lead_times_{product_id or 'all'}"
        
        if use_cache:
            cached = self._get_from_cache(cache_key)
            if cached is not None:
                return cached
        
        product_filter = ""
        params = {}
        if product_id is not None:
            product_filter = "AND crc.CRC_TwrId = :product_id"
            params["product_id"] = product_id
        
        query = f"""
        SELECT 
            crc.CRC_TwrId AS ProductId,
            t.Twr_Kod AS ProductCode,
            t.Twr_Nazwa AS ProductName,
            -- Delivery times
            crc.CRC_CzasMinMin AS LeadTime_Min,
            crc.CRC_CzasOPTIMin AS LeadTime_Optimum,
            crc.CRC_CzasMAXMin AS LeadTime_Max,
            crc.CRC_CzasMinTyp AS LeadTime_Type,  -- 1=hours, 2=days, 3=weeks
            crc.CRC_KosztMin AS LeadCost_Min,
            crc.CRC_KosztOPTI AS LeadCost_Optimum,
            crc.CRC_KosztMAX AS LeadCost_Max,
            -- Production times
            crc.CRC_CzasMinMinP AS ProdTime_Min,
            crc.CRC_CzasOPTIMinP AS ProdTime_Optimum,
            crc.CRC_CzasMAXMinP AS ProdTime_Max,
            crc.CRC_CzasMinTypP AS ProdTime_Type,
            crc.CRC_KosztMinP AS ProdCost_Min,
            crc.CRC_KosztOPTIP AS ProdCost_Optimum,
            crc.CRC_KosztMAXP AS ProdCost_Max,
            crc.CRC_OpisOPTI AS Description
        FROM dbo.CtiTwrCzasy crc
        LEFT JOIN CDN.Towary t ON crc.CRC_TwrId = t.Twr_TwrId
        WHERE crc.CRC_TwrId IS NOT NULL {product_filter}
        ORDER BY t.Twr_Kod
        """
        
        df = self.execute_query(query, params=params if params else None,
                               query_name="get_product_lead_times")
        
        if not df.empty:
            # Convert time type to label
            time_type_map = {1: 'hours', 2: 'days', 3: 'weeks'}
            if 'LeadTime_Type' in df.columns:
                df['LeadTime_Unit'] = df['LeadTime_Type'].map(time_type_map).fillna('days')
            if 'ProdTime_Type' in df.columns:
                df['ProdTime_Unit'] = df['ProdTime_Type'].map(time_type_map).fillna('days')
            
            self._set_cache(cache_key, df)
        
        return df
    
    def get_bom_with_delivery_info(self, final_product_id: int, technology_id: int = None, 
                                    warehouse_ids: list = None) -> pd.DataFrame:
        """
        Enhanced BOM query that includes delivery times from CtiDelivery.
        Used by MRP Simulator for production planning with lead times.
        
        Args:
            final_product_id: ID of the final product
            technology_id: Optional specific technology ID
            warehouse_ids: Optional warehouse filter for stock
            
        Returns:
            DataFrame with BOM info plus:
            - DefaultVendor, VendorCode
            - DeliveryTime_Optimum (days)
            - MinOrderQty
        """
        warehouse_filter = ""
        if warehouse_ids:
            warehouse_list = ",".join(map(str, warehouse_ids))
            warehouse_filter = f" AND z.TwZ_MagId IN ({warehouse_list})"
        
        tech_filter = ""
        params = {"final_product_id": int(final_product_id)}
        
        if technology_id is not None:
            tech_filter = " AND n.CTN_ID = :technology_id"
            params["technology_id"] = int(technology_id)
        
        query = f"""
        SELECT 
            elem_t.Twr_TwrId AS IngredientId,
            elem_t.Twr_Kod AS IngredientCode,
            elem_t.Twr_Nazwa AS IngredientName,
            e.CTE_Ilosc AS QuantityPerUnit,
            elem_t.Twr_JM AS Unit,
            ISNULL(SUM(z.TwZ_Ilosc), 0) AS CurrentStock,
            -- Delivery info from CtiDelivery (prefer default vendor)
            cd.CD_OptimumDeliveryTime AS DeliveryTime_Days,
            cd.CD_MinAmount AS MinOrderQty,
            cd.CD_MaxAmount AS MaxOrderQty,
            k.Knt_Kod AS VendorCode,
            k.Knt_Nazwa1 AS VendorName,
            cd.CD_DefaultProvider AS IsDefaultVendor,
            -- Lead time from CtiTwrCzasy (fallback)
            crc.CRC_CzasOPTIMin AS LeadTime_Fallback,
            crc.CRC_CzasOPTITyp AS LeadTime_Type
        FROM dbo.CtiTechnolNag n WITH (NOLOCK)
        JOIN dbo.CtiTechnolElem e WITH (NOLOCK) ON n.CTN_ID = e.CTE_CTNId
        JOIN CDN.Towary elem_t WITH (NOLOCK) ON e.CTE_TwrId = elem_t.Twr_TwrId
        LEFT JOIN CDN.TwrZasoby z WITH (NOLOCK) ON elem_t.Twr_TwrId = z.TwZ_TwrId{warehouse_filter}
        -- Join CtiDelivery for delivery info (get default vendor if exists)
        LEFT JOIN dbo.CtiDelivery cd WITH (NOLOCK) 
            ON elem_t.Twr_TwrId = cd.CD_TwrId 
            AND (cd.CD_DefaultProvider = 1 OR cd.CD_ID = (
                SELECT TOP 1 cd2.CD_ID FROM dbo.CtiDelivery cd2 
                WHERE cd2.CD_TwrId = elem_t.Twr_TwrId ORDER BY cd2.CD_DefaultProvider DESC
            ))
        LEFT JOIN CDN.Kontrahenci k WITH (NOLOCK) ON cd.CD_KntId = k.Knt_KntId
        -- Join CtiTwrCzasy for lead time fallback
        LEFT JOIN dbo.CtiTwrCzasy crc WITH (NOLOCK) ON elem_t.Twr_TwrId = crc.CRC_TwrId
        WHERE n.CTN_TwrId = :final_product_id
          AND e.CTE_Typ IN (1, 2)
          AND elem_t.Twr_Typ != 2
          {tech_filter}
        GROUP BY 
            elem_t.Twr_TwrId, elem_t.Twr_Kod, elem_t.Twr_Nazwa, 
            e.CTE_Ilosc, elem_t.Twr_JM,
            cd.CD_OptimumDeliveryTime, cd.CD_MinAmount, cd.CD_MaxAmount,
            k.Knt_Kod, k.Knt_Nazwa1, cd.CD_DefaultProvider,
            crc.CRC_CzasOPTIMin, crc.CRC_CzasOPTITyp
        ORDER BY e.CTE_Ilosc DESC
        """
        
        df = self.execute_query(query, params=params,
                               query_name=f"get_bom_with_delivery_info({final_product_id})")
        
        if not df.empty:
            # Use fallback lead time if no CtiDelivery data
            df['DeliveryTime_Days'] = df.apply(
                lambda row: row['DeliveryTime_Days'] if pd.notna(row['DeliveryTime_Days']) and row['DeliveryTime_Days'] > 0
                else (row['LeadTime_Fallback'] if row.get('LeadTime_Type') == 2 else 0),
                axis=1
            )
            df['DeliveryTime_Days'] = df['DeliveryTime_Days'].fillna(0).astype(int)
        
        return df
    
    # ========== CTI Deep Integration Methods ==========
    
    def get_cti_holidays(self, year_from: int = None, year_to: int = None, use_cache: bool = True) -> pd.DataFrame:
        """
        Fetches company holidays from CtiHolidays table.
        Better than holidays library - includes Easter and company-specific days.
        
        Args:
            year_from: Optional start year filter
            year_to: Optional end year filter
            use_cache: If True, returns cached data
            
        Returns:
            DataFrame with columns: HolidayDate (as datetime)
        """
        cache_key = f"cti_holidays_{year_from}_{year_to}"
        
        if use_cache:
            cached = self._get_from_cache(cache_key)
            if cached is not None:
                return cached
        
        year_filter = ""
        if year_from and year_to:
            year_filter = f"WHERE YEAR(CH_Date) BETWEEN {int(year_from)} AND {int(year_to)}"
        elif year_from:
            year_filter = f"WHERE YEAR(CH_Date) >= {int(year_from)}"
        elif year_to:
            year_filter = f"WHERE YEAR(CH_Date) <= {int(year_to)}"
        
        query = f"""
        SELECT CH_Date AS HolidayDate
        FROM dbo.CtiHolidays
        {year_filter}
        ORDER BY CH_Date
        """
        
        df = self.execute_query(query, query_name="get_cti_holidays")
        
        if not df.empty:
            df['HolidayDate'] = pd.to_datetime(df['HolidayDate'])
            self._set_cache(cache_key, df)
        
        return df
    
    def get_cti_holidays_set(self, year_from: int = 2020, year_to: int = 2030) -> set:
        """
        Returns holidays as a set for fast lookup in forecasting.
        
        Returns:
            Set of datetime.date objects
        """
        df = self.get_cti_holidays(year_from, year_to)
        if df.empty:
            return set()
        return set(df['HolidayDate'].dt.date.tolist())
    
    def get_product_substitutes(self, product_id: int = None, technology_id: int = None, 
                                 use_cache: bool = True) -> pd.DataFrame:
        """
        Fetches product substitutes from CtiTechnolZamienniki.
        Critical for MRP when main ingredient is unavailable.
        
        Args:
            product_id: Filter by original product ID
            technology_id: Filter by technology ID
            use_cache: If True, returns cached data
            
        Returns:
            DataFrame with columns:
            - OriginalId, OriginalCode, OriginalName
            - SubstituteId, SubstituteCode, SubstituteName
            - IsAllowed, SubstituteType
        """
        cache_key = f"substitutes_{product_id}_{technology_id}"
        
        if use_cache:
            cached = self._get_from_cache(cache_key)
            if cached is not None:
                return cached
        
        filters = []
        params = {}
        
        if product_id is not None:
            filters.append("z.CTM_TwrID = :product_id")
            params["product_id"] = product_id
        if technology_id is not None:
            filters.append("z.CTM_CTNID = :technology_id")
            params["technology_id"] = technology_id
        
        where_clause = "WHERE " + " AND ".join(filters) if filters else ""
        
        query = f"""
        SELECT 
            z.CTM_TwrID AS OriginalId,
            t_orig.Twr_Kod AS OriginalCode,
            t_orig.Twr_Nazwa AS OriginalName,
            z.CTM_ZamID AS SubstituteId,
            t_zam.Twr_Kod AS SubstituteCode,
            t_zam.Twr_Nazwa AS SubstituteName,
            z.CTM_Dozwolony AS IsAllowed,
            z.CTM_Typ AS SubstituteType,
            z.CTM_CTNID AS TechnologyId
        FROM dbo.CtiTechnolZamienniki z
        LEFT JOIN CDN.Towary t_orig ON z.CTM_TwrID = t_orig.Twr_TwrId
        LEFT JOIN CDN.Towary t_zam ON z.CTM_ZamID = t_zam.Twr_TwrId
        {where_clause}
        ORDER BY t_orig.Twr_Kod
        """
        
        df = self.execute_query(query, params=params if params else None,
                               query_name="get_product_substitutes")
        
        if not df.empty:
            self._set_cache(cache_key, df)
        
        return df
    
    def get_shortage_analysis_cti(self, warehouse_id: int = None, 
                                   department_id: int = None) -> pd.DataFrame:
        """
        Calls CTI's built-in shortage analysis logic via CTIProdukcjaBrakiSurowca procedure.
        Uses the same business logic as the CTI Production program.
        
        Args:
            warehouse_id: Optional warehouse filter
            department_id: Optional department (Dział) filter
            
        Returns:
            DataFrame with shortage analysis results
        """
        # First get existing shortages from CtiBrakiElem with details
        query = """
        SELECT 
            bn.CBN_NrPelny AS ShortageDocNumber,
            bn.CBN_DataRealizacji AS RealizationDate,
            bn.CBN_Status AS Status,
            be.CBE_TwrId AS ProductId,
            t.Twr_Kod AS ProductCode,
            t.Twr_Nazwa AS ProductName,
            be.CBE_Ilosc AS ShortageQty,
            be.CBE_DostawcaID AS VendorId,
            k.Knt_Kod AS VendorCode,
            k.Knt_Nazwa1 AS VendorName,
            be.CBE_MagazynID AS WarehouseId,
            be.CBE_DzialID AS DepartmentId
        FROM dbo.CtiBrakiNag bn
        JOIN dbo.CtiBrakiElem be ON bn.CBN_ID = be.CBE_CBNId
        LEFT JOIN CDN.Towary t ON be.CBE_TwrId = t.Twr_TwrId
        LEFT JOIN CDN.Kontrahenci k ON be.CBE_DostawcaID = k.Knt_KntId
        WHERE bn.CBN_Status = 0  -- Active shortages only
        ORDER BY bn.CBN_DataRealizacji DESC, be.CBE_Ilosc DESC
        """
        
        df = self.execute_query(query, query_name="get_shortage_analysis_cti")
        
        return df
    
    def get_production_departments(self, use_cache: bool = True) -> pd.DataFrame:
        """
        Fetches production departments from CtiDzial with warehouse mappings.
        
        Returns:
            DataFrame with department info and source/destination warehouses
        """
        cache_key = "production_departments"
        
        if use_cache:
            cached = self._get_from_cache(cache_key)
            if cached is not None:
                return cached
        
        query = """
        SELECT 
            d.CDZ_ID AS DepartmentId,
            d.CDZ_Kod AS DepartmentCode,
            d.CDZ_MagSId AS SourceWarehouseId,
            ms.Mag_Symbol AS SourceWarehouseCode,
            d.CDZ_MagPId AS DestWarehouseId,
            mp.Mag_Symbol AS DestWarehouseCode
        FROM dbo.CtiDzial d
        LEFT JOIN CDN.Magazyny ms ON d.CDZ_MagSId = ms.Mag_MagId
        LEFT JOIN CDN.Magazyny mp ON d.CDZ_MagPId = mp.Mag_MagId
        ORDER BY d.CDZ_Kod
        """
        
        df = self.execute_query(query, query_name="get_production_departments")
        
        if not df.empty:
            self._set_cache(cache_key, df)
        
        return df
    
    def get_production_resources(self, department_id: int = None, 
                                  use_cache: bool = True) -> pd.DataFrame:
        """
        Fetches production resources (CtiZasob) with costs and work times.
        Useful for capacity planning and cost estimation.
        
        Args:
            department_id: Optional filter by department
            use_cache: If True, returns cached data
            
        Returns:
            DataFrame with resource info including hourly costs
        """
        cache_key = f"production_resources_{department_id}"
        
        if use_cache:
            cached = self._get_from_cache(cache_key)
            if cached is not None:
                return cached
        
        dept_filter = ""
        params = {}
        if department_id is not None:
            dept_filter = "WHERE z.CZ_DzialID = :department_id"
            params["department_id"] = department_id
        
        query = f"""
        SELECT 
            z.CZ_ID AS ResourceId,
            z.CZ_Kod AS ResourceCode,
            z.CZ_KosztPracy AS HourlyCost,
            z.CZ_CzasPracy AS WorkTime,
            z.CZ_CzasUzbrojenia AS SetupTime,
            z.CZ_JMCzasu AS TimeUnit,  -- 1=hours, 2=days
            z.CZ_DzialID AS DepartmentId,
            z.CZ_Typ AS ResourceType,
            z.CZ_KontrolaDostepnosci AS AvailabilityCheck
        FROM dbo.CtiZasob z
        {dept_filter}
        ORDER BY z.CZ_Kod
        """
        
        df = self.execute_query(query, params=params if params else None,
                               query_name="get_production_resources")
        
        if not df.empty:
            self._set_cache(cache_key, df)
        
        return df
    
    def get_order_statuses(self) -> pd.DataFrame:
        """
        Fetches production order status dictionary from CtiStatusy.
        Useful for understanding production workflow states.
        
        Returns:
            DataFrame with status codes and names by type
        """
        query = """
        SELECT 
            CS_StatusNr AS StatusCode,
            CS_Typ AS StatusType,
            CS_StatusNazwa AS StatusName
        FROM dbo.CtiStatusy
        ORDER BY CS_Typ, CS_StatusNr
        """
        
        return self.execute_query(query, query_name="get_order_statuses")
    
    # ========== CTI Deep Integration - U1: Production Status ==========
    
    def get_production_status(self, order_id: int = None, use_cache: bool = True) -> pd.DataFrame:
        """
        [U1] Fetches production status from CtiProdukcjaStatus.
        Critical for MRP: determines which orders are complete vs in-progress.
        
        Args:
            order_id: Specific order ID. If None, returns all recent statuses.
            use_cache: If True, returns cached data if available
            
        Returns:
            DataFrame with columns:
            - OrderId, OrderNumber
            - MaterialsIssued (0/1=NIE, 2=CZĘŚCIOWO, 3=TAK)
            - ProductReceived (0/1=NIE, 2=CZĘŚCIOWO, 3=TAK)
            - CompletedQty
            - StatusCode (from CtiStatusy)
            - StatusName
            - LastModified
        """
        cache_key = f"production_status_{order_id or 'all'}"
        
        if use_cache:
            cached = self._get_from_cache(cache_key)
            if cached is not None:
                return cached
        
        order_filter = ""
        params = {}
        if order_id is not None:
            order_filter = "AND ps.CPS_DokID = :order_id"
            params["order_id"] = order_id
        
        query = f"""
        SELECT 
            ps.CPS_DokID AS OrderId,
            zn.CZN_NrPelny AS OrderNumber,
            ps.CPS_StatusMMWydane AS MaterialsIssued,
            ps.CPS_StatusPWWG AS ProductReceived,
            ps.IloscZrealizowana AS CompletedQty,
            ps.CPS_StatusProdukcjaEnum AS StatusCode,
            cs.CS_StatusNazwa AS StatusName,
            ps.DataModyfikacji AS LastModified,
            zn.CZN_Ilosc AS TargetQty,
            CASE 
                WHEN ps.IloscZrealizowana >= zn.CZN_Ilosc THEN 'ZAKOŃCZONE'
                WHEN ps.IloscZrealizowana > 0 THEN 'W REALIZACJI'
                ELSE 'NIE ROZPOCZĘTE'
            END AS RealizationStatus
        FROM dbo.CtiProdukcjaStatus ps
        LEFT JOIN dbo.CtiZlecenieNag zn ON ps.CPS_DokID = zn.CZN_ID
        LEFT JOIN dbo.CtiStatusy cs ON ps.CPS_StatusProdukcjaEnum = cs.CS_StatusNr AND cs.CS_Typ = 1
        WHERE ps.CPS_DokTyp = 6  -- Production Orders (ZP)
        {order_filter}
        ORDER BY ps.DataModyfikacji DESC
        """
        
        df = self.execute_query(query, params=params if params else None,
                               query_name="get_production_status")
        
        if not df.empty:
            self._set_cache(cache_key, df)
        
        return df
    
    def get_active_orders_demand(self, product_ids: list = None, 
                                  exclude_completed: bool = True) -> pd.DataFrame:
        """
        [U1 Extension] Gets raw material demand from active (non-completed) production orders.
        Essential for calculating net requirements in MRP.
        
        Args:
            product_ids: Optional list of ingredient product IDs to filter
            exclude_completed: If True, excludes orders with CompletedQty >= TargetQty
            
        Returns:
            DataFrame with pending demand per ingredient from active orders
        """
        product_filter = ""
        completed_filter = ""
        
        if product_ids:
            product_list = ",".join(map(str, product_ids))
            product_filter = f"AND ze.CZE_TwrId IN ({product_list})"
        
        if exclude_completed:
            completed_filter = """
            AND (
                ps.IloscZrealizowana IS NULL 
                OR ps.IloscZrealizowana < zn.CZN_Ilosc
            )
            """
        
        query = f"""
        SELECT 
            ze.CZE_TwrId AS IngredientId,
            t.Twr_Kod AS IngredientCode,
            t.Twr_Nazwa AS IngredientName,
            SUM(ze.CZE_Ilosc * (zn.CZN_Ilosc - ISNULL(ps.IloscZrealizowana, 0))) AS PendingDemand,
            COUNT(DISTINCT zn.CZN_ID) AS ActiveOrderCount
        FROM dbo.CtiZlecenieElem ze WITH (NOLOCK)
        JOIN dbo.CtiZlecenieNag zn WITH (NOLOCK) ON ze.CZE_CZNId = zn.CZN_ID
        LEFT JOIN dbo.CtiProdukcjaStatus ps ON zn.CZN_ID = ps.CPS_DokID AND ps.CPS_DokTyp = 6
        LEFT JOIN CDN.Towary t WITH (NOLOCK) ON ze.CZE_TwrId = t.Twr_TwrId
        WHERE ze.CZE_Typ IN (1, 2)  -- Raw materials only
          AND zn.CZN_Status > 0     -- Active orders only
          {product_filter}
          {completed_filter}
        GROUP BY ze.CZE_TwrId, t.Twr_Kod, t.Twr_Nazwa
        ORDER BY PendingDemand DESC
        """
        
        return self.execute_query(query, query_name="get_active_orders_demand")
    
    # ========== CTI Deep Integration - U2: Shortage Synchronization ==========
    
    def compare_with_cti_shortages(self, calculated_shortages: pd.DataFrame,
                                    warehouse_id: int = None) -> dict:
        """
        [U2] Compares AI-calculated shortages with existing CTI shortage documents.
        Enables synchronization between AI recommendations and CTI workflow.
        
        Args:
            calculated_shortages: DataFrame with columns [IngredientId, ShortageQty]
            warehouse_id: Optional warehouse filter
            
        Returns:
            dict with keys:
            - 'new_shortages': Items to add to CTI (not in existing docs)
            - 'already_in_cti': Items already registered in CTI
            - 'cti_resolved': CTI items that may no longer be needed
            - 'summary': Text summary for AI
        """
        # Get existing CTI shortages
        cti_shortages = self.get_shortage_analysis_cti(warehouse_id=warehouse_id)
        
        result = {
            'new_shortages': [],
            'already_in_cti': [],
            'cti_resolved': [],
            'summary': ''
        }
        
        if calculated_shortages.empty:
            result['summary'] = "Brak wyliczonych braków do porównania."
            return result
        
        if cti_shortages.empty:
            result['new_shortages'] = calculated_shortages.to_dict('records')
            result['summary'] = f"Wszystkie {len(calculated_shortages)} braki do zgłoszenia w CTI."
            return result
        
        # Create lookup for CTI shortages by product ID
        cti_products = set(cti_shortages['ProductId'].tolist()) if 'ProductId' in cti_shortages.columns else set()
        
        for _, row in calculated_shortages.iterrows():
            product_id = row.get('IngredientId') or row.get('ProductId')
            if product_id in cti_products:
                result['already_in_cti'].append(row.to_dict())
            else:
                result['new_shortages'].append(row.to_dict())
        
        # Find CTI items not in calculated shortages (potentially resolved)
        calc_products = set(calculated_shortages.get('IngredientId', calculated_shortages.get('ProductId', [])).tolist())
        for _, row in cti_shortages.iterrows():
            if row['ProductId'] not in calc_products:
                result['cti_resolved'].append(row.to_dict())
        
        # Generate summary
        lines = []
        if result['new_shortages']:
            lines.append(f"🆕 Nowe braki do zgłoszenia: {len(result['new_shortages'])}")
        if result['already_in_cti']:
            lines.append(f"✅ Już w CTI: {len(result['already_in_cti'])}")
        if result['cti_resolved']:
            lines.append(f"❓ Do weryfikacji (może rozwiązane): {len(result['cti_resolved'])}")
        
        result['summary'] = "\n".join(lines) if lines else "Brak różnic."
        
        return result
    
    # ========== CTI Deep Integration - U3: Smart Substitutes ==========
    
    def get_smart_substitutes(self, product_id: int, required_qty: float = 0,
                               warehouse_ids: list = None) -> pd.DataFrame:
        """
        [U3] Enhanced substitute lookup with stock availability.
        Returns substitutes sorted by best availability to cover shortage.
        
        Args:
            product_id: Original ingredient ID
            required_qty: How much is needed (for coverage calculation)
            warehouse_ids: Optional warehouse filter for stock
            
        Returns:
            DataFrame with columns:
            - SubstituteId, SubstituteCode, SubstituteName
            - IsAllowed (1 = can use, 0 = cannot)
            - CurrentStock
            - Coverage (how much of required_qty can be covered)
            - Recommendation (text)
        """
        warehouse_filter = ""
        if warehouse_ids:
            warehouse_list = ",".join(map(str, warehouse_ids))
            warehouse_filter = f" AND z.TwZ_MagId IN ({warehouse_list})"
        
        query = f"""
        SELECT 
            zam.CTM_ZamID AS SubstituteId,
            t.Twr_Kod AS SubstituteCode,
            t.Twr_Nazwa AS SubstituteName,
            zam.CTM_Dozwolony AS IsAllowed,
            zam.CTM_Typ AS SubstituteType,
            ISNULL(SUM(z.TwZ_Ilosc), 0) AS CurrentStock,
            t.Twr_JM AS Unit
        FROM dbo.CtiTechnolZamienniki zam
        LEFT JOIN CDN.Towary t ON zam.CTM_ZamID = t.Twr_TwrId
        LEFT JOIN CDN.TwrZasoby z ON zam.CTM_ZamID = z.TwZ_TwrId{warehouse_filter}
        WHERE zam.CTM_TwrID = :product_id
        GROUP BY zam.CTM_ZamID, t.Twr_Kod, t.Twr_Nazwa, zam.CTM_Dozwolony, zam.CTM_Typ, t.Twr_JM
        ORDER BY zam.CTM_Dozwolony DESC, CurrentStock DESC
        """
        
        df = self.execute_query(query, params={"product_id": product_id},
                               query_name=f"get_smart_substitutes({product_id})")
        
        if not df.empty and required_qty > 0:
            # Calculate coverage percentage
            df['Coverage'] = (df['CurrentStock'] / required_qty * 100).clip(upper=100).round(1)
            
            # Generate recommendations
            def get_recommendation(row):
                if row['IsAllowed'] == 0:
                    return "⛔ Niedozwolony"
                elif row['CurrentStock'] >= required_qty:
                    return "✅ Pełna zamiana możliwa"
                elif row['CurrentStock'] > 0:
                    return f"⚠️ Częściowo ({row['Coverage']:.0f}%)"
                else:
                    return "❌ Brak na stanie"
            
            df['Recommendation'] = df.apply(get_recommendation, axis=1)
        
        return df
    
    # ========== CTI Deep Integration - U4: Dashboard Stats ==========
    
    def get_production_dashboard_stats(self, date_from: str = None, 
                                        date_to: str = None) -> dict:
        """
        [U4] Aggregated statistics for production dashboard.
        Combines multiple CTI tables for a comprehensive overview.
        
        Args:
            date_from: Optional start date filter (YYYY-MM-DD)
            date_to: Optional end date filter (YYYY-MM-DD)
            
        Returns:
            dict with keys:
            - orders: {total, by_status}
            - shortages: {active_docs, total_items}
            - technologies: {total, active}
            - resources: {total, by_department}
        """
        import datetime
        
        if not date_from:
            date_from = (datetime.datetime.now() - datetime.timedelta(days=30)).strftime('%Y-%m-%d')
        if not date_to:
            date_to = datetime.datetime.now().strftime('%Y-%m-%d')
        
        result = {
            'orders': {'total': 0, 'by_status': {}},
            'shortages': {'active_docs': 0, 'total_items': 0},
            'technologies': {'total': 0, 'active': 0},
            'resources': {'total': 0, 'by_department': {}},
            'period': {'from': date_from, 'to': date_to}
        }
        
        # Orders by status
        try:
            q_orders = f"""
            SELECT 
                ISNULL(cs.CS_StatusNazwa, 'Brak statusu') AS StatusName,
                COUNT(*) AS Count
            FROM dbo.CtiZlecenieNag zn WITH (NOLOCK)
            LEFT JOIN dbo.CtiStatusy cs ON zn.CZN_Status = cs.CS_StatusNr AND cs.CS_Typ = 1
            WHERE zn.CZN_DataWystaw BETWEEN '{date_from}' AND '{date_to}'
            GROUP BY cs.CS_StatusNazwa
            """
            df_orders = self.execute_query(q_orders, query_name="dashboard_orders")
            if not df_orders.empty:
                result['orders']['total'] = int(df_orders['Count'].sum())
                result['orders']['by_status'] = dict(zip(df_orders['StatusName'], df_orders['Count']))
        except Exception as e:
            logger.debug(f"Dashboard orders error: {e}")
        
        # Shortages
        try:
            q_shortages = """
            SELECT 
                COUNT(DISTINCT bn.CBN_ID) AS DocCount,
                COUNT(*) AS ItemCount
            FROM dbo.CtiBrakiNag bn
            JOIN dbo.CtiBrakiElem be ON bn.CBN_ID = be.CBE_CBNId
            WHERE bn.CBN_Status = 0
            """
            df_short = self.execute_query(q_shortages, query_name="dashboard_shortages")
            if not df_short.empty:
                result['shortages']['active_docs'] = int(df_short['DocCount'].iloc[0] or 0)
                result['shortages']['total_items'] = int(df_short['ItemCount'].iloc[0] or 0)
        except Exception as e:
            logger.debug(f"Dashboard shortages error: {e}")
        
        # Technologies
        try:
            q_tech = """
            SELECT 
                COUNT(*) AS Total,
                SUM(CASE WHEN CTN_Status = 1 THEN 1 ELSE 0 END) AS Active
            FROM dbo.CtiTechnolNag
            """
            df_tech = self.execute_query(q_tech, query_name="dashboard_tech")
            if not df_tech.empty:
                result['technologies']['total'] = int(df_tech['Total'].iloc[0] or 0)
                result['technologies']['active'] = int(df_tech['Active'].iloc[0] or 0)
        except Exception as e:
            logger.debug(f"Dashboard technologies error: {e}")
        
        # Resources by department
        try:
            q_resources = """
            SELECT 
                d.CDZ_Kod AS Department,
                COUNT(*) AS ResourceCount
            FROM dbo.CtiZasob z
            LEFT JOIN dbo.CtiDzial d ON z.CZ_DzialID = d.CDZ_ID
            GROUP BY d.CDZ_Kod
            """
            df_res = self.execute_query(q_resources, query_name="dashboard_resources")
            if not df_res.empty:
                result['resources']['total'] = int(df_res['ResourceCount'].sum())
                result['resources']['by_department'] = dict(zip(
                    df_res['Department'].fillna('Brak').tolist(), 
                    df_res['ResourceCount'].tolist()
                ))
        except Exception as e:
            logger.debug(f"Dashboard resources error: {e}")
        
        return result
    
    # ========== CTI Deep Integration - U5: Completions History ==========
    
    def get_completions_history(self, order_id: int = None, 
                                 limit: int = 100) -> pd.DataFrame:
        """
        [U5] Fetches completion records from CtiKompletacja tables.
        Shows what products were assembled and what materials were used.
        
        Args:
            order_id: Optional filter by production order (ZP) ID
            limit: Maximum records to return (default 100)
            
        Returns:
            DataFrame with completion details:
            - CompletionId, OrderId, CreatedDate
            - ProductCode, ProductName, ProductQty
            - IngredientCode, IngredientName, UsedQty
        """
        order_filter = ""
        params = {}
        if order_id is not None:
            order_filter = "AND kn.KPN_ZPID = :order_id"
            params["order_id"] = order_id
        
        query = f"""
        SELECT TOP {int(limit)}
            kn.KPN_ID AS CompletionId,
            kn.KPN_ZPID AS OrderId,
            kn.KPN_DataUtworzenia AS CreatedDate,
            kw.KPW_TwrKod AS ProductCode,
            kw.KPW_TwrNazwa AS ProductName,
            kw.KPW_IloscWyrobu AS ProductQty,
            ks.KPS_TwrKod AS IngredientCode,
            ks.KPS_TwrNazwa AS IngredientName,
            ks.KPS_IloscSurowca AS UsedQty,
            zn.CZN_NrPelny AS OrderNumber
        FROM dbo.CtiKompletacjaNag kn
        JOIN dbo.CtiKompletacjaWyrob kw ON kn.KPN_ID = kw.KPW_KPNID
        JOIN dbo.CtiKompletacjaSurowiec ks ON kw.KPW_ID = ks.KPS_KPWID
        LEFT JOIN dbo.CtiZlecenieNag zn ON kn.KPN_ZPID = zn.CZN_ID
        WHERE 1=1 {order_filter}
        ORDER BY kn.KPN_DataUtworzenia DESC
        """
        
        return self.execute_query(query, params=params if params else None,
                                 query_name="get_completions_history")
    
    def get_completion_summary(self, product_id: int = None) -> pd.DataFrame:
        """
        [U5 Extension] Aggregated completion statistics per product.
        
        Args:
            product_id: Optional filter by product ID
            
        Returns:
            DataFrame with: ProductCode, TotalProduced, TotalCompletions, AvgBatchSize
        """
        product_filter = ""
        if product_id:
            product_filter = f"AND kw.KPW_TwrID = {int(product_id)}"
        
        query = f"""
        SELECT 
            kw.KPW_TwrKod AS ProductCode,
            kw.KPW_TwrNazwa AS ProductName,
            SUM(kw.KPW_IloscWyrobu) AS TotalProduced,
            COUNT(DISTINCT kn.KPN_ID) AS TotalCompletions,
            AVG(kw.KPW_IloscWyrobu) AS AvgBatchSize
        FROM dbo.CtiKompletacjaNag kn
        JOIN dbo.CtiKompletacjaWyrob kw ON kn.KPN_ID = kw.KPW_KPNID
        WHERE 1=1 {product_filter}
        GROUP BY kw.KPW_TwrKod, kw.KPW_TwrNazwa
        ORDER BY TotalProduced DESC
        """
        
        return self.execute_query(query, query_name="get_completion_summary")
    
    # ========== CTI Deep Integration - U6: CTI Attributes ==========
    
    def get_product_cti_attributes(self, product_id: int = None,
                                    doc_type: int = 1) -> pd.DataFrame:
        """
        [U6] Fetches CTI-specific attributes from CtiAtrybutyElem.
        These are custom attributes defined in CTI Production, not CDN attributes.
        
        Args:
            product_id: Optional product ID to filter
            doc_type: Document type (1=product, 6=ZP order, etc.)
            
        Returns:
            DataFrame with columns:
            - ProductId (or DocId)
            - AttributeName, AttributeValue, AttributeType
        """
        product_filter = ""
        params = {"doc_type": doc_type}
        if product_id is not None:
            product_filter = "AND cae.CAE_IdDok = :product_id"
            params["product_id"] = product_id
        
        query = f"""
        SELECT 
            cae.CAE_IdDok AS DocId,
            cae.CAE_TypDok AS DocType,
            can.CAN_Lp AS AttrOrder,
            can.CAN_Nazwa AS AttributeName,
            cae.CAE_Wartosc AS AttributeValue,
            can.CAN_Typ AS AttributeType,
            can.CAN_Opis AS AttributeDescription
        FROM dbo.CtiAtrybutyElem cae
        JOIN dbo.CtiAtrybutyNag can ON cae.CAE_CANLp = can.CAN_Lp
        WHERE cae.CAE_TypDok = :doc_type
        {product_filter}
        ORDER BY cae.CAE_IdDok, can.CAN_Lp
        """
        
        return self.execute_query(query, params=params,
                                 query_name="get_product_cti_attributes")
    
    def get_available_cti_attributes(self) -> pd.DataFrame:
        """
        [U6 Extension] Lists all available CTI attribute definitions.
        
        Returns:
            DataFrame with all attribute definitions from CtiAtrybutyNag
        """
        query = """
        SELECT 
            CAN_Lp AS AttrOrder,
            CAN_Nazwa AS AttributeName,
            CAN_Typ AS AttributeType,
            CAN_Domysla AS DefaultValue,
            CAN_Opis AS Description,
            CAN_Panel AS ShowInPanel
        FROM dbo.CtiAtrybutyNag
        ORDER BY CAN_Lp
        """
        
        return self.execute_query(query, query_name="get_available_cti_attributes")


