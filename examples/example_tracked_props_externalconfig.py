from time import sleep
from typing import Any, Dict, Optional
import configparser
import os
import json

from cvr_osc_lib import (
    OscInterface,
    PropAvailability,
    PropCreateReceive,
    PropDelete,
    PropLocationSub,
    PropParameter,
    TrackingDeviceData,
    TrackingDeviceStatus,
)
from cvr_osc_lib.osc_messages_data import TrackingDeviceType, TrackingViveTrackerName

#######################################################################################################################

#CONFIG FILE
# This script expects to find its config file at the path 'C:\CVR\OSC\OSC_Configs\trackers.conf' if you want to keep it
# somewhere else change the following

configFilePath = r'C:\CVR\OSC\OSC_Configs\trackers.conf'

#Example config file is `trackers.conf` found in this repo

## You should not have to make changes after this line to make the script run
#______________________________________________________________________________________________________________________

## START CONFIG LOAD

# Handle missing config file
if not os.path.exists(configFilePath):
  print(f'\nConfig file not found, please copy the example file "trackers.conf" to {configFilePath} and modify it to your needs')
  print(f'Closing in 8 seconds \n')
  sleep(8)
  quit()

# Load config file 
config = configparser.RawConfigParser()
config.read(configFilePath)

## Load GUIDs
# pull in the GUIDs from the config file 
base_stations_guid = config.get('guids', 'base_stations' )
tracker_0_2_controllers_guid = config.get('guids', 'tracker_0_2_controllers' )
tracker_3_7_guid = config.get('guids', 'tracker_3_7' )

## Load OSC connection config
osc_receive_port = int(config.get('connection', 'osc_receive_port' )) # port to listen for messages from CVR on
osc_receive_ip = str(config.get('connection', 'osc_receive_ip' )) # IP script should listen on for messages from CVR
osc_send_port = int(config.get('connection', 'osc_send_port' )) # port to send OSC messages to
osc_send_ip = str(config.get('connection', 'osc_send_ip' )) # IP of the system where CVR is running


# ### Tracker mapping
# The following loads in tracker mappings from the config file.
# The Tracker role is the steamvr config of your trackers, you can change the role there to match it to another prop
# sub-sync (for example the tracker_mapping_3_7 [4] is the one that has the bottle)
# The indexes 0-4 are the positions of the sub-sync transforms (basically the order which you added to prop descriptor)
# I only recommend changing here the role if you want to swap which tracker is which sub-sync

###
## Default prop mappings
# waist = Vive tracker 3.0
# left_foot = Tundra tracker
# right_foot = Tundra tracker
#

tracker_0_2__role__sub_sync_index: Dict[Any, int] = {
    TrackingViveTrackerName.waist.value: int(config.get('trackermappings', 'waist')), 
    TrackingViveTrackerName.left_foot.value: int(config.get('trackermappings', 'left_foot')),
    TrackingViveTrackerName.right_foot.value: int(config.get('trackermappings', 'right_foot')),
}
###
## Default prop mappings
# chest = Tundra tracker
# left_knee = Tundra tracker
# right_knee = Tundra tracker
# right_elbow = Tundra tracker
# left_elbow = Tundra tracker with bottle

tracker_3_7_mapping__role__sub_sync_index: Dict[Any, int] = {
    TrackingViveTrackerName.chest.value: int(config.get('trackermappings', 'chest')),
    TrackingViveTrackerName.left_knee.value: int(config.get('trackermappings', 'left_knee')),
    TrackingViveTrackerName.right_knee.value: int(config.get('trackermappings', 'right_knee')), 
    TrackingViveTrackerName.right_elbow.value: int(config.get('trackermappings', 'right_elbow')),
    TrackingViveTrackerName.left_elbow.value: int(config.get('trackermappings', 'left_elbow')),
}

# END CONFIG LOAD ###########################################################################################################

# print out config settings
print(f'\nLoaded config is as follows\n')
print(f'Base stations prop GUID = {base_stations_guid}' )
print(f'Trackers 0 to 2 + Controllers prop GUID = {tracker_0_2_controllers_guid}' )
print(f'Trackers 3 to 7 prop GUID = {tracker_3_7_guid}' )

print(f'\nTracker mapping configs')
print(json.dumps(tracker_0_2__role__sub_sync_index, indent=2))
print(json.dumps(tracker_3_7_mapping__role__sub_sync_index, indent=2))

sleep(2)
print(f'\nStarting main program\n-------------------\n')

# We're going to grab the instance ids from the latest created prop
base_stations_instance_id: Optional[str] = None
tracker_0_2_controllers_instance_id: Optional[str] = None
tracker_3_7_instance_id: Optional[str] = None

# We're going to track the availability for the last instances of each prop
base_stations_is_available: Optional[bool] = None
tracker_0_2_controllers_is_available: Optional[bool] = None
tracker_3_7_is_available: Optional[bool] = None

# Assign an id for each basestation based on their indexes
base_station_index_id_mapping = dict()

# Tracker connected state cache for the props
connection_status_cache: Dict[int, TrackingDeviceStatus] = dict()


def on_prop_created(data: PropCreateReceive):
    global base_stations_instance_id
    global tracker_0_2_controllers_instance_id
    global tracker_3_7_instance_id

    # Save the instance ids from the latest spawned prop with the corresponding guid
    if base_stations_guid == data.prop_guid:
        base_stations_instance_id = data.prop_instance_id
    elif tracker_0_2_controllers_guid == data.prop_guid:
        tracker_0_2_controllers_instance_id = data.prop_instance_id
    elif tracker_3_7_guid == data.prop_guid:
        tracker_3_7_instance_id = data.prop_instance_id

    update_props_connected_param()

    print(f'The prop {data.prop_guid} has been spawned with the instance id {data.prop_instance_id}, and has '
          f'{data.prop_sub_sync_transform_count} sub-sync transforms!')


def on_prop_deleted(data: PropDelete):
    global base_stations_instance_id
    global tracker_0_2_controllers_instance_id
    global tracker_3_7_instance_id

    # Clear the instance ids if they are the last ones and the corresponding prop is deleted
    if base_stations_instance_id == data.prop_instance_id:
        base_stations_instance_id = None
    elif tracker_0_2_controllers_instance_id == data.prop_instance_id:
        tracker_0_2_controllers_instance_id = None
    elif tracker_3_7_instance_id == data.prop_instance_id:
        tracker_3_7_instance_id = None

    update_props_connected_param()

    print(f'The prop {data.prop_guid} with the instance id {data.prop_instance_id} has been deleted!')


def on_prop_availability_changed(data: PropAvailability):
    global base_stations_is_available
    global tracker_0_2_controllers_is_available
    global tracker_3_7_is_available

    # Update the availability for each prop
    if data.prop_guid == base_stations_guid and data.prop_instance_id == base_stations_instance_id:
        base_stations_is_available = data.prop_is_available
    if data.prop_guid == tracker_0_2_controllers_guid and data.prop_instance_id == tracker_0_2_controllers_instance_id:
        tracker_0_2_controllers_is_available = data.prop_is_available
    if data.prop_guid == tracker_3_7_guid and data.prop_instance_id == tracker_3_7_instance_id:
        tracker_3_7_is_available = data.prop_is_available

    update_props_connected_param()

    print(f'The prop {data.prop_guid} with the instance id {data.prop_instance_id} is '
          f'{"now" if data.prop_is_available else "NOT"} available!')


def send_prop_param_status(
        prop_guid: str,
        prop_instance_id: str,
        prop_sync_name: str,
        device_is_connected: bool,
):
    is_connected_float: float = 1.0 if device_is_connected else 0.0
    osc.send_prop_parameter(PropParameter(
        prop_guid=prop_guid,
        prop_instance_id=prop_instance_id,
        prop_sync_name=prop_sync_name,
        prop_sync_value=is_connected_float,
    ))


def update_props_connected_param(device_idx: Optional[int] = None):
    statuses = connection_status_cache.values() if device_idx is None else [connection_status_cache[device_idx]]
    for data in statuses:

        # Handle base_stations prop
        if data.device_type == TrackingDeviceType.base_station \
                and base_stations_instance_id is not None \
                and base_stations_is_available:
            prop_sync_name = f'Basestation - {base_station_index_id_mapping[data.device_steam_vr_index]}'
            send_prop_param_status(
                base_stations_guid,
                base_stations_instance_id,
                prop_sync_name,
                data.device_is_connected,
            )
            continue

        # Handle trackers_0_2 & controllers prop
        if tracker_0_2_controllers_instance_id is not None and tracker_0_2_controllers_is_available:

            if data.device_type == TrackingDeviceType.left_controller:
                send_prop_param_status(
                    tracker_0_2_controllers_guid,
                    tracker_0_2_controllers_instance_id,
                    'Left Controller',
                    data.device_is_connected,
                )
                continue
            elif data.device_type == TrackingDeviceType.right_controller:
                send_prop_param_status(
                    tracker_0_2_controllers_guid,
                    tracker_0_2_controllers_instance_id,
                    'Right Controller',
                    data.device_is_connected,
                )
                continue
            elif data.device_type == TrackingDeviceType.tracker \
                    and data.device_steam_vr_name in tracker_0_2__role__sub_sync_index:
                # The name of the sync on the tracker_0_2 prop starts at index 2, but we need 0
                prop_sync_name = f'Tracker - {tracker_0_2__role__sub_sync_index[data.device_steam_vr_name] - 2 }'
                send_prop_param_status(
                    tracker_0_2_controllers_guid,
                    tracker_0_2_controllers_instance_id,
                    prop_sync_name,
                    data.device_is_connected,
                )
                continue

        # Handle trackers_3_7 prop
        if data.device_type == TrackingDeviceType.tracker \
                and tracker_3_7_instance_id is not None \
                and data.device_steam_vr_name in tracker_3_7_mapping__role__sub_sync_index:
            # The name of the sync on the tracker_3_7 prop starts at 3
            prop_sync_name = f'Tracker - {tracker_3_7_mapping__role__sub_sync_index[data.device_steam_vr_name] + 3}'
            send_prop_param_status(
                tracker_3_7_guid,
                tracker_3_7_instance_id,
                prop_sync_name,
                data.device_is_connected,
            )
            continue


def on_tracking_device_status_changed(data: TrackingDeviceStatus):

    # Assign ids to the base stations counting from 0 to <num_of_base_stations> when they connect for the first time
    if data.device_type == TrackingDeviceType.base_station \
            and data.device_steam_vr_index not in base_station_index_id_mapping:
        id_to_assign = len(base_station_index_id_mapping)
        base_station_index_id_mapping[data.device_steam_vr_index] = id_to_assign

    # Save latest device statuses
    connection_status_cache[data.device_steam_vr_index] = data

    # Update the prop connected param
    update_props_connected_param(data.device_steam_vr_index)

    print(f'Tacking device type: {data.device_type.value} named: {data.device_steam_vr_name} index: '
          f'{data.device_steam_vr_index} has been {"connected" if data.device_is_connected else "disconnected"}!')


def sdl(data: TrackingDeviceData, prop_guid, prop_instance_id, prop_sub_sync_index):
    osc.send_prop_location_sub_sync(PropLocationSub(
        prop_guid=prop_guid,
        prop_instance_id=prop_instance_id,
        prop_sub_sync_index=prop_sub_sync_index,
        prop_position=data.device_position,
        prop_euler_rotation=data.device_euler_rotation,
    ))


def on_tracking_device_data_updated(data: TrackingDeviceData):
    # Update sub-sync spawnable transforms to make them move with the trackers

    # Handle base_stations prop
    if data.device_type == TrackingDeviceType.base_station and base_stations_instance_id is not None:
        prop_sub_sync_index = base_station_index_id_mapping[data.device_steam_vr_index]
        sdl(data, base_stations_guid, base_stations_instance_id, prop_sub_sync_index)
        return

    # Handle trackers_0_2 & controllers prop
    if tracker_0_2_controllers_instance_id is not None:

        if data.device_type == TrackingDeviceType.left_controller:
            sdl(data, tracker_0_2_controllers_guid, tracker_0_2_controllers_instance_id, 0)
            return
        elif data.device_type == TrackingDeviceType.right_controller:
            sdl(data, tracker_0_2_controllers_guid, tracker_0_2_controllers_instance_id, 1)
            return
        elif data.device_type == TrackingDeviceType.tracker:
            if data.device_steam_vr_name in tracker_0_2__role__sub_sync_index:
                prop_sub_sync_index = tracker_0_2__role__sub_sync_index[data.device_steam_vr_name]
                sdl(data, tracker_0_2_controllers_guid, tracker_0_2_controllers_instance_id, prop_sub_sync_index)
                return

    # Handle trackers_3_7 prop
    if data.device_type == TrackingDeviceType.tracker and tracker_3_7_instance_id is not None and \
            data.device_steam_vr_name in tracker_3_7_mapping__role__sub_sync_index:
        prop_sub_sync_index = tracker_3_7_mapping__role__sub_sync_index[data.device_steam_vr_name]
        sdl(data, tracker_3_7_guid, tracker_3_7_instance_id, prop_sub_sync_index)

    # Commented because it's spammy af
    # print(f'Tacking device type: {data.device_type} named: {data.device_steam_vr_name} index: '
    #       f'{data.device_steam_vr_index} Location [Pos: {str(data.device_position)} '
    #       f'Rot: {str(data.device_euler_rotation)}] and Battery: {data.device_battery_percentage}')


if __name__ == '__main__':

    # Load OSC link info from config file and Initialise interface
    osc = OscInterface(osc_lib_port=osc_receive_port, osc_cvr_ip=osc_send_ip, osc_cvr_port=osc_send_port, osc_lib_ip=osc_receive_ip)

    # Initialize the functions to react on events (needs to be set before starting the interface)

    # Listen to prop creation events (useful to get the prop id and their instance ids)
    osc.on_prop_created(on_prop_created)
    # Listen to prop deletion events (useful to know when an instance id is gone)
    osc.on_prop_deleted(on_prop_deleted)
    # Listen to prop availability changes (useful to know when you're able to send location/parameter updates)
    osc.on_prop_availability_changed(on_prop_availability_changed)

    # Listen to tracked devices status changes (careful this is very spammy, every frame by default)
    osc.on_tracking_device_status_changed(on_tracking_device_status_changed)
    # Listen to tracked devices data updates (careful this is very spammy, every frame by default)
    osc.on_tracking_device_data_updated(on_tracking_device_data_updated)

    # Start the osc interface (starts both osc sender client and listener server)
    
    osc.start(start_sender=True, start_receiver=True)

    # Inform the mod that a new osc server is listening, so it resends all the cached state (if previously connected)
    osc.send_config_reset()

    sleep(2)

    # We can now wait here and listen for osc messages
    print('\n\nPress Enter to exit...')
    input()
