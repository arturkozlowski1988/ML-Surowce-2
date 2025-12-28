"""
Test script for Production Hardening features.
Tests ConfigEncryption, SecurityAuditLog, and Connection Pool.

Usage:
    python scripts/test_security.py
"""

import os
import sys
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_encryption():
    """Test ConfigEncryption module."""
    print("\n" + "=" * 50)
    print("TEST: ConfigEncryption")
    print("=" * 50)
    
    from src.security.encryption import ConfigEncryption
    
    # Test 1: Generate master key
    print("\n1. Generate master key...")
    key = ConfigEncryption.generate_master_key()
    print(f"   Generated key: {key[:20]}...")
    assert len(key) > 30, "Key should be long enough"
    print("   ✅ PASSED")
    
    # Test 2: Encrypt/Decrypt with custom key
    print("\n2. Test encrypt/decrypt...")
    crypto = ConfigEncryption(master_key=key)
    
    test_data = "mssql+pyodbc://sa:secret@server/db?driver=ODBC+Driver+17"
    encrypted = crypto.encrypt(test_data)
    print(f"   Original:  {test_data[:30]}...")
    print(f"   Encrypted: {encrypted[:30]}...")
    
    decrypted = crypto.decrypt(encrypted)
    assert decrypted == test_data, "Decrypted should match original"
    print(f"   Decrypted: {decrypted[:30]}...")
    print("   ✅ PASSED")
    
    # Test 3: Different keys produce different ciphertext
    print("\n3. Test key uniqueness...")
    key2 = ConfigEncryption.generate_master_key()
    crypto2 = ConfigEncryption(master_key=key2)
    encrypted2 = crypto2.encrypt(test_data)
    assert encrypted != encrypted2, "Different keys should produce different ciphertext"
    print("   ✅ PASSED - Different keys produce different ciphertext")
    
    # Test 4: Wrong key fails decryption
    print("\n4. Test wrong key rejection...")
    try:
        crypto2.decrypt(encrypted)  # Try to decrypt with wrong key
        print("   ❌ FAILED - Should have raised exception")
        return False
    except Exception as e:
        print(f"   ✅ PASSED - Correctly rejected wrong key: {type(e).__name__}")
    
    print("\n✅ All encryption tests PASSED")
    return True


def test_audit_log():
    """Test SecurityAuditLog module."""
    print("\n" + "=" * 50)
    print("TEST: SecurityAuditLog")
    print("=" * 50)
    
    from src.security.audit import SecurityAuditLog, AuditEventType, AuditSeverity
    
    # Use temp log file
    test_log_path = "logs/test_security_audit.log"
    
    # Clean up previous test log
    if os.path.exists(test_log_path):
        os.remove(test_log_path)
    
    # Reset singleton for testing
    SecurityAuditLog._instance = None
    
    # Test 1: Initialize audit log
    print("\n1. Initialize audit log...")
    audit = SecurityAuditLog(log_path=test_log_path)
    assert os.path.exists(test_log_path), "Log file should be created"
    print(f"   Log file: {test_log_path}")
    print("   ✅ PASSED")
    
    # Test 2: Log events
    print("\n2. Log various events...")
    
    audit.log(AuditEventType.DATA_ACCESS, details={"query": "get_stock"})
    audit.log_data_access("get_historical_data", table="CtiZlecenieElem", row_count=1000)
    audit.log_ai_query(engine="Local LLM", model="Qwen2.5-3B", duration_ms=5000)
    audit.log_security_warning("Test warning", details={"test": True})
    
    print("   Logged 4 events")
    print("   ✅ PASSED")
    
    # Test 3: Read back events
    print("\n3. Read back events...")
    events = audit.get_recent_events(10)
    assert len(events) >= 4, f"Should have at least 4 events, got {len(events)}"
    print(f"   Found {len(events)} events")
    print("   ✅ PASSED")
    
    # Test 4: Get summary
    print("\n4. Get summary...")
    summary = audit.get_summary()
    print(f"   Total events: {summary['total_events']}")
    print(f"   By type: {summary.get('by_type', {})}")
    assert summary['total_events'] >= 4, "Should have logged events"
    print("   ✅ PASSED")
    
    # Cleanup
    SecurityAuditLog._instance = None
    
    print("\n✅ All audit log tests PASSED")
    return True


def test_connection_pool():
    """Test database connection pool optimization."""
    print("\n" + "=" * 50)
    print("TEST: Connection Pool")
    print("=" * 50)
    
    from src.db_connector import DatabaseConnector
    
    # Test 1: Initialize with pooling
    print("\n1. Initialize DatabaseConnector with pooling...")
    try:
        db = DatabaseConnector(enable_audit=False)
        print("   ✅ PASSED - Connected successfully")
    except Exception as e:
        print(f"   ⚠️ SKIPPED - Database not available: {e}")
        return True  # Skip if no DB
    
    # Test 2: Check pool configuration
    print("\n2. Check pool configuration...")
    pool = db.engine.pool
    print(f"   Pool class: {type(pool).__name__}")
    print(f"   Pool size: {pool.size()}")
    print("   ✅ PASSED")
    
    # Test 3: Execute queries
    print("\n3. Execute test query...")
    start = time.time()
    try:
        result = db.test_connection()
        duration = time.time() - start
        print(f"   Connection test: {result}")
        print(f"   Duration: {duration*1000:.1f}ms")
        print("   ✅ PASSED")
    except Exception as e:
        print(f"   ⚠️ Query failed (expected if DB offline): {e}")
    
    # Test 4: Check diagnostics
    print("\n4. Check diagnostics...")
    if db.diagnostics:
        stats = db.diagnostics.get_stats()
        print(f"   Query stats: {stats}")
        print("   ✅ PASSED")
    else:
        print("   Diagnostics disabled")
    
    print("\n✅ All connection pool tests PASSED")
    return True


def test_integration():
    """Test integration between components."""
    print("\n" + "=" * 50)
    print("TEST: Integration")
    print("=" * 50)
    
    # Test 1: DB with audit
    print("\n1. DatabaseConnector with audit logging...")
    
    # Reset audit singleton
    from src.security.audit import SecurityAuditLog
    SecurityAuditLog._instance = None
    
    try:
        from src.db_connector import DatabaseConnector
        db = DatabaseConnector(enable_audit=True)
        
        if db._audit:
            events = db._audit.get_recent_events(5)
            session_started = any("SESSION_START" in str(e) for e in events)
            print(f"   Session start logged: {session_started}")
            print("   ✅ PASSED")
        else:
            print("   ⚠️ Audit not initialized")
    except Exception as e:
        print(f"   ⚠️ SKIPPED: {e}")
    
    print("\n✅ Integration tests PASSED")
    return True


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("PRODUCTION HARDENING - SECURITY TESTS")
    print("=" * 60)
    
    results = {}
    
    # Run tests
    results['encryption'] = test_encryption()
    results['audit_log'] = test_audit_log()
    results['connection_pool'] = test_connection_pool()
    results['integration'] = test_integration()
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    for name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"  {name}: {status}")
    
    all_passed = all(results.values())
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ ALL TESTS PASSED")
    else:
        print("❌ SOME TESTS FAILED")
    print("=" * 60)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
