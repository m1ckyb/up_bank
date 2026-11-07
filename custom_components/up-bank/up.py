import aiohttp
import logging
from typing import Any

_LOGGER = logging.getLogger(__name__)

BASE_URL = "https://api.up.com.au/api/v1"


class UP:
    def __init__(self, api_key: str, session: aiohttp.ClientSession | None = None) -> None:
        self.api_key = api_key
        self._session = session

    async def call(self, endpoint: str, params: dict[str, Any] | None = None, method: str = "get") -> dict[str, Any] | None:
        if params is None:
            params = {}
        headers = {"Authorization": f"Bearer {self.api_key}"}

        _LOGGER.debug(
            "Making %s request to %s%s with params: %s",
            method.upper(),
            BASE_URL,
            endpoint,
            params,
        )

        if self._session and not self._session.closed:
            try:
                async with self._session.request(
                    method, BASE_URL + endpoint, headers=headers, params=params
                ) as resp:
                    _LOGGER.debug("Received response status: %s", resp.status)
                    if resp.status == 401:
                        _LOGGER.error("Unauthorized: Invalid API Key")
                        return None
                    if resp.status != 200:
                        _LOGGER.error("Error: Received status code %s", resp.status)
                        return None
                    response_data = await resp.json()
                    return response_data
            except aiohttp.ClientError as e:
                _LOGGER.error("Network error occurred: %s", e)
                return None

        async with aiohttp.ClientSession(headers=headers) as session:
            try:
                async with session.request(
                    method, BASE_URL + endpoint, params=params
                ) as resp:
                    _LOGGER.debug("Received response status: %s", resp.status)
                    if resp.status == 401:
                        _LOGGER.error("Unauthorized: Invalid API Key")
                        return None
                    if resp.status != 200:
                        _LOGGER.error("Error: Received status code %s", resp.status)
                        return None
                    response_data = await resp.json()
                    return response_data
            except aiohttp.ClientError as e:
                _LOGGER.error("Network error occurred: %s", e)
                return None

    async def test(self, api_key: str | None = None) -> bool:
        original_key = self.api_key
        if api_key:
            self.api_key = api_key

        try:
            result = await self.call("/util/ping")
            if result is not None:
                _LOGGER.debug("API key validated successfully.")
                return True
            _LOGGER.error("API key validation failed.")
            return False
        finally:
            self.api_key = original_key

    async def get_accounts(self) -> dict[str, "BankAccount"] | None:
        result = await self.call("/accounts", {"page[size]": 100})
        if result is None:
            _LOGGER.warning("Failed to retrieve accounts.")
            return None

        accounts: dict[str, BankAccount] = {}
        for account in result.get("data", []):
            details = BankAccount(account)
            accounts[details.id] = details
        _LOGGER.debug("Retrieved %d accounts", len(accounts))
        return accounts

    async def getAccounts(self) -> dict[str, "BankAccount"] | None:
        """Backward compatibility alias for get_accounts."""
        return await self.get_accounts()


class BankAccount:
    def __init__(self, data: dict[str, Any]) -> None:
        attributes = data.get("attributes", {})
        balance_obj = attributes.get("balance", {})
        self.name: str = attributes.get("displayName", "Unnamed Account")
        self.balance: str = str(balance_obj.get("value", "0.00"))
        self.currency_code: str = str(balance_obj.get("currencyCode", "AUD"))
        self.id: str = str(data.get("id", ""))
        self.created_at: str | None = attributes.get("createdAt")
        self.account_type: str = str(attributes.get("accountType", ""))
        self.ownership: str = str(attributes.get("ownershipType", ""))

    @property
    def accountType(self) -> str:
        """Backward compatibility property for account_type."""
        return self.account_type

    @property
    def createdAt(self) -> str | None:
        """Backward compatibility property for created_at."""
        return self.created_at
