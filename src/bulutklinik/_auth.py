"""Login helpers shared by the sync and async auth resources."""

from __future__ import annotations

from typing import Any

from .errors import BulutklinikError
from .models import LoginResult
from .tokens import TokenStore


def connect_body(
    api_user_name: str,
    api_user_password: str | None,
    api_client_id: str | None,
    api_secret_key: str | None,
    login_mode: str,
    with_phone_number: str | None,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "apiUserName": api_user_name,
        "apiUserPassword": api_user_password,
        "apiClientId": api_client_id,
        "apiSecretKey": api_secret_key,
        "loginMode": login_mode,
    }
    if with_phone_number is not None:
        body["withPhoneNumber"] = with_phone_number
    return body


def register_body(
    name: str,
    surname: str,
    api_user_name: str,
    phone_number: str,
    password: str,
    sms_verification_code: str,
    response: str,
    accept_user_agreement: int,
    api_client_id: str | None,
    api_secret_key: str | None,
) -> dict[str, Any]:
    return {
        "name": name,
        "surname": surname,
        "apiUserName": api_user_name,
        "phoneNumber": phone_number,
        "password": password,
        "smsVerificationCode": sms_verification_code,
        "response": response,
        "acceptUserAgreement": accept_user_agreement,
        "apiClientId": api_client_id,
        "apiSecretKey": api_secret_key,
    }


def finish_login(data: Any, token_store: TokenStore) -> LoginResult:
    if isinstance(data, dict) and isinstance(data.get("access_token"), str):
        store_tokens(data, token_store)
        return LoginResult(two_factor_required=False)
    if isinstance(data, dict) and isinstance(data.get("response"), str):
        return LoginResult(two_factor_required=True, two_factor_response=data["response"])
    return LoginResult(two_factor_required=False)


def store_tokens(data: Any, token_store: TokenStore) -> None:
    if not isinstance(data, dict) or not isinstance(data.get("access_token"), str):
        raise BulutklinikError("Login response did not contain an access token")
    refresh = data.get("refresh_token")
    token_store.set_tokens(data["access_token"], refresh if isinstance(refresh, str) else None)
