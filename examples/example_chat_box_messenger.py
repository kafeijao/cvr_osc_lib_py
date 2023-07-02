import time
import threading

from keyboard import KeyboardEvent

from cvr_osc_lib import OscInterface
from cvr_osc_lib.osc_messages_data import ChatBoxMessage, ChatBoxIsTyping
import keyboard

###
# Example to send messages to the ChatBox via OSC. For this to work you need to install the keyboard package
#
# pip install keyboard
#
###

# Globals
typing = False
last_key_press_time = 0


def stop_typing():
    global typing
    osc.send_chat_box_is_typing(ChatBoxIsTyping(
        is_typing=False,
        sound_notification=True,
    ))
    typing = False


def on_key_pressed(event: KeyboardEvent):
    global typing, last_key_press_time

    if event.name == 'enter':
        stop_typing()
        return

    if len(event.name) > 1 or not event.name.isalnum():
        return

    if not typing:
        osc.send_chat_box_is_typing(ChatBoxIsTyping(
            is_typing=True,
            sound_notification=True,
        ))
        typing = True

    last_key_press_time = time.time()


def check_typing_timeout():
    global typing, last_key_press_time
    while True:
        if typing and time.time() - last_key_press_time > 5:
            stop_typing()
        time.sleep(1)


if __name__ == '__main__':

    osc = OscInterface()

    # Start the osc interface, starts osc sender
    osc.start(start_receiver=False)

    # Send the press events
    keyboard.on_press(on_key_pressed)

    # Start typing timeout thread
    typing_thread = threading.Thread(target=check_typing_timeout, daemon=True)
    typing_thread.start()

    while True:

        user_input = input('\nEnter your message> ')
        if user_input:
            osc.send_chat_box_message(ChatBoxMessage(
                message=user_input,
                send_immediately=True,
                sound_notification=True,
                show_in_chat_box=True,
                show_in_history_window=True,
            ))
