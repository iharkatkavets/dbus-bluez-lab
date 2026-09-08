import asyncio

from dbus_next.aio.message_bus import MessageBus
from dbus_next.constants import BusType
from typing import Any, cast
from dbus_next.signature import Variant


BLUEZ_SERVICE_NAME = "org.bluez"
ADAPTER_PATH_ID = "/org/bluez/hci0"


async def main():
    bus = await MessageBus(
        bus_type=BusType.SYSTEM
    ).connect() # pyright: ignore[reportArgumentType]

    adapter_introspection = await bus.introspect(
        BLUEZ_SERVICE_NAME,
        ADAPTER_PATH_ID,
    )

    adapter_object = bus.get_proxy_object(
        BLUEZ_SERVICE_NAME,
        ADAPTER_PATH_ID,
        adapter_introspection,
    )

    properties = adapter_object.get_interface(
        "org.freedesktop.DBus.Properties"
    )

    properties = cast(
        Any,
        adapter_object.get_interface("org.freedesktop.DBus.Properties"),
    )

    await properties.call_set(
        "org.bluez.Adapter1",
        "Powered",
        Variant("b", True),
    )

    adapter_values = await properties.call_get_all(
        "org.bluez.Adapter1"
    )

    for name, value in adapter_values.items():
        print(f"{name}: {value.value}")


asyncio.run(main())
