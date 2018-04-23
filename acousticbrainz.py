import asyncio
import async_timeout
import aiohttp
from recording import Recording

import logging
log = logging.getLogger("live-mir." + __name__)

class FailedRequest(Exception):
    """
    A wrapper of all possible exception during a HTTP request
    """
    code = 0
    message = ''
    url = ''
    raised = ''

    def __init__(self, *, raised='', message='', code='', url=''):
        self.raised = raised
        self.message = message
        self.code = code
        self.url = url

        super().__init__("code:{c} url={u} message={m} raised={r}".format(
            c=self.code, u=self.url, m=self.message, r=self.raised))


class Acousticbrainz(object):

    class Error(Exception):
        """Base class for exceptioons in this module"""
        pass
        
    class SongdataError(Error):
        """ Catch-all for errors retrieving song data. Should mean that the data is not available """
        
        def __init__(self, recordingId, message):
            self.recordingId = recordingId
            self.message = message

    def __init__(self, aiohttp_session, server, loop):
        self.server = "acousticbrainz.org"
        self.lastId = 0     
        self.aiohttp_session = aiohttp_session
        self.server = server
        self.loop = loop

    async def get_leveldata(self, recordingId, level):
        abUrl = "http://" + self.server + "/" + str(recordingId) + "/" + str(level)
        log.debug("get_leveldata: fetching %s" % abUrl)
        try:
            async with async_timeout.timeout(timeout = 10):
                async with self.aiohttp_session.get(abUrl) as response:
                    if response.status == 200:
                        try:
                            data = await response.json()
                        except json.decoder.JSONDecodeError as exc:
                            log.error("JSONDecodeError: %s on %s" % (exc, abUrl))
                            raise aiohttp.errors.HttpProcessingError(code=response.status, message=exc.msg)
                        else:
                            log.debug("Got %s data for recordingId %s" % (level, recordingId))
                            raised_exc = None
                            return data
                    
                    else:
                        log.error("Non-200 response")
                        raise FailedRequest(code = response.status, message = response.reason,
                            url = abUrl, raised='')
                        raised_exc = None
        except (aiohttp.ClientError,
                asyncio.TimeoutError) as exc:
            log.error("Failed to get song data")
            try:
                code = exc.code
            except AttributeError:
                code = ""
            raised_exc = FailedRequest(code = code, message = exc, url = abUrl,
                                    raised = exc.__class__.__name__)
        else:
            raised_exc = None
                
                           
    async def get_recordingdata(self, recordingId):
        nodes = [
            self.loop.create_task(self.get_leveldata(recordingId, "low-level")),
            self.loop.create_task(self.get_leveldata(recordingId, "high-level"))
        ]
        try:
            responses = await asyncio.gather(*nodes)
        except Exception as exc:
            log.error("Error: {}".format(exc))
            raise
            return
        
        for nextResponse in responses[1:]:
            responses[0].update(nextResponse)
            
        return responses[0]            
        
        
    async def lookup_recording(self, recordingId):
        log.debug("lookup_recording: finding recordingId %s" % recordingId)
        if (recordingId == self.lastId):
            return
        
        self.lastId = recordingId        
        
        try:
            songData = await self.get_recordingdata(recordingId)
        except (FailedRequest) as exc:
            log.warning("Could not get song data")
            raise 

        return songData
