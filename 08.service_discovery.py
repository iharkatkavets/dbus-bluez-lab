import asyncio

from dbus_next.aio.message_bus import MessageBus
from dbus_next.constants import BusType
from typing import Any, cast


BLUEZ_SERVICE_NAME = "org.bluez"
DEVICE_INTERFACE  = "org.bluez.Device1"
ADAPTER_PATH_ID = "/org/bluez/hci0"


unique_devices = set[str]


class App:
    def __init__(self) -> None:
        self.bus: MessageBus | None = None
        self.object_manager: Any | None = None
        self.adapter: Any | None = None


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
        for path, interfaces in objects.items():
            if DEVICE_INTERFACE not in interfaces:
                continue

            properties = interfaces[DEVICE_INTERFACE]
            print("Existent device:", path)

            for name, value in properties.items():
                print(name, value.value)
            print("----------------")

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


    def interfaces_added(self, path, interfaces):
        device = interfaces.get(DEVICE_INTERFACE)

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

        print("----------------")

        asyncio.create_task(self.observe_device(path, address))


    async def observe_device(self, path: str, address):
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

        device_properties = cast(
            Any,
            device_object.get_interface(
                "org.freedesktop.DBus.Properties"
            ),
        )

        def properties_changed(interface, changed_properties, invalidated_properties):
            if interface != DEVICE_INTERFACE:
                return

            print(f"Update device {address.value}")

            for name, value in changed_properties.items():
                print(f"    {name}: {value.value}")

            print("----------------")


        device_properties.on_properties_changed(
            properties_changed
        )


    async def shutdown(self):
        print("Stop scanning...")
        assert self.adapter is not None
        await self.adapter.call_stop_discovery()

        assert self.object_manager is not None
        self.object_manager.off_interfaces_added(
            self.interfaces_added
        )


async def main():
    app = App()
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
