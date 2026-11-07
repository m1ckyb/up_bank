import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import UpCoordinator
from .up import BankAccount

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Up Bank sensor entities from a config entry."""
    entry_data = hass.data[DOMAIN][config_entry.entry_id]

    if isinstance(entry_data, dict) and "coordinator" in entry_data:
        coordinator: UpCoordinator = entry_data["coordinator"]
    else:
        # Fallback for compatibility
        coordinator = UpCoordinator(hass, entry_data)
        await coordinator.async_config_entry_first_refresh()

    entities: list[SensorEntity] = []
    accounts: dict[str, BankAccount] = coordinator.data.get("accounts", {})

    for account in accounts.values():
        entities.append(Account(coordinator, account))

    totals = coordinator.data.get("totals", {})

    individual_totals = totals.get("individual", {})
    individual_id = individual_totals.get("id", "")
    individual_acc = accounts.get(individual_id) if individual_id else None
    entities.append(TotalSavings(coordinator, "individual", individual_acc))

    joint_totals = totals.get("joint", {})
    joint_id = joint_totals.get("id", "")
    joint_balance = joint_totals.get("balance", 0.0)
    if joint_id or joint_balance > 0:
        joint_acc = accounts.get(joint_id) if joint_id else None
        entities.append(TotalSavings(coordinator, "joint", joint_acc))

    async_add_entities(entities)


class Account(CoordinatorEntity[UpCoordinator], SensorEntity):
    """Representation of an Up Bank account sensor."""

    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.TOTAL

    def __init__(self, coordinator: UpCoordinator, account: BankAccount) -> None:
        super().__init__(coordinator, context=account)
        self.account = account
        self.id = account.id
        self._attr_unique_id = f"up_{account.id}"
        self._attr_name = account.name
        self._attr_native_unit_of_measurement = account.currency_code or "AUD"

    @property
    def native_value(self) -> float | None:
        """Return the balance of the account."""
        try:
            return float(self.account.balance)
        except (ValueError, TypeError):
            return None

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information for the account."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._attr_unique_id)},
            name=self.account.name,
            manufacturer=self.account.ownership,
            model=self.account.account_type,
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        accounts = self.coordinator.data.get("accounts", {})
        if self.id in accounts:
            self.account = accounts[self.id]
        super()._handle_coordinator_update()


class TotalSavings(CoordinatorEntity[UpCoordinator], SensorEntity):
    """Representation of total savings sensor."""

    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.TOTAL
    _attr_native_unit_of_measurement = "AUD"

    def __init__(
        self,
        coordinator: UpCoordinator,
        savings_type: str,
        account: BankAccount | None = None,
    ) -> None:
        super().__init__(coordinator, context=account)
        self.savings_type = savings_type
        self.account = account
        self._attr_unique_id = f"up_total_savings_{savings_type}"
        self._attr_name = f"Total {savings_type} savings"

    @property
    def native_value(self) -> float | None:
        """Return the total savings balance."""
        totals = self.coordinator.data.get("totals", {})
        type_totals = totals.get(self.savings_type, {})
        balance = type_totals.get("balance")
        if balance is not None:
            try:
                return float(balance)
            except (ValueError, TypeError):
                return None
        return None

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        if self.account:
            return DeviceInfo(
                identifiers={(DOMAIN, f"up_{self.account.id}")},
                name=self.account.name,
                manufacturer=self.account.ownership,
                model=self.account.account_type,
            )
        return DeviceInfo(
            identifiers={(DOMAIN, f"up_{self.savings_type}_savings")},
            name=f"Up {self.savings_type.capitalize()} Savings",
            manufacturer="Up Bank",
            model="Savings Summary",
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if self.account:
            accounts = self.coordinator.data.get("accounts", {})
            if self.account.id in accounts:
                self.account = accounts[self.account.id]
        super()._handle_coordinator_update()
