# Example scripts

## Intro

This folder contains examples of how to use the `cvr_osc_lib` python library.

## Dependencies  

### From pip  

- configparser  

## Unity package

Included in this repo are the props used for this script 'example_tracked_props.unitypackage'  
You need to install the [CCK 3.4](https://docs.abinteractive.net/cck/setup/) before importing the unity package!

## example_tracked_props.py & example_tracked_props_externalconfig.py

These examples should be used with the 3 props that are provided in the unity package (or shared by me).  
Currently the trackers are set up as 1 Vive 3.0 and 7 Tundra. You can change by going to the trackers in unity, and hide all tundras and show the vive ones.  
Note: For this to work you need to have the steamvr vive tracker roles properly set up!!!  
Note: you will need a copy of the `tracker.conf` file at the path `C:\CVR\OSC\OSC_Configs\trackers.conf` if you use the externalconfig variant.  

## example_run_all.py

This script provides examples of all the commands you can send (and listen for).  
Feel free to uncomment some listeners if you want to see their output, but be warned, some of those are crazy spammy.  
Also if you want this to run smoothly for you, you need to edit the configuration section, unfortunately I can't Provide working prop ids, as there's (currently) no way to make public props yet, so you need to configure it for your props.  

## example_windows_global_media.py  

This example script shows how to feed windows global media info into OSC  
Note: This uses the winsdk package, so before you use this you need to install it with the command:  
`pip install winsdk`  

## example_windows_global_media_chat_box.py  

This example script shows how to feed windows global media info into chat boxes via OSC 
Note: This uses the winsdk package, so before you use this you need to install it with the command:  
`pip install winsdk`  

## example_chat_box_messenger.py  

This example script shows how send messages and is typing state to the chat box via OSC
Note: This uses the keyboard package, so before you use this you need to install it with the command:  
`pip install keyboard`  
