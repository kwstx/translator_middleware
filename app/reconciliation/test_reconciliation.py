import os
import sys
import asyncio
import uuid
import pytest
from sqlmodel import select, SQLModel
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

# Ensure we can import the app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.db.models import ProtocolMapping, MappingFailureLog, ProtocolType
from app.reconciliation.engine import ReconciliationEngine

# Use file-based SQLite for repeatable tests
DB_FILE = "test_reconciliation.db"
test_database_url = f"sqlite+aiosqlite:///{DB_FILE}"

if os.path.exists(DB_FILE):
    os.remove(DB_FILE)

test_engine = create_async_engine(test_database_url, echo=False)

# Monkeypatch the module's engine for tests
import app.reconciliation.engine
app.reconciliation.engine.db_engine = test_engine

async def test_drift_cases():
    engine = ReconciliationEngine()
    
    print("Testing 'email'...")
    res = await engine.resolve_field("SOURCE_A", "TARGET_B", "email")
    print(f"Result for 'email': {res}")
    assert res == "email"

    print("Testing 'contact_email'...")
    res = await engine.resolve_field("SOURCE_A", "TARGET_B", "contact_email")
    print(f"Result for 'contact_email': {res}")
    assert res == "email"

    print("Testing 'customer_first_name'...")
    res = await engine.resolve_field("SOURCE_A", "TARGET_B", "customer_first_name")
    print(f"Result for 'customer_first_name': {res}")
    assert res == "first_name"

    # Check persistence
    async with AsyncSession(test_engine) as session:
        query = select(ProtocolMapping).where(
            ProtocolMapping.source_protocol == "SOURCE_A",
            ProtocolMapping.target_protocol == "TARGET_B"
        )
        result = await session.execute(query)
        mapping = result.scalars().first()
        
        assert mapping is not None
        assert "contact_email" in mapping.semantic_equivalents
        assert mapping.semantic_equivalents["contact_email"] == "email"
        print(f"Persisted mapping: {mapping.semantic_equivalents}")

async def test_repair_loop():
    engine = ReconciliationEngine()
    
    # Manually insert a high-confidence failure
    async with AsyncSession(test_engine) as session:
        failure = MappingFailureLog(
            source_protocol="REPAIR_SRC",
            target_protocol="REPAIR_TGT",
            source_field="cust_email",
            model_suggestion="email",
            model_confidence=0.95,
            error_type="SEMANTIC_MISMATCH",
            applied=False
        )
        session.add(failure)
        await session.commit()

    # Run repair loop
    await engine.repair_loop()

    # Check if applied
    async with AsyncSession(test_engine) as session:
        query = select(ProtocolMapping).where(
            ProtocolMapping.source_protocol == "REPAIR_SRC",
            ProtocolMapping.target_protocol == "REPAIR_TGT"
        )
        result = await session.execute(query)
        mapping = result.scalars().first()
        assert mapping is not None
        assert mapping.semantic_equivalents["cust_email"] == "email"
        
        query = select(MappingFailureLog).where(
            MappingFailureLog.source_protocol == "REPAIR_SRC",
            MappingFailureLog.source_field == "cust_email"
        )
        result = await session.execute(query)
        failure = result.scalars().first()
        assert failure.applied == True

async def main():
    # Initialize DB (create tables for SQLite)
    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
        
    try:
        await test_drift_cases()
        await test_repair_loop()
        print("\n" + "="*40)
        print("All reconciliation tests passed!")
        print("="*40)
    except Exception as e:
        print(f"Tests failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await test_engine.dispose()
        if os.path.exists(DB_FILE):
             os.remove(DB_FILE)

if __name__ == "__main__":
    asyncio.run(main())
