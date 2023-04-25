import asyncio
import os
import time
from enum import Enum
from typing import Dict

from winsdk.windows.media.control import (
    GlobalSystemMediaTransportControlsSession as Session,
    GlobalSystemMediaTransportControlsSessionManager as MediaManager,
    GlobalSystemMediaTransportControlsSessionMediaProperties as MediaProperties,
    GlobalSystemMediaTransportControlsSessionPlaybackInfo as PlaybackInfo,
    GlobalSystemMediaTransportControlsSessionPlaybackStatus as PlaybackStatus,
)

from cvr_osc_lib import OscInterface
from cvr_osc_lib.osc_messages_data import ChatBoxMessage

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


only_send_if_playing: bool = False


class AppModelId(str, Enum):
    none = 'None'
    spotify = 'Spotify.exe'
    chrome = 'chrome.exe'
    firefox = 'firefox.exe'
    vlc = 'vlc.exe'  # currently needs an addon to use windows global media thingy
    brave = 'brave.exe'

    # Default value for when not found
    @classmethod
    def _missing_(cls, value):
        return cls.none


app_color_mapping: Dict[AppModelId, str] = {
    AppModelId.none: 'FFFFFF',  # Parameter when there is no media app found or when is not mapped in AppModelId
    AppModelId.spotify: '1db954',
    AppModelId.chrome: 'e23a2e',
    AppModelId.firefox: 'FF6611',
    AppModelId.vlc: 'E85E00',
    AppModelId.brave: 'E7301C',
}

# Send prints to the console, useful if you want to see the app id to add to the AppModelId enum
debug_mode = True
########################################################################################################################


async def update_playing_info():

    manager: MediaManager = await MediaManager.request_async()
    current_session: Session = manager.get_current_session()
    if not current_session:
        return

    # Check if the session has valid playback info
    curr_playback_info: PlaybackInfo = current_session.get_playback_info()
    if curr_playback_info is None or hasattr(curr_playback_info, 'last_playback'):
        return

    # Get the playback status
    playback_status: PlaybackStatus = PlaybackStatus(curr_playback_info.playback_status)
    if playback_status is None:
        return

    # Only send info if it's playing
    if only_send_if_playing and playback_status != PlaybackStatus.PLAYING:
        return

    # Get media properties
    current_media_properties: MediaProperties = await current_session.try_get_media_properties_async()
    if current_media_properties is None:
        return

    # Parse current app
    if current_session.source_app_user_model_id is None:
        current_app = AppModelId.none
    else:
        current_app = AppModelId(current_session.source_app_user_model_id)

    app_name = str.upper(os.path.splitext(current_app.value)[0])
    playback_status = str.lower(playback_status.name)
    artist = current_media_properties.artist + '<br>'
    title = current_media_properties.title

    if debug_mode:
        print(f'{app_name=}, {playback_status=}, {artist=}, {title=}')

    message = (
        f'<b><color=#{app_color_mapping[current_app]}>{app_name}</color></b><br>'
        f'<i><color=#AAAAAA>{playback_status}</color></i><br>'
        f'{artist}'
        f'{title}'
    )

    # Send to the Chat Box
    osc.send_chat_box_message(ChatBoxMessage(
        message=message,
        send_immediately=True,
        sound_notification=False,
    ))


async def loop():
    while True:
        await update_playing_info()
        time.sleep(4)


if __name__ == '__main__':
    osc = OscInterface()

    # Start the osc interface (starts both osc sender client and listener server)
    osc.start()

    # Start Update loop
    asyncio.run(loop())

