from collections import defaultdict
from configparser import NoSectionError, RawConfigParser
from enum import Enum
from functools import partial
from time import sleep
import math
import threading
from typing import (
    Callable,
    Dict,
    Final,
    Optional,
    Union,
)

from inputs import (
    UnpluggedError,
    devices,
    get_gamepad,
)

from cvr_osc_lib import (
    OscInterface,
    PropAvailability,
    PropCreateReceive,
    PropDelete,
    PropParameter,
)

###
# Welcome to an example how to use an XBox Controller to control an RC prop, to use this script follow the steps:
#
# 1. Install the inputs module by running the following in the cmd: pip install inputs
# 2. Edit the config example_xbox_controller_rc_prop.conf to configure with your settings
# 3. Run
#
# Note: I started messed with this, but don't remember finishing... So it might be broken/missing something
#       Feel free to contact me if you want to get this working ^^
###

# Load config file
config = RawConfigParser()
config_path = 'example_xbox_controller_rc_prop.conf'
try:
    config.read(config_path)
    # Prop guid
    rc_x_wing_guid: Final[str] = config.get('config', 'prop_guid')
    # Will buttons be used as toggles
    buttons_as_toggles: Final[bool] = config.get('config', 'buttons_as_toggles').casefold() == 'true'.casefold()
    # Joystick dead zones
    joystick_dead_zone: Final[float] = float(config.get('config', 'joystick_dead_zone'))
    # debug_mode
    debug_mode: Final[bool] = config.get('config', 'debug_mode').casefold() == 'true'.casefold()
    # Control -> Parameter mapping
    control_parameter_mapping: Final[Dict[str, str]] = dict(config.items('mapping'))
except NoSectionError:
    print(f'Failed to read the section [config] from {config_path}. Check if the file exists and is valid.')
    print('Press Enter to close...')
    input()
    quit()

# Internals
# We're going to grab the instance ids from the latest created prop
midi_prop_instance_id: Optional[str] = None

# We're going to track the availability for the last instances of each prop
midi_prop_is_available: Optional[bool] = None


def on_prop_created(data: PropCreateReceive):
    global midi_prop_instance_id

    # Save the instance ids from the latest spawned prop with the corresponding guid
    if data.prop_guid == rc_x_wing_guid:
        rc_x_wing_instance_id = data.prop_instance_id

    print(f'The prop {data.prop_guid} has been spawned with the instance id {data.prop_instance_id}, and has '
          f'{data.prop_sub_sync_transform_count} sub-sync transforms!')


def on_prop_deleted(data: PropDelete):
    global midi_prop_instance_id

    # Clear the instance ids if they are the last ones and the corresponding prop is deleted
    if data.prop_guid == rc_x_wing_guid:
        rc_x_wing_instance_id = None

    print(f'The prop {data.prop_guid} with the instance id {data.prop_instance_id} has been deleted!')


def on_prop_availability_changed(data: PropAvailability):
    global midi_prop_is_available

    # Update the availability for each prop
    if data.prop_guid == rc_x_wing_guid and data.prop_instance_id == midi_prop_instance_id:
        rc_x_wing_is_available = data.prop_is_available

    print(f'The prop {data.prop_guid} with the instance id {data.prop_instance_id} is '
          f'{"now" if data.prop_is_available else "NOT"} available!')


def prop_parameter_change(data: PropParameter):
    if data.prop_guid == rc_x_wing_guid and data.prop_instance_id == midi_prop_instance_id:
        print(f'The parameter {data.prop_sync_name} has changed to the value: {data.prop_sync_value}')


class XBoxControl(str, Enum):
    LeftJoystickY = 'ABS_Y'
    LeftJoystickX = 'ABS_X'
    RightJoystickY = 'ABS_RY'
    RightJoystickX = 'ABS_RX'
    LeftTrigger = 'ABS_Z'
    RightTrigger = 'ABS_RZ'
    LeftBumper = 'BTN_TL'
    RightBumper = 'BTN_TR'
    A = 'BTN_SOUTH'
    Y = 'BTN_NORTH'  # newer controllers switched with X
    X = 'BTN_WEST'  # newer controllers switched with Y
    B = 'BTN_EAST'
    LeftThumb = 'BTN_THUMBL'
    RightThumb = 'BTN_THUMBR'
    Back = 'BTN_SELECT'
    Start = 'BTN_START'
    LeftDPad = 'BTN_TRIGGER_HAPPY1'
    RightDPad = 'BTN_TRIGGER_HAPPY2'
    UpDPad = 'BTN_TRIGGER_HAPPY3'
    DownDPad = 'BTN_TRIGGER_HAPPY4'


class XBoxControlType(Enum):
    Button = partial(lambda value: value)  # 0 for button released, 1 for button pressed
    Trigger = partial(lambda value: value / math.pow(2, 8))  # normalize between 0 and 1
    Joystick = partial(lambda value: value / math.pow(2, 15))  # normalize between -1 and 1


xbox_control_type_map: Final[Dict[XBoxControl, XBoxControlType]] = {
    # Joysticks
    XBoxControl.LeftJoystickY: XBoxControlType.Joystick,
    XBoxControl.LeftJoystickX: XBoxControlType.Joystick,
    XBoxControl.RightJoystickY: XBoxControlType.Joystick,
    XBoxControl.RightJoystickX: XBoxControlType.Joystick,
    # Triggers
    XBoxControl.LeftTrigger: XBoxControlType.Trigger,
    XBoxControl.RightTrigger: XBoxControlType.Trigger,
    # Buttons
    XBoxControl.LeftBumper: XBoxControlType.Button,
    XBoxControl.RightBumper: XBoxControlType.Button,
    XBoxControl.A: XBoxControlType.Button,
    XBoxControl.X: XBoxControlType.Button,
    XBoxControl.Y: XBoxControlType.Button,
    XBoxControl.B: XBoxControlType.Button,
    XBoxControl.LeftThumb: XBoxControlType.Button,
    XBoxControl.RightThumb: XBoxControlType.Button,
    XBoxControl.Back: XBoxControlType.Button,
    XBoxControl.Start: XBoxControlType.Button,
    XBoxControl.LeftDPad: XBoxControlType.Button,
    XBoxControl.RightDPad: XBoxControlType.Button,
    XBoxControl.UpDPad: XBoxControlType.Button,
    XBoxControl.DownDPad: XBoxControlType.Button,
}


class XboxController(object):

    def __init__(self):
        self._map: Dict[XBoxControl, Callable[[Union[int, float]], None]] = {}

        self._monitor_thread = threading.Thread(target=self._monitor_controller, args=())
        self._monitor_thread.daemon = True
        self._monitor_thread.start()

    def set_input_handler(self, xbox_ctrl: XBoxControl, handler: Callable[[Union[int, float]], None]):
        self._map[xbox_ctrl] = handler

    def _monitor_controller(self):

        device_connected = len(devices.gamepads) > 0
        if device_connected:
            print(f'Gamepad Found: {devices.gamepads[0].name} (first connected)')
        else:
            print('No gamepad found... Waiting...')

        while True:

            try:
                # Grab the events
                events = get_gamepad()

                # Send found a device msg
                if not device_connected or device_connected is None:
                    print(f'Gamepad Found: {devices.gamepads[0].name} (first connected)')
                    device_connected = True

            except UnpluggedError:
                # Send found no device msg
                if device_connected or device_connected is None:
                    print('No gamepad found... Waiting...')
                    device_connected = False

                # Ignore and wait 1 second until a gamepad is connected
                sleep(1)
                continue

            for event in events:

                # Ignore non-mapped controls
                if event.code not in XBoxControl._value2member_map_:
                    if event.code != 'SYN_REPORT' and debug_mode:
                        print(f'UNMAPED: {event.code} [{event.state}]')
                    continue

                # Get the current control
                gamepad_control: XBoxControl = XBoxControl(event.code)

                # Only call available handlers
                if gamepad_control in self._map:

                    # Parse control value using the proper control type handler
                    control_value = xbox_control_type_map[gamepad_control].value(event.state)

                    # Call handler for this control
                    self._map[gamepad_control](control_value)

            # Wait 10 ms
            sleep(0.01)


rc_prop_toggle_cache = defaultdict(lambda: 0)
rc_prop_values_cache = {}


def send_rc_prop_parameter(
        osc_interface: OscInterface,
        xbox_control: XBoxControl,
        param_value: float,
):
    # Use the enum keys for the prop parameter names
    control_name = xbox_control.name

    # process buttons as toggles
    if xbox_control_type_map[xbox_control] == XBoxControlType.Button and buttons_as_toggles:
        # Ignore the on release presses
        if param_value == 0:
            return

        # Toggle value according to the cache
        param_value = 0 if rc_prop_toggle_cache[control_name] == 1 else 1
        rc_prop_toggle_cache[control_name] = param_value

    # process joystick dead zones
    if xbox_control_type_map[xbox_control] == XBoxControlType.Joystick and abs(param_value) < joystick_dead_zone:
        param_value = 0

    # Ignore if the value is going to send is the same, otherwise update cache
    if control_name in rc_prop_values_cache and rc_prop_values_cache[control_name] == param_value:
        return
    rc_prop_values_cache[control_name] = param_value

    # Get the parameter name from the mapping
    param_name = control_parameter_mapping[control_name.lower()]

    if debug_mode:
        print(f'{control_name} control -> param: "{param_name}" value [{param_value}]')

    # Ignore if there are no ready props
    if midi_prop_instance_id is None or midi_prop_is_available is not True:
        if debug_mode:
            print(f'\tWarning: Ignoring input since no prop with guid {rc_x_wing_guid} has been found...')
        return

    # Send the parameter update
    osc_interface.send_prop_parameter(PropParameter(
        prop_guid=rc_x_wing_guid,
        prop_instance_id=midi_prop_instance_id,
        prop_sync_name=param_name,
        prop_sync_value=param_value,
    ))


def send_input_handler(osc_int, input_control: XBoxControl) -> Callable[[Union[int, float]], None]:
    def send_input_value(value: Union[int, float]):
        send_rc_prop_parameter(osc_int, input_control, value)
    return send_input_value


if __name__ == '__main__':
    osc = OscInterface()

    # Initialize the functions to react on events (needs to be set before starting the interface)

    # Listen to prop parameter changes
    osc.on_prop_parameter_changed(prop_parameter_change)
    # Listen to prop creation events (useful to get the prop id and their instance ids)
    osc.on_prop_created(on_prop_created)
    # Listen to prop deletion events (useful to know when an instance id is gone)
    osc.on_prop_deleted(on_prop_deleted)
    # Listen to prop availability changes (useful to know when you're able to send location/parameter updates)
    osc.on_prop_availability_changed(on_prop_availability_changed)

    # Start the osc interface (starts both osc sender client and listener server)
    # You can optionally not start the sender (it will be started if you attempt to send an osc msg)
    # You only need to call the start if you intend to listen to osc messages, otherwise you don't need to which will
    # keep the 9001 port free for other osc apps :) You can have multiple senders, but only 1 server bound to a port
    osc.start(start_sender=True, start_receiver=True)

    # Inform the mod that a new osc server is listening, so it resends all the cached state (if previously connected)
    osc.send_config_reset()

    # Initialize an XBox controller instance
    controller = XboxController()

    # Set up the handlers for all the xbox controls
    for control in XBoxControl:
        controller.set_input_handler(control, send_input_handler(osc, control))

    # Prevent the app from ending
    input()
