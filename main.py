import asyncio

from dbus_next.aio.message_bus import MessageBus
from dbus_next.constants import BusType
from typing import Any, cast
from dbus_next.service import (
    ServiceInterface,
    dbus_property,
)
from dbus_next.constants import PropertyAccess


unique_devices = set[str]


class App:
    def __init__(self) -> None:
        self.bus: MessageBus | None = None
        self.adapter: Any | None = None

    async def connect(self):
        self.bus = await MessageBus(
            bus_type=BusType.SYSTEM
        ).connect() # pyright: ignore[reportArgumentType]

    async def run(self):
        assert self.bus is not None

        bluez_bus_introspection = await self.bus.introspect(
            "org.bluez",
            "/",
        )

        root_object = self.bus.get_proxy_object( "org.bluez",
            "/",
            bluez_bus_introspection,
        )

        object_manager = cast(
            Any,
            root_object.get_interface("org.freedesktop.DBus.ObjectManager"),
        )

        object_manager.on_interfaces_added(
            self.interfaces_added
        )

        adapter_introspection = await self.bus.introspect(
            "org.bluez",
            "/org/bluez/hci0",
        )

        adapter_object = self.bus.get_proxy_object(
            "org.bluez",
            "/org/bluez/hci0",
            adapter_introspection,
        )
        self.adapter = cast(
            Any,
            adapter_object.get_interface("org.bluez.Adapter1"),
        )
        assert self.adapter is not None

        await self.adapter.call_start_discovery()
        print("Scanning...")

        await asyncio.Event().wait()


    def interfaces_added(self, path, interfaces):
        device = interfaces.get("org.bluez.Device1")

        if device is None:
            return

        address = device.get("Address")
        if address is None:
            return

        print(f"Found device: {address.value}")

        name = device.get("Name")

        if name is not None:
            print(f"    Name: {name.value}")

        rssi = device.get("RSSI")
        if rssi is not None:
            print(f"    RSSI: {rssi.value}")

        asyncio.create_task(self.observe_device(path, address))


    async def observe_device(self, path: str, address):
        assert self.bus is not None

        device_introspection = await self.bus.introspect(
            "org.bluez",
            path,
        )

        device_object = self.bus.get_proxy_object(
            "org.bluez",
            path,
            device_introspection,
        )

        device_properties = cast(
            Any,
            device_object.get_interface(
                "org.freedesktop.DBus.Properties"
            ),
        )

        def properties_changed(interface, changed_properties, invalidated_properties):
            if interface != "org.bluez.Device1":
                return

            rssi = changed_properties.get("RSSI")
            if rssi is None:
                return

            print(f"Update device {address.value}")
            print(f"    RSSI: {rssi.value}")


        device_properties.on_properties_changed(
            properties_changed
        )


    async def shutdown(self):
        print("Shutting down...")

        assert self.adapter is not None

        print("Stop scanning")
        await self.adapter.call_stop_discovery()


async def main():
    app = App()
    try: 
        await app.connect()
        await app.run()
    finally:
        await app.shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
