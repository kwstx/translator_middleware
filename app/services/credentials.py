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
        refresh_token: Optional[str] = None,
        expires_at: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ProviderCredential:
        encrypted_token = CryptoService.encrypt(token)
        encrypted_refresh_token = CryptoService.encrypt(refresh_token) if refresh_token else None
        
        # Check if already exists for this user/provider
        existing = await CredentialService.get_credential_by_provider(db, user_id, provider_name)
        if existing:
            existing.encrypted_token = encrypted_token
            existing.encrypted_refresh_token = encrypted_refresh_token
            existing.expires_at = expires_at
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
            encrypted_refresh_token=encrypted_refresh_token,
            expires_at=expires_at,
            credential_metadata=metadata or {}
        )
        db.add(new_cred)
        await db.commit()
        await db.refresh(new_cred)
        return new_cred

    @staticmethod
    async def get_active_token(db: AsyncSession, user_id: UUID, provider_name: str) -> Optional[str]:
        """
        Retrieves the access token, automatically refreshing it if expired.
        """
        cred = await CredentialService.get_credential_by_provider(db, user_id, provider_name)
        if not cred:
            return None

        # Check for expiration (with 1-minute buffer)
        from datetime import datetime, timezone, timedelta
        if cred.expires_at and cred.expires_at < datetime.now(timezone.utc) + timedelta(minutes=1):
            if cred.encrypted_refresh_token:
                # Attempt to refresh
                refreshed = await CredentialService.refresh_oauth_token(db, cred)
                if refreshed:
                    return CryptoService.decrypt(refreshed.encrypted_token)
        
        return CryptoService.decrypt(cred.encrypted_token)

    @staticmethod
    async def refresh_oauth_token(db: AsyncSession, credential: ProviderCredential) -> Optional[ProviderCredential]:
        """
        Generic OAuth2 refresh logic. 
        In a real app, you'd need provider-specific token URLs.
        """
        import httpx
        from datetime import datetime, timezone, timedelta
        
        refresh_token = CryptoService.decrypt(credential.encrypted_refresh_token)
        if not refresh_token:
            return None

        # Determine token URL (demo logic - in production these would be in config)
        token_url = credential.credential_metadata.get("token_url")
        client_id = credential.credential_metadata.get("client_id")
        client_secret = credential.credential_metadata.get("client_secret")

        if not token_url:
            # Fallback/Default or error
            return None

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    token_url,
                    data={
                        "grant_type": "refresh_token",
                        "refresh_token": refresh_token,
                        "client_id": client_id,
                        "client_secret": client_secret,
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                # Update credential
                credential.encrypted_token = CryptoService.encrypt(data["access_token"])
                if "refresh_token" in data:
                    credential.encrypted_refresh_token = CryptoService.encrypt(data["refresh_token"])
                
                if "expires_in" in data:
                    credential.expires_at = datetime.now(timezone.utc) + timedelta(seconds=data["expires_in"])
                
                db.add(credential)
                await db.commit()
                await db.refresh(credential)
                return credential
        except Exception:
            # Log failure - maybe mark credential as invalid
            return None

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

