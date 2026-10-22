from .const import DATA_STOCK, DOMAIN


async def async_get_config_entry_diagnostics(hass, entry):
    return hass.data[DOMAIN][DATA_STOCK][entry.entry_id].diagnostics()
