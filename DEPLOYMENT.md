# AI Supply Assistant - Deployment Guide

> **Wersja**: 1.5.0  
> **Środowisko**: Windows Server + MS SQL Server

---

## Spis Treści

1. [Quick Start (Local)](#quick-start-local)
2. [Deployment Sieciowy (LAN)](#deployment-sieciowy-lan)
3. [Instalacja jako Windows Service](#instalacja-jako-windows-service)
4. [Local LLM Setup](#local-llm-setup)
5. [Security](#security)
6. [Troubleshooting](#troubleshooting)

---

## Quick Start (Local)

Uruchomienie na jednym komputerze:

1. **Skonfiguruj bazę danych**:

   ```bash
   copy .env.example .env
   # Edytuj .env z danymi SQL Server
   ```

2. **Zainstaluj zależności**:

   ```bash
   pip install -r requirements.txt
   ```

3. **Uruchom aplikację**:

   ```bash
   run_app.bat
   # lub: streamlit run main.py
   ```

4. **Otwórz w przeglądarce**: <http://localhost:8501>

---

## Deployment Sieciowy (LAN)

Udostępnienie aplikacji użytkownikom w sieci lokalnej.

### Wymagania

| Komponent | Wersja | Uwagi |
|-----------|--------|-------|
| Windows Server | 2016+ | Zalecany Windows Server 2019/2022 |
| Python | 3.9+ | Zainstalowany globalnie |
| MS SQL Server | 2016+ | Na tym samym serwerze lub w sieci |
| RAM | 8 GB+ | 16 GB+ dla Local LLM |
| ODBC Driver | 17+ | ODBC Driver 17 for SQL Server |

### Krok 1: Instalacja

```powershell
# Na Windows Server (jako Administrator)

# 1. Skopiuj folder aplikacji na serwer
# np. C:\Apps\AISupplyAssistant

# 2. Przejdź do folderu
cd C:\Apps\AISupplyAssistant

# 3. Zainstaluj zależności
pip install -r requirements.txt

# 4. Skonfiguruj bazę danych
copy .env.example .env
notepad .env
```

### Krok 2: Konfiguracja .env

```ini
# Połączenie z lokalnym SQL Server na tym samym serwerze
DB_CONN_STR=mssql+pyodbc://sa:password@localhost/cdn_test?driver=ODBC+Driver+17+for+SQL+Server&TrustServerCertificate=yes

# Lub z Windows Authentication (zalecane)
DB_CONN_STR=mssql+pyodbc://./cdn_test?driver=ODBC+Driver+17+for+SQL+Server&Trusted_Connection=yes

# AI API (opcjonalne)
GEMINI_API_KEY=your_key_here
```

### Krok 3: Konfiguracja Firewall

**Otwórz port 8501** (domyślny) w Windows Firewall:

```powershell
# Uruchom jako Administrator
netsh advfirewall firewall add rule name="AI Supply Assistant" dir=in action=allow protocol=tcp localport=8501
```

Lub przez GUI:

1. Panel Sterowania → System i zabezpieczenia → Zapora Windows
2. Ustawienia zaawansowane → Reguły przychodzące → Nowa reguła
3. Port → TCP → 8501 → Zezwalaj → Nazwa: "AI Supply Assistant"

### Krok 4: Uruchomienie Serwera

```batch
start_server.bat
```

Skrypt wyświetli adres IP serwera i URL dla użytkowników:

```
Server IP Address: 192.168.1.100
Users can access the application at:
  http://192.168.1.100:8501
```

### Konfiguracja Sieci

Plik `.streamlit/config.toml` zawiera konfigurację serwera:

```toml
[server]
address = "0.0.0.0"    # Nasłuch na wszystkich interfejsach
port = 8501            # Port (zmień na 80 dla standardowego HTTP)
headless = true        # Nie otwieraj przeglądarki na serwerze
enableXsrfProtection = true
```

---

## Instalacja jako Windows Service

Dla produkcji - automatyczny start po restarcie serwera.

### Używając NSSM (Non-Sucking Service Manager)

1. **Pobierz NSSM**: <https://nssm.cc/download>

2. **Zainstaluj usługę**:

   ```powershell
   nssm install AISupplyAssistant "C:\Python39\python.exe" "-m streamlit run C:\Apps\AISupplyAssistant\main.py --server.address 0.0.0.0 --server.port 8501 --server.headless true"
   
   # Ustaw katalog roboczy
   nssm set AISupplyAssistant AppDirectory "C:\Apps\AISupplyAssistant"
   
   # Uruchom usługę
   nssm start AISupplyAssistant
   ```

3. **Zarządzanie usługą**:

   ```powershell
   # Status
   nssm status AISupplyAssistant
   
   # Restart
   nssm restart AISupplyAssistant
   
   # Stop
   nssm stop AISupplyAssistant
   
   # Usuń usługę
   nssm remove AISupplyAssistant confirm
   ```

---

## Local LLM Setup

Dla pracy offline bez API Google Gemini:

1. **Pobierz model GGUF**:
   - [Qwen2.5-7B-Instruct](https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF) (~5GB)
   - Plik: `qwen2.5-7b-instruct-q4_k_m.gguf`

2. **Umieść w folderze `models/`**

3. **Skonfiguruj w `.env`**:

   ```ini
   LOCAL_LLM_PATH=models/qwen2.5-7b-instruct-q4_k_m.gguf
   ```

---

## Security

### Zalecenia dla produkcji

1. **Zmień domyślne hasła** użytkowników w Panel Admina
2. **Użyj HTTPS** (reverse proxy nginx/IIS z certyfikatem SSL)
3. **Ogranicz dostęp** tylko do sieci wewnętrznej (nie eksponuj do internetu)
4. **Regularne backupy** plików konfiguracyjnych i bazy danych

### Przykład IIS Reverse Proxy (HTTPS)

```
URL Rewrite:
  Pattern: ^(.*)$
  Rewrite URL: http://localhost:8501/{R:1}
```

---

## Troubleshooting

### Problem: Użytkownicy nie mogą się połączyć

1. **Sprawdź firewall**:

   ```powershell
   netsh advfirewall firewall show rule name="AI Supply Assistant"
   ```

2. **Sprawdź czy serwer nasłuchuje**:

   ```powershell
   netstat -an | findstr 8501
   ```

   Powinno pokazać: `0.0.0.0:8501 ... LISTENING`

3. **Sprawdź dostępność z klienta**:

   ```powershell
   # Z komputera użytkownika
   ping 192.168.1.100
   telnet 192.168.1.100 8501
   ```

### Problem: Database Connection Failed

- Sprawdź czy SQL Server działa
- Sprawdź connection string w `.env`
- Sprawdź czy SQL Server akceptuje połączenia TCP/IP

### Problem: Aplikacja działa wolno

- Zwiększ connection pool w `db_connector.py`
- Użyj SSD dla bazy danych
- Rozważ zwiększenie RAM dla TensorFlow/LSTM

### Logi

Logi aplikacji znajdują się w:

- `logs/audit.log` - audyt działań użytkowników
- Konsola serwera - logi Streamlit
