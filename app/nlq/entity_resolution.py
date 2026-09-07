from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from app.db.models.domain import Party, Inventory
import uuid
import re

class EntityResolver:
    async def resolve_party(self, session: AsyncSession, entity_name: str) -> uuid.UUID | None:
        """
        Attempts to resolve a party name deterministically.
        """
        if not entity_name:
            return None
            
        clean_name = entity_name.strip().lower()
        
        # 1. Substring match (case insensitive)
        query = select(Party.id).where(Party.name.ilike(f"%{clean_name}%"))
        result = await session.execute(query)
        rows = result.fetchall()
        
        if len(rows) == 1:
            return rows[0][0]
            
        # 2. Simple 'contains' match if exact fails
        query = select(Party.id).where(Party.name.ilike(f"%{clean_name}%"))
        result = await session.execute(query)
        rows = result.fetchall()
        
        # If there is exactly one reasonable match, use it. Otherwise, it's ambiguous.
        if len(rows) == 1:
            return rows[0][0]
            
        # Ambiguous or no match
        return None

    async def resolve_material(self, session: AsyncSession, entity_name: str) -> str | None:
        """
        Attempts to resolve a material name to a material_code.
        """
        if not entity_name:
            return None
            
        clean_name = entity_name.strip().lower()
        
        # Exact match
        query = select(Inventory.material_code).where(
            or_(
                Inventory.material_name.ilike(f"{clean_name}"),
                Inventory.material_code.ilike(f"{clean_name}")
            )
        )
        result = await session.execute(query)
        rows = result.fetchall()
        
        if len(rows) == 1:
            return rows[0][0]
            
        # Contains match
        query = select(Inventory.material_code).where(Inventory.material_name.ilike(f"%{clean_name}%"))
        result = await session.execute(query)
        rows = result.fetchall()
        
        if len(rows) == 1:
            return rows[0][0]
            
        return None
