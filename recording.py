import logging
log = logging.getLogger("live-mir." + __name__)

import json
       
class Recording:
    """ 
        Metadata about a recording, not including any specifics of this playback
    """
    def __init__(self, persistent_id):
        self.persistent_id = persistent_id
        
        self.summary = {}
        self.detail = None
        
    def load_acousticbrainz(self, songData):
        #print("{}".format(json.dumps(songData)))       
        
        songMetadata = songData["metadata"]
        #print("{}".format(json.dumps(songMetadata)))       
        self.summary["title"] = songData["metadata"]["tags"]["title"]
        self.summary["artist"] = songData["metadata"]["tags"]["artist"]
        self.summary["album"] = songData["metadata"]["tags"]["album"]
        self.summary["genre"] = songData["highlevel"]["genre_dortmund"]["value"]
        if "tonal" in songData:
            tonal = songData["tonal"]
            if "keys_key" in tonal:
                self.summary["tonal"]["keys_key"] = songData["tonal"]["keys_key"]
            
            if "keys_scale" in tonal:
                self.summary["tonal"]["keys_scale"] = songData["tonal"]["key_scale"]
                

        self.detail = songData
        
    def string_or_unknown(self, input):
        if (input is None) or (input == ""):
            return "(unknown)"
        else:
            return input
        
    def load_metadata(self, metadata):
        self.summary["title"] = string_or_unknown(metadata["itemname"])
        self.summary["artist"] = string_or_unknown(metadata["songartistname"])
        self.summary["album"] =  string_or_unknown(metadata["songalbum"])
        self.summary["genre"] =  string_or_unknown(metadata["songgenre"])
        self.detail = None
    
    def get_persistent_id(self):
        return self.persistent_id
        
    def get_beat_times(self):
        if self.detail is None:
            raise RuntimeError("Attempt to get beat positions with no data available")
            
        beats = []
        for beat in self.detail["rhythm"]["beats_position"]:
            beats.append({"time" : beat})
        
        return beats
            
            
    def saved(self):
        if "rhythm" in songData:
            rhythm = songData["rhythm"]
            if "bpm" in rhythm:  
                self.summary["rhythm"]["bpm"] = songData["rhythm"]["bpm"]
            if "type" in rhythm:
                self.summary["rhythm"]["type"] = songData["highlevel"]["ismir04_rhythm"]["value"]
        
        if "moods" in songData:
            self.summary["moods"]["acoustic"] = songData["highlevel"]["mood_acoustic"]["all"]["acoustic"]
            self.summary["moods"]["aggressive"] = songData["highlevel"]["mood_aggressive"]["all"]["aggressive"]
            self.summary["moods"]["electronic"] = songData["highlevel"]["mood_electronic"]["all"]["electronic"]
            self.summary["moods"]["happy"] = songData["highlevel"]["mood_happy"]["all"]["happy"]
            self.summary["moods"]["party"] = songData["highlevel"]["mood_party"]["all"]["party"]
            self.summary["moods"]["relaxed"] = songData["highlevel"]["mood_relaxed"]["all"]["relaxed"]
            self.summary["moods"]["sad"] = songData["highlevel"]["mood_sad"]["all"]["sad"]
        
        if "highlevel" in songData:
            highLevel = songData["highLevel"]
            if "timbre" in highLevel:
                timbre = highLevel["timbre"]
                self.summary["timbre"] = timbre["value"]    
            

                    
        
    
    