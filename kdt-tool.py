# Written by Nisto
# Developed under Python 3.4.2

import os
import sys
import struct
#import math

KDT_HEADER_SIZE  = 0x10
KDT_OFF_ID       = 0x00
KDT_OFF_FILESIZE = 0x04
KDT_OFF_TICKDIV  = 0x08
KDT_OFF_UNUSED1  = 0x0A
KDT_OFF_TRACKS   = 0x0C
KDT_OFF_UNUSED2  = 0x0E
KDT_OFF_SIZETBL  = 0x10

# KDT_EVT_SET_CHAN_VOL   = 0x87
# KDT_EVT_SET_PANNING    = 0x8A
# KDT_EVT_SET_CTRL_VOL   = 0x8B
# KDT_EVT_SET_CHANNEL    = 0xC6
# KDT_EVT_SET_TEMPO      = 0xC7
# KDT_EVT_UNK            = 0xC8
# KDT_EVT_SET_INSTRUMENT = 0xC9
# KDT_EVT_NOTE_OFF_STOP  = 0xCA
# KDT_EVT_NOTE_OFF_CONT  = 0xCB
# KDT_EVT_SET_TEMPO_LO   = 0xCC
# KDT_EVT_SET_TEMPO_HI   = 0xCD
# KDT_EVT_RESERVED       = 0xCE
# KDT_EVT_END_OF_TRACK   = 0xFF

class KDT:
    def __init__(self, path, log=False, convert=False):
        self.path = path
        self.log = log
        self.convert = convert

        with open(self.path, "rb") as kdt:
            self.buf = kdt.read()

        if len(self.buf) < KDT_HEADER_SIZE or self.buf[KDT_OFF_ID:KDT_OFF_ID+4] != b"KDT1":
            sys.exit("ERROR: Not a valid KDT1 file: %s" % self.path)

        self.filesize = get_u32_le(self.buf, KDT_OFF_FILESIZE)
        self.tickdiv = get_u16_le(self.buf, KDT_OFF_TICKDIV)
        self.tracks = get_u16_le(self.buf, KDT_OFF_TRACKS)

        self.buf = bytearray(self.buf[:self.filesize])

        if self.convert:
            self.midi = bytearray(51200)

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
        self.offset        = self.trk_off_start
        self.channel       = 0
        self.running       = 0 # sequence running status (expect delta-time when zero - note or command otherwise)

    def read_cmd(self):
        cmd = self.buf[self.offset]

        if self.log: print("0x%04X   COMMAND      Command: 0x%02X/0x%02X " % (self.offset - self.trk_off_start, cmd, cmd & 0x7F), end="")

        # all commands except 0xCA and 0xCB take a parameter
        if cmd == 0xCA:
            self.running = 0
            self.offset += 1
        elif cmd == 0xCB:
            self.running = 1
            self.offset += 1
        else:
            param = self.buf[self.offset+1]
            self.running = param & 0x80
            self.offset += 2

        # Might be worth looking into:
        # http://web.archive.org/web/20151016183420/http://wiki.spinout182.com/w/Music_Sequences
        # https://sites.google.com/site/messiaen64/parsed-music-files

        if cmd == 0x86: # Sets reverb type (hall, room, etc.) on first call, volume/depth on next call (e.g. 86[tt], 86[vv]) ... I think?
            # param & 0x??
            if self.log: print("(Set Reverb Type), Parameter: 0x%02X" % (param & 0x7F))
            if self.convert:
                self.midi[self.moff:self.moff+4] = b"\xFF\x01\x01\x3F"
                self.moff += 4

        elif cmd == 0x87: # Set main / channel volume
            if self.log: print("(Set Main/Channel Volume), Parameter: 0x%02X" % (param & 0x7F))
            if self.convert:
                self.midi[self.moff+0] = 0xB0 | self.channel
                self.midi[self.moff+1] = 0x07
                self.midi[self.moff+2] = param & 0x7F
                self.moff += 3

        elif cmd == 0x8A: # Set panning
            if self.log: print("(Set Panning), Parameter: 0x%02X" % (param & 0x7F))
            if self.convert:
                self.midi[self.moff+0] = 0xB0 | self.channel
                self.midi[self.moff+1] = 0x0A
                self.midi[self.moff+2] = param & 0x7F
                self.moff += 3

        elif cmd == 0x8B: # Set controller volume ("expression is a percentage of the channel volume"?)
            if self.log: print("(Set Controller Volume), Parameter: 0x%02X" % (param & 0x7F))
            if self.convert:
                self.midi[self.moff+0] = 0xB0 | self.channel
                self.midi[self.moff+1] = 0x0B
                self.midi[self.moff+2] = param & 0x7F
                self.moff += 3

        elif cmd == 0xC6: # Set channel
            if self.log: print("(Set Channel), Parameter: 0x%02X" % (param & 0x0F))
            if self.convert:
                self.channel = param & 0x0F
                self.midi[self.moff:self.moff+4] = b"\xFF\x01\x01\x3F"
                self.moff += 4

        elif cmd == 0xC7: # Set tempo
            if self.log: print("(Set Tempo), Parameter: 0x%02X" % (param & 0x7F))
            if self.convert:
                # this equation is taken from the Silent Hill 2 driver;
                # Suikoden 2 and Silent Hill 1 both add by 2 instead of 10;
                # I don't know why, or what it represents, but adding by 10
                # seems to give a more accurate result for ALL games;
                # change if needed, and please report
                bpm = ((param & 0x7F) * 2) + 10

                # micrsoseconds per quarter-note = microseconds per minute / beats per minute
                mpqn = 60000000 // bpm

                self.midi[self.moff+0] = 0xFF
                self.midi[self.moff+1] = 0x51
                self.midi[self.moff+2] = 0x03
                self.midi[self.moff+3] = (mpqn >> 16) & 0xFF
                self.midi[self.moff+4] = (mpqn >>  8) & 0xFF
                self.midi[self.moff+5] = (mpqn >>  0) & 0xFF
                self.moff += 6

        elif cmd == 0xC8: # Not sure.. calls SsUtVibrateOff ???
            # param & 0x7F
            if self.log: print("(Unknown, calls SsUtVibrateOff), Parameter: 0x%02X" % (param & 0x7F))
            if self.convert:
                self.midi[self.moff:self.moff+4] = b"\xFF\x01\x01\x3F"
                self.moff += 4

        elif cmd == 0xC9: # Set instrument
            if self.log: print("(Set Instrument), Parameter: 0x%02X" % (param & 0x7F))
            if self.convert:
                self.midi[self.moff+0] = 0xC0 | self.channel
                self.midi[self.moff+1] = param & 0x7F
                self.moff += 2

        elif cmd == 0xCA: # Note-off last note (reset running status)
            if self.log: print("(Note-off + reset running status)")
            if self.convert:
                self.midi[self.moff+0] = 0x80 | self.channel
                self.midi[self.moff+1] = self.note
                self.midi[self.moff+2] = 0
                self.moff += 3

        elif cmd == 0xCB: # Note-off last note (keep running status)
            if self.log: print("(Note-off + keep running status)")
            if self.convert:
                self.midi[self.moff+0] = 0x80 | self.channel
                self.midi[self.moff+1] = self.note
                self.midi[self.moff+2] = 0
                self.moff += 3

        elif cmd == 0xCC: # Set tempo, low (added between 1999-2001)
            # (param & 0x7F) & 0xFF
            if self.log: print("(Set Tempo, BPM=0-127), Parameter: 0x%02X" % (param & 0x7F))
            if self.convert:
                bpm = param & 0x7F
                mpqn = 60000000 // bpm
                self.midi[self.moff+0] = 0xFF
                self.midi[self.moff+1] = 0x51
                self.midi[self.moff+2] = 0x03
                self.midi[self.moff+3] = (mpqn >> 16) & 0xFF
                self.midi[self.moff+4] = (mpqn >>  8) & 0xFF
                self.midi[self.moff+5] = (mpqn >>  0) & 0xFF
                self.moff += 6

        elif cmd == 0xCD: # Set tempo, high (added between 1999-2001)
            # (param & 0x7F) | 0x80
            if self.log: print("(Set Tempo, BPM=128-255), Parameter: 0x%02X" % (param & 0x7F))
            if self.convert:
                bpm = (param & 0x7F) | 0x80
                mpqn = 60000000 // bpm
                self.midi[self.moff+0] = 0xFF
                self.midi[self.moff+1] = 0x51
                self.midi[self.moff+2] = 0x03
                self.midi[self.moff+3] = (mpqn >> 16) & 0xFF
                self.midi[self.moff+4] = (mpqn >>  8) & 0xFF
                self.midi[self.moff+5] = (mpqn >>  0) & 0xFF
                self.moff += 6

        elif cmd == 0xCE: # Reserved (does nothing) as of 2002 (added between 1999-2001)
            if self.log: print("(Reserved), Parameter: 0x%02X" % (param & 0x7F))
            if self.convert:
                self.midi[self.moff:self.moff+4] = b"\xFF\x01\x01\x3F"
                self.moff += 4

        elif cmd == 0xDB: # Reverb send amount? (or may at least affect reverb somehow it seems)
            # param & 0x??
            if self.log: print("(Reverb Send Amount?), Parameter: 0x%02X" % (param & 0x7F))
            if self.convert:
                self.midi[self.moff:self.moff+4] = b"\xFF\x01\x01\x3F"
                self.moff += 4

        elif cmd == 0xF6: # Tune request?
            # param & 0x??
            if self.log: print("(Tune Request?), Parameter: 0x%02X" % (param & 0x7F))
            if self.convert:
                self.midi[self.moff:self.moff+4] = b"\xFF\x01\x01\x3F"
                self.moff += 4

        elif cmd == 0xFF: # End of track
            if self.log: print("(End of track)")
            if self.convert:
                self.midi[self.moff+0] = 0xFF
                self.midi[self.moff+1] = 0x2F
                self.midi[self.moff+2] = 0x00
                self.moff += 3

        else:
            if self.log: print("(Unknown), Parameter: 0x%02X" % (param & 0x7F))
            if self.convert: # Remaining commands are probably a subset of Sony's SEQp or SCEIMidi format
                self.midi[self.moff:self.moff+4] = b"\xFF\x01\x01\x3F"
                self.moff += 4

    def read_note(self):
        self.note = self.buf[self.offset] & 0x7F
        self.velocity = self.buf[self.offset+1] & 0x7F
        self.running = self.buf[self.offset+1] & 0x80
        if self.log: 
            if self.velocity:
                print("0x%04X   NOTE-ON      Key: 0x%02X, Velocity: 0x%02X" % (self.offset - self.trk_off_start, self.note, self.velocity))
            else:
                print("0x%04X   NOTE-OFF     Key: 0x%02X" % (self.offset - self.trk_off_start, self.note))
        if self.convert:
            self.midi[self.moff+0] = (0x90 if self.velocity else 0x80) | self.channel
            self.midi[self.moff+1] = self.note
            self.midi[self.moff+2] = self.velocity
            # self.midi[self.moff+2] = int(127.0 * math.sqrt(self.velocity / 127.0))
            self.moff += 3
        self.offset += 2

    def read_delta_time(self):
        if self.log: print("0x%04X   DELTA-TIME   Time: " % (self.offset - self.trk_off_start), end="")
        if self.convert:
            self.midi[self.moff] = self.buf[self.offset]
            self.moff += 1
        self.time = self.buf[self.offset] & 0x7F
        more = self.buf[self.offset] & 0x80
        self.offset += 1
        while more:
            if self.convert:
                self.midi[self.moff] = self.buf[self.offset]
                self.moff += 1
            self.time <<= 7
            self.time |= self.buf[self.offset] & 0x7F
            more = self.buf[self.offset] & 0x80
            self.offset += 1
        if self.log: print("%d" % self.time)
        self.running = 1

    def read_seq(self):
        if not self.running:
            self.read_delta_time()
        else:
            if self.buf[self.offset] & 0x80:
                self.read_cmd()
            else:
                self.read_note()

            # instead of having delta-times of 0 between events, KDT1 uses the
            # MSB in the command parameter / note velocity to save some bytes
            if self.convert:
                if self.running:
                    if self.offset < self.trk_off_end:
                        self.midi[self.moff] = 0
                        self.moff += 1

    def find_cmd(self, cmd):
        cmd |= 0x80

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

def put_u16_be(n):
    return struct.pack(">H", n & 0xFFFF)

def put_u32_be(n):
    return struct.pack(">I", n & 0xFFFFFFFF)

def isnum(n):
    try:
        int(n)
    except ValueError:
        return False
    return True

def print_bgm_type(kdt):
    dynamic = False
    for trknum in range(2, kdt.tracks): # skip tracks 0 and 1
        for cmd in [0x87, 0x8B]:
            kdt.set_track(trknum)
            if kdt.find_cmd(cmd):
                volume = kdt.buf[kdt.offset+1] & 0x7F
                if volume == 0:
                    dynamic = True
    if dynamic:
        print("Dynamic: %s" % os.path.basename(kdt.path))
    else:
        print("Standard: %s" % os.path.basename(kdt.path))

def print_initial_track_volumes(kdt):
    basename = os.path.basename(kdt.path)
    for trknum in range(kdt.tracks):
        for cmd in [0x87, 0x8B]:
            kdt.set_track(trknum)
            if kdt.find_cmd(cmd):
                voltype = "main" if cmd == 0x87 else "ctrl"
                volume = kdt.buf[kdt.offset+1] & 0x7F
                print("%s: track %02d %s volume = 0x%02X" % (basename, trknum, voltype, volume))

def print_note_event_counts(kdt):
    basename = os.path.basename(kdt.path)
    for trknum in range(2, kdt.tracks): # skip tracks 0 and 1
        events = 0
        kdt.set_track(trknum)
        while kdt.offset < kdt.trk_off_end:
            if kdt.running:
                if kdt.buf[kdt.offset] < 0x80:
                    events += 1
            kdt.read_seq()

        print("%s: %d note events in track %02d" % (basename, events, trknum))
        # if events == 0:
        #     print("%s: no note events in track %02d" % (basename, trknum))

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
    out_path = os.path.splitext(kdt.path)[0]
    for filenum in range(kdt.tracks):
        out_buf = kdt.buf
        for trknum in range(kdt.tracks):
            for cmd in [0x87, 0x8B]: # try finding main/channel vol first, then controller vol
                kdt.set_track(trknum)
                if kdt.find_cmd(cmd):
                    if trknum < 2 or trknum == filenum:
                        if not out_buf[kdt.offset+1] & 0x7F:
                            out_buf[kdt.offset+1] |= 0x6E # demute (ALL initially demuted tracks in Silent Hill except track 2 of T.KDT and T2.KDT are initialized to 0x6E)
                    else:
                        out_buf[kdt.offset+1] &= 0x80 # isolate (keep status bit intact)

        with open("%s (track %02d).KDT" % (out_path, filenum), "wb") as out:
            out.write(out_buf)

# Creates a new KDT file with specified tracks demuted
def demute_and_isolate_specified_tracks_to_single_file(kdt, demute_args):
    if not demute_args:
        sys.exit("ERROR: No tracks to demute supplied")

    demute = []

    for arg in demute_args:
        if "-" in arg:
            if arg.count("-") == 1:
                start, end = arg.split("-")
                if isnum(start) and isnum(end):
                    start = int(start)
                    end = int(end)

                    if start > end:
                        start, end = end, start

                    if start > kdt.tracks-1:
                        start = kdt.tracks-1 if kdt.tracks else 0

                    if end > kdt.tracks-1:
                        end = kdt.tracks-1 if kdt.tracks else 0

                    if start == end:
                        if start not in demute:
                            demute.append(start)
                    else:
                        for n in range(start, end+1):
                            if n not in demute:
                                demute.append(n)
                else:
                    sys.exit("Invalid argument: %s" % arg)
            else:
                sys.exit("Invalid argument: %s" % arg)
        elif isnum(arg):
            n = int(arg)

            if n > kdt.tracks-1:
                n = kdt.tracks-1 if kdt.tracks else 0

            if n not in demute:
                demute.append(n)
        else:
            sys.exit("Invalid argument: %s" % arg)

    out_buf = kdt.buf

    for trknum in range(kdt.tracks):
        for cmd in [0x87, 0x8B]:
            kdt.set_track(trknum)
            if kdt.find_cmd(cmd):
                if trknum < 2 or trknum in demute:
                    if not out_buf[kdt.offset+1] & 0x7F:
                        out_buf[kdt.offset+1] |= 0x6E
                else:
                    out_buf[kdt.offset+1] &= 0x80

    i = 0
    tracks = []
    demute = sorted(demute)

    while i < len(demute):
        start = end = demute[i]
        i += 1
        while end + 1 in demute:
            end += 1
            i += 1
        if start == end:
            tracks.append("%02d" % start)
        else:
            tracks.append("%02d-%02d" % (start, end))

    if len(demute) == 1:
        out_path = "%s (track %s).KDT" % (os.path.splitext(kdt.path)[0], tracks[0])
    else:
        out_path = "%s (tracks %s).KDT" % (os.path.splitext(kdt.path)[0], ", ".join(tracks))

    with open(out_path, "wb") as out:
        out.write(out_buf)

def kdt2midi(path):
    kdt = KDT(path, convert=True)

    kdt.midi[0x00:0x04] = b"MThd"
    kdt.midi[0x04:0x08] = put_u32_be(6) # mthd size
    kdt.midi[0x08:0x0A] = put_u16_be(1) # midi type
    kdt.midi[0x0A:0x0C] = put_u16_be(kdt.tracks)
    kdt.midi[0x0C:0x0E] = put_u16_be(kdt.tickdiv)
    kdt.moff = 0x0E

    for trknum in range(kdt.tracks):
        kdt.set_track(trknum)

        mtrk_off_start = kdt.moff

        kdt.midi[kdt.moff:kdt.moff+4] = b"MTrk" # id
        kdt.moff += 4
        kdt.midi[kdt.moff:kdt.moff+4] = put_u32_be(0) # size (tmp)
        kdt.moff += 4
        kdt.midi[kdt.moff+0] = 0x00 # delta time
        kdt.midi[kdt.moff+1] = 0xFF # meta event
        kdt.midi[kdt.moff+2] = 0x03 # track/seq name
        kdt.midi[kdt.moff+3] = 0x08 # size
        kdt.moff += 4
        kdt.midi[kdt.moff:kdt.moff+8] = bytes("Track %02d" % trknum, encoding="ascii")
        kdt.moff += 8

        while kdt.offset < kdt.trk_off_end:
            kdt.read_seq()

        kdt.midi[mtrk_off_start+4:mtrk_off_start+8] = put_u32_be( kdt.moff - (mtrk_off_start + 8) )

    with open(os.path.splitext(kdt.path)[0] + ".midi", "wb") as midi:
        midi.write(kdt.midi[0:kdt.moff])

def main(argc=len(sys.argv), argv=sys.argv):
    path = os.path.realpath(argv[1])

    if not os.path.exists(path):
        sys.exit("ERROR: Invalid path")

    # for filename in os.listdir(path):
    #     filepath = os.path.join(path, filename)
    #     if os.path.splitext(filename)[1].upper() == ".KDT":
    #         print_note_event_counts(KDT(filepath))

    # demute_and_isolate_all_tracks_to_separate_files(KDT(path))

    # demute_and_isolate_specified_tracks_to_single_file(KDT(path), argv[2:])

    # print_events(KDT(path))

    kdt2midi(path)

    return 0

if __name__=="__main__":
    main()
