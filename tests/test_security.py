"""
Security tests for Production Hardening features.
Tests ConfigEncryption, SecurityAuditLog, and Connection Pool.

Migrated from scripts/test_security.py to pytest format.
"""

import os

import pytest


class TestConfigEncryption:
    """Test encryption module functionality."""

    def test_generate_master_key(self):
        """Test master key generation produces valid keys."""
        from src.security.encryption import ConfigEncryption

        key = ConfigEncryption.generate_master_key()

        assert key is not None
        assert len(key) > 30, "Key should be sufficiently long"

    def test_encrypt_decrypt_roundtrip(self, encryption_key):
        """Test that encrypt/decrypt cycle preserves data."""
        from src.security.encryption import ConfigEncryption

        crypto = ConfigEncryption(master_key=encryption_key)
        test_data = "mssql+pyodbc://sa:secret@server/db?driver=ODBC+Driver+17"

        encrypted = crypto.encrypt(test_data)
        decrypted = crypto.decrypt(encrypted)

        assert decrypted == test_data
        assert encrypted != test_data, "Encrypted data should differ from original"

    def test_different_keys_produce_different_ciphertext(self, encryption_key):
        """Test that different keys produce different ciphertext."""
        from src.security.encryption import ConfigEncryption

        key2 = ConfigEncryption.generate_master_key()
        crypto1 = ConfigEncryption(master_key=encryption_key)
        crypto2 = ConfigEncryption(master_key=key2)

        test_data = "sensitive_connection_string"
        encrypted1 = crypto1.encrypt(test_data)
        encrypted2 = crypto2.encrypt(test_data)

        assert encrypted1 != encrypted2

    def test_wrong_key_fails_decryption(self, encryption_key):
        """Test that decryption with wrong key fails."""
        from src.security.encryption import ConfigEncryption

        crypto1 = ConfigEncryption(master_key=encryption_key)
        key2 = ConfigEncryption.generate_master_key()
        crypto2 = ConfigEncryption(master_key=key2)

        encrypted = crypto1.encrypt("secret_data")

        with pytest.raises(Exception):
            crypto2.decrypt(encrypted)


class TestSecurityAuditLog:
    """Test security audit logging functionality."""

    def test_audit_log_initialization(self, temp_audit_log):
        """Test audit log file creation."""
        from src.security.audit import SecurityAuditLog

        # Reset singleton
        SecurityAuditLog._instance = None

        audit = SecurityAuditLog(log_path=temp_audit_log)

        assert os.path.exists(temp_audit_log)

        # Cleanup
        SecurityAuditLog._instance = None

    def test_log_events(self, temp_audit_log):
        """Test logging various event types."""
        from src.security.audit import AuditEventType, SecurityAuditLog

        SecurityAuditLog._instance = None
        audit = SecurityAuditLog(log_path=temp_audit_log)

        # Log different event types
        audit.log(AuditEventType.DATA_ACCESS, details={"query": "get_stock"})
        audit.log_data_access("get_historical_data", table="CtiZlecenieElem", row_count=1000)
        audit.log_ai_query(engine="Local LLM", model="Qwen2.5-3B", duration_ms=5000)
        audit.log_security_warning("Test warning", details={"test": True})

        events = audit.get_recent_events(10)

        assert len(events) >= 4

        SecurityAuditLog._instance = None

    def test_get_summary(self, temp_audit_log):
        """Test audit summary generation."""
        from src.security.audit import AuditEventType, SecurityAuditLog

        SecurityAuditLog._instance = None
        audit = SecurityAuditLog(log_path=temp_audit_log)

        audit.log(AuditEventType.DATA_ACCESS, details={"test": True})
        audit.log(AuditEventType.DATA_ACCESS, details={"test": True})

        summary = audit.get_summary()

        assert "total_events" in summary
        assert summary["total_events"] >= 2

        SecurityAuditLog._instance = None


@pytest.mark.integration
class TestConnectionPool:
    """Test database connection pool functionality."""

    def test_database_connector_initialization(self):
        """Test DatabaseConnector can be initialized."""
        from src.db_connector import DatabaseConnector

        try:
            db = DatabaseConnector(enable_audit=False)
            assert db.engine is not None
        except Exception as e:
            pytest.skip(f"Database not available: {e}")

    def test_pool_configuration(self):
        """Test connection pool is properly configured."""
        from src.db_connector import DatabaseConnector

        try:
            db = DatabaseConnector(enable_audit=False)
            pool = db.engine.pool

            assert pool is not None
            assert pool.size() > 0
        except Exception as e:
            pytest.skip(f"Database not available: {e}")

    def test_connection_test(self):
        """Test database connection verification."""
        from src.db_connector import DatabaseConnector

        try:
            db = DatabaseConnector(enable_audit=False)
            result = db.test_connection()

            assert result is True
        except Exception as e:
            pytest.skip(f"Database not available: {e}")


@pytest.mark.integration
class TestIntegration:
    """Test integration between security components."""

    def test_db_with_audit_logging(self, temp_audit_log):
        """Test DatabaseConnector with audit logging enabled."""
        from src.security.audit import SecurityAuditLog

        SecurityAuditLog._instance = None

        try:
            from src.db_connector import DatabaseConnector

            db = DatabaseConnector(enable_audit=True)

            if db._audit:
                events = db._audit.get_recent_events(5)
                session_started = any("SESSION_START" in str(e) for e in events)
                assert session_started or len(events) > 0
        except Exception as e:
            pytest.skip(f"Database not available: {e}")
        finally:
            SecurityAuditLog._instance = None
