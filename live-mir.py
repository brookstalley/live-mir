from cement.core.foundation import CementApp
from cement.core import hook
from cement.utils.misc import init_defaults
from cement.ext.ext_logging import LoggingLogHandler
from cement.core.exc import CaughtSignal
from cement.core.controller import CementBaseController, expose

from metadatalistener import MetadataListener
from acousticbrainz import Acousticbrainz, FailedRequest

from metadataparser import MetadataParser
from media_metadata import Metadata
from rtspsync import RtspSync
from recording import Recording
from playbackitem import PlaybackItem
import acousticbrainz

from osc4py3.as_allthreads import *

import asyncio
import aiohttp
import socket

import os
import sys

from asyncio.streams import StreamWriter, FlowControlMixin

reader, writer = None, None

from enum import Enum

import logging
log = logging.getLogger("live-mir")

# define any hook functions here
def my_cleanup_hook(app):
    pass
          

class PlaybackState(Enum):
    STOPPED = 0
    PLAYING = 1
    PAUSED = 2
          
#configuration defaults
defaults = init_defaults('live-mir')
defaults['live-mir']['metadata_address'] = '239.255.10.2'          
defaults['live-mir']['metadata_port'] = '5555'    
defaults['live-mir']['osc_target'] = '239.255.10.2'          
defaults['live-mir']['osc_port'] = '5555'    
 
defaults['live-mir']['debug'] = False
defaults['live-mir']['musicbrainz_server'] = ''
defaults['live-mir']['acousticbrainz_server'] = ''

async def stdio(loop=None):
    if loop is None:
        loop = asyncio.get_event_loop()

    reader = asyncio.StreamReader()
    reader_protocol = asyncio.StreamReaderProtocol(reader)

    writer_transport, writer_protocol = await loop.connect_write_pipe(FlowControlMixin, os.fdopen(1, 'wb'))
    writer = StreamWriter(writer_transport, writer_protocol, None, loop)

    await loop.connect_read_pipe(lambda: reader_protocol, sys.stdin)

    return reader, writer
    
async def async_input(message):
    if isinstance(message, str):
        message = message.encode('utf8')

    global reader, writer
    if (reader, writer) == (None, None):
        reader, writer = await stdio()

    writer.write(message)
    await writer.drain()

    line = await reader.readline()
    return line.decode('utf8').replace('\r', '').replace('\n', '')    

def setup_logging(app):
    # set up logging to file - see previous section for more details
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                        datefmt='%m-%d %H:%M',
                        filename='/tmp/myapp.log',
                        filemode='w')
    # define a Handler which writes INFO messages or higher to the sys.stderr
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    # set a format which is simpler for console use
    formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
    # tell the handler to use this format
    console.setFormatter(formatter)
    # add the handler to the root logger
    logging.getLogger('').addHandler(console)
    
def setup_osc(app): 
    #osc_startup(logger = log)
    osc_startup()
    log.debug("Starting OSC for target={}, port={}".format(app.config.get("live-mir", "osc_target"), app.config.get("live-mir", "osc_port")))
    osc_udp_client(app.config.get("live-mir", "osc_target"), app.config.get("live-mir", "osc_port"), "lightjams")

def setup(app):
    setup_logging(app)
    setup_osc(app)
          
# define the application class
class BaseController(CementBaseController):
    class Meta:
        label = 'base'

    @expose(hide=True)
    def default(self):
        self.app = app
        self.quitting = False
        self.loop = asyncio.get_event_loop()
        self.aiohttp_session = aiohttp.ClientSession(loop = self.loop)

        self.currentRecoding = None
        self.nextRecording = None
        self.next_item = None
        self.next_item_task = None
        self.rtsp_sync = RtspSync(44100, self.loop)
        
        self.set_preschedule_s(int(app.config.get("live-mir", "preschedule_ms"))/1000)        
        
        self.acoustic_brainz = Acousticbrainz(self.aiohttp_session, app.config.get("live-mir", "acousticbrainz_server"), self.loop)
        self.metadata_parser = MetadataParser()
        
        self.playback_state = PlaybackState.STOPPED
        
        self.metadataReceiver = MetadataListener(queueSize = 20)
        self.metadataReceiver.bind_socket (app.config.get("live-mir", "metadata_address")
                , int(app.config.get("live-mir", "metadata_port"))
                , socket.INADDR_ANY)
                
        self.loop.run_until_complete(self.metadataReceiver.start_listener())
        self.loop.run_until_complete(self.main()) 
        self.loop.close()        

   
    async def main(self):
        nodes = [
            self.loop.create_task(self.metadata_loop()),
            self.loop.create_task(self.command_loop())
        ]        
        await asyncio.gather(*nodes)

    
    def set_preschedule_s(self, seconds):
        log.debug("Setting preschedule to {} ms".format(seconds * 1000))
        self.preschedule_s = seconds
     
    async def shutdown(self):
        if (self.next_item_task):
            self.next_item_task.cancel()

        osc_terminate()
        self.metadataReceiver.stop()
        await self.aiohttp_session.close()
  
    async def test_sequence_end(self):
        log.debug("Sequence ended")
        
    def sync_rtsp(self, frame):
        self.rtsp_sync.set_rtsp_frame(frame)
        
    async def handle_progress (self, item):
        print("handle_progress: {}".format(item))
        current_frame = item["value"]["current"]
        self.sync_rtsp(current_frame)
        sequence_end_time, delta = self.rtsp_sync.loop_time_for_frame(item["value"]["end"])
        sequence_start_time, delta = self.rtsp_sync.loop_time_for_frame(item["value"]["start"])
        if (self.next_item):
            self.next_item.set_starts(item["value"]["start"],sequence_start_time)
            
        log.debug("Scheduling start and end events for loop times {}, {}".format(sequence_start_time, sequence_end_time))
        self.sequence_end_task = self.loop.call_at(sequence_end_time, self.test_sequence_end)
        if self.next_item:
            next_item_task = self.loop.call_at(sequence_start_time - self.preschedule_s, self.start_next_item)
    
    
    async def handle_volume(item):
        print("{}".format(item))
        values = item["value"].split(",")
        volumes = {}
        volumes["airplay_volume"], volumes["volume"], volumes["lowest_volume"], volumes["highest_volume"] = item["value"].split
        #await send_volume(volumes)
        
    
    async def item_changed(self):
        """
            The currently playing item changed, and we should update any
            non-time-critical UI 
        """
        log.info("Recording changed. Now playing {}".format(self.current_item.recording.summary["title"]))
        
    def start_next_item(self):
        """
            We're starting the next song
        """
        log.debug("Starting next playlist item")
        self.current_item = self.next_item
        self.next_item = None
        self.next_item_task = None
        ### We can only have gotten here if there has been a prgr message,
        ### so we know that the loop time to rtsp frame sync is running
        self.current_item.playback_started(self.loop,self.preschedule_s)
        self.current_item.schedule_events()
        
        ### Any UI or other non-critical event
        self.loop.create_task(self.item_changed())
        
    async def queue_item(self, recording):
        ### Create a playbackitem 
        self.next_item = PlaybackItem(recording)
        
              
    async def metadata_loop(self):
        while not self.quitting:
            data = await(self.metadataReceiver.receive())
            # This is a really ugly hack but it works
            if (data != b"exiting"):
                item = self.metadata_parser.ParseItem(data)

                if (item is None):
                    log.warning(self,"Could not get valid metadata item for {}".format(data))
                else:
                    ### This could be anything from info about the next song
                    ### to notification that we have skipped a song or changed
                    ### volume
                    await self.process_metadata(item)   
                
    async def command_loop(self):
        while not self.quitting:
            command = await async_input("\nCommand: ")
            self.on_command(command)
            
    def display_status(self):
        print("Preschedule: {}ms".format(self.preschedule_s * 1000))
        try: 
            if self.current_item and self.current_item is not None:
                print("Playing {}".format(self.current_item.recording.summary["title"]))
                if self.current_item.recording.detail is not None:
                    detail = self.current_item.recording.detail
                    print("\tKey: {} {}".format(detail["tonal"]["key_key"], detail["tonal"]["key_scale"]))
        except (AttributeError):
            print("No song playing, or no metadata yet")
            
                
    
    def on_command(self,command):
        command_help = {"sync" : "Adjust timing of output messages. Syntax: sync +5 | -5",
                    "status" : "Print current status",
                    "quit" : "Exit program"
                    }
        if command == "help":
            print("Commands:")
            for command,text in command_help.items():
                print("{}\t\t\t{}".format(command,text))
            
        elif command == "sync -5":
            self.set_preschedule_s(self.preschedule_s - 5/1000)           
        elif command == "sync +5":
            self.set_preschedule_s(self.preschedule_s + 5/1000)
        elif command == "status":
            self.display_status()
        elif command == "quit":
            print("Shutting down...")
            self.quitting = True
            self.loop.create_task(self.shutdown())
        elif command == "":
            pass # No op, but give another command prompt
        else:
            print("Unknown command '{}'".format(command))

        
    async def process_metadata(self, item):
        if item["type"] == "ssnc":
            if item["code"] == "mdst": # beginning of metadata
                ### Start with fresh metadata, does not matter if we already had some
                self.current_metadata = Metadata(self.aiohttp_session, app)
                ### Add the mdst timing info as the first item in our metadata list
                self.current_metadata.set_field(item["name"], item["value"])
                #self.sync_rtsp(item["value"])
            
            elif item["code"] == "mden": # end of metadata
                ### Add the mden as the last item to our metadata list                
                self.current_metadata.set_field(item["name"], item["value"])
                persistent_id = self.current_metadata.get_field("persistentid")
                log.debug("Ended metadata {} for persistent_id {}".format(item["value"], persistent_id))
                if self.next_item is None or self.next_item.recording.get_persistent_id() != persistent_id:
                    if self.next_item is None:
                        log.debug("No next item queued, looking up")
                    else:
                        log.debug("Next item id changed from {} to {}, looking up".format(self.next_item.recording.get_persistent_id(), persistent_id))
                    ### Set up our recording object
                    recording = Recording(self.current_metadata.get_field("persistentid"))
                    
                    ### Get the recording ID, if possible. Load the recording info
                    ### from either Acousticbrainz or just the metadata we were sent
                    try:
                        recordingId = await self.current_metadata.get_recordingId()     
                        ab_info = await self.acoustic_brainz.lookup_recording(recordingId)
                        recording.load_acousticbrainz(ab_info) 
                    except (Metadata.RecordingLookupError, TypeError, FailedRequest):
                        recordingId = 0
                        recording.load_metadata(self.current_metadata)
                                       
                    ### Enqueue the item, to start at the frame specified in the mden message
                    await self.queue_item(recording)
                self.current_metadata = None
                
            elif item["code"] == "prgr": # progress info
                await self.handle_progress(item)
                
            elif item["code"] == "pbeg": # start playing
                pass
                
            elif item["code"] == "prsm": # resume playing
                pass
                
            elif item["code"] == "pend": # stop playing
                self.playback_state = PlaybackState.STOPPED
                if (self.current_item):
                    self.current_item.cancel()
                if (self.next_item):
                    self.next_item.cancel()
                    
                pass
                
            elif item["code"] == "pfls": # flush (pause?)
                pass
            
            elif item["code"] == "pvol": # volume
                await handle_volume(item)
        
        elif item["type"] == "core":
            self.current_metadata.set_field(item["name"], item["value"])    
        
# define the application class
class LiveMirApp(CementApp):
    class Meta:
        label = 'live-mir'
        config_files = ['live-mir.conf']
        config_defaults = defaults
        arguments_override_config = True
        extensions = ['daemon']
        hooks = [
            ('post_argument_parsing', setup),
            ('pre_close', my_cleanup_hook)
        ]
        base_controller = BaseController
        
                
with LiveMirApp() as app:
    # add arguments to the parser
    app.args.add_argument('-m', '--musicbrainz-server', action='store', dest='musicbrainz_server', metavar='STR',
                          help='Musicbrainz server DNS or IP')
                          
    app.args.add_argument('-a', '--acousticbrainz-server', action='store', dest='acousticbrainz_server', metavar='STR',
                          help='Acousticbrainz server DNS or IP')
                          
    app.args.add_argument('-s', '--osc-target', action='store', dest='osc_target', metavar='STR',
                          help='IP address to send OSC messages to')
                          
    app.args.add_argument('-p', '--osc-port', action='store', dest='osc_port', metavar='STR',
                          help='UDP port to send OSC messages to')
                          
    app.args.add_argument('-u', '--metadata-address', action='store', dest='metadata_address', metavar='STR',
                          help='UDP port to send OSC messages to')
                          
    app.args.add_argument('-l', '--metadata-port', action='store', dest='metadata_port', metavar='STR',
                          help='UDP port to send OSC messages to')
                          
    app.args.add_argument('-e', '--preschedule-ms', action='store', dest='preschedule_ms', metavar='STR',
                          help='Milliseconds in advance to send OSC messages')                          

                  
    # log stuff
    log.debug("Starting Shairport Sync OSC")
    
    # run the application
    app.run()
 

    app.close()