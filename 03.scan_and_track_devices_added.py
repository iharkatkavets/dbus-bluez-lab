import asyncio

from dbus_next.aio.message_bus import MessageBus
from dbus_next.constants import BusType
from typing import Any, cast


BLUEZ_SERVICE_NAME = "org.bluez"
ADAPTER_PATH_ID = "/org/bluez/hci0"


def interfaces_added(path, interfaces):
    device = interfaces.get("org.bluez.Device1")

    if device is None:
        return

    print(f"Device: {path}")
    address = device.get("Address")
    name = device.get("Name")
    rssi = device.get("RSSI")

    if address is not None:
        print(f"NEW    Address: {address.value}")

    if name is not None:
        print(f"NEW    Name: {name.value}")

    if rssi is not None:
        print(f"NEW    RSSI: {rssi.value}")
    print("----------------")


async def main():
    bus = await MessageBus(
        bus_type=BusType.SYSTEM
    ).connect() # pyright: ignore[reportArgumentType]

    bluez_bus_introspection = await bus.introspect(
        BLUEZ_SERVICE_NAME,
        "/",
    )

    root_object = bus.get_proxy_object(
        BLUEZ_SERVICE_NAME,
        "/",
        bluez_bus_introspection,
    )

    object_manager = cast(
        Any,
        root_object.get_interface("org.freedesktop.DBus.ObjectManager"),
    )

    object_manager.on_interfaces_added(
        interfaces_added
    )

    adapter_introspection = await bus.introspect(
        BLUEZ_SERVICE_NAME,
        ADAPTER_PATH_ID,
    )

    adapter_object = bus.get_proxy_object(
        BLUEZ_SERVICE_NAME,
        ADAPTER_PATH_ID,
        adapter_introspection,
    )
    adapter = cast(
        Any,
        adapter_object.get_interface("org.bluez.Adapter1"),
    )

    await adapter.call_start_discovery()
    print("Scanning...")

    await asyncio.Event().wait()


asyncio.run(main())
