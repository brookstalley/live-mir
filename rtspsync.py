from datetime import datetime, timedelta

import logging
log = logging.getLogger("live-mir." + __name__)

class SyncError(Exception):
    def __init__(self, message):
        self.message = message

class RtspSync(object):
    def __init__(self, bitrate, loop):
        self.last_loop_time = 0
        self.last_rtsp_frame = -1     
        self.bitrate = bitrate
        self.loop = loop
    
    def set_rtsp_frame(self, frame):
        # Save the old values so we can compare for drift
        prev_rtsp_frame = self.last_rtsp_frame
        prev_loop_time = self.last_loop_time
        
        # Store the current values
        self.last_rtsp_frame = frame
        self.last_loop_time = self.loop.time()
        
        if (prev_loop_time > 0):
            seconds_passed = (self.last_loop_time - prev_loop_time)
            frames_passed = frame - prev_rtsp_frame
            
            frames_second = frames_passed / seconds_passed
            log.debug("New RTSP frame {0:d} at loop time {1:f}. Measured sample rate: {2:5.2f}".format(frame, self.last_loop_time, frames_second))
        else:
            log.debug("New RTSP frame {0:d} at loop time {1:f}.".format(frame, self.last_loop_time))

            
    def set_bitrate(self, bitrate):
        self.bitrate = bitrate
        
    def loop_time_for_frame(self, frame):
        """ 
            Returns the system time corresponding to the RTSP frame value.
            Assumes that the current frame has been set (very) recently
        """
        if (self.last_rtsp_frame < 0):
            raise SyncError("Current RTSP frame not set before calling system_time_for_frame")
                
        frame_diff = frame - self.last_rtsp_frame
        second_diff = frame_diff/self.bitrate
        
        delta = timedelta(0,second_diff)
        return self.loop.time() + second_diff, delta
        
    def estimate_frame_now(self):
        assert (self.last_rtsp_frame>0)
        
        seconds_since_sync = (self.loop.time() - self.last_loop_time).total_seconds()
        frames_since_sync = self.bitrate * seconds_since_sync
        return self.last_rtsp_frame + frames_since_sync
        
        
    
        
        