import pytest
import uuid
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.db.base import Base
from app.db.models.domain import Party, Inventory
from app.nlq.entity_resolution import EntityResolver

@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine)
    async with Session() as sess:
        yield sess
    await engine.dispose()

@pytest.mark.asyncio
async def test_resolve_party(session):
    party_id = uuid.uuid4()
    session.add(Party(id=party_id, name="Jindal Steel", party_type="customer"))
    session.add(Party(name="Sharma Brothers", party_type="customer"))
    await session.commit()
    
    resolver = EntityResolver()
    
    # Exact match
    res_id = await resolver.resolve_party(session, "Jindal Steel")
    assert res_id == party_id
    
    # Contains match (fuzzy)
    res_id = await resolver.resolve_party(session, "Jindal")
    assert res_id == party_id
    
    # Missing
    res_id = await resolver.resolve_party(session, "Unknown")
    assert res_id is None
