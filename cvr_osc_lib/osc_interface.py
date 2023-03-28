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
    AVATAR_CHANGE = '/avatar/change'
    AVATAR_PARAMETER = '/avatar/parameter'
    AVATAR_PARAMETERS_LEGACY = '/avatar/parameters/'
    INPUT = '/input/'
    PROP_CREATE = '/prop/create'
    PROP_DELETE = '/prop/delete'
    PROP_AVAILABLE = '/prop/available'
    PROP_PARAMETER = '/prop/parameter'
    PROP_LOCATION = '/prop/location'
    PROP_LOCATION_SUB = '/prop/location_sub'
    TRACKING_DEVICE_STATUS = '/tracking/device/status'
    TRACKING_DEVICE_DATA = '/tracking/device/data'
    TRACKING_PLAY_SPACE_DATA = '/tracking/play_space/data'
    CONFIG_RESET = '/config/reset'


# def osc_default_handler(address: str,
#                         *args) -> None:
#     """
#     Default handler for the OSC messages.
#     note this is only used for debugging purposes, and will spam the console

#     parameters
#     ----------
#     address : str
#         The OSC address
#     args : list
#         The OSC arguments
#     returns
#     -------
#     None
#     """
#     args_str = ''
#     for i, arg in enumerate(args):
#         args_str += f'\n\targ#{i + 1}: {arg} [{type(arg).__name__}]'
#     print(f'Received {address} {args_str}')


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
        #uncomment the following line to enable the default handler (debugging purposes only)
        # self.dispatcher.set_default_handler(osc_default_handler)

        self.osc_lib_ip = osc_lib_ip
        self.osc_lib_port = osc_lib_port
        self.osc_cvr_ip = osc_cvr_ip
        self.osc_cvr_port = osc_cvr_port
        self.print_starting_messages = True

        self.sender = None
        self.receiver = None

    def start(self,
              *,
              start_sender=True,
              start_receiver=True,
              print_starting_messages=True):
        """
        Starts the OSC sender and receiver threads.

        parameters
        ----------
        start_sender : bool, optional
            Whether to start the sender thread or not
        start_receiver : bool, optional
            Whether to start the receiver thread or not
        print_starting_messages : bool, optional
            Whether to print the starting messages or not

        returns
        -------
        None
        """

        self.print_starting_messages = print_starting_messages

        if self.sender is None and start_sender:
            self._start_sender()

        if self.receiver is None and start_receiver:
            self.receiver = BlockingOSCUDPServer((self.osc_lib_ip, self.osc_lib_port),
                                                 self.dispatcher)
            self._print_starting_message('receiver')

            # Start receiver thread
            osc_receiver_thread = threading.Thread(name='osc_server_loop',
                                                   target=lambda: self.receiver.serve_forever())
            osc_receiver_thread.daemon = True
            osc_receiver_thread.start()

    def _start_sender(self):
        self.sender = udp_client.SimpleUDPClient(self.osc_cvr_ip, self.osc_cvr_port)
        self._print_starting_message('sender')

    def _send_data(self,
                   address: str,
                   *args):
        if self.sender is None:
            self._start_sender()
        self.sender.send_message(address, args)


    def _print_starting_message(self,
                                startup_message_mode: str):
        """
        Prints the starting message, if self.print_starting_messages is True

        parameters
        ----------
        startup_message_mode : str
            The mode the library is starting in. Can be either 'sender' or 'receiver'

        returns
        -------
        None
        """
        if self.print_starting_messages:
            if startup_message_mode == 'sender':
                print(f'Starting the OSC sender... Will send messages to\
                        {self.osc_cvr_ip}:{self.osc_cvr_port}')
            elif startup_message_mode == 'receiver':
                print(f'Starting the OSC receiver... Will listen for messages from\
                        {self.osc_lib_ip}:{self.osc_lib_port}')

    def on_avatar_changed(self,
                          callback: Callable[[AvatarChangeReceive],
                          None]):
        self.dispatcher.map(
            EndpointPrefix.AVATAR_CHANGE,
            lambda address, *args: callback(AvatarChangeReceive(args[0], args[1])),
        )

    def send_avatar_change(self,
                           data: AvatarChangeSend):
        self._send_data(EndpointPrefix.AVATAR_CHANGE, data.avatar_guid)

    def on_avatar_parameter_changed(self,
                                    callback: Callable[[AvatarParameterChange],
                                    None]):
        self.dispatcher.map(
            f'{EndpointPrefix.AVATAR_PARAMETER.value}',
            lambda address, *args: callback(AvatarParameterChange(args[1], args[0])),
        )

    def send_avatar_parameter(self,
                              data: AvatarParameterChange):
        self._send_data(EndpointPrefix.AVATAR_PARAMETER, data.parameter_value, data.parameter_name)

    def on_avatar_parameter_changed_legacy(self,
                                           callback: Callable[[AvatarParameterChange],
                                           None]):
        self.dispatcher.map(
            f'{EndpointPrefix.AVATAR_PARAMETERS_LEGACY.value}*',
            lambda address, *args: callback(AvatarParameterChange(
                address[len(EndpointPrefix.AVATAR_PARAMETERS_LEGACY):],
                args[0],
            )),
        )

    def send_avatar_parameter_legacy(self,
                                     data: AvatarParameterChange):
        self._send_data(f'{EndpointPrefix.AVATAR_PARAMETERS_LEGACY.value}{data.parameter_name}',
                        data.parameter_value)

    def set_input(self,
                  data: Input):
        self._send_data(f'{EndpointPrefix.INPUT.value}{data.input_name.value}', data.input_value)

    def on_prop_created(self,
                        callback: Callable[[PropCreateReceive],
                        None]):
        self.dispatcher.map(
            EndpointPrefix.PROP_CREATE,
            lambda address, *args: callback(PropCreateReceive(args[0], args[1], args[2])),
        )

    def send_prop_create(self,
                         data: PropCreateSend):
        if data.prop_local_position is None:
            self._send_data(EndpointPrefix.PROP_CREATE, data.prop_guid)
        else:
            self._send_data(EndpointPrefix.PROP_CREATE,
                            data.prop_guid,
                            *astuple(data.prop_local_position))

    def on_prop_deleted(self,
                        callback: Callable[[PropDelete],
                        None]):
        self.dispatcher.map(
            EndpointPrefix.PROP_DELETE,
            lambda address, *args: callback(PropDelete(args[0], args[1])),
        )

    def send_prop_delete(self,
                         data: PropDelete):
        self._send_data(
            EndpointPrefix.PROP_DELETE,
            data.prop_guid,
            data.prop_instance_id,
        )

    def on_prop_availability_changed(self,
                                     callback: Callable[[PropAvailability],
                                     None]):
        self.dispatcher.map(
            EndpointPrefix.PROP_AVAILABLE,
            lambda address, *args: callback(PropAvailability(args[0], args[1], args[2])),
        )

    def on_prop_parameter_changed(self,
                                  callback: Callable[[PropParameter],
                                  None]):
        self.dispatcher.map(
            EndpointPrefix.PROP_PARAMETER,
            lambda address, *args: callback(PropParameter(args[0], args[1], args[2], args[3])),
        )

    def send_prop_parameter(self,
                            data: PropParameter):
        self._send_data(
            EndpointPrefix.PROP_PARAMETER,
            data.prop_guid,
            data.prop_instance_id,
            data.prop_sync_name,
            data.prop_sync_value,
        )

    def on_prop_location_updated(self,
                                 callback: Callable[[PropLocation],
                                 None]):
        self.dispatcher.map(
            EndpointPrefix.PROP_LOCATION,
            lambda address, *args: callback(PropLocation(
                args[0],
                args[1],
                Vector3(args[2], args[3], args[4]),
                Vector3(args[5], args[6], args[7]),
            )),
        )

    def send_prop_location(self,
                           data: PropLocation):
        self._send_data(
            EndpointPrefix.PROP_LOCATION,
            data.prop_guid,
            data.prop_instance_id,
            *astuple(data.prop_position),
            *astuple(data.prop_euler_rotation),
        )

    def on_prop_location_sub_updated(self,
                                     callback: Callable[[PropLocationSub],
                                     None]):
        self.dispatcher.map(
            EndpointPrefix.PROP_LOCATION_SUB,
            lambda address, *args: callback(PropLocationSub(
                args[0],
                args[1],
                args[2],
                Vector3(args[3], args[4], args[5]),
                Vector3(args[6], args[7], args[8]),
            )),
        )

    def send_prop_location_sub_sync(self,
                                    data: PropLocationSub):
        self._send_data(
            EndpointPrefix.PROP_LOCATION_SUB,
            data.prop_guid,
            data.prop_instance_id,
            data.prop_sub_sync_index,
            *astuple(data.prop_position),
            *astuple(data.prop_euler_rotation),
        )

    def on_tracking_play_space_data_updated(self,
                                            callback: Callable[[TrackingPlaySpaceData],
                                            None]):
        self.dispatcher.map(
            EndpointPrefix.TRACKING_PLAY_SPACE_DATA,
            lambda address, *args: callback(TrackingPlaySpaceData(
                Vector3(args[0], args[1], args[2]),
                Vector3(args[3], args[4], args[5]),
            )),
        )

    def on_tracking_device_status_changed(self,
                                          callback: Callable[[TrackingDeviceStatus],
                                          None]):
        self.dispatcher.map(
            EndpointPrefix.TRACKING_DEVICE_STATUS,
            lambda address, *args: callback(
                TrackingDeviceStatus(args[0], TrackingDeviceType[args[1]], args[2], args[3]),
            ),
        )

    def on_tracking_device_data_updated(self,
                                        callback: Callable[[TrackingDeviceData],
                                        None]):
        self.dispatcher.map(
            EndpointPrefix.TRACKING_DEVICE_DATA,
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
        """
        Send a message to CVR to reset the config.
        
        note: sending a parameter because python-osc doesn't support actual nulls,
              but it is ignored on the mod's end
        parameters
        ----------
        None
        returns
        -------
        None
        """
        self._send_data(
            EndpointPrefix.CONFIG_RESET,
            "null",
        )
