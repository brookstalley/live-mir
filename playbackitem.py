"""
    Represents the totality of a playback item, 
    including the recording to be played, its relative
    start time, and the schedule of events to send during
    playback
    

    Takes canned metadata about a recording and schedules
    low-level events on an asyncio loop    
"""

import logging
log = logging.getLogger("audiosc." + __name__)

import asyncio

from osc4py3.as_eventloop import *
from osc4py3 import oscbuildparse

def key_to_index(key):
    keys = [ "A", "A#", "B", "C", "C#", "D", "D#", "E", "F", "F#", "G", "G#" ]
    try:
        key_num = keys.index(key)
    except:
        log.warning("Failed to look up key '{}'".format(key))
        key_num = -1
    return key_num
    
def scale_to_index(scale):
    scales = ["major", "minor"]
    try: 
        scale_num = scales.index(scale)
    except:
       log.warning("Failed to look up scale '{}'".format(scale))
       scale_num = -1
    return scale_num

class PlaybackItem(object):
    def __init__(self, recording):
        ### We only know frame, not time, when we are created 
        self.recording = recording
        self.recording_start_frame = None
        self.recording_start_time = None
        self.events = []
        self.loop = None
        self.preschedule_ms = 0
        
    def set_starts(self, start_frame, start_loop_time):
        self.start_frame = start_frame
        self.start_loop_time = start_loop_time
     
    def playback_started(self, loop, preschedule_ms):
        self.loop = loop
        self.preschedule_ms = int(preschedule_ms)/1000
        self.recording_start_time = self.start_loop_time
        log.info("Started recording {}".format(self.recording.summary["title"]))
        if self.recording.detail is not None:
            key_name = self.recording.detail["tonal"]["key_key"]
            key_scale = self.recording.detail["tonal"]["key_scale"]
            key_strength = self.recording.detail["tonal"]["key_strength"]
            
            key_number = key_to_index(key_name)
            scale_number = scale_to_index(key_scale)
            
        else:
            key_number = -1
            scale_number = -1
            key_strength = 0
            
        msg = oscbuildparse.OSCMessage("/songdata/songstart".format(self.recording.get_persistent_id()),",hsiif",
                    [self.recording.get_persistent_id(), self.recording.summary["title"], key_number, scale_number, key_strength])
        osc_send(msg, "lightjams")
    
    def schedule_events(self): 
        self.setup_beat_events()        
        self.setup_recording_end()

    def cancel(self):
        for event in self.events:
            event.cancel()
                    
    def setup_beat_events(self):
        beatTimes = self.recording.get_beat_times()
        # times are relative to the recording; add to the loop timer
        for beat in beatTimes:
            self.events.append(self.loop.call_at(beat["time"] + self.start_loop_time - self.preschedule_ms, self.event_beat))        
        
    def setup_recording_end(self):
        """
            TODO: any fadeout, etc
        """
        pass
        
        
    def event_beat(self):
        #log.info("Beat")
        msg = oscbuildparse.OSCMessage("/songdata/beat".format(self.recording.persistent_id),",i",[1])
        osc_send(msg, "lightjams")       
            
   
    
    