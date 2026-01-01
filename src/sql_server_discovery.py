"""
SQL Server Discovery Module.
Provides functions to detect local SQL Server instances, list databases,
and manage connection configuration.

This module enables the first-run connection wizard to auto-detect
available SQL Server instances on Windows systems.
"""

import os
import logging
import urllib.parse
from typing import List, Tuple, Optional
from pathlib import Path

logger = logging.getLogger('SQLServerDiscovery')


def discover_sql_servers() -> List[str]:
    """
    Discovers locally installed SQL Server instances from Windows Registry.
    
    Returns:
        List of server instance names (e.g., ['DESKTOP-ABC\\SQL', 'DESKTOP-ABC\\SQLEXPRESS'])
    """
    servers = []
    
    try:
        import winreg
        
        # Get computer name for full server path
        computer_name = os.environ.get('COMPUTERNAME', 'localhost')
        
        # Try to read from Instance Names\SQL key
        try:
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Microsoft SQL Server\Instance Names\SQL",
                0,
                winreg.KEY_READ | winreg.KEY_WOW64_64KEY
            )
            
            i = 0
            while True:
                try:
                    instance_name, _, _ = winreg.EnumValue(key, i)
                    if instance_name.upper() == 'MSSQLSERVER':
                        # Default instance - use just computer name
                        servers.append(computer_name)
                    else:
                        servers.append(f"{computer_name}\\{instance_name}")
                    i += 1
                except OSError:
                    break
            
            winreg.CloseKey(key)
            
        except FileNotFoundError:
            logger.debug("No SQL Server instances found in registry (Instance Names\\SQL)")
        
        # Also try InstalledInstances key as fallback
        if not servers:
            try:
                key = winreg.OpenKey(
                    winreg.HKEY_LOCAL_MACHINE,
                    r"SOFTWARE\Microsoft\Microsoft SQL Server",
                    0,
                    winreg.KEY_READ | winreg.KEY_WOW64_64KEY
                )
                
                try:
                    instances, _ = winreg.QueryValueEx(key, "InstalledInstances")
                    if instances:
                        for instance in instances:
                            if instance.upper() == 'MSSQLSERVER':
                                servers.append(computer_name)
                            else:
                                servers.append(f"{computer_name}\\{instance}")
                except FileNotFoundError:
                    pass
                
                winreg.CloseKey(key)
                
            except FileNotFoundError:
                logger.debug("No SQL Server found in registry (InstalledInstances)")
                
    except ImportError:
        logger.warning("winreg not available - SQL Server discovery disabled (non-Windows)")
    except Exception as e:
        logger.error(f"Error discovering SQL servers: {e}")
    
    logger.info(f"Discovered SQL Server instances: {servers}")
    return servers


def get_odbc_drivers() -> List[str]:
    """
    Returns list of available ODBC drivers for SQL Server.
    
    Returns:
        List of driver names (e.g., ['ODBC Driver 17 for SQL Server', 'ODBC Driver 18 for SQL Server'])
    """
    drivers = []
    
    try:
        import pyodbc
        all_drivers = pyodbc.drivers()
        
        # Filter for SQL Server drivers
        sql_drivers = [d for d in all_drivers if 'SQL Server' in d]
        
        # Sort by version (prefer newer drivers)
        drivers = sorted(sql_drivers, reverse=True)
        
        logger.info(f"Available SQL Server ODBC drivers: {drivers}")
        
    except ImportError:
        logger.error("pyodbc not installed")
    except Exception as e:
        logger.error(f"Error getting ODBC drivers: {e}")
    
    return drivers


def get_preferred_driver() -> str:
    """
    Returns the preferred ODBC driver for SQL Server connections.
    Prefers newer driver versions.
    
    Returns:
        Driver name string or default fallback
    """
    drivers = get_odbc_drivers()
    
    # Preference order
    preferred = [
        'ODBC Driver 18 for SQL Server',
        'ODBC Driver 17 for SQL Server',
        'SQL Server Native Client 11.0',
        'SQL Server'
    ]
    
    for driver in preferred:
        if driver in drivers:
            return driver
    
    # Return first available or default
    return drivers[0] if drivers else 'ODBC Driver 17 for SQL Server'


def list_databases(server: str, user: str, password: str, use_windows_auth: bool = False) -> Tuple[List[str], Optional[str]]:
    """
    Lists available databases on a SQL Server instance.
    
    Args:
        server: Server instance name (e.g., 'DESKTOP-ABC\\SQL')
        user: SQL Server username (ignored if use_windows_auth=True)
        password: SQL Server password (ignored if use_windows_auth=True)
        use_windows_auth: If True, use Windows Authentication instead of SQL Auth
        
    Returns:
        Tuple of (database_list, error_message). If successful, error_message is None.
    """
    databases = []
    error = None
    
    try:
        import pyodbc
        
        driver = get_preferred_driver()
        
        if use_windows_auth:
            conn_str = (
                f"DRIVER={{{driver}}};"
                f"SERVER={server};"
                f"Trusted_Connection=yes;"
                f"TrustServerCertificate=yes;"
            )
        else:
            conn_str = (
                f"DRIVER={{{driver}}};"
                f"SERVER={server};"
                f"UID={user};"
                f"PWD={password};"
                f"TrustServerCertificate=yes;"
            )
        
        with pyodbc.connect(conn_str, timeout=10) as conn:
            cursor = conn.execute("""
                SELECT name 
                FROM sys.databases 
                WHERE state = 0 
                  AND name NOT IN ('master', 'tempdb', 'model', 'msdb')
                ORDER BY name
            """)
            databases = [row[0] for row in cursor.fetchall()]
            
        logger.info(f"Listed {len(databases)} databases on {server}")
        
    except ImportError:
        error = "Moduł pyodbc nie jest zainstalowany"
        logger.error(error)
    except Exception as e:
        error = str(e)
        logger.error(f"Error listing databases: {e}")
    
    return databases, error


def test_connection(
    server: str, 
    database: str, 
    user: str, 
    password: str,
    use_windows_auth: bool = False
) -> Tuple[bool, str]:
    """
    Tests connection to a specific SQL Server database.
    
    Args:
        server: Server instance name
        database: Database name
        user: SQL Server username
        password: SQL Server password
        use_windows_auth: If True, use Windows Authentication
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        import pyodbc
        
        driver = get_preferred_driver()
        
        if use_windows_auth:
            conn_str = (
                f"DRIVER={{{driver}}};"
                f"SERVER={server};"
                f"DATABASE={database};"
                f"Trusted_Connection=yes;"
                f"TrustServerCertificate=yes;"
            )
        else:
            conn_str = (
                f"DRIVER={{{driver}}};"
                f"SERVER={server};"
                f"DATABASE={database};"
                f"UID={user};"
                f"PWD={password};"
                f"TrustServerCertificate=yes;"
            )
        
        with pyodbc.connect(conn_str, timeout=10) as conn:
            cursor = conn.execute("SELECT 1")
            result = cursor.fetchone()
            
            if result and result[0] == 1:
                logger.info(f"Connection test successful: {server}/{database}")
                return True, "✅ Połączenie udane!"
            else:
                return False, "❌ Nieoczekiwana odpowiedź serwera"
                
    except ImportError:
        return False, "❌ Moduł pyodbc nie jest zainstalowany"
    except Exception as e:
        error_msg = str(e)
        # Make error message more user-friendly
        if "Login failed" in error_msg:
            return False, "❌ Błędny login lub hasło"
        elif "Cannot open database" in error_msg:
            return False, f"❌ Nie można otworzyć bazy danych '{database}'"
        elif "server was not found" in error_msg or "Named Pipes Provider" in error_msg:
            return False, f"❌ Nie można połączyć się z serwerem '{server}'"
        elif "timeout" in error_msg.lower():
            return False, "❌ Przekroczono limit czasu połączenia"
        else:
            return False, f"❌ Błąd: {error_msg[:100]}"


def build_connection_string(
    server: str,
    database: str,
    user: str,
    password: str,
    use_windows_auth: bool = False
) -> str:
    """
    Builds a SQLAlchemy-compatible connection string for MS SQL Server.
    
    Args:
        server: Server instance name
        database: Database name
        user: SQL Server username
        password: SQL Server password
        use_windows_auth: If True, use Windows Authentication
        
    Returns:
        SQLAlchemy connection string
    """
    driver = get_preferred_driver()
    driver_encoded = driver.replace(' ', '+')
    
    if use_windows_auth:
        conn_str = (
            f"mssql+pyodbc://@{server}/{database}"
            f"?driver={driver_encoded}&TrustServerCertificate=yes&Trusted_Connection=yes"
        )
    else:
        # URL-encode password to handle special characters
        password_encoded = urllib.parse.quote_plus(password)
        conn_str = (
            f"mssql+pyodbc://{user}:{password_encoded}@{server}/{database}"
            f"?driver={driver_encoded}&TrustServerCertificate=yes"
        )
    
    return conn_str


def save_connection_to_env(
    server: str,
    database: str,
    user: str,
    password: str,
    use_windows_auth: bool = False,
    env_path: str = None
) -> Tuple[bool, str]:
    """
    Saves database connection configuration to .env file.
    
    Args:
        server: Server instance name
        database: Database name
        user: SQL Server username
        password: SQL Server password
        use_windows_auth: If True, use Windows Authentication
        env_path: Path to .env file (defaults to project root)
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        # Determine .env path
        if env_path is None:
            # Find project root (where main.py is)
            current_dir = Path(__file__).parent.parent  # src -> project root
            env_path = current_dir / ".env"
        else:
            env_path = Path(env_path)
        
        # Build connection string
        conn_str = build_connection_string(server, database, user, password, use_windows_auth)
        
        # Read existing .env content
        existing_content = ""
        if env_path.exists():
            with open(env_path, 'r', encoding='utf-8') as f:
                existing_content = f.read()
        
        # Update or add DB_CONN_STR
        lines = existing_content.split('\n')
        new_lines = []
        found = False
        
        for line in lines:
            if line.startswith('DB_CONN_STR='):
                new_lines.append(f'DB_CONN_STR={conn_str}')
                found = True
            else:
                new_lines.append(line)
        
        if not found:
            # Add at beginning after comments
            insert_pos = 0
            for i, line in enumerate(new_lines):
                if not line.startswith('#') and line.strip():
                    insert_pos = i
                    break
            new_lines.insert(insert_pos, f'DB_CONN_STR={conn_str}')
        
        # Write back
        with open(env_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(new_lines))
        
        # FIX: Update current process environment immediately so is_configured() sees the change
        os.environ['DB_CONN_STR'] = conn_str
        
        logger.info(f"Saved connection configuration to {env_path}")
        return True, f"✅ Konfiguracja zapisana do {env_path.name}"
        
    except Exception as e:
        error_msg = f"❌ Błąd zapisu: {e}"
        logger.error(error_msg)
        return False, error_msg


def is_configured() -> bool:
    """
    Checks if database connection is properly configured.
    
    Returns:
        True if DB_CONN_STR is set and doesn't contain placeholder values
    """
    from dotenv import load_dotenv
    load_dotenv()
    
    conn_str = os.getenv('DB_CONN_STR', '')
    
    if not conn_str:
        return False
    
    # Check for placeholder values
    placeholders = [
        'YOUR_PASSWORD_HERE',
        'YOUR_SERVER',
        'YOUR_',
        'PLACEHOLDER'
    ]
    
    for placeholder in placeholders:
        if placeholder in conn_str:
            return False
    
    return True


def get_current_config() -> dict:
    """
    Parses and returns current database configuration from .env.
    
    Returns:
        Dict with keys: server, database, user, configured
    """
    from dotenv import load_dotenv
    load_dotenv()
    
    conn_str = os.getenv('DB_CONN_STR', '')
    
    result = {
        'server': '',
        'database': '',
        'user': '',
        'configured': False
    }
    
    if not conn_str:
        return result
    
    try:
        # Parse connection string: mssql+pyodbc://user:pass@server/database?...
        import re
        
        # Extract user
        user_match = re.search(r'://([^:@]+):', conn_str)
        if user_match:
            result['user'] = user_match.group(1)
        
        # Extract server
        server_match = re.search(r'@([^/]+)/', conn_str)
        if server_match:
            result['server'] = server_match.group(1)
        
        # Extract database
        db_match = re.search(r'/([^?]+)\?', conn_str)
        if db_match:
            result['database'] = db_match.group(1)
        
        result['configured'] = is_configured()
        
    except Exception as e:
        logger.error(f"Error parsing connection string: {e}")
    
    return result
