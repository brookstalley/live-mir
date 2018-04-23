from datetime import datetime

import logging
log = logging.getLogger("audiosc." + __name__)

class MetadataParser(object):
    __instance = None
    
    def __new__(cls):
        if MetadataParser.__instance is None:
            MetadataParser.__instance = object.__new__(cls)
           
        MetadataParser.__instance.fieldList = {
        # ssnc values
            "PICT" : ["picture", cls.intHandler],
            "mdst" : ["metadatastart", cls.time_handler],
            "snua" : ["useragent", cls.string_handler],
            "mden" : ["metadataend", cls.time_handler],
            "pbeg" : ["playbegin", cls.zero_byte_handler],
            "pfls" : ["playpause", cls.zero_byte_handler],
            "prsm" : ["playstart", cls.zero_byte_handler],
            "pffr" : ["playstart", cls.zero_byte_handler],
            
            "pend" : ["plaend", cls.zero_byte_handler],
            "pvol" : ["playvolume", cls.play_volume_handler],
            "daid" : ["dacpid", cls.intHandler],
            "acre" : ["activeremote", cls.intHandler],
            "prgr" : ["playprogress", cls.progress_handler],
            "caps" : ["playstate", cls.one_byte_handler],
            "flsr" : ["flushtime", cls.time_handler],
            
        # Core values
            "mikd" : ["itemkind", cls.one_byte_handler],
            "minm" : ["itemname", cls.string_handler],
            "mper" : ["persistentid", cls.eight_byte_handler],
            "miid" : ["itemid", cls.four_byte_handler],
            "asal" : ["songalbum", cls.string_handler],
            "asar" : ["songartist", cls.string_handler],
            "ascm" : ["songcomment", cls.string_handler],
            "asco" : ["songcompilation", cls.bool_handler],
            "asbr" : ["songbitrate", cls.two_byte_handler], 
            "ascp" : ["songcomposer", cls.string_handler],
            "asda" : ["songdateadded", cls.date_handler],
            "aspl" : ["songdateplayed", cls.date_handler],
            "asdm" : ["songdatemodified", cls.date_handler],
            "asdc" : ["songdisccount", cls.two_byte_handler],
            "asdn" : ["songdiscnumber", cls.two_byte_handler],
            "aseq" : ["songeqpreset", cls.string_handler],
            "asgn" : ["songgenre", cls.string_handler],
            "asdt" : ["songdescription", cls.string_handler],
            "asrv" : ["songrelativevolume", cls.one_byte_handler],
            "assr" : ["songsamplerate", cls.four_byte_handler],
            "assz" : ["songsize", cls.four_byte_handler],
            "asst" : ["songstarttime", cls.four_byte_handler],
            "assp" : ["songstoptime", cls.four_byte_handler],
            "astm" : ["songtime", cls.four_byte_handler],
            "astc" : ["songtrackcount", cls.two_byte_handler],
            "astn" : ["songtracknumber", cls.two_byte_handler],
            "asur" : ["songuserrating", cls.one_byte_handler],
            "asyr" : ["songyear", cls.two_byte_handler],
            "asfm" : ["songformat", cls.string_handler],
            "asdb" : ["songdisabled", cls.bool_handler],
            "asdk" : ["songdatakind", cls.one_byte_handler],
            "asbt" : ["songbeatsperminute", cls.two_byte_handler],
            "agrp" : ["songgrouping", cls.string_handler],
            "ascd" : ["songcodectype", cls.string_handler],
            "ascs" : ["songcodecsubtype", cls.intHandler],
            "asct" : ["songcategory", cls.string_handler],
            "ascn" : ["songcontentdescription", cls.string_handler],
            "ascr" : ["songcontentrating", cls.intHandler],
            "asri" : ["singartistid", cls.intHandler],
            "asai" : ["songalbumid", cls.intHandler],
            "askd" : ["songlastskipdate", cls.date_handler],
            "assn" : ["songsortname", cls.string_handler],
            "assu" : ["songsortalbum", cls.string_handler],
            "aeNV" : ["itunesnormvolume", cls.intHandler],
            "aePC" : ["itunesispodcast", cls.bool_handler],
            "aeHV" : ["ituneshasvideo", cls.bool_handler],
            "aeMK" : ["itunesmediakind", cls.intHandler],
            "aeSN" : ["itunesseriesname", cls.string_handler],
            "aeEN" : ["itunesepisodenumber", cls.string_handler],
            "meia" : ["unknownmeia", cls.string_handler],
            "meip" : ["unknownmeip", cls.string_handler]
        }
        return MetadataParser.__instance
            
    def ParseItem(self, rawItem):
        assert isinstance(rawItem, (bytes, bytearray))
        
        type = rawItem[0:4].decode("utf-8")
        code = rawItem[4:8].decode("utf-8")
        rawData = rawItem[8:]
        #print("Finding %s:%s:%s" % (ty pe, code, rawData))
        try:
            fieldInfo = self.fieldList[code]
        except KeyError: 
            print("Key not found: %s (value %s)" % (code, rawData))
            return
        
        data = fieldInfo[1](self,rawData)
        fieldName = fieldInfo[0]
        log.debug("Setting %s : %s to %s (%s)" % (code, fieldName, data, rawData))
        
        item = {"type" : type, "code" : code, "name" : fieldName, "value" : data}
        return item
        
    def string_handler(self, rawData):
        return rawData.decode("utf-8")
        
    def bool_handler(self, rawData):
        if (rawData[0]>0):
            return True
        else:
            return False        
        
    def intHandler(self, rawData):
        return 0
    
    def zero_byte_handler(self, rawData):
        """Used for fields whose presence is the message"""
        return True
    
    def one_byte_handler(self, rawData):
        return int(rawData[0])
    
    def two_byte_handler(self, rawData):
        #stringed = rawData.decode("utf-8")
        return (rawData[0] << 8) + rawData[1]
    
    def four_byte_handler(self, rawData):
        return (rawData[0] << 24) + (rawData[1] << 16) + (rawData[2] << 8) + rawData[3]
        
    def eight_byte_handler(self, rawData):
        return (rawData[0] << 56) + (rawData[1] << 48) + (rawData[2] << 40) + (rawData[3] << 32) +(rawData[4] << 24) + (rawData[5] << 16) + (rawData[6] << 8) + rawData[7]

    def date_handler(self, rawData):
        return datetime.now()
    
    def time_handler(self, rawData):
        stringTime = rawData.decode("utf-8")
        return int(stringTime)
        
    def progress_handler(self, rawData):
        stringTimes = rawData.decode("utf-8")
        timeList = stringTimes.split("/")
        progress = {"start" : int(timeList[0]), "current" : int(timeList[1]), "end" : int(timeList[2])}
        return progress
        
    def play_volume_handler(self, rawData):
        return 9999999999
        

