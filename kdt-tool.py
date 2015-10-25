# Written by Nisto
# Developed under Python 3.4.2

import os
import sys
import struct

KDT_HEADER_SIZE  = 0x10
KDT_OFF_ID       = 0x00
KDT_OFF_FILESIZE = 0x04
KDT_OFF_TICKDIV  = 0x08
KDT_OFF_UNUSED1  = 0x0A
KDT_OFF_TRACKS   = 0x0C
KDT_OFF_UNUSED2  = 0x0E
KDT_OFF_SIZETBL  = 0x10

class KDT:
    def __init__(self, path, log=False):
        self.path = path
        self.log = log

        with open(self.path, "rb") as kdt:
            self.buf = kdt.read()

        if len(self.buf) < KDT_HEADER_SIZE or self.buf[KDT_OFF_ID:4] != b"KDT1":
            sys.exit("ERROR: Not a valid KDT1 file: %s" % self.path)

        self.filesize = get_u32_le(self.buf, KDT_OFF_FILESIZE)
        self.tickdiv = get_u16_le(self.buf, KDT_OFF_TICKDIV)
        self.tracks = get_u16_le(self.buf, KDT_OFF_TRACKS)

        self.buf = bytearray(self.buf[:self.filesize])

        if self.tracks > 0:

            self.offset = KDT_OFF_SIZETBL

            self.trk_size_tbl = []

            for trknum in range(self.tracks):
                self.trk_size_tbl.append( get_u16_le(self.buf, self.offset) )
                self.offset += 2

            self.trk_off_tbl = []

            for trknum in range(self.tracks):
                self.trk_off_tbl.append(self.offset)
                self.offset += self.trk_size_tbl[trknum]

            self.set_track(0)

    def set_track(self, trknum):
        self.trknum        = trknum
        self.trk_size      = self.trk_size_tbl[trknum]
        self.trk_off_start = self.trk_off_tbl[trknum]
        self.trk_off_end   = self.trk_off_start + self.trk_size
        self.trk_ended     = 0 # set by command 0xFFFF
        self.running       = 0 # sequence running status (expect delta-time when zero - note or command otherwise)
        self.offset        = self.trk_off_start

    def read_cmd(self):
        self.cmd = self.buf[self.offset]

        # only non-0xCA/0xCB commands takes an argument/parameter (confirmed via disassembly)
        if self.cmd == 0xCA:
            self.running = 0
            self.offset += 1
        elif self.cmd == 0xCB:
            self.offset += 1
        else:
            self.cmdarg = self.buf[self.offset+1]
            self.running = self.cmdarg & 0x80
            self.offset += 2

        """

        Might be worth looking into:
        http://web.archive.org/web/20151016183420/http://wiki.spinout182.com/w/Music_Sequences

        """

        if self.cmd == 0x86: # Sets reverb type (hall, room, etc.) on first call, volume/depth on next call (e.g. 86[tt], 86[vv]) ... I think?
            # self.cmdarg & 0x??
            if self.log: print("0x%04X   COMMAND      Command: 0x86/0x06 (Set Controller Volume), Argument/Parameter: 0x%02X" % (self.offset - 2 - self.trk_off_start, self.cmdarg & 0x7F))

        elif self.cmd == 0x87: # Set main / channel volume
            # self.cmdarg & 0x7F
            if self.log: print("0x%04X   COMMAND      Command: 0x87/0x07 (Set Main/Channel Volume), Argument/Parameter: 0x%02X" % (self.offset - 2 - self.trk_off_start, self.cmdarg & 0x7F))

        elif self.cmd == 0x8A: # Set panning
            # self.cmdarg & 0x7F
            if self.log: print("0x%04X   COMMAND      Command: 0x8A/0x0A (Set Panning), Argument/Parameter: 0x%02X" % (self.offset - 2 - self.trk_off_start, self.cmdarg & 0x7F))

        elif self.cmd == 0x8B: # Set controller volume ("expression is a percentage of the channel volume"?)
            # self.cmdarg & 0x7F
            if self.log: print("0x%04X   COMMAND      Command: 0x8B/0x0B (Set Controller Volume), Argument/Parameter: 0x%02X" % (self.offset - 2 - self.trk_off_start, self.cmdarg & 0x7F))

        elif self.cmd == 0xC6: # Set MIDI channel
            # self.cmdarg & 0x0F
            if self.log: print("0x%04X   COMMAND      Command: 0xC6/0x46 (Set Channel), Argument/Parameter: 0x%02X" % (self.offset - 2 - self.trk_off_start, self.cmdarg & 0x0F))

        elif self.cmd == 0xC7: # Set Tempo
            # self.cmdarg & 0x??
            if self.log: print("0x%04X   COMMAND      Command: 0xC7/0x47 (Set Tempo), Argument/Parameter: 0x%02X" % (self.offset - 2 - self.trk_off_start, self.cmdarg & 0x7F))

        elif self.cmd == 0xC8: # Not sure.. calls SsUtVibrateOff ???
            # self.cmdarg & 0x??
            if self.log: print("0x%04X   COMMAND      Command: 0xC8/0x48 (Unknown, calls SsUtVibrateOff), Argument/Parameter: 0x%02X" % (self.offset - 2 - self.trk_off_start, self.cmdarg & 0x7F))

        elif self.cmd == 0xC9: # Set Instrument
            # self.cmdarg & 0x7F
            if self.log: print("0x%04X   COMMAND      Command: 0xC9/0x49 (Set Instrument), Argument/Parameter: 0x%02X" % (self.offset - 2 - self.trk_off_start, self.cmdarg & 0x7F))

        elif self.cmd == 0xCA: # Note-off last note (reset running status)
            if self.log: print("0x%04X   COMMAND      Command: 0xCA/0x4A (Note-off + reset running status)" % (self.offset - 1 - self.trk_off_start))

        elif self.cmd == 0xCB: # Note-off last note (keep running status)
            if self.log: print("0x%04X   COMMAND      Command: 0xCB/0x4B (Note-off + keep running status)" % (self.offset - 1 - self.trk_off_start))

        elif self.cmd == 0xCC: # Note-off all notes?
            # self.cmdarg & 0x??
            if self.log: print("0x%04X   COMMAND      Command: 0xCC/0x4C (Note-off all notes?), Argument/Parameter: 0x%02X" % (self.offset - 2 - self.trk_off_start, self.cmdarg & 0x7F))

        elif self.cmd == 0xDB: # Reverb send amount? (or at least affects reverb somehow it seems)
            # self.cmdarg & 0x??
            if self.log: print("0x%04X   COMMAND      Command: 0xDB/0x5B (Reverb Send Amount?), Argument/Parameter: 0x%02X" % (self.offset - 2 - self.trk_off_start, self.cmdarg & 0x7F))

        elif self.cmd == 0xFF: # End of track
            if self.cmdarg == 0xFF:
                self.trk_ended = 1
                # self.running = 0
                if self.log:
                    print     ("0x%04X   COMMAND      Command: 0xFF/0x7F (End of track)" % (self.offset - 2 - self.trk_off_start))

        else:
            if self.log: print("0x%04X   COMMAND      Command: 0x%02X/0x%02X (Unknown), Argument/Parameter: 0x%02X" % (self.offset-2-self.trk_off_start, self.cmd, self.cmd & 0x7F, self.cmdarg & 0x7F))

    def read_note(self):
        self.note = self.buf[self.offset]
        self.velocity = self.buf[self.offset+1] & 0x7F
        self.running = self.buf[self.offset+1] & 0x80
        if self.log: 
            if self.velocity:
                print("0x%04X   NOTE-ON      Key: 0x%02X, Velocity: 0x%02X" % (self.offset - self.trk_off_start, self.note, self.velocity))
            else:
                print("0x%04X   NOTE-OFF     Key: 0x%02X" % (self.offset - self.trk_off_start, self.note))
        self.offset += 2

    def read_delta_time(self):
        if self.log: print("0x%04X   DELTA-TIME   Time: " % (self.offset - self.trk_off_start), end="")
        self.time = self.buf[self.offset] & 0x7F
        more = self.buf[self.offset] & 0x80
        self.offset += 1
        while more:
            self.time <<= 7
            self.time |= self.buf[self.offset] & 0x7F
            more = self.buf[self.offset] & 0x80
            self.offset += 1
        if self.log: print("%d" % self.time)
        self.running = 1

    def read_seq(self):
        if self.running: # Delta-time (time since last event)
            if self.buf[self.offset] & 0x80: # Command
                self.read_cmd()
            else: # Note/velocity pair(s)
                self.read_note()
        else:
            self.read_delta_time()

    def find_cmd(self, cmd):
        cmd |= 0x80 # MSB is always set in commands

        while self.offset < self.trk_off_end:
            if self.running:
                if self.buf[self.offset] == cmd:
                    return True
            self.read_seq()

        return False

def get_u16_le(buf, offset=0):
    return struct.unpack("<H", buf[offset:offset+2])[0]

def get_u32_le(buf, offset=0):
    return struct.unpack("<I", buf[offset:offset+4])[0]

def isnum(n):
    try:
        int(n)
    except ValueError:
        return False
    return True










def print_initial_track_volumes(kdt):
    basename = os.path.basename(kdt.path)
    for trknum in range(kdt.tracks):
        kdt.set_track(trknum)
        if kdt.find_cmd(0x87):
            volume = kdt.buf[kdt.offset+1] & 0x7F
            print("%s: track %02d volume = 0x%02X" % (basename, trknum, volume))

def print_bgm_type(kdt):
    basename = os.path.basename(kdt.path)
    dynamic = False
    for trknum in range(2, kdt.tracks): # skip tracks 0 and 1
        kdt.set_track(trknum)
        if kdt.find_cmd(0x87):
            volume = kdt.buf[kdt.offset+1] & 0x7F
            if volume == 0:
                dynamic = True
    if dynamic:
        print("Dynamic: %s" % basename)
    else:
        print("Standard: %s" % basename)

def print_note_event_counts(kdt):
    for trknum in range(2, kdt.tracks): # skip tracks 0 and 1

        events = 0

        kdt.set_track(trknum)

        while kdt.offset < kdt.trk_off_end:
            if kdt.running:
                if kdt.buf[kdt.offset] < 0x80:
                    events += 1
            kdt.read_seq()

        # print("%s: %d note events in track %02d" % (kdt.path, events, trknum))
        if events == 0:
            print("%s: no note events in track %02d" % (kdt.path, trknum))

# Prints all sequence events as human-readable lines for each track
def print_events(kdt):
    kdt.log = True
    for trknum in range(kdt.tracks):
        print("TRACK %02d" % trknum)
        print("=" * 80)
        print()
        kdt.set_track(trknum)
        while kdt.offset < kdt.trk_off_end:
            kdt.read_seq()
        print("\n" * 5)

# Creates separate KDT files for each track (I suck at naming stuff :P)
def demute_and_isolate_all_tracks_to_separate_files(kdt):
    dir = os.path.dirname(kdt.path)
    basename = os.path.basename(kdt.path)
    basename = os.path.splitext(basename)[0]
    filecount = kdt.tracks
    for filenum in range(filecount):

        out_buf = kdt.buf

        for trknum in range(kdt.tracks):

            kdt.set_track(trknum)

            if kdt.find_cmd(0x87): # seek to first 0x87 command byte (if present)
                if trknum < 2 or trknum == filenum: # always demute tracks 0 and 1 (special global tracks)
                    out_buf[kdt.offset+1] |= 0x6E # demute (ALL initially demuted tracks EXCEPT the second track of both T and T2 are initialized to volume = 0x6E)
                else:
                    out_buf[kdt.offset+1] &= 0x80 # isolate; i.e. mute everything except the track for the current file (and keep MSB intact)

        out_path = os.path.join(dir, "%s (track %02d).KDT" % (basename, filenum))
        with open(out_path, "wb") as out:
            out.write(out_buf)

# Creates a new KDT file with specified tracks demuted
def demute_and_isolate_specified_tracks_to_single_file(kdt, demute_args):
    demute = []
    trackgroups = []

    for trknum in demute_args:
        if "-" in trknum:
            if len(trknum.replace("-", "")) == len(trknum) - 1:
                start, end = trknum.split("-")
                if isnum(start) and isnum(end):
                    start = int(start)
                    end = int(end)
                    demute.extend(range(start, end+1))
                    trackgroups.append("%02d-%02d" % (start, end))
                else:
                    sys.exit("Invalid track range: %s" % trknum)
            else:
                sys.exit("Invalid track range: %s" % trknum)
        elif isnum(trknum):
            demute.append(int(trknum))
            trackgroups.append("%02d" % int(trknum))
        else:
            sys.exit("Invalid tracks argument: %s" % trknum)

    out_buf = kdt.buf

    for trknum in range(kdt.tracks):
        kdt.set_track(trknum)
        if kdt.find_cmd(0x87):
            if trknum < 2 or trknum in demute:
                out_buf[kdt.offset+1] |= 0x6E
            else:
                out_buf[kdt.offset+1] &= 0x80

    dir = os.path.dirname(kdt.path)

    basename = os.path.basename(kdt.path)

    basename = os.path.splitext(basename)[0]
    
    if len(demute) > 1:
        trackstr = "tracks %s" % ", ".join( sorted(trackgroups) )
    elif len(demute) == 1:
        trackstr = "track %s" % trackgroups[0]

    out_path = os.path.join(dir, "%s (%s).KDT" % (basename, trackstr))

    with open(out_path, "wb") as out:
        out.write(out_buf)

def main(argc=len(sys.argv), argv=sys.argv):
    path = os.path.realpath(argv[1])

    if not os.path.exists(path):
        sys.exit("ERROR: Invalid path")

    # for filename in os.listdir(path):
    #     filepath = os.path.join(path, filename)
    #     if os.path.splitext(filename)[1].upper() == ".KDT":
    #         print_note_event_counts(KDT(filepath))

    # demute_and_isolate_all_tracks_to_separate_files(KDT(path))

    demute_and_isolate_specified_tracks_to_single_file(KDT(path), argv[2:])

    return 0

if __name__=="__main__":
    main()
