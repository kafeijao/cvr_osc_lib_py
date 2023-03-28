"""
This library is used to communicate with the CVR OSC Mod.
"""
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
    """ The OSC endpoint prefixes """
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


# def osc_default_handler(
#                     address: str,
#                     *args
# ) -> None:
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
    """ This class provides the interface to communicate with the CVR OSC Mod. """
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
        # uncomment the following line to enable the default handler (debugging purposes only)
        # self.dispatcher.set_default_handler(osc_default_handler)

        self.osc_lib_ip = osc_lib_ip
        self.osc_lib_port = osc_lib_port
        self.osc_cvr_ip = osc_cvr_ip
        self.osc_cvr_port = osc_cvr_port
        self.print_starting_messages = True

        self.sender = None
        self.receiver = None

    def start(
          self,
          *,
          start_sender=True,
          start_receiver=True,
          print_starting_messages=True
    ):
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
            self.receiver = BlockingOSCUDPServer((self.osc_lib_ip, self.osc_lib_port), self.dispatcher)
            self._print_starting_message('receiver')

            # Start receiver thread
            osc_receiver_thread = threading.Thread(name='osc_server_loop', target=lambda: self.receiver.serve_forever())
            osc_receiver_thread.daemon = True
            osc_receiver_thread.start()

    def _start_sender(self):
        self.sender = udp_client.SimpleUDPClient(self.osc_cvr_ip, self.osc_cvr_port)
        self._print_starting_message('sender')

    def _send_data(
               self,
               address: str,
               *args
    ):
        if self.sender is None:
            self._start_sender()
        self.sender.send_message(address, args)

    def _print_starting_message(
                            self,
                            startup_message_mode: str
    ):
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

    def on_avatar_changed(
                     self,
                     callback: Callable[[AvatarChangeReceive], None]
    ):
        """
        Registers a callback for the avatar change event.

        parameters
        ----------
        callback : Callable[[AvatarChangeReceive], None]
            The callback function to be called when the avatar change event is received.
            The callback function should have one parameter, which is the AvatarChangeReceive object.

        returns
        -------
        None
        """
        self.dispatcher.map(
            EndpointPrefix.avatar_change,
            lambda address, *args: callback(AvatarChangeReceive(args[0], args[1])),
        )

    def send_avatar_change(
                       self,
                       data: AvatarChangeSend
    ):
        """
        Sends an avatar change event to CVR.

        parameters
        ----------
        data : AvatarChangeSend
            The data to be sent to CVR.

        returns
        -------
        None
        """
        self._send_data(EndpointPrefix.avatar_change, data.avatar_guid)

    def on_avatar_parameter_changed(
                               self,
                               callback: Callable[[AvatarParameterChange], None]
    ):
        """
        Registers a callback for the avatar parameter change event.

        parameters
        ----------
        callback : Callable[[AvatarParameterChange], None]
            The callback function to be called when the avatar parameter change event is received.
            The callback function should have one parameter, which is the AvatarParameterChange object.

        returns
        -------
        None
        """
        self.dispatcher.map(
            f'{EndpointPrefix.avatar_parameter.value}',
            lambda address, *args: callback(AvatarParameterChange(args[1], args[0])),
        )

    def send_avatar_parameter(
                           self,
                           data: AvatarParameterChange
    ):
        """
        Sends an avatar parameter change event to CVR.

        parameters
        ----------
        data : AvatarParameterChange
            The data to be sent to CVR.

        returns
        -------
        None
        """
        self._send_data(EndpointPrefix.avatar_parameter, data.parameter_value, data.parameter_name)

    def on_avatar_parameter_changed_legacy(
                                       self,
                                       callback: Callable[[AvatarParameterChange], None]
    ):
        """
        Registers a callback for the avatar parameter change event.

        parameters
        ----------
        callback : Callable[[AvatarParameterChange], None]
            The callback function to be called when the avatar parameter change event is received.
            The callback function should have one parameter, which is the AvatarParameterChange object.

            returns
            -------
            None
            """
        self.dispatcher.map(
            f'{EndpointPrefix.avatar_parameters_legacy.value}*',
            lambda address, *args: callback(AvatarParameterChange(
                address[len(EndpointPrefix.avatar_parameters_legacy):],
                args[0],
            )),
        )

    def send_avatar_parameter_legacy(
                                 self,
                                 data: AvatarParameterChange
    ):
        """
        Sends an avatar parameter change event to CVR.

        parameters
        ----------
        data : AvatarParameterChange
            The data to be sent to CVR.

        returns
        -------
        None
        """
        self._send_data(f'{EndpointPrefix.avatar_parameters_legacy.value}{data.parameter_name}',
                        data.parameter_value)

    def set_input(
              self,
              data: Input
    ):
        """
        Sets an input value.

        parameters
        ----------
        data : Input
            The data to be sent to CVR.

        returns
        -------
        None
        """

        self._send_data(f'{EndpointPrefix.input.value}{data.input_name.value}', data.input_value)

    def on_prop_created(
                   self,
                   callback: Callable[[PropCreateReceive], None]
    ):
        """
        Registers a callback for the prop create event.

        parameters
        ----------
        callback : Callable[[PropCreateReceive], None]
            The callback function to be called when the prop create event is received.
            The callback function should have one parameter, which is the PropCreateReceive object.

        returns
        -------
        None
        """
        self.dispatcher.map(
            EndpointPrefix.prop_create,
            lambda address, *args: callback(PropCreateReceive(args[0], args[1], args[2])),
        )

    def send_prop_create(
                     self,
                     data: PropCreateSend
    ):
        """
        Sends a prop create event to CVR.

        parameters
        ----------
        data : PropCreateSend
            The data to be sent to CVR.

        returns
        -------
        None
        """
        if data.prop_local_position is None:
            self._send_data(EndpointPrefix.prop_create, data.prop_guid)
        else:
            self._send_data(EndpointPrefix.prop_create,
                            data.prop_guid,
                            *astuple(data.prop_local_position))

    def on_prop_deleted(
                    self,
                    callback: Callable[[PropDelete], None]
    ):
        """
        Registers a callback for the prop delete event.

        parameters
        ----------
        callback : Callable[[PropDelete], None]
            The callback function to be called when the prop delete event is received.
            The callback function should have one parameter,which is the PropDelete object.

        returns
        -------
        None
        """
        self.dispatcher.map(
            EndpointPrefix.PROP_DELETE,
            lambda address, *args: callback(PropDelete(args[0], args[1])),
        )

    def send_prop_delete(
                     self,
                     data: PropDelete
    ):
        """
        Sends a prop delete event to CVR.

        parameters
        ----------
        data : PropDelete
            The data to be sent to CVR.

        returns
        -------
        None
        """
        self._send_data(
            EndpointPrefix.PROP_DELETE,
            data.prop_guid,
            data.prop_instance_id,
        )

    def on_prop_availability_changed(
                                self,
                                callback: Callable[[PropAvailability], None]
    ):
        """
        Registers a callback for the prop availability change event.

        parameters
        ----------
        callback : Callable[[PropAvailability], None]
            The callback function to be called when the prop availability change event is received.
            The callback function should have one parameter, which is the PropAvailability object.

        returns
        -------
        None
        """
        self.dispatcher.map(
            EndpointPrefix.prop_available,
            lambda address, *args: callback(PropAvailability(args[0], args[1], args[2])),
        )

    def on_prop_parameter_changed(
                             self,
                             callback: Callable[[PropParameter], None]
    ):
        """
        Registers a callback for the prop parameter change event.

        parameters
        ----------
        callback : Callable[[PropParameter], None]
            The callback function to be called when the prop parameter change event is received.
            The callback function should have one parameter, which is the PropParameter object.

        returns
        -------
        None
        """
        self.dispatcher.map(
            EndpointPrefix.prop_parameter,
            lambda address, *args: callback(PropParameter(args[0], args[1], args[2], args[3])),
        )

    def send_prop_parameter(
                       self,
                       data: PropParameter
    ):
        """
        Sends a prop parameter change event to CVR.

        parameters
        ----------
        data : PropParameter
            The data to be sent to CVR.

        returns
        -------
        None
        """
        self._send_data(
            EndpointPrefix.prop_parameter,
            data.prop_guid,
            data.prop_instance_id,
            data.prop_sync_name,
            data.prop_sync_value,
        )

    def on_prop_location_updated(
                            self,
                            callback: Callable[[PropLocation], None]
    ):
        """
        Registers a callback for the prop location change event.

        parameters
        ----------
        callback : Callable[[PropLocation], None]
            The callback function to be called when the prop location change event is received.
            The callback function should have one parameter, which is the PropLocation object.

        returns
        -------
        None
        """
        self.dispatcher.map(
            EndpointPrefix.prop_location,
            lambda address, *args: callback(PropLocation(
                args[0],
                args[1],
                Vector3(args[2], args[3], args[4]),
                Vector3(args[5], args[6], args[7]),
            )),
        )

    def send_prop_location(
                       self,
                       data: PropLocation
    ):
        """
        Sends a prop location change event to CVR.

        parameters
        ----------
        data : PropLocation
            The data to be sent to CVR.

        returns
        -------
        None
        """
        self._send_data(
            EndpointPrefix.prop_location,
            data.prop_guid,
            data.prop_instance_id,
            *astuple(data.prop_position),
            *astuple(data.prop_euler_rotation),
        )

    def on_prop_location_sub_updated(
                                 self,
                                 callback: Callable[[PropLocationSub], None]
    ):
        """
        Registers a callback for the prop location sub change event.

        parameters
        ----------
        callback : Callable[[PropLocationSub], None]
            The callback function to be called when the prop location sub change event is received.
            The callback function should have one parameter, which is the PropLocationSub object.

        returns
        -------
        None
        """
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

    def send_prop_location_sub_sync(
                                self,
                                data: PropLocationSub
    ):
        """
        Sends a prop location sub sync event to CVR.

        parameters
        ----------
        data : PropLocationSub
            The data to be sent to CVR.

        returns
        -------
        None
        """
        self._send_data(
            EndpointPrefix.prop_location_sub,
            data.prop_guid,
            data.prop_instance_id,
            data.prop_sub_sync_index,
            *astuple(data.prop_position),
            *astuple(data.prop_euler_rotation),
        )

    def on_tracking_play_space_data_updated(
                                        self,
                                        callback: Callable[[TrackingPlaySpaceData], None]
    ):
        """
        Registers a callback for the tracking play space data change event.

        parameters
        ----------
        callback : Callable[[TrackingPlaySpaceData], None]
            The callback function to be called when the tracking play space data change event is received.
            The callback function should have one parameter, which is the TrackingPlaySpaceData object.

        returns
        -------
        None
        """
        self.dispatcher.map(
            EndpointPrefix.tracking_play_space_data,
            lambda address, *args: callback(TrackingPlaySpaceData(
                Vector3(args[0], args[1], args[2]),
                Vector3(args[3], args[4], args[5]),
            )),
        )

    def on_tracking_device_status_changed(
                                      self,
                                      callback: Callable[[TrackingDeviceStatus], None]
    ):
        """
        Registers a callback for the tracking device status change event.

        parameters
        ----------
        callback : Callable[[TrackingDeviceStatus], None]
            The callback function to be called when the tracking device status change event is received.
            The callback function should have one parameter, which is the TrackingDeviceStatus object.

        returns
        -------
        None
        """
        self.dispatcher.map(
            EndpointPrefix.tracking_device_status,
            lambda address, *args: callback(
                TrackingDeviceStatus(args[0], TrackingDeviceType[args[1]], args[2], args[3]),
            ),
        )

    def on_tracking_device_data_updated(
                                    self,
                                    callback: Callable[[TrackingDeviceData], None]
    ):
        """
        Registers a callback for the tracking device data change event.

        parameters
        ----------
        callback : Callable[[TrackingDeviceData], None]
            The callback function to be called when the tracking device data change event is received.
            The callback function should have one parameter, which is the TrackingDeviceData object.

        returns
        -------
        None
        """
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
        """
        Send a message to CVR to reset the config.

        note: sending a parameter because python-osc doesn't support actual nulls, but it is ignored on the mod's end
        parameters
        ----------
        None
        returns
        -------
        None
        """
        self._send_data(
            EndpointPrefix.config_reset,
            "null",
        )
