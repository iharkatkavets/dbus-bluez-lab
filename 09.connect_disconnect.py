import asyncio

from dbus_next.aio.message_bus import MessageBus
from dbus_next.constants import BusType
from typing import Any, cast

import argparse


BLUEZ_SERVICE_NAME = "org.bluez"
DEVICE_INTERFACE  = "org.bluez.Device1"
ADAPTER_PATH_ID = "/org/bluez/hci0"


class App:
    def __init__(self, name: str, mac: str) -> None:
        self.bus: MessageBus | None = None
        self.object_manager: Any | None = None
        self.adapter: Any | None = None
        self.device: Any | None = None
        self.name: str | None = name
        self.mac: str | None = mac


    async def connect_bus(self):
        self.bus = await MessageBus(
            bus_type=BusType.SYSTEM
        ).connect() # pyright: ignore[reportArgumentType]


    async def run(self):
        assert self.bus is not None
        bluez_bus_introspection = await self.bus.introspect(
            BLUEZ_SERVICE_NAME,
            "/",
        )

        root_object = self.bus.get_proxy_object( 
            BLUEZ_SERVICE_NAME,
            "/",
            bluez_bus_introspection,
        )

        self.object_manager = cast(
            Any,
            root_object.get_interface("org.freedesktop.DBus.ObjectManager"),
        )

        assert self.object_manager is not None
        objects = await self.object_manager.call_get_managed_objects()
        for _, interfaces in objects.items():
            if DEVICE_INTERFACE not in interfaces:
                continue

            properties = interfaces[DEVICE_INTERFACE]
            address = properties.get("Address")
            name = properties.get("Name")
            if address is None or name is None:
                continue

            if name.value == self.name or address.value == self.mac:
                await self.connect_device(address.value)

        self.object_manager.on_interfaces_added(
            self.interfaces_added
        )

        adapter_introspection = await self.bus.introspect(
            BLUEZ_SERVICE_NAME,
            ADAPTER_PATH_ID,
        )

        adapter_object = self.bus.get_proxy_object(
            BLUEZ_SERVICE_NAME,
            ADAPTER_PATH_ID,
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


    async def connect_device(self, mac: str):
        path = device_path(mac)

        assert self.bus is not None
        device_introspection = await self.bus.introspect(
            BLUEZ_SERVICE_NAME,
            path,
        )

        device_object = self.bus.get_proxy_object(
            BLUEZ_SERVICE_NAME,
            path,
            device_introspection,
        )

        self.device = cast(
            Any,
            device_object.get_interface(DEVICE_INTERFACE),
        )

        print(f"Connecting {mac}...")
        assert self.device is not None
        await self.device.call_connect()
        print("Connected")

        await asyncio.Event().wait()


    def interfaces_added(self, _, interfaces):
        device = interfaces.get("org.bluez.Device1")

        if device is None:
            return

        address = device.get("Address")
        name = device.get("Name")
        if address is None or name is None:
            return

        if name.value == self.name or address.value == self.mac:
            asyncio.create_task(self.connect_device(address.value))


    async def shutdown(self):
        print("Disconnecting...")
        if self.device is not None:
            await self.device.call_disconnect()


def device_path(mac: str) -> str:
    return f"{ADAPTER_PATH_ID}/dev_{mac.replace(':', '_')}"


async def main():
    parser = argparse.ArgumentParser(
        description="iPiLink Bluetooth client"
    )
    parser.add_argument(
        "--mac",
        required=False,
        help="Bluetooth device MAC address",
    )
    parser.add_argument(
        "--name",
        required=False,
        help="Bluetooth device name",
    )
    args = parser.parse_args()
    if not args.mac and not args.name:
        parser.error("one of --mac or --name is required")

    app = App(args.name, args.mac)
    try: 
        await app.connect_bus()
        await app.run()
    finally:
        await app.shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
