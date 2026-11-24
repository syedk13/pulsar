"""Verifies a Supabase access token server-side and returns the user id."""

from functools import cached_property
from typing import Protocol

from app.config import Settings
from app.errors import ServiceUnavailable


class AuthVerifier(Protocol):
    def user_id(self, access_token: str) -> str | None:
        """The Supabase user id for a valid token, or None if the token is not valid."""
        ...


class SupabaseAuthVerifier:
    """Asks Supabase Auth (`GET /auth/v1/user`) who the token belongs to. This works for any
    JWT signing method and rejects expired or revoked sessions."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    @cached_property
    def _client(self):
        if not (self._settings.supabase_url and self._settings.supabase_secret_key):
            raise ServiceUnavailable("SUPABASE_URL and SUPABASE_SECRET_KEY must be set.")
        from supabase import create_client

        # Separate client from the data client, so auth calls can never change the
        # credentials used for database queries.
        return create_client(self._settings.supabase_url, self._settings.supabase_secret_key)

    def user_id(self, access_token: str) -> str | None:
        from supabase_auth.errors import AuthApiError

        try:
            response = self._client.auth.get_user(access_token)
        except AuthApiError:
            return None  # invalid, expired or revoked token
        except ServiceUnavailable:
            raise
        except Exception as exc:  # network failure talking to Supabase Auth
            raise ServiceUnavailable("Could not verify the access token.") from exc
        return response.user.id if response and response.user else None
