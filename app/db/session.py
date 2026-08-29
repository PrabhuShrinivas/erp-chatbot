from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import event
import logging
from app.core.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False)

logger = logging.getLogger("erp_qa")

@event.listens_for(engine.sync_engine, "before_execute")
def before_execute(conn, clauseelement, multiparams, params, execution_options):
    print(f"\n--- SQL GENERATED ---\n{clauseelement}\nParams: {params}\n---------------------", flush=True)

async_session = async_sessionmaker(engine, expire_on_commit=False)

async def get_db():
    async with async_session() as session:
        yield session
