import asyncio
from enum import Enum
from typing import Dict

from winsdk.windows.media.control import (
    GlobalSystemMediaTransportControlsSessionManager as MediaManager,
    GlobalSystemMediaTransportControlsSessionPlaybackStatus as PlaybackStatus,
)

from cvr_osc_lib import OscInterface, AvatarParameterChange


###
# Welcome to an example how to feet the windows global media info into OSC
# This uses the winsdk package, so before you use this you need to install it with the command:
#
# pip install winsdk
#
###

# ### Config ###########################################################################################################
# Possible apps (feel free to add more) use debug_mode = True to find the app ids
# If you add don't forget to map to the parameter_app_mapping as well
class AppModelId(str, Enum):
    none = 'None'
    spotify = 'Spotify.exe'
    chrome = 'chrome.exe'
    firefox = 'firefox.exe'
    vlc = 'vlc.exe'  # currently needs an addon to use windows global media thingy

    # Default value for when not found
    @classmethod
    def _missing_(cls, value):
        return cls.none


# Possible Apps, change the integers to correspond to the animator parameter values you want to be sent for each app
parameter_app_mapping: Dict[AppModelId, int] = {
    AppModelId.none: 0,  # Parameter when there is no media app found or when is not mapped in AppModelId
    AppModelId.spotify: 1,
    AppModelId.chrome: 2,
    AppModelId.firefox: 3,
    AppModelId.vlc: 4,
}

# Possible playback status parameter mapping, change the integers to match the parameters being sent for each state
# learn.microsoft.com/en-us/uwp/api/windows.media.control.globalsystemmediatransportcontrolssessionplaybackstatus
# Note: Some apps completely bork this, so enable debug mode and test to see its behavior
parameter_status_mapping: Dict[PlaybackStatus, int] = {
    PlaybackStatus.CLOSED: 0,
    PlaybackStatus.OPENED: 1,
    PlaybackStatus.CHANGING: 2,
    PlaybackStatus.STOPPED: 3,
    PlaybackStatus.PLAYING: 4,
    PlaybackStatus.PAUSED: 5,
}

# Parameter names
parameter_name_playback_app = 'osc_playback_app'
parameter_name_playback_status = 'osc_playback_status'

# Send prints to the console, useful if you want to see the app id to add to the AppModelId enum
debug_mode = True
########################################################################################################################


session = None
playback_info = None
playback_change_listener_token = None


def on_invalid_session():
    global playback_info

    if playback_info != PlaybackStatus.CLOSED:
        playback_info = PlaybackStatus.CLOSED
    if debug_mode:
        print(f'\t[Playback Info] Status: {playback_info.name}')

    osc.send_avatar_parameter(AvatarParameterChange(
        parameter_name=parameter_name_playback_status,
        parameter_value=parameter_status_mapping[playback_info],
    ))


def on_current_playback_info_changed(*args):
    global playback_info

    # Check if there is a session
    if session is None:
        on_invalid_session()
        return

    # Check if the session has valid playback info
    curr_playback_info = session.get_playback_info()
    if curr_playback_info is None or hasattr(curr_playback_info, 'last_playback'):
        on_invalid_session()
        return

    # Update the playback status
    curr_playback_info_status = PlaybackStatus(curr_playback_info.playback_status)

    # Prevent state change if changed into the same state
    if curr_playback_info_status != playback_info:
        if debug_mode:
            print(f'\t[Playback Info] Status: {curr_playback_info_status.name}')

        osc.send_avatar_parameter(AvatarParameterChange(
            parameter_name=parameter_name_playback_status,
            parameter_value=parameter_status_mapping[curr_playback_info_status],
        ))

    playback_info = curr_playback_info_status


def on_current_session_changed(manager, *args):
    global session
    global playback_change_listener_token

    # Get current session
    current_session = manager.get_current_session()

    if session is not None:
        # If the session didn't change just ignore
        if session == current_session:
            return

        # Remove listener from old session
        if playback_change_listener_token is not None:
            session.remove_playback_info_changed(playback_change_listener_token)

    # If we got a valid session, lets set up the listener for playback changes
    if current_session:
        # Add listener for playback info change and save the listener token
        session = current_session
        playback_change_listener_token = current_session.add_playback_info_changed(on_current_playback_info_changed)

        if debug_mode:
            print(f'[Session] Session changed to target app: {current_session.source_app_user_model_id}')

        osc.send_avatar_parameter(AvatarParameterChange(
            parameter_name=parameter_name_playback_app,
            parameter_value=parameter_app_mapping[AppModelId(current_session.source_app_user_model_id)],
        ))

        # Since we changed session, lets poll the current playback info
        on_current_playback_info_changed()

    # There is no session (and we haven't set it to None)
    elif session is not None:
        session = None
        if debug_mode:
            print('[Session] No session available :(')

        osc.send_avatar_parameter(AvatarParameterChange(
            parameter_name=parameter_name_playback_app,
            parameter_value=parameter_app_mapping[AppModelId.none],
        ))

        # Since we changed session, lets poll the current playback info
        on_current_playback_info_changed()


async def debug_check_all_sessions():
    # Debug script to check all the current sessions and if they are being closed/opened
    manager = await MediaManager.request_async()

    sessions = {}
    while True:
        curr_sessions = manager.get_sessions()
        curr_sessions_apps = [c.source_app_user_model_id for c in curr_sessions]

        # Check for removed apps
        to_delete = []
        for prev_sessions_app in sessions.keys():
            if prev_sessions_app not in curr_sessions_apps:
                to_delete.append(prev_sessions_app)
                new_session_kys = list(sessions.keys())
                new_session_kys.remove(prev_sessions_app)
                print(f'\nApp {prev_sessions_app} was removed! \n\tCurrent_Sessions: {", ".join(new_session_kys)}')
        for d in to_delete:
            del sessions[d]

        # Check for additions
        for curr_session in curr_sessions:
            if not curr_session:
                continue

            if curr_session.source_app_user_model_id not in sessions.keys():
                sessions[curr_session.source_app_user_model_id] = curr_session
                print(
                    f'\nAdded {curr_session.source_app_user_model_id} to sessions! '
                    f'\n\tCurrent_Sessions: {", ".join(sessions.keys())}'
                )


async def start_manager_listener():
    manager = await MediaManager.request_async()

    # Initialize the listener
    manager.add_current_session_changed(lambda *args: on_current_session_changed(manager, *args))

    # Fetch the current session
    on_current_session_changed(manager)


if __name__ == '__main__':
    osc = OscInterface()

    # Start the osc interface (starts both osc sender client and listener server)
    osc.start()

    # Start winsdk listener
    print('Starting winsdk session change listener...')
    asyncio.run(start_manager_listener())

    # Don't let the program end
    input()
