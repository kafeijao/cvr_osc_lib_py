# CVR OSC Lib

This is a simple python wrapper that allows to interface with the CVR OSC Melon Loader mod.

The data structures are using data classes so if you have a smarter IDE you can get auto-completion and type checking.
I also added typing hits in most places, so should be pretty easy to use.

[Melon Loader OSC mod](https://github.com/kafeijao/Kafe_CVR_Mods/tree/master/OSC)

**Compatible with**: [v1.0.3](https://github.com/kafeijao/Kafe_CVR_Mods/releases/tag/r13)

I also included a few examples how to use the library, they require specific prop setup, and since
we're not able to publish public props yet, you will need to either upload your own or ask me to
share them with you (if you happen to find me in-game).

## Installation

1. Install Python 3.9 or above.
2. Create a `venv` [Optional]
3. Run: `pip install cvr-osc-lib`
4. Now the library is installed, you can start using it!

## Usage

Small example of starting the osc server and client while listening to parameter and
avatar changes. Then proceeds to change to one of the default robot avatars and change
its color to red.

The sleeps() and inputs() are there just to keep the example working,
you probably shouldn't use them when making your script.

```python
from time import sleep
from cvr_osc_lib import OscInterface, AvatarChangeReceive, AvatarParameterChange, AvatarChangeSend)


def avatar_change(data: AvatarChangeReceive):
    print(f'Changed to an avatar with the id: {data.avatar_guid}, and the json config is '
          f'located at: {data.avatar_json_config_path}')


def avatar_parameter_change(data: AvatarParameterChange):
    print(f'The parameter {data.parameter_name} has changed to the value: {data.parameter_value}')


if __name__ == '__main__':
    osc = OscInterface()

    # Prepare listeners
    # Prepare Listening to avatar changes (useful to get the avatar guid)
    osc.on_avatar_changed(avatar_change)
    # Prepare Listening to avatar parameter changes
    osc.on_avatar_parameter_changed(avatar_parameter_change)

    # Start the osc interface (starts both osc sender client and listener server)
    # If you only want to send osc msg, you don't need to call this, the sender will start
    # when you attempt to send your first OSC msg
    osc.start(start_sender=True, start_receiver=True)

    # Start sending OSC commands (needs to be done after the interface is started)
    # Inform the mod that a new osc server is listening, so it resends all the cached state
    osc.send_config_reset()
    sleep(1)  # Wait for the mod send us the current avatar event (because we reset)

    # Change avatar to a certain avatar ID
    print('\nPress Enter to change to the robot avatar...')
    input()  # Wait for <enter>
    osc.send_avatar_change(AvatarChangeSend(avatar_guid='6b86cced-e17c-4f57-8bdf-812615773ce6'))
    sleep(5)  # Wait to load the avatar (might fail if not cached/slow internet)

    print('\nPress Enter to change color to red...')
    input()  # Wait for <enter>
    osc.send_avatar_parameter(AvatarParameterChange(parameter_name='MainColor-r', parameter_value=1.0))
    osc.send_avatar_parameter(AvatarParameterChange(parameter_name='MainColor-g', parameter_value=0.0))
    osc.send_avatar_parameter(AvatarParameterChange(parameter_name='MainColor-b', parameter_value=0.0))

    # We can now wait here and listen for osc messages
    print('\nPress Enter to exit...')
    input()  # Wait for <enter>

```

## Example Run All

This script has an interactive python console script that will iterate through all the osc
endpoints. You can use as a reference on how to use a certain command or listen to a certain
endpoint.

There is a small description in the python file for the example, feel free to take a look.

## Example Tracked Props

This script shows a possible implementation of attaching a prop/prop sub-sync transforms to a
tracked device, like vive trackers.

For the current setup I also shared a `.unitypackage` containing the props I used for the example.
Feel free to upload them to your account, and then replace the guids in the script.

Don't forget to import the `CCK 3.4` first!

I would recommend checking the script for more info, has it has a little introduction and a bit
of explanation on how to configure it.
