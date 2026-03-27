from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from app.db.models import ProviderCredential, CredentialType
from app.core.crypto import CryptoService

class CredentialService:
    @staticmethod
    async def get_credentials(db: AsyncSession, user_id: UUID) -> List[ProviderCredential]:
        statement = select(ProviderCredential).where(ProviderCredential.user_id == user_id)
        result = await db.execute(statement)
        return list(result.scalars().all())

    @staticmethod
    async def get_credential_by_provider(db: AsyncSession, user_id: UUID, provider_name: str) -> Optional[ProviderCredential]:
        statement = select(ProviderCredential).where(
            ProviderCredential.user_id == user_id, 
            ProviderCredential.provider_name == provider_name
        )
        result = await db.execute(statement)
        return result.scalars().first()

    @staticmethod
    async def save_credential(
        db: AsyncSession, 
        user_id: UUID, 
        provider_name: str, 
        token: str, 
        credential_type: CredentialType,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ProviderCredential:
        encrypted_token = CryptoService.encrypt(token)
        
        # Check if already exists for this user/provider
        existing = await CredentialService.get_credential_by_provider(db, user_id, provider_name)
        if existing:
            existing.encrypted_token = encrypted_token
            existing.credential_type = credential_type
            if metadata:
                existing.credential_metadata = metadata
            db.add(existing)
            await db.commit()
            await db.refresh(existing)
            return existing
        
        new_cred = ProviderCredential(
            user_id=user_id,
            provider_name=provider_name,
            credential_type=credential_type,
            encrypted_token=encrypted_token,
            credential_metadata=metadata or {}
        )
        db.add(new_cred)
        await db.commit()
        await db.refresh(new_cred)
        return new_cred

    @staticmethod
    async def delete_credential(db: AsyncSession, user_id: UUID, provider_name: str) -> bool:
        cred = await CredentialService.get_credential_by_provider(db, user_id, provider_name)
        if cred:
            await db.delete(cred)
            await db.commit()
            return True
        return False

    @staticmethod
    def decrypt_token(credential: ProviderCredential) -> str:
        return CryptoService.decrypt(credential.encrypted_token)
