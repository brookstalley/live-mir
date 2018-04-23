import logging
log = logging.getLogger("live-mir." + __name__)

import musicbrainzngs

class Metadata(object):

    class Error(Exception):
        """Base class for exceptioons in this module"""
        pass
        
    class RecordingLookupError(Error):
        """ Catch-all for errors retrieving recording data. Should mean that the data is not available """
        
        def __init__(self, message):
            self.message = message

    def __init__(self, aiohttp_session, app):
        self.fields = {}
        self.aiohttp_session = aiohttp_session
        self.app = app
        musicbrainzngs.set_useragent(app.config.get("live-mir", "brainz_app")
                ,app.config.get("live-mir", "brainz_ver")
                ,app.config.get("live-mir", "brainz_contact"))        
    
    def set_field(self, field_name, field_value):
        self.fields[field_name] = field_value
        
    def get_field(self, field_name):
        return self.fields[field_name]  
        
    async def get_recordingId (self): 
        kwargs = {
            "query" : self.fields["itemname"],
            "limit" : 1,
            "artist" : self.fields["songartist"],
            "release" : self.fields["songalbum"]
        }
        if "songtime" in self.fields and self.fields["songtime"] is not None:
            kwargs["dur"] = self.fields["songtime"]
            
        result = musicbrainzngs.search_recordings(**kwargs)
        
        try:
            recording = result["recording-list"][0]
        except:
            raise RecordingLookupError("Could not look up recording")
            
        title = recording["title"]
        recordingId = recording["id"]
        print("Got recording id %s for title %s" % (recordingId, title))
        return recordingId
        
        