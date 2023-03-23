import sys
from time import sleep
from typing import Optional

from cvr_osc_lib import (
    AvatarChangeReceive,
    AvatarChangeSend,
    AvatarParameterChange,
    Input,
    InputName,
    OscInterface,
    PropAvailability,
    PropCreateReceive,
    PropCreateSend,
    PropDelete,
    PropLocation,
    PropLocationSub,
    PropParameter,
    TrackingDeviceData,
    TrackingDeviceStatus,
    TrackingPlaySpaceData,
    Vector3,
)

###
# Welcome to an example how to use this half ass wrapper.
# We'll go through all the commands you can send (and listen) in this script.
# Feel free to uncomment some listeners if you want to see their output, but be warned, some of those are crazy spammy
# Also if you want this to run smoothly for you, you need to edit the configuration on the bottom, unfortunately I can't
# leave there prop ids that would just work, because there's no way to make public props (yet), so you need to configure
# it for your props.
###

# CONFIG ###############################################################################################################
# Change this guid to a prop that the root object is visible, so we can test moving it.
prop_root_visible_guid = '1aa10cac-36ba-4e00-b48d-a76dc37f61bb'
# Name of the sync parameter (the one you set on the spawnable script, not the one in the animator)
prop_root_visible_sync_param_name = 'IsOn'
prop_root_visible_sync_param_value_to_set = 1.0

# Change this guid to a prop you own and has sub-sync transforms, so we test moving a sub-sync transform.
prop_with_sub_sync_guid = '33807561-c701-470c-abbe-43da89d35cae'
# Name of the sync parameter (the one you set on the spawnable script, not the one in the animator)
prop_with_sub_sync_sync_param_name = '1 - Basestation'
prop_with_sub_sync_sync_param_value_to_set = 1.0
# Which sub-sync transform you want to move, it follows the oder you set in the spawnable component, where 0 is the
# first one.
prop_with_sub_sync_index = 0
# END CONFIG ###########################################################################################################

# These will be filled in the prop creation listener
prop_root_visible_instance_id: Optional[str] = None
prop_with_sub_sync_instance_id: Optional[str] = None

# These will be filled in the play space tracking updates
tracking_play_space_pos: Optional[Vector3] = None
tracking_play_space_rot: Optional[Vector3] = None


def avatar_change(data: AvatarChangeReceive):
    print(f'Changed to an avatar with the id: {data.avatar_guid}, and the json config is '
          f'located at: {data.avatar_json_config_path}')


def avatar_parameter_change(data: AvatarParameterChange):
    print(f'The parameter {data.parameter_name} has changed to the value: {data.parameter_value}')


def on_prop_created(data: PropCreateReceive):
    global prop_root_visible_instance_id
    global prop_with_sub_sync_instance_id

    if prop_root_visible_guid == data.prop_guid:
        prop_root_visible_instance_id = data.prop_instance_id
    elif prop_with_sub_sync_guid == data.prop_guid:
        prop_with_sub_sync_instance_id = data.prop_instance_id

    print(f'The prop {data.prop_guid} has been spawned with the instance id {data.prop_instance_id}, and has '
          f'{data.prop_sub_sync_transform_count} sub-sync transforms!')


def on_prop_deleted(data: PropDelete):
    global prop_root_visible_instance_id
    global prop_with_sub_sync_instance_id

    if prop_root_visible_instance_id == data.prop_instance_id:
        prop_root_visible_instance_id = None
    elif prop_with_sub_sync_instance_id == data.prop_instance_id:
        prop_with_sub_sync_instance_id = None

    print(f'The prop {data.prop_guid} with the instance id {data.prop_instance_id} has been deleted!')


def on_prop_availability_changed(data: PropAvailability):
    print(f'The prop {data.prop_guid} with the instance id {data.prop_instance_id} is '
          f'{"now" if data.prop_is_available else "NOT"} available!')


def on_prop_parameter_changed(data: PropParameter):
    print(f'The prop {data.prop_guid} with the instance id {data.prop_instance_id} has changed the '
          f'{data.prop_sync_name} parameter to {data.prop_sync_value}')


def on_prop_location_updated(data: PropLocation):
    # Commented because it's spammy af
    # print(f'The prop p+{data.prop_guid}~{data.prop_instance_id} location is Pos: {str(data.prop_position)} '
    #       f'Rot: {str(data.prop_euler_rotation)}')
    pass


def on_prop_location_sub_updated(data: PropLocationSub):
    # Commented because it's spammy af
    # print(f'The prop p+{data.prop_guid}~{data.prop_instance_id} sub-sync[{data.prop_sub_sync_index}] location is '
    #       f'Pos: {str(data.prop_position)} Rot: {str(data.prop_euler_rotation)}')
    pass


def on_tracking_play_space_data_updated(data: TrackingPlaySpaceData):
    global tracking_play_space_pos
    global tracking_play_space_rot
    tracking_play_space_pos = data.play_space_position
    tracking_play_space_rot = data.play_space_euler_rotation
    # Commented because it's spammy af
    # print(f'Play Space location is Pos: {str(data.play_space_position)} Rot: {str(data.play_space_euler_rotation)}')


def on_tracking_device_status_changed(data: TrackingDeviceStatus):
    print(f'Tacking device type: {data.device_type} named: {data.device_steam_vr_name} index: '
          f'{data.device_steam_vr_index} has been {"connected" if data.device_is_connected else "disconnected"}!')


def on_tracking_device_data_updated(data: TrackingDeviceData):
    # Commented because it's spammy af
    # print(f'Tracking device type: {data.device_type} named: {data.device_steam_vr_name} index: '
    #       f'{data.device_steam_vr_index} Location [Pos: {str(data.device_position)} '
    #       f'Rot: {str(data.device_euler_rotation)}] and Battery: {data.device_battery_percentage}')
    pass


if __name__ == '__main__':
    osc = OscInterface()

    # Initialize the functions to react on events (needs to be set before starting the interface)

    # Listen to avatar changes (useful to get the avatar guid)
    osc.on_avatar_changed(avatar_change)
    # Listen to avatar parameter changes
    osc.on_avatar_parameter_changed(avatar_parameter_change)

    # Listen to prop creation events (useful to get the prop id and their instance ids)
    osc.on_prop_created(on_prop_created)
    # Listen to prop deletion events (useful to know when an instance id is gone)
    osc.on_prop_deleted(on_prop_deleted)
    # Listen to prop availability changes (useful to know when you're able to send location/parameter updates)
    osc.on_prop_availability_changed(on_prop_availability_changed)
    # Listen to prop parameter changes
    osc.on_prop_parameter_changed(on_prop_parameter_changed)
    # Listen to prop location updates (careful this is very spammy, every frame by default)
    osc.on_prop_location_updated(on_prop_location_updated)
    # Listen to prop sub-sync location updates (careful this is very spammy, every frame by default)
    osc.on_prop_location_sub_updated(on_prop_location_sub_updated)

    # Listen to play space location updates (careful this is very spammy, every frame by default)
    osc.on_tracking_play_space_data_updated(on_tracking_play_space_data_updated)
    # Listen to tracked devices status changes (careful this is very spammy, every frame by default)
    osc.on_tracking_device_status_changed(on_tracking_device_status_changed)
    # Listen to tracked devices data updates (careful this is very spammy, every frame by default)
    osc.on_tracking_device_data_updated(on_tracking_device_data_updated)

    # Start the osc interface (starts both osc sender client and listener server)
    # You can optionally not start the sender (it will be started if you attempt to send an osc msg)
    # You only need to call the start if you intend to listen to osc messages, otherwise you don't need to which will
    # keep the 9001 port free for other osc apps :) You can have multiple senders, but only 1 server bound to a port
    osc.start(start_sender=True, start_receiver=True)

    # Inform the mod that a new osc server is listening, so it resends all the cached state (if previously connected)
    osc.send_config_reset()

    # During this script I will have a bunch of waits to let the mod execute the commands and send back the responses
    # This way the logs in the console will look in a more understandable order
    # DO NOT USE SLEEPS WHEN WRITING YOUR CODE! This is just for the showcase
    sleep(1)

    # Start sending OSC commands (needs to be done after the interface is started)

    # Change avatar to a certain avatar ID
    print('\n\nPress Enter to change to the robot avatar...')
    input()
    osc.send_avatar_change(AvatarChangeSend(avatar_guid='6b86cced-e17c-4f57-8bdf-812615773ce6'))
    sleep(1)

    print('\n\nPress Enter to change color to red...')
    input()
    osc.send_avatar_parameter(AvatarParameterChange(parameter_name='MainColor-r', parameter_value=1.0))
    osc.send_avatar_parameter(AvatarParameterChange(parameter_name='MainColor-g', parameter_value=0.0))
    osc.send_avatar_parameter(AvatarParameterChange(parameter_name='MainColor-b', parameter_value=0.0))
    sleep(.1)

    print('\n\nPress Enter to change color to blue...')
    input()
    osc.send_avatar_parameter_legacy(AvatarParameterChange(parameter_name='MainColor-r', parameter_value=0.0))
    osc.send_avatar_parameter_legacy(AvatarParameterChange(parameter_name='MainColor-g', parameter_value=0.0))
    osc.send_avatar_parameter_legacy(AvatarParameterChange(parameter_name='MainColor-b', parameter_value=1.0))
    sleep(.1)

    print('\n\nLook to the right for 2 seconds...')
    input()
    osc.set_input(Input(input_name=InputName.look_right, input_value=1))
    sleep(2)
    osc.set_input(Input(input_name=InputName.look_right, input_value=0))
    sleep(.1)

    print('\n\nSpawn the prop X with a visible root while providing a location...')
    input()
    osc.send_prop_create(PropCreateSend(
        prop_guid=prop_root_visible_guid,
        prop_local_position=Vector3(x=0.0, y=1.0, z=1.0),
    ))
    sleep(2)

    if prop_root_visible_instance_id is None:
        print(f'\n\n[Error] Failed to spawn the prop {prop_root_visible_guid}, try again maybe?...')
        sys.exit()

    print('\n\nSpawn the prop Y with sub-sync transforms, without providing the spawning location...')
    input()
    osc.send_prop_create(PropCreateSend(prop_guid=prop_with_sub_sync_guid))
    sleep(1)

    if prop_root_visible_instance_id is None:
        print(f'\n\n[Error] Failed to spawn the prop {prop_with_sub_sync_guid}, try again maybe?...')
        sys.exit()

    print('\n\nChange the sync of the lightsaber prop "IsOn" to 1...')
    input()
    osc.send_prop_parameter(PropParameter(
        prop_guid=prop_root_visible_guid,
        prop_instance_id=prop_root_visible_instance_id,
        prop_sync_name=prop_root_visible_sync_param_name,
        prop_sync_value=prop_root_visible_sync_param_value_to_set,
    ))
    sleep(1)

    print('\n\nChange the sync of the basestation prop "1 - Basestation" to 1...')
    input()
    osc.send_prop_parameter(PropParameter(
        prop_guid=prop_with_sub_sync_guid,
        prop_instance_id=prop_with_sub_sync_instance_id,
        prop_sync_name=prop_with_sub_sync_sync_param_name,
        prop_sync_value=prop_with_sub_sync_sync_param_value_to_set,
    ))
    sleep(1)

    print('\n\nChange the location of the lightsaber prop to our play space location...')
    input()
    osc.send_prop_location(PropLocation(
        prop_guid=prop_root_visible_guid,
        prop_instance_id=prop_root_visible_instance_id,
        prop_position=tracking_play_space_pos,
        prop_euler_rotation=tracking_play_space_rot,
    ))
    sleep(1)

    print('\n\nChange the location of the sub-sync 1 basestation prop to our play space location...')
    input()
    osc.send_prop_location_sub_sync(PropLocationSub(
        prop_guid=prop_with_sub_sync_guid,
        prop_instance_id=prop_with_sub_sync_instance_id,
        prop_sub_sync_index=prop_with_sub_sync_index,
        prop_position=tracking_play_space_pos,
        prop_euler_rotation=tracking_play_space_rot,
    ))
    sleep(1)

    print('\n\nDelete the lightsaber prop...')
    input()
    osc.send_prop_delete(
        PropDelete(prop_guid=prop_root_visible_guid, prop_instance_id=prop_root_visible_instance_id),
    )
    sleep(1)

    print('\n\nDelete the basestation prop...')
    input()
    osc.send_prop_delete(
        PropDelete(prop_guid=prop_with_sub_sync_guid, prop_instance_id=prop_with_sub_sync_instance_id),
    )
    sleep(1)

    # We can now wait here and listen for osc messages
    print('\n\nPress Enter to exit...')
    input()
