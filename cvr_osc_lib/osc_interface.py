import threading
from dataclasses import astuple
from enum import Enum
from typing import Callable

from pythonosc import udp_client
from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import BlockingOSCUDPServer

from cvr_osc_lib.osc_messages_data import (
    AvatarChangeReceive,
    AvatarChangeSend,
    AvatarParameterChange,
    Input,
    PropAvailability,
    PropCreateReceive,
    PropCreateSend,
    PropDelete,
    PropLocation,
    PropLocationSub,
    PropParameter,
    TrackingDeviceData,
    TrackingDeviceStatus,
    TrackingDeviceType,
    TrackingPlaySpaceData,
    Vector3,
)


class EndpointPrefix(str, Enum):
    avatar_change = '/avatar/change'
    avatar_parameter = '/avatar/parameter'
    avatar_parameters_legacy = '/avatar/parameters/'
    input = '/input/'
    prop_create = '/prop/create'
    prop_delete = '/prop/delete'
    prop_available = '/prop/available'
    prop_parameter = '/prop/parameter'
    prop_location = '/prop/location'
    prop_location_sub = '/prop/location_sub'
    tracking_device_status = '/tracking/device/status'
    tracking_device_data = '/tracking/device/data'
    tracking_play_space_data = '/tracking/play_space/data'
    config_reset = '/config/reset'


# def osc_default_handler(address: str, *args) -> None:
#     args_str = ''
#     for i, arg in enumerate(args):
#         args_str += f'\n\targ#{i + 1}: {arg} [{type(arg).__name__}]'
#     #print(f'Received {address} {args_str}')


class OscInterface:
    def __init__(
            self,
            osc_lib_port: int = 9001,
            osc_cvr_ip: str = '127.0.0.1',
            osc_cvr_port: int = 9000,
            *,
            osc_lib_ip: str = '127.0.0.1',
    ):
        """
        The interface class should be used to communicate with the CVR OSC Mod.

        Parameters
        ----------
        osc_lib_port : int, optional
            Port this library should listen for messages coming from CVR
        osc_cvr_ip : str, optional
            Ip address this library should send the osc messages to CVR
        osc_cvr_port : int, optional
            Port this library should send the osc messages to CVR
        osc_lib_ip : str, optional
            Ip this library should listen for messages coming from CVR
        """

        self.dispatcher: Dispatcher = Dispatcher()

        # noinspection PyTypeChecker
        # self.dispatcher.set_default_handler(osc_default_handler)

        self.osc_lib_ip = osc_lib_ip
        self.osc_lib_port = osc_lib_port
        self.osc_cvr_ip = osc_cvr_ip
        self.osc_cvr_port = osc_cvr_port

        self.sender = None
        self.receiver = None

    def start(self):
        self.sender = udp_client.SimpleUDPClient(self.osc_cvr_ip, self.osc_cvr_port)
        print(f'Starting the OSC sender... Will send messages to {self.osc_cvr_ip}:{self.osc_cvr_port}')
        self.receiver = BlockingOSCUDPServer((self.osc_lib_ip, self.osc_lib_port), self.dispatcher)
        print(f'Starting the OSC receiver... Will listen for messages from {self.osc_lib_ip}:{self.osc_lib_port}')

        # Start receiver thread
        osc_receiver_thread = threading.Thread(name='osc_server_loop', target=lambda: self.receiver.serve_forever())
        osc_receiver_thread.daemon = True
        osc_receiver_thread.start()

    def _send_data(self, address: str, *args):
        if self.sender is None:
            print('You need to call the start function on the OscInterface before sending/listening for stuff')
            return
        # print(f'Sending {address} [{args}]')
        self.sender.send_message(address, args)

    def on_avatar_changed(self, callback: Callable[[AvatarChangeReceive], None]):
        self.dispatcher.map(
            EndpointPrefix.avatar_change,
            lambda address, *args: callback(AvatarChangeReceive(args[0], args[1])),
        )

    def send_avatar_change(self, data: AvatarChangeSend):
        self._send_data(EndpointPrefix.avatar_change, data.avatar_guid)

    def on_avatar_parameter_changed(self, callback: Callable[[AvatarParameterChange], None]):
        self.dispatcher.map(
            f'{EndpointPrefix.avatar_parameter}',
            lambda address, *args: callback(AvatarParameterChange(args[1], args[0])),
        )

    def send_avatar_parameter(self, data: AvatarParameterChange):
        self._send_data(EndpointPrefix.avatar_parameter, data.parameter_value, data.parameter_name)

    def on_avatar_parameter_changed_legacy(self, callback: Callable[[AvatarParameterChange], None]):
        self.dispatcher.map(
            f'{EndpointPrefix.avatar_parameters_legacy}*',
            lambda address, *args: callback(AvatarParameterChange(
                address[len(EndpointPrefix.avatar_parameters_legacy):],
                args[0],
            )),
        )

    def send_avatar_parameter_legacy(self, data: AvatarParameterChange):
        self._send_data(f'{EndpointPrefix.avatar_parameters_legacy}{data.parameter_name}', data.parameter_value)

    def set_input(self, data: Input):
        self._send_data(f'{EndpointPrefix.input}{data.input_name.value}', data.input_value)

    def on_prop_created(self, callback: Callable[[PropCreateReceive], None]):
        self.dispatcher.map(
            EndpointPrefix.prop_create,
            lambda address, *args: callback(PropCreateReceive(args[0], args[1], args[2])),
        )

    def send_prop_create(self, data: PropCreateSend):
        if data.prop_local_position is None:
            self._send_data(EndpointPrefix.prop_create, data.prop_guid)
        else:
            self._send_data(EndpointPrefix.prop_create, data.prop_guid, *astuple(data.prop_local_position))

    def on_prop_deleted(self, callback: Callable[[PropDelete], None]):
        self.dispatcher.map(
            EndpointPrefix.prop_delete,
            lambda address, *args: callback(PropDelete(args[0], args[1])),
        )

    def send_prop_delete(self, data: PropDelete):
        self._send_data(
            EndpointPrefix.prop_delete,
            data.prop_guid,
            data.prop_instance_id,
        )

    def on_prop_availability_changed(self, callback: Callable[[PropAvailability], None]):
        self.dispatcher.map(
            EndpointPrefix.prop_available,
            lambda address, *args: callback(PropAvailability(args[0], args[1], args[2])),
        )

    def on_prop_parameter_changed(self, callback: Callable[[PropParameter], None]):
        self.dispatcher.map(
            EndpointPrefix.prop_parameter,
            lambda address, *args: callback(PropParameter(args[0], args[1], args[2], args[3])),
        )

    def send_prop_parameter(self, data: PropParameter):
        self._send_data(
            EndpointPrefix.prop_parameter,
            data.prop_guid,
            data.prop_instance_id,
            data.prop_sync_name,
            data.prop_sync_value,
        )

    def on_prop_location_updated(self, callback: Callable[[PropLocation], None]):
        self.dispatcher.map(
            EndpointPrefix.prop_location,
            lambda address, *args: callback(PropLocation(
                args[0],
                args[1],
                Vector3(args[2], args[3], args[4]),
                Vector3(args[5], args[6], args[7]),
            )),
        )

    def send_prop_location(self, data: PropLocation):
        self._send_data(
            EndpointPrefix.prop_location,
            data.prop_guid,
            data.prop_instance_id,
            *astuple(data.prop_position),
            *astuple(data.prop_euler_rotation),
        )

    def on_prop_location_sub_updated(self, callback: Callable[[PropLocationSub], None]):
        self.dispatcher.map(
            EndpointPrefix.prop_location_sub,
            lambda address, *args: callback(PropLocationSub(
                args[0],
                args[1],
                args[2],
                Vector3(args[3], args[4], args[5]),
                Vector3(args[6], args[7], args[8]),
            )),
        )

    def send_prop_location_sub_sync(self, data: PropLocationSub):
        self._send_data(
            EndpointPrefix.prop_location_sub,
            data.prop_guid,
            data.prop_instance_id,
            data.prop_sub_sync_index,
            *astuple(data.prop_position),
            *astuple(data.prop_euler_rotation),
        )

    def on_tracking_play_space_data_updated(self, callback: Callable[[TrackingPlaySpaceData], None]):
        self.dispatcher.map(
            EndpointPrefix.tracking_play_space_data,
            lambda address, *args: callback(TrackingPlaySpaceData(
                Vector3(args[0], args[1], args[2]),
                Vector3(args[3], args[4], args[5]),
            )),
        )

    def on_tracking_device_status_changed(self, callback: Callable[[TrackingDeviceStatus], None]):
        self.dispatcher.map(
            EndpointPrefix.tracking_device_status,
            lambda address, *args: callback(
                TrackingDeviceStatus(args[0], TrackingDeviceType[args[1]], args[2], args[3]),
            ),
        )

    def on_tracking_device_data_updated(self, callback: Callable[[TrackingDeviceData], None]):
        self.dispatcher.map(
            EndpointPrefix.tracking_device_data,
            lambda address, *args: callback(TrackingDeviceData(
                TrackingDeviceType[args[0]],
                args[1],
                args[2],
                Vector3(args[3], args[4], args[5]),
                Vector3(args[6], args[7], args[8]),
                args[9],
            )),
        )

    def send_config_reset(self):
        self._send_data(
            EndpointPrefix.config_reset,
            "null",  # sending a parameter because python-osc doesn't support actual nulls. But it is ignored on the mod
        )
