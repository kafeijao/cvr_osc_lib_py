from configparser import RawConfigParser, NoSectionError
from typing import (
    Dict,
    Final,
    Optional,
)

import mido

from cvr_osc_lib import (
    OscInterface,
    PropAvailability,
    PropCreateReceive,
    PropDelete,
    PropParameter,
)

###
# Welcome to an example how to transform midi inputs into the synced prop parameters
# As time of writing, this ONLY supports Python 3 (3.6, 3.7, 3.8, and 3.9).
# python-rtmidi requirements, check: https://github.com/SpotlightKid/python-rtmidi
#
# 1. Install mido: pip install mido
# 2. Install python-rtmidi: pip install python-rtmidi
# 3. Edit the example_midi_prop.config properly
# 4. Execute: python example_midi_prop.py
#
#
# Extras:
# I also included a unity package with a script to generate an animator (because it would be literally pain to do it
# manually...
#
# Instructions:
# 1. Import `example_midi_prop_Generate_Midi_Animator_v1.0.0.unitypackage`
# 2. Drag `Midi_Animator_Generator.prefab` into a scene, it's in: Assets/kafeijao/Scripts/GenerateMidiAnimator/
# 3. Fill the Animation clips into the slots. You can lock the inspector allowing you can drag all the clips in one go
# 4. Press `Generate Animator`
# 5. Wait a while, unity will freeze. Stay in the window until it's done (might take 1 minute or more)
# 6. Enjoy :3
#
# Notes:
# 1. Your animations need to start with `midi_X_` X being the midi note of the sound, for example `midi_38_ELow.anim`
# 2. If there is a midi note without a matching animation the `Not Playing Clip` will be used, so you don't need to
#    worry about them. Only put the animations you want to play sounds.
# 3. If there is already an animator on the path:
#    `Assets/kafeijao/Scripts/GenerateMidiAnimator/GeneratedMidiAnimator.controller` a new one will **NOT** be generated
#
###

# Load config file
config = RawConfigParser()
config_path = 'example_midi_prop.conf'
try:
    config.read(config_path)
    # Prop guid
    midi_prop_guid: Final[str] = config.get('config', 'prop_guid')
    # Number of concurrent keys
    number_of_keys: Final[int] = int(config.get('config', 'number_of_keys'))
    # debug_mode
    debug_mode: Final[bool] = config.get('config', 'debug_mode').casefold() == 'true'.casefold()
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

# Value of our notes when nothing is being pressed
no_note_value: Final[int] = -1


def on_prop_created(data: PropCreateReceive):
    global midi_prop_instance_id

    # Save the instance ids from the latest spawned prop with the corresponding guid
    if data.prop_guid == midi_prop_guid:
        midi_prop_instance_id = data.prop_instance_id

    print(f'The prop {data.prop_guid} has been spawned with the instance id {data.prop_instance_id}')


def on_prop_deleted(data: PropDelete):
    global midi_prop_instance_id

    # Clear the instance ids if they are the last ones and the corresponding prop is deleted
    if data.prop_guid == midi_prop_guid:
        midi_prop_instance_id = None

    print(f'The prop {data.prop_guid} with the instance id {data.prop_instance_id} has been deleted!')


def on_prop_availability_changed(data: PropAvailability):
    global midi_prop_is_available

    # Update the availability for each prop
    if data.prop_guid == midi_prop_guid and data.prop_instance_id == midi_prop_instance_id:
        midi_prop_is_available = data.prop_is_available

    print(f'The prop {data.prop_guid} with the instance id {data.prop_instance_id} is '
          f'{"now" if data.prop_is_available else "NOT"} available!')


def prop_parameter_change(data: PropParameter):
    if data.prop_guid == midi_prop_guid and data.prop_instance_id == midi_prop_instance_id:
        print(f'The parameter {data.prop_sync_name} has changed to the value: {data.prop_sync_value}.')


def initialize_osc_interface() -> OscInterface:
    osc = OscInterface()

    # Initialize the functions to react on events (needs to be set before starting the interface)

    # Listen to prop parameter changes
    # osc.on_prop_parameter_changed(prop_parameter_change)
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

    return osc


def send_midi_prop_parameters_keys(
        osc_interface: OscInterface,
        param_name: str,
        midi_key_value: int,
):

    param_value_float = -1.0 if midi_key_value == -1 else midi_key_value / 127.0

    if debug_mode:
        if midi_key_value == -1:
            print(f'The parameter {param_name} has changed to the value: {param_value_float}. You could use less than: '
                  f'-0.5')
        else:
            gt = param_value_float - ((1/127)/2)
            lt = param_value_float + ((1/127)/2)
            print(f'The parameter {param_name} has changed to the value: {param_value_float} '
                  f'(midi_key={midi_key_value}). You could use Greater than: {gt:.5f} and Less than {lt:.5f}')

    # Ignore if there are no ready props
    if midi_prop_instance_id is None or midi_prop_is_available is not True:
        if debug_mode:
            print(f'\tWarning: Ignoring input since no prop with guid {midi_prop_guid} has been found...')
        return

    # Send the parameter update
    osc_interface.send_prop_parameter(PropParameter(
        prop_guid=midi_prop_guid,
        prop_instance_id=midi_prop_instance_id,
        prop_sync_name=param_name,
        prop_sync_value=param_value_float,
    ))


def on_midi_msg(osc, keys_values, msg):

    if msg.type == 'note_on' and msg.note not in keys_values.values():
        # Find the first entry with value no_note_value and set it to msg.note
        try:
            key_name = next(key for key, value in keys_values.items() if value == no_note_value)
            keys_values[key_name] = msg.note
            send_midi_prop_parameters_keys(osc, key_name, msg.note)
            # if debug_mode:
            #     print(f'Current Held Keys: {keys_values}')
        except StopIteration:
            print("Warning: Not enough concurrent notes to output all currently pressed keys!")

    elif msg.type == 'note_off':
        # Set all keys with value equal to msg.note to no_note_value
        for key, value in keys_values.items():
            if value == msg.note:
                keys_values[key] = no_note_value
                send_midi_prop_parameters_keys(osc, key, no_note_value)
                # if debug_mode:
                #     print(f'Current Held Keys: {keys_values}')


def listen_to_midi_msg_from_input(input_name: str):

    osc = initialize_osc_interface()

    # Initialize the dict with the max concurrent keys and defaults to no_note_value (-1)
    keys_values: Dict[str, int] = {}
    for i in range(1, number_of_keys + 1):
        key_name = "Key_" + str(i)
        keys_values[key_name] = no_note_value

    # mid = mido.MidiFile('MIDI_sample.mid')
    # for msg in mid.play():
    #     on_midi_msg(osc, keys_values, msg)

    with mido.open_input(input_name) as in_port:
        for msg in in_port:
            on_midi_msg(osc, keys_values, msg)


if __name__ == '__main__':

    midi_devices = mido.get_input_names()

    if len(midi_devices) == 0:
        print('No midi devices were found... Existing!')
        quit()

    print('Found the following midi devices:')
    for idx, midi_device in enumerate(midi_devices):
        print(f'\t{idx}.\t{midi_device}')
    device_num = input(f'\nPick a device number, between 0 and {len(midi_devices) - 1} > ')

    try:
        # Validate the chosen device number and fetch its name
        idx = int(device_num)
        device_name = midi_devices[idx]

        print(f'Listening to input from: {device_name}...')
        listen_to_midi_msg_from_input(device_name)

    except ValueError:
        print(f'The provided device number ({device_num}) is not a number...')
    except IndexError:
        print('The provided device number doesn\'t exist...')
