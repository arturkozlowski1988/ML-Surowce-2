# 🗺️ Mapa Drogowa Optymalizacji: AI Supply Assistant

> **Wersja dokumentu**: 1.0  
> **Data utworzenia**: 2025-12-27  
> **Autor**: Lead Software Architect & Security Specialist  
> **Status**: Projekt do wdrożenia

---

## Spis Treści

1. [Podsumowanie Wykonawcze](#1-podsumowanie-wykonawcze)
2. [Audyt Bezpieczeństwa (SecOps)](#2-audyt-bezpieczeństwa-secops)
3. [Optymalizacja SQL i Ładowania Danych](#3-optymalizacja-sql-i-ładowania-danych)
4. [Architektura LLM - Przenośność](#4-architektura-llm---przenośność)
5. [Optymalizacja UX/GUI](#5-optymalizacja-uxgui)
6. [Priorytety Wdrożenia](#6-priorytety-wdrożenia)
7. [Rekomendowane Indeksy Bazy Danych](#7-rekomendowane-indeksy-bazy-danych)
8. [Metryki Sukcesu](#8-metryki-sukcesu)

---

## 1. Podsumowanie Wykonawcze

### Stan Obecny

Aplikacja **AI Supply Assistant** integruje bazę danych MS SQL z modelami LLM (Ollama/Gemini) dla wsparcia działów zakupów i produkcji. Projekt wymaga optymalizacji w następujących obszarach:

| Obszar | Ryzyko | Status |
|--------|--------|--------|
| Security | 🔴 Wysokie | Wymagana natychmiastowa akcja |
| Performance | 🟡 Średnie | Optymalizacja zalecana |
| Deployment | 🟡 Średnie | Zależność od Ollama |
| UX | 🟢 Niskie | Poprawa ergonomii |

### Zidentyfikowane Mocne Strony

- ✅ Parametryzowane zapytania SQL (ochrona przed SQL Injection)
- ✅ Moduł anonimizacji danych przed wysyłką do chmury
- ✅ Mechanizm cache w DatabaseConnector
- ✅ Diagnostyka wydajności zapytań
- ✅ Retry logic w kliencie Gemini

---

## 2. Audyt Bezpieczeństwa (SecOps)

### 2.1 Analiza Obecnego Stanu

#### Zidentyfikowane Problemy

**⚠️ PROBLEM #1: Hardcoded Credentials w GUI**

Plik `main.py` (linie 31-34) zawiera domyślne wartości połączenia:

```python
manual_server = st.text_input("Server", value="DESKTOP-JHQ03JE\SQL")
manual_db = st.text_input("Database", value="cdn_test")
manual_user = st.text_input("User", value="sa")
```

**Ryzyko**: Ujawnienie nazwy serwera i loginu domyślnego (sa = administrator SQL).

**⚠️ PROBLEM #2: Connection String w Środowisku**

Connection string w `.env` zawiera hasło w czystej postaci:

```env
DB_CONN_STR=mssql+pyodbc://sa:PASSWORD@SERVER/DATABASE?driver=...
```

**⚠️ PROBLEM #3: API Keys bez Rotacji**

Klucz `GEMINI_API_KEY` przechowywany w `.env` bez mechanizmu rotacji lub walidacji ważności.

### 2.2 Zalecenia - Must Have

#### 2.2.1 Menedżer Sekretów

**Rekomendacja**: Zaimplementuj warstwę abstrakcji dla sekretów z obsługą wielu backendów.

```python
# src/security/secrets_manager.py
import os
import logging
from abc import ABC, abstractmethod
from typing import Optional
from dotenv import load_dotenv

logger = logging.getLogger('SecretsManager')


class SecretsBackend(ABC):
    """Abstrakcyjna klasa bazowa dla backendów sekretów."""
    
    @abstractmethod
    def get_secret(self, key: str) -> Optional[str]:
        """Pobiera sekret po kluczu."""
        pass


class EnvFileBackend(SecretsBackend):
    """Backend dla plików .env (development)."""
    
    def __init__(self, env_path: str = ".env"):
        load_dotenv(env_path)
        
    def get_secret(self, key: str) -> Optional[str]:
        return os.getenv(key)


class AzureKeyVaultBackend(SecretsBackend):
    """Backend dla Azure Key Vault (production)."""
    
    def __init__(self, vault_url: str):
        try:
            from azure.identity import DefaultAzureCredential
            from azure.keyvault.secrets import SecretClient
            
            credential = DefaultAzureCredential()
            self.client = SecretClient(vault_url=vault_url, credential=credential)
            logger.info(f"Connected to Azure Key Vault: {vault_url}")
        except ImportError:
            logger.error("Azure SDK not installed. Run: pip install azure-keyvault-secrets azure-identity")
            raise
        except Exception as e:
            logger.error(f"Failed to connect to Azure Key Vault: {e}")
            raise
            
    def get_secret(self, key: str) -> Optional[str]:
        try:
            secret = self.client.get_secret(key.replace('_', '-'))  # Azure naming convention
            return secret.value
        except Exception as e:
            logger.warning(f"Secret '{key}' not found in Azure Key Vault: {e}")
            return None


class SecretsManager:
    """
    Zarządza dostępem do sekretów z różnych źródeł.
    Priorytet: Azure Key Vault > Environment Variables > .env File
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self.backends = []
        self._cache = {}
        
        # 1. Try Azure Key Vault (production)
        vault_url = os.getenv('AZURE_KEYVAULT_URL')
        if vault_url:
            try:
                self.backends.append(AzureKeyVaultBackend(vault_url))
            except Exception:
                logger.warning("Azure Key Vault unavailable, falling back to local secrets")
        
        # 2. Environment variables + .env file (always as fallback)
        self.backends.append(EnvFileBackend())
        
        self._initialized = True
        logger.info(f"SecretsManager initialized with {len(self.backends)} backend(s)")
    
    def get_secret(self, key: str, required: bool = True) -> Optional[str]:
        """
        Pobiera sekret z pierwszego dostępnego backendu.
        
        Args:
            key: Nazwa sekretu
            required: Czy rzucić wyjątek gdy brak sekretu
            
        Returns:
            Wartość sekretu lub None
            
        Raises:
            ValueError: Gdy required=True i sekret nie istnieje
        """
        # Check cache first
        if key in self._cache:
            return self._cache[key]
        
        for backend in self.backends:
            try:
                value = backend.get_secret(key)
                if value is not None:
                    self._cache[key] = value
                    return value
            except Exception as e:
                logger.warning(f"Backend {type(backend).__name__} failed for '{key}': {e}")
                continue
        
        if required:
            raise ValueError(f"Required secret '{key}' not found in any backend")
        
        return None
    
    def clear_cache(self):
        """Czyści cache sekretów (np. przed rotacją)."""
        self._cache.clear()
        logger.info("Secrets cache cleared")


# Użycie:
# secrets = SecretsManager()
# db_conn_str = secrets.get_secret('DB_CONN_STR')
# api_key = secrets.get_secret('GEMINI_API_KEY', required=False)
```

#### 2.2.2 Szyfrowanie Danych Wrażliwych

**Rekomendacja**: Dodaj warstwę szyfrowania dla danych konfiguracyjnych.

```python
# src/security/encryption.py
import os
import base64
import logging
from typing import Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger('Encryption')


class ConfigEncryption:
    """
    Szyfrowanie symetryczne dla danych konfiguracyjnych.
    Używa algorytmu Fernet (AES-128-CBC + HMAC-SHA256).
    
    ⚠️ UWAGA: Klucz główny powinien być przechowywany w HSM/Key Vault w produkcji.
    """
    
    def __init__(self, master_key: Optional[str] = None, salt: Optional[bytes] = None):
        """
        Inicjalizuje moduł szyfrowania.
        
        Args:
            master_key: Klucz główny (z env lub Key Vault)
            salt: Sól do derywacji klucza (powinna być unikalna per instalacja)
        """
        self.master_key = master_key or os.getenv('ENCRYPTION_MASTER_KEY')
        
        if not self.master_key:
            raise ValueError(
                "ENCRYPTION_MASTER_KEY is required. "
                "Generate with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
            )
        
        # Derive actual encryption key from master key
        self.salt = salt or os.getenv('ENCRYPTION_SALT', 'AI_Supply_Assistant_v1').encode()
        self._fernet = self._derive_key()
        logger.info("ConfigEncryption initialized")
    
    def _derive_key(self) -> Fernet:
        """Derywuje klucz szyfrowania z master key używając PBKDF2."""
        try:
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=self.salt,
                iterations=480000,  # OWASP recommendation 2023
            )
            key = base64.urlsafe_b64encode(kdf.derive(self.master_key.encode()))
            return Fernet(key)
        except Exception as e:
            logger.error(f"Key derivation failed: {e}")
            raise
    
    def encrypt(self, plaintext: str) -> str:
        """
        Szyfruje tekst.
        
        Args:
            plaintext: Tekst do zaszyfrowania
            
        Returns:
            Zaszyfrowany tekst (base64)
        """
        try:
            encrypted = self._fernet.encrypt(plaintext.encode())
            return encrypted.decode()
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise
    
    def decrypt(self, ciphertext: str) -> str:
        """
        Odszyfrowuje tekst.
        
        Args:
            ciphertext: Zaszyfrowany tekst (base64)
            
        Returns:
            Odszyfrowany tekst
            
        Raises:
            InvalidToken: Gdy klucz jest nieprawidłowy lub dane zostały zmodyfikowane
        """
        try:
            decrypted = self._fernet.decrypt(ciphertext.encode())
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise
    
    def encrypt_connection_string(self, conn_str: str) -> dict:
        """
        Szyfruje connection string i zwraca komponenty.
        
        Returns:
            dict z zaszyfrowanym connection string i metadanymi
        """
        return {
            'encrypted': self.encrypt(conn_str),
            'algorithm': 'Fernet',
            'kdf': 'PBKDF2-SHA256',
            'iterations': 480000
        }


# Przykład użycia:
# 
# # Szyfrowanie (jednorazowo podczas konfiguracji):
# crypto = ConfigEncryption(master_key="your-master-key-from-vault")
# encrypted = crypto.encrypt("mssql+pyodbc://sa:secret@server/db")
# print(f"ENCRYPTED_DB_CONN_STR={encrypted}")
#
# # Odszyfrowywanie (w runtime):
# conn_str = crypto.decrypt(os.getenv('ENCRYPTED_DB_CONN_STR'))
```

#### 2.2.3 Bezpieczna Konfiguracja GUI

**Rekomendacja**: Usuń domyślne wartości z formularza połączenia.

```python
# Obecny kod (main.py):
manual_server = st.text_input("Server", value="DESKTOP-JHQ03JE\SQL")  # ❌ Hardcoded

# Zalecana zmiana:
manual_server = st.text_input(
    "Server", 
    value=os.getenv('DB_SERVER_DEFAULT', ''),  # ✅ Z env lub pusty
    placeholder="np. SERWER\\INSTANCJA"
)
manual_db = st.text_input(
    "Database", 
    value=os.getenv('DB_NAME_DEFAULT', ''),
    placeholder="np. cdn_test"
)
manual_user = st.text_input(
    "User", 
    value="",  # ✅ Zawsze pusty
    placeholder="Login SQL"
)
```

### 2.3 Zalecenia - Nice to Have

#### 2.3.1 Audit Log

```python
# src/security/audit.py
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any

logger = logging.getLogger('SecurityAudit')


class SecurityAuditLog:
    """Logowanie zdarzeń bezpieczeństwa."""
    
    def __init__(self, log_path: str = "security_audit.log"):
        self.audit_logger = logging.getLogger('AuditTrail')
        handler = logging.FileHandler(log_path)
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        ))
        self.audit_logger.addHandler(handler)
        self.audit_logger.setLevel(logging.INFO)
    
    def log_event(
        self, 
        event_type: str, 
        user: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        severity: str = "INFO"
    ):
        """
        Loguje zdarzenie bezpieczeństwa.
        
        Args:
            event_type: Typ zdarzenia (np. 'LOGIN', 'DATA_ACCESS', 'CONFIG_CHANGE')
            user: Identyfikator użytkownika
            details: Dodatkowe szczegóły
            severity: Poziom ważności
        """
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "user": user or "SYSTEM",
            "severity": severity,
            "details": details or {}
        }
        
        log_method = getattr(self.audit_logger, severity.lower(), self.audit_logger.info)
        log_method(json.dumps(event))


# Użycie w db_connector.py:
# audit = SecurityAuditLog()
# audit.log_event("DB_CONNECTION", user=manual_user, details={"server": manual_server})
```

---

## 3. Optymalizacja SQL i Ładowania Danych

### 3.1 Analiza Obecnego Stanu

#### Zidentyfikowane Wzorce

| Zapytanie | Czas (typowy) | Problem |
|-----------|---------------|---------|
| `get_historical_data()` | ~1-3s | JOIN 3 tabel, brak indeksów dedykowanych |
| `get_current_stock()` | ~2-5s | Subquery w WHERE |
| `get_bom_with_stock()` | ~0.5-1s | OK, z cache |

#### Użycie NOLOCK

⚠️ **OSTRZEŻENIE o NOLOCK**: Obecna implementacja używa `WITH (NOLOCK)` we wszystkich zapytaniach raportowych.

**Ryzyka**:
- **Dirty Reads**: Możliwość odczytania niezacommitowanych danych
- **Non-repeatable Reads**: Dane mogą się zmienić między odczytami
- **Phantom Reads**: Nowe wiersze mogą pojawić się podczas skanowania

**Kiedy NOLOCK jest akceptowalny**:
- ✅ Raporty analityczne (dashboard, trendy)
- ✅ Dane historyczne (rzadko modyfikowane)
- ✅ Agregacje na dużych zbiorach danych

**Kiedy NIE używać NOLOCK**:
- ❌ Kalkulacje finansowe
- ❌ Sprawdzanie stanów magazynowych przed zamówieniem
- ❌ Decyzje biznesowe wymagające dokładności 100%

### 3.2 Zalecenia - Must Have

#### 3.2.1 Asynchroniczne Ładowanie Danych

**Problem**: Zapytania SQL blokują główny wątek GUI Streamlit.

**Rozwiązanie**: Implementacja asynchronicznego ładowania z `concurrent.futures`.

```python
# src/async_data_loader.py
import concurrent.futures
import threading
import logging
from typing import Callable, Any, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger('AsyncDataLoader')


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class TaskResult:
    """Wynik asynchronicznego zadania."""
    status: TaskStatus
    data: Any = None
    error: Optional[str] = None
    progress: float = 0.0


class AsyncDataLoader:
    """
    Asynchroniczny loader danych dla Streamlit GUI.
    Wykonuje zapytania SQL w tle, nie blokując interfejsu.
    
    ⚠️ UWAGA: Streamlit wymaga specjalnej obsługi stanu między reruns.
    """
    
    def __init__(self, max_workers: int = 3):
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        self._tasks = {}
        self._lock = threading.Lock()
        logger.info(f"AsyncDataLoader initialized with {max_workers} workers")
    
    def submit_task(
        self, 
        task_id: str, 
        func: Callable, 
        *args, 
        **kwargs
    ) -> str:
        """
        Dodaje zadanie do wykonania w tle.
        
        Args:
            task_id: Unikalny identyfikator zadania
            func: Funkcja do wykonania
            *args, **kwargs: Argumenty funkcji
            
        Returns:
            task_id
        """
        with self._lock:
            if task_id in self._tasks:
                # Task already exists
                return task_id
            
            future = self.executor.submit(self._execute_task, task_id, func, *args, **kwargs)
            self._tasks[task_id] = {
                'future': future,
                'result': TaskResult(status=TaskStatus.PENDING)
            }
            
        logger.debug(f"Task '{task_id}' submitted")
        return task_id
    
    def _execute_task(self, task_id: str, func: Callable, *args, **kwargs) -> Any:
        """Wykonuje zadanie i aktualizuje status."""
        try:
            with self._lock:
                self._tasks[task_id]['result'].status = TaskStatus.RUNNING
            
            result = func(*args, **kwargs)
            
            with self._lock:
                self._tasks[task_id]['result'] = TaskResult(
                    status=TaskStatus.COMPLETED,
                    data=result,
                    progress=1.0
                )
            
            logger.debug(f"Task '{task_id}' completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Task '{task_id}' failed: {e}")
            with self._lock:
                self._tasks[task_id]['result'] = TaskResult(
                    status=TaskStatus.FAILED,
                    error=str(e)
                )
            raise
    
    def get_result(self, task_id: str, timeout: float = None) -> TaskResult:
        """
        Pobiera wynik zadania.
        
        Args:
            task_id: Identyfikator zadania
            timeout: Maksymalny czas oczekiwania (None = nie czekaj)
            
        Returns:
            TaskResult z aktualnym statusem
        """
        with self._lock:
            if task_id not in self._tasks:
                return TaskResult(status=TaskStatus.PENDING, error="Task not found")
            
            task = self._tasks[task_id]
        
        if timeout is not None:
            try:
                task['future'].result(timeout=timeout)
            except concurrent.futures.TimeoutError:
                pass
            except Exception:
                pass
        
        with self._lock:
            return self._tasks[task_id]['result']
    
    def is_complete(self, task_id: str) -> bool:
        """Sprawdza czy zadanie jest zakończone."""
        result = self.get_result(task_id)
        return result.status in (TaskStatus.COMPLETED, TaskStatus.FAILED)
    
    def clear_task(self, task_id: str):
        """Usuwa zakończone zadanie z pamięci."""
        with self._lock:
            self._tasks.pop(task_id, None)
    
    def shutdown(self, wait: bool = True):
        """Zamyka executor."""
        self.executor.shutdown(wait=wait)
        logger.info("AsyncDataLoader shutdown complete")


# Integracja ze Streamlit (main.py):
#
# import streamlit as st
# from src.async_data_loader import AsyncDataLoader, TaskStatus
#
# @st.cache_resource
# def get_data_loader():
#     return AsyncDataLoader()
#
# loader = get_data_loader()
# task_id = f"historical_data_{st.session_state.get('session_id', 'default')}"
#
# # Submit task if not running
# if not loader.is_complete(task_id):
#     loader.submit_task(task_id, db.get_historical_data)
#
# result = loader.get_result(task_id)
#
# if result.status == TaskStatus.RUNNING:
#     st.spinner("Ładowanie danych...")
#     st.rerun()  # Poll for completion
# elif result.status == TaskStatus.COMPLETED:
#     df_hist = result.data
#     # Process data...
# elif result.status == TaskStatus.FAILED:
#     st.error(f"Błąd: {result.error}")
```

#### 3.2.2 Optymalizacja Zapytań SQL

**Rekomendacja**: Zoptymalizowane wersje głównych zapytań.

```sql
-- get_historical_data() - Wersja zoptymalizowana
-- ⚠️ WITH (NOLOCK) używany tylko dla raportów analitycznych
-- Ryzyko: Dirty reads - dane mogą być niespójne

SELECT 
    DATEPART(ISO_WEEK, n.CZN_DataRealizacji) as Week,
    YEAR(n.CZN_DataRealizacji) as Year,
    e.CZE_TwrId as TowarId,
    SUM(e.CZE_Ilosc) as Quantity
FROM dbo.CtiZlecenieElem e WITH (NOLOCK)
INNER JOIN dbo.CtiZlecenieNag n WITH (NOLOCK) 
    ON e.CZE_CZNId = n.CZN_ID
-- USUNIĘTO: JOIN CDN.Towary (używany tylko do filtrowania)
WHERE n.CZN_DataRealizacji IS NOT NULL 
  AND e.CZE_Typ IN (1, 2)
  AND e.CZE_TwrId IN (
      SELECT Twr_TwrId FROM CDN.Towary WITH (NOLOCK) WHERE Twr_Typ != 2
  )
  -- OPCJONALNIE: Filtr dat dla ograniczenia zakresu
  -- AND n.CZN_DataRealizacji >= DATEADD(YEAR, -2, GETDATE())
GROUP BY 
    YEAR(n.CZN_DataRealizacji), 
    DATEPART(ISO_WEEK, n.CZN_DataRealizacji), 
    e.CZE_TwrId
ORDER BY Year, Week

-- Zalecane indeksy (patrz sekcja 7):
-- CREATE INDEX IX_CtiZlecenieElem_TwrId_Typ ON dbo.CtiZlecenieElem(CZE_TwrId, CZE_Typ)
-- CREATE INDEX IX_CtiZlecenieNag_DataRealizacji ON dbo.CtiZlecenieNag(CZN_DataRealizacji)
```

#### 3.2.3 Bezpieczne Transakcje dla Modyfikacji

⚠️ **KRYTYCZNE**: Wszelkie modyfikacje bazy danych muszą używać transakcji.

```python
# src/db_connector.py - Dodać metodę

def execute_modification(
    self, 
    query: str, 
    params: dict = None, 
    auto_commit: bool = False
) -> tuple:
    """
    Wykonuje zapytanie modyfikujące dane z pełną kontrolą transakcji.
    
    ⚠️ KRYTYCZNE: Domyślnie wykonuje ROLLBACK (tryb testowy).
    Ustaw auto_commit=True tylko w produkcji po pełnej weryfikacji.
    
    Args:
        query: Zapytanie SQL (INSERT/UPDATE/DELETE)
        params: Parametry zapytania
        auto_commit: Czy zacommitować zmiany (domyślnie False = ROLLBACK)
        
    Returns:
        tuple: (affected_rows, success)
        
    Example:
        # BEGIN TRAN ... ROLLBACK pattern (safety guardrail):
        
        query = '''
        BEGIN TRANSACTION;
        
        UPDATE <NAZWA_TABELI>
        SET <KOLUMNA> = :nowa_wartosc
        WHERE <WARUNEK>;
        
        -- Weryfikacja przed commit/rollback
        SELECT @@ROWCOUNT as AffectedRows;
        '''
        
        affected, success = db.execute_modification(query, params, auto_commit=False)
        
        if affected > 0 and success:
            # Dane wyglądają poprawnie - można zacommitować ręcznie
            pass
    """
    try:
        with self.engine.begin() as connection:
            # Rozpocznij transakcję (BEGIN TRAN jest implicit w begin())
            logger.info("Transaction started")
            
            result = connection.execute(text(query), params or {})
            affected_rows = result.rowcount
            
            if auto_commit:
                # COMMIT - zmiany zostaną zapisane
                logger.info(f"Transaction COMMIT: {affected_rows} rows affected")
                return (affected_rows, True)
            else:
                # ROLLBACK - zmiany zostaną cofnięte (tryb testowy)
                connection.rollback()
                logger.warning(f"Transaction ROLLBACK (test mode): {affected_rows} rows would be affected")
                return (affected_rows, False)
                
    except Exception as e:
        logger.error(f"Transaction failed: {e}")
        # Transakcja zostanie automatycznie wycofana przy wyjątku
        return (0, False)
```

### 3.3 Zalecenia - Nice to Have

#### 3.3.1 Connection Pooling Optimization

```python
# db_connector.py - Ulepszony engine

def _create_db_engine(self):
    """Creates SQLAlchemy engine with optimized connection pool."""
    try:
        engine = create_engine(
            self.conn_str,
            pool_pre_ping=True,          # Weryfikacja połączeń przed użyciem
            pool_size=5,                  # Bazowy rozmiar puli
            max_overflow=10,              # Dodatkowe połączenia w szczycie
            pool_recycle=3600,            # Recykling co godzinę
            pool_timeout=30,              # Timeout na pobranie połączenia
            echo=False,                   # Wyłącz logi SQL (włącz do debugowania)
            connect_args={
                "timeout": 30,            # Connection timeout
                "autocommit": False       # Explicit transaction control
            }
        )
        return engine
    except Exception as e:
        logger.error(f"Error creating engine: {e}")
        raise
```

---

## 4. Architektura LLM - Przenośność

### 4.1 Analiza Obecnego Stanu

**Obecna architektura**:
- Ollama API (HTTP) - wymaga zewnętrznej usługi
- Google Gemini API - wymaga internetu i klucza API

**Problem**: Zależność od `ollama serve` utrudnia deployment i offline usage.

### 4.2 Plan Migracji na llama-cpp-python

**Cel**: Uruchamianie modeli GGUF bezpośrednio w procesie Pythona.

#### 4.2.1 Nowy Klient LLM (Embedded)

```python
# src/ai_engine/llama_cpp_client.py
import os
import logging
from typing import Optional, List, Dict
from pathlib import Path

logger = logging.getLogger('LlamaCppClient')


class LlamaCppClient:
    """
    Klient dla modeli GGUF uruchamianych lokalnie przez llama-cpp-python.
    Eliminuje zależność od zewnętrznego serwera Ollama.
    
    ⚠️ UWAGA: Domyślnie używa CPU (OpenBLAS). GPU wymaga dodatkowej konfiguracji.
    """
    
    # Rekomendowane "lekkie" modele dla środowisk o niskich zasobach
    RECOMMENDED_MODELS = {
        'phi-3-mini': {
            'name': 'Phi-3 Mini',
            'file': 'Phi-3-mini-4k-instruct-q4.gguf',
            'url': 'https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf',
            'context_length': 4096,
            'ram_required': '4GB',
            'quality': 'Good for simple tasks'
        },
        'qwen2-1.5b': {
            'name': 'Qwen2 1.5B',
            'file': 'qwen2-1_5b-instruct-q4_k_m.gguf',
            'url': 'https://huggingface.co/Qwen/Qwen2-1.5B-Instruct-GGUF',
            'context_length': 8192,
            'ram_required': '3GB',
            'quality': 'Best for low-resource environments'
        },
        'llama3-8b': {
            'name': 'Llama 3.2 8B',
            'file': 'Meta-Llama-3.2-8B-Instruct-Q4_K_M.gguf',
            'url': 'https://huggingface.co/bartowski/Meta-Llama-3.2-8B-Instruct-GGUF',
            'context_length': 8192,
            'ram_required': '8GB',
            'quality': 'Best quality, higher resources'
        }
    }
    
    def __init__(
        self, 
        model_path: Optional[str] = None,
        n_ctx: int = 4096,
        n_threads: Optional[int] = None,
        n_gpu_layers: int = 0,  # 0 = CPU only (fallback)
        verbose: bool = False
    ):
        """
        Inicjalizuje klienta LLM.
        
        Args:
            model_path: Ścieżka do pliku .gguf
            n_ctx: Długość kontekstu (tokens)
            n_threads: Liczba wątków CPU (None = auto)
            n_gpu_layers: Warstwy na GPU (0 = tylko CPU - bezpieczny fallback)
            verbose: Czy pokazywać logi llama.cpp
            
        ⚠️ Environment Fallback:
            Jeśli GPU NVIDIA nie jest dostępne, automatycznie używa CPU (OpenBLAS).
        """
        try:
            from llama_cpp import Llama
        except ImportError:
            raise ImportError(
                "llama-cpp-python not installed. Run:\n"
                "  pip install llama-cpp-python\n"
                "Or for GPU support:\n"
                "  CMAKE_ARGS='-DLLAMA_CUBLAS=on' pip install llama-cpp-python"
            )
        
        self.model_path = model_path or os.getenv('LLAMA_MODEL_PATH')
        
        if not self.model_path:
            raise ValueError(
                "Model path required. Set LLAMA_MODEL_PATH env var or pass model_path. "
                f"Recommended models: {list(self.RECOMMENDED_MODELS.keys())}"
            )
        
        if not Path(self.model_path).exists():
            raise FileNotFoundError(
                f"Model file not found: {self.model_path}\n"
                f"Download from HuggingFace or use recommended models."
            )
        
        # Detect GPU availability
        try:
            actual_gpu_layers = n_gpu_layers
            if n_gpu_layers > 0:
                # Test GPU availability
                import torch
                if not torch.cuda.is_available():
                    logger.warning("CUDA not available, falling back to CPU (OpenBLAS)")
                    actual_gpu_layers = 0
        except ImportError:
            logger.info("PyTorch not installed, using CPU inference")
            actual_gpu_layers = 0
        except Exception as e:
            logger.warning(f"GPU detection failed: {e}, using CPU")
            actual_gpu_layers = 0
        
        logger.info(f"Loading model: {self.model_path}")
        logger.info(f"GPU layers: {actual_gpu_layers}, Context: {n_ctx}, Threads: {n_threads or 'auto'}")
        
        try:
            self.llm = Llama(
                model_path=self.model_path,
                n_ctx=n_ctx,
                n_threads=n_threads,
                n_gpu_layers=actual_gpu_layers,
                verbose=verbose
            )
            logger.info("Model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise
    
    def generate_explanation(
        self, 
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.9,
        stop: Optional[List[str]] = None
    ) -> str:
        """
        Generuje odpowiedź na prompt.
        
        Args:
            prompt: Tekst wejściowy
            max_tokens: Maksymalna długość odpowiedzi
            temperature: Kreatywność (0.0-1.0)
            top_p: Nucleus sampling
            stop: Sekwencje kończące generację
            
        Returns:
            Wygenerowany tekst
        """
        try:
            # Format as chat for instruction-tuned models
            formatted_prompt = self._format_chat_prompt(prompt)
            
            output = self.llm(
                formatted_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                stop=stop or ["<|endoftext|>", "###", "\n\n\n"],
                echo=False
            )
            
            response = output['choices'][0]['text'].strip()
            logger.debug(f"Generated {len(response)} characters")
            return response
            
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            return f"Error during generation: {e}"
    
    def _format_chat_prompt(self, user_message: str) -> str:
        """Formatuje prompt dla modeli instruction-tuned."""
        # Phi-3 / Llama 3 format
        return f"""<|user|>
{user_message}
<|assistant|>
"""
    
    def get_model_info(self) -> Dict:
        """Zwraca informacje o załadowanym modelu."""
        return {
            'model_path': self.model_path,
            'context_length': self.llm.n_ctx(),
            'vocab_size': self.llm.n_vocab(),
        }
    
    @classmethod
    def list_recommended_models(cls) -> Dict:
        """Zwraca listę rekomendowanych modeli."""
        return cls.RECOMMENDED_MODELS


# Użycie w main.py:
#
# if ai_source == "Local (Embedded)":
#     from src.ai_engine.llama_cpp_client import LlamaCppClient
#     client = LlamaCppClient(
#         model_path="models/phi-3-mini-4k-instruct-q4.gguf",
#         n_ctx=4096,
#         n_gpu_layers=0  # CPU fallback
#     )
#     response_text = client.generate_explanation(prompt)
```

#### 4.2.2 Aktualizacja Requirements

```txt
# requirements.txt - Dodać:

# Embedded LLM (opcjonalnie - dla offline mode)
llama-cpp-python>=0.2.50  # CPU: pip install llama-cpp-python
                          # GPU: CMAKE_ARGS="-DLLAMA_CUBLAS=on" pip install llama-cpp-python
```

#### 4.2.3 Integracja z GUI

```python
# Fragment main.py - Rozszerzony wybór silnika AI

with col_ai_1:
    ai_source = st.radio(
        "Wybierz Silnik AI:", 
        [
            "Local Embedded (CPU)",      # Nowy - bez zależności
            "Ollama (Local Server)", 
            "Google Gemini (Cloud)"
        ]
    )
    
    if ai_source == "Local Embedded (CPU)":
        # Show available models
        from src.ai_engine.llama_cpp_client import LlamaCppClient
        models = LlamaCppClient.list_recommended_models()
        
        st.caption("Modele uruchamiane bezpośrednio w Pythonie (offline)")
        model_choice = st.selectbox(
            "Model:",
            list(models.keys()),
            format_func=lambda x: f"{models[x]['name']} ({models[x]['ram_required']} RAM)"
        )
        st.info(f"💡 {models[model_choice]['quality']}")
    
    elif "Ollama" in ai_source:
        ollama_model = st.selectbox(
            "Model Ollama:", 
            ["llama3.2", "phi3", "mistral"]
        )
```

### 4.3 Porównanie Rozwiązań LLM

| Aspekt | Ollama API | llama-cpp-python | Gemini Cloud |
|--------|------------|------------------|--------------|
| **Offline** | ❌ Wymaga serwera | ✅ Pełne offline | ❌ Wymaga internetu |
| **Setup** | Łatwy | Średni | Łatwy |
| **Performance** | Dobra | Dobra (CPU/GPU) | Najlepsza |
| **Privacy** | ✅ Lokalne | ✅ Lokalne | ⚠️ Dane w chmurze |
| **RAM (8B model)** | ~8GB | ~8GB | N/A |
| **GPU Support** | ✅ | ✅ (opcjonalne) | N/A |
| **Deployment** | Wymaga Docker/binary | Tylko pip | Tylko API key |

---

## 5. Optymalizacja UX/GUI

### 5.1 Analiza Obecnego Stanu

**Zidentyfikowane problemy**:
1. Brak separacji logiki od prezentacji (wszystko w `main.py`)
2. Brak wskaźników postępu dla długich operacji
3. Responsywność - UI zamraża podczas zapytań SQL

### 5.2 Zalecenia - Must Have

#### 5.2.1 Wzorzec MVC/MVVM

**Rekomendacja**: Separacja warstw aplikacji.

```
src/
├── models/           # Warstwa danych (M)
│   ├── __init__.py
│   ├── stock_model.py
│   └── forecast_model.py
├── viewmodels/       # Logika biznesowa (VM)
│   ├── __init__.py
│   ├── analysis_viewmodel.py
│   └── prediction_viewmodel.py
├── views/            # Warstwa prezentacji (V) - Streamlit components
│   ├── __init__.py
│   ├── analysis_view.py
│   └── prediction_view.py
└── main.py           # Entry point - routing only
```

```python
# src/viewmodels/analysis_viewmodel.py
from dataclasses import dataclass
from typing import Optional, List
import pandas as pd
from src.db_connector import DatabaseConnector
from src.preprocessing import prepare_time_series, fill_missing_weeks


@dataclass
class AnalysisState:
    """Stan widoku analizy."""
    df_stock: Optional[pd.DataFrame] = None
    df_historical: Optional[pd.DataFrame] = None
    selected_products: List[int] = None
    is_loading: bool = False
    error_message: Optional[str] = None
    
    def __post_init__(self):
        if self.selected_products is None:
            self.selected_products = []


class AnalysisViewModel:
    """
    ViewModel dla modułu Analiza Danych.
    Oddziela logikę biznesową od widoku Streamlit.
    """
    
    def __init__(self, db: DatabaseConnector):
        self.db = db
        self.state = AnalysisState()
    
    def load_data(self) -> AnalysisState:
        """Ładuje wszystkie potrzebne dane."""
        self.state.is_loading = True
        
        try:
            # Stock data
            self.state.df_stock = self.db.get_current_stock()
            
            # Historical data
            df_hist = self.db.get_historical_data()
            if not df_hist.empty:
                df_clean = prepare_time_series(df_hist)
                self.state.df_historical = fill_missing_weeks(df_clean)
            
            self.state.error_message = None
            
        except Exception as e:
            self.state.error_message = str(e)
        
        finally:
            self.state.is_loading = False
        
        return self.state
    
    def get_product_map(self) -> dict:
        """Zwraca mapę ID -> Nazwa produktu."""
        if self.state.df_stock is None or self.state.df_stock.empty:
            return {}
        
        df = self.state.df_stock
        df['DisplayName'] = df['Name'] + " (" + df['Code'] + ")"
        return dict(zip(df['TowarId'], df['DisplayName']))
    
    def filter_by_date(self, start_date, end_date) -> pd.DataFrame:
        """Filtruje dane historyczne po zakresie dat."""
        if self.state.df_historical is None:
            return pd.DataFrame()
        
        df = self.state.df_historical
        mask = (df['Date'].dt.date >= start_date) & (df['Date'].dt.date <= end_date)
        return df.loc[mask]
    
    def get_metrics(self, df_filtered: pd.DataFrame) -> dict:
        """Oblicza metryki dla widoku."""
        return {
            'total_qty': df_filtered['Quantity'].sum(),
            'total_products': df_filtered['TowarId'].nunique()
        }


# Użycie w views/analysis_view.py:
#
# def render_analysis_view(vm: AnalysisViewModel):
#     state = vm.load_data()
#     
#     if state.is_loading:
#         st.spinner("Ładowanie...")
#         return
#     
#     if state.error_message:
#         st.error(state.error_message)
#         return
#     
#     # Render UI using state...
```

#### 5.2.2 Wskaźniki Postępu

```python
# src/views/components/progress_indicators.py
import streamlit as st
from typing import Optional, Callable
import time


class ProgressIndicator:
    """Komponent wskaźnika postępu dla długich operacji."""
    
    @staticmethod
    def with_progress(
        func: Callable,
        message: str = "Przetwarzanie...",
        steps: Optional[list] = None
    ):
        """
        Dekorator/wrapper dla funkcji z długim czasem wykonania.
        
        Args:
            func: Funkcja do wykonania
            message: Komunikat dla użytkownika
            steps: Lista kroków do wyświetlenia (opcjonalnie)
            
        Example:
            result = ProgressIndicator.with_progress(
                lambda: db.get_historical_data(),
                message="Pobieranie danych historycznych...",
                steps=["Łączenie z bazą", "Pobieranie danych", "Przetwarzanie"]
            )
        """
        if steps:
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                for i, step in enumerate(steps):
                    status_text.text(f"⏳ {step}...")
                    progress_bar.progress((i + 1) / (len(steps) + 1))
                    time.sleep(0.1)  # Visual feedback
                
                result = func()
                
                progress_bar.progress(1.0)
                status_text.text("✅ Zakończono")
                time.sleep(0.3)
                
                progress_bar.empty()
                status_text.empty()
                
                return result
                
            except Exception as e:
                progress_bar.empty()
                status_text.error(f"❌ Błąd: {e}")
                raise
        else:
            with st.spinner(message):
                return func()
    
    @staticmethod
    def render_ai_thinking(message: str = "AI analizuje dane..."):
        """Animowany wskaźnik dla operacji AI."""
        return st.status(message, expanded=True)


# Użycie:
#
# with ProgressIndicator.render_ai_thinking("Generowanie analizy eksperckiej..."):
#     st.write("🔍 Analizowanie trendów zużycia...")
#     time.sleep(0.5)
#     st.write("📊 Porównywanie z historią...")
#     time.sleep(0.5)
#     st.write("💡 Formułowanie wniosków...")
#     response = client.generate_explanation(prompt)
# 
# st.markdown(response)
```

### 5.3 Zalecenia - Nice to Have

#### 5.3.1 Responsive Layout

```python
# src/views/components/responsive_layout.py
import streamlit as st


def responsive_columns(desktop_ratio: list, mobile_stack: bool = True):
    """
    Tworzy responsywne kolumny.
    
    Args:
        desktop_ratio: Proporcje kolumn na desktopie, np. [2, 1, 1]
        mobile_stack: Czy stackować na mobile (CSS)
    """
    # CSS dla mobile
    if mobile_stack:
        st.markdown("""
        <style>
        @media (max-width: 768px) {
            .stColumns > div {
                flex-direction: column !important;
            }
            .stColumns > div > div {
                width: 100% !important;
            }
        }
        </style>
        """, unsafe_allow_html=True)
    
    return st.columns(desktop_ratio)
```

---

## 6. Priorytety Wdrożenia

### 🔴 Must Have (P0) - Wdrożenie Natychmiastowe

| # | Zadanie | Estymacja | Ryzyko bez wdrożenia |
|---|---------|-----------|---------------------|
| 1 | Usunąć hardcoded credentials z main.py | 30 min | Wyciek danych |
| 2 | Wdrożyć SecretsManager | 2h | Bezpieczeństwo sekretów |
| 3 | Dodać ConfigEncryption dla conn strings | 2h | Hasła w plain text |
| 4 | Wdrożyć AsyncDataLoader dla SQL | 4h | GUI freezes |
| 5 | Dodać wskaźniki postępu | 2h | Złe UX |

### 🟡 Nice to Have (P1) - Planowane

| # | Zadanie | Estymacja | Korzyść |
|---|---------|-----------|---------|
| 6 | Migracja na llama-cpp-python | 8h | Offline deployment |
| 7 | Refaktoring do MVC/MVVM | 16h | Maintainability |
| 8 | SecurityAuditLog | 4h | Compliance |
| 9 | Connection Pool optimization | 2h | Performance |
| 10 | Responsive layout | 4h | Mobile UX |

### 🟢 Backlog (P2)

| # | Zadanie | Estymacja |
|---|---------|-----------|
| 11 | Azure Key Vault integration | 8h |
| 12 | Automated index recommendations | 4h |
| 13 | Real-time query monitoring dashboard | 8h |

---

## 7. Rekomendowane Indeksy Bazy Danych

⚠️ **UWAGA**: Poniższe polecenia należy wykonać z uprawnieniami DBA.  
⚠️ **UWAGA**: Przed utworzeniem indeksów sprawdź w `INFORMATION_SCHEMA` czy tabele istnieją.

```sql
-- Weryfikacja struktury tabel przed utworzeniem indeksów
-- Sprawdź czy kolumny istnieją:

SELECT 
    TABLE_SCHEMA,
    TABLE_NAME, 
    COLUMN_NAME
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME IN ('CtiZlecenieElem', 'CtiZlecenieNag', 'CtiTechnolNag', 'CtiTechnolElem')
  AND COLUMN_NAME IN ('CZE_TwrId', 'CZE_Typ', 'CZN_DataRealizacji', 'CTN_TwrId', 'CTE_CTNId')
ORDER BY TABLE_NAME, COLUMN_NAME;

-- Jeśli kolumny istnieją, wykonaj:

-- 1. Indeks dla filtrowania surowców
CREATE INDEX IX_CtiZlecenieElem_TwrId_Typ 
ON dbo.CtiZlecenieElem(CZE_TwrId, CZE_Typ)
WITH (ONLINE = ON);  -- Minimalizuje blokady

-- 2. Indeks dla zapytań historycznych po dacie
CREATE INDEX IX_CtiZlecenieNag_DataRealizacji 
ON dbo.CtiZlecenieNag(CZN_DataRealizacji)
WITH (ONLINE = ON);

-- 3. Indeks dla BOM lookup
CREATE INDEX IX_CtiTechnolElem_CTNId 
ON dbo.CtiTechnolElem(CTE_CTNId)
WITH (ONLINE = ON);

-- 4. Indeks dla technology lookup
CREATE INDEX IX_CtiTechnolNag_TwrId 
ON dbo.CtiTechnolNag(CTN_TwrId)
WITH (ONLINE = ON);

-- Weryfikacja utworzonych indeksów:
SELECT 
    i.name AS IndexName,
    t.name AS TableName,
    i.type_desc AS IndexType
FROM sys.indexes i
JOIN sys.tables t ON i.object_id = t.object_id
WHERE i.name LIKE 'IX_Cti%';
```

---

## 8. Metryki Sukcesu

### KPI do monitorowania po wdrożeniu

| Metryka | Baseline (obecny) | Target | Sposób pomiaru |
|---------|-------------------|--------|----------------|
| Czas ładowania danych historycznych | 1-3s | <1s | QueryDiagnostics |
| Responsywność GUI (bez freeze) | ❌ | ✅ | Manual testing |
| Hardcoded credentials | 3 | 0 | Code scan |
| Offline deployment possible | ❌ | ✅ | Integration test |
| Security audit events logged | 0% | 100% | Log analysis |

### Weryfikacja Wdrożenia

```python
# scripts/verify_optimization.py
"""
Skrypt weryfikacyjny dla wdrożonych optymalizacji.
Uruchom po każdej fazie wdrożenia.
"""

def verify_security():
    """Weryfikuje wdrożenie zabezpieczeń."""
    import ast
    import re
    
    with open('main.py', 'r') as f:
        content = f.read()
    
    # Check for hardcoded credentials
    patterns = [
        r'value="[A-Z]{2,}[\\\\]SQL"',  # Server names
        r'value="sa"',                    # SA login
        r'password.*=.*"[^"]+"',          # Hardcoded passwords
    ]
    
    issues = []
    for pattern in patterns:
        if re.search(pattern, content, re.IGNORECASE):
            issues.append(f"Found hardcoded credential pattern: {pattern}")
    
    return issues


def verify_performance():
    """Weryfikuje optymalizacje wydajnościowe."""
    from src.db_connector import DatabaseConnector
    
    try:
        db = DatabaseConnector()
        stats = db.get_diagnostics_stats()
        
        return {
            'cache_enabled': hasattr(db, '_cache'),
            'diagnostics_enabled': db.diagnostics is not None,
            'slow_query_threshold': db.diagnostics.slow_query_threshold if db.diagnostics else None
        }
    except Exception as e:
        return {'error': str(e)}


if __name__ == "__main__":
    print("=== Security Verification ===")
    security_issues = verify_security()
    if security_issues:
        for issue in security_issues:
            print(f"❌ {issue}")
    else:
        print("✅ No hardcoded credentials found")
    
    print("\n=== Performance Verification ===")
    perf = verify_performance()
    for key, value in perf.items():
        status = "✅" if value else "❌"
        print(f"{status} {key}: {value}")
```

---

## Załączniki

### A. Checklist Wdrożenia Security

- [ ] Usunięto domyślne wartości w formularzu połączenia (main.py)
- [ ] Wdrożono SecretsManager z fallback na .env
- [ ] Skonfigurowano ENCRYPTION_MASTER_KEY
- [ ] Zaszyfrowano connection string w .env
- [ ] Dodano .env.local do .gitignore
- [ ] Skonfigurowano audit logging
- [ ] Przeprowadzono code review bezpieczeństwa

### B. Checklist Wdrożenia Performance

- [ ] Wdrożono AsyncDataLoader
- [ ] Skonfigurowano connection pooling
- [ ] Utworzono rekomendowane indeksy
- [ ] Zweryfikowano użycie NOLOCK (tylko raporty)
- [ ] Skonfigurowano cache TTL
- [ ] Dodano wskaźniki postępu

### C. Checklist Wdrożenia LLM

- [ ] Zainstalowano llama-cpp-python
- [ ] Pobrano rekomendowany model GGUF
- [ ] Skonfigurowano LLAMA_MODEL_PATH
- [ ] Przetestowano CPU fallback
- [ ] Zintegrowano z GUI
- [ ] Zweryfikowano offline mode

---

> **Dokument przygotowany przez**: Lead Software Architect & Security Specialist  
> **Ostatnia aktualizacja**: 2025-12-27  
> **Następna rewizja**: Po wdrożeniu P0