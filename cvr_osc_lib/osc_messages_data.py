"""Module to define the OSC messages data classes."""
# Disable all the UPPER_CASE violations detections in this file as
#  there are already too many scripts using this convention,
#  to interface with this library and it would cause too much
#  inconvenience for others if the names were changed.
# pylint: disable=invalid-name

import dataclasses
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Union


class InputName(str, Enum):
    """Class to represent the input names."""
    # AXIS

    horizontal = 'Horizontal',
    vertical = 'Vertical'
    look_horizontal = 'LookHorizontal'

    # == = Waiting for features == =
    # UseAxisRight,
    # GrabAxisRight,
    move_hold_fb = 'MoveHoldFB',
    # SpinHoldCwCcw,
    # SpinHoldUD,
    # SpinHoldLR,

    # == = New == =
    look_vertical = 'LookVertical'
    grip_left_value = 'GripLeftValue'
    grip_right_value = 'GripRightValue'

    # BUTTONS

    move_forward = 'MoveForward'
    move_backward = 'MoveBackward'
    move_left = 'MoveLeft'
    move_right = 'MoveRight'
    look_left = 'LookLeft'
    look_right = 'LookRight'
    jump = 'Jump'
    run = 'Run'
    comfort_left = 'ComfortLeft'
    comfort_right = 'ComfortRight'
    drop_right = 'DropRight'
    use_right = 'UseRight'
    grab_right = 'GrabRight'
    drop_left = 'DropLeft'
    use_left = 'UseLeft'
    grab_left = 'GrabLeft'
    panic_button = 'PanicButton'
    quick_menu_toggle_left = 'QuickMenuToggleLeft'
    quick_menu_toggle_right = 'QuickMenuToggleRight'
    voice = 'Voice'

    # == = New == ='
    crouch = 'Crouch'
    prone = 'Prone'
    independent_head_turn = 'IndependentHeadTurn'
    zoom = 'Zoom'
    reload = 'Reload'
    toggle_nameplates = 'ToggleNameplates'
    toggle_hud = 'ToggleHUD'
    switch_mode = 'SwitchMode'
    toggle_flight_mode = 'ToggleFlightMode'
    respawn = 'Respawn'
    toggle_camera = 'ToggleCamera'
    toggle_seated = 'ToggleSeated'
    quit_game = 'QuitGame'

    # VALUES

    # == = New == =
    emote = 'Emote'
    gesture_left = 'GestureLeft'
    gesture_right = 'GestureRight'
    toggle = 'Toggle'


class TrackingDeviceType(str, Enum):
    """Class to represent the tracking device types."""
    hmd = 'hmd'
    base_station = 'base_station'
    left_controller = 'left_controller'
    right_controller = 'right_controller'
    tracker = 'tracker'
    unknown = 'unknown'


class TrackingViveTrackerName(str, Enum):
    """Class to represent the vive tracker names."""
    disabled = 'vive_tracker'
    held_in_hand = 'vive_tracker_handed'
    camera = 'vive_tracker_camera'
    keyboard = 'vive_tracker_keyboard'

    left_foot = 'vive_tracker_left_foot'
    right_foot = 'vive_tracker_right_foot'

    left_shoulder = 'vive_tracker_left_shoulder'
    right_shoulder = 'vive_tracker_right_shoulder'

    left_elbow = 'vive_tracker_left_elbow'
    right_elbow = 'vive_tracker_right_elbow'

    left_knee = 'vive_tracker_left_knee'
    right_knee = 'vive_tracker_right_knee'

    waist = 'vive_tracker_waist'
    chest = 'vive_tracker_chest'


@dataclass
class Vector3:
    """Class to represent a Vector with 3 floats."""
    x: float
    y: float
    z: float

    def __str__(self):
        return f'({", ".join("{:.4f}".format(getattr(self, field.name)) for field in dataclasses.fields(self))})'


@dataclass
class AvatarChangeSend:
    """Class to represent an avatar change data to send."""
    avatar_guid: str


@dataclass
class AvatarChangeReceive:
    """Class to represent an avatar change event data that will receive."""
    avatar_guid: str
    avatar_json_config_path: str


@dataclass
class AvatarParameterChange:
    """Class to represent an avatar parameter change event data."""
    parameter_name: str
    parameter_value: Optional[Union[int, float, bool]]


@dataclass
class Input:
    """Class to represent an input event data."""
    input_name: InputName
    input_value: Union[int, float, bool]


@dataclass
class PropCreateSend:
    """Class to represent a prop creation required data."""
    prop_guid: str
    prop_local_position: Optional[Vector3] = None


@dataclass
class PropCreateReceive:
    """Class to represent a prop created event data."""
    prop_guid: str
    prop_instance_id: str
    prop_sub_sync_transform_count: int


@dataclass
class PropDelete:
    """Class to represent a prop deletion event data."""
    prop_guid: str
    prop_instance_id: str


@dataclass
class PropAvailability:
    """Class to represent a prop availability event data."""
    prop_guid: str
    prop_instance_id: str
    prop_is_available: bool


@dataclass
class PropParameter:
    """Class to represent a prop parameter change event data."""
    prop_guid: str
    prop_instance_id: str
    prop_sync_name: str
    prop_sync_value: float


@dataclass
class PropLocation:
    """Class to represent a prop location change event data."""
    prop_guid: str
    prop_instance_id: str
    prop_position: Optional[Vector3] = None
    prop_euler_rotation: Optional[Vector3] = None


@dataclass
class PropLocationSub:
    """Class to represent a prop sub sync location change event data."""
    prop_guid: str
    prop_instance_id: str
    prop_sub_sync_index: int
    prop_position: Optional[Vector3] = None
    prop_euler_rotation: Optional[Vector3] = None


@dataclass
class TrackingPlaySpaceData:
    """Class to represent a play space tracking update event data."""
    play_space_position: Optional[Vector3] = None
    play_space_euler_rotation: Optional[Vector3] = None


@dataclass
class TrackingDeviceStatus:
    """Class to represent a device tracking status event data."""
    device_is_connected: bool
    device_type: TrackingDeviceType
    device_steam_vr_index: int
    device_steam_vr_name: str


@dataclass
class TrackingDeviceData:
    """Class to represent a device tracking update event data."""
    device_type: TrackingDeviceType
    device_steam_vr_index: int
    device_steam_vr_name: str
    device_position: Optional[Vector3] = None
    device_euler_rotation: Optional[Vector3] = None
    device_battery_percentage: float = 0.0
