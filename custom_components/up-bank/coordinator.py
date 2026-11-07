from datetime import timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .up import UP

_LOGGER = logging.getLogger(__name__)


class UpCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(self, hass: HomeAssistant, api: UP) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="UP Coordinator",
            update_interval=timedelta(hours=1),
        )
        self.api = api

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            return await self.get_data()
        except UpdateFailed:
            raise
        except Exception as err:
            raise UpdateFailed(f"Error communicating with Up Bank API: {err}") from err

    async def get_data(self) -> dict[str, Any]:
        accounts = await self.api.get_accounts()
        if accounts is None:
            raise UpdateFailed("Failed to retrieve accounts from Up Bank API")

        joint = 0.0
        joint_id = ""
        individual = 0.0
        individual_id = ""

        for account in accounts.values():
            account_type = account.account_type.upper() if account.account_type else ""
            ownership = account.ownership.upper() if account.ownership else ""

            try:
                balance_val = float(account.balance)
            except (ValueError, TypeError):
                balance_val = 0.0

            if account_type == "SAVER":
                if ownership == "JOINT":
                    joint += balance_val
                else:
                    individual += balance_val
            elif account_type == "TRANSACTIONAL":
                if ownership == "JOINT":
                    joint_id = account.id
                else:
                    individual_id = account.id

        return {
            "accounts": accounts,
            "totals": {
                "joint": {
                    "balance": round(joint, 2),
                    "id": joint_id,
                },
                "individual": {
                    "balance": round(individual, 2),
                    "id": individual_id,
                },
            },
        }
