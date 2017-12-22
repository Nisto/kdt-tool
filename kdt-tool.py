import os
import sys
import struct

class KDT:

    SIZE_LIMIT = 50*1024*1024

    HEADER_SIZE = 0x10

    OFF_FILE_SIZE   = 0x04
    OFF_TICKDIV     = 0x08
    OFF_TRACK_COUNT = 0x0C
    OFF_TRACK_SIZES = 0x10

    def __init__(self, path, log=False, convert=False):
        self.path = path
        self.log = log
        self.convert = convert

        if os.path.getsize(self.path) > KDT.SIZE_LIMIT:
            sys.exit("ERROR: File too large: %s" % self.path)

        with open(self.path, "rb") as kdt:
            self.buf = kdt.read()[0x30:]

        if self.buf[:4] != b"KDT1" or os.path.getsize(self.path) < KDT.HEADER_SIZE:
            sys.exit("ERROR: Not a valid KDT1 file: %s" % self.path)

        self.filesize = struct.unpack("<I", self.buf[KDT.OFF_FILE_SIZE:KDT.OFF_FILE_SIZE+4])[0]
        self.tickdiv = struct.unpack("<H", self.buf[KDT.OFF_TICKDIV:KDT.OFF_TICKDIV+2])[0]
        self.tracks = struct.unpack("<H", self.buf[KDT.OFF_TRACK_COUNT:KDT.OFF_TRACK_COUNT+2])[0]

        self.bpm = 120

        if self.filesize > os.path.getsize(self.path):
            sys.exit("ERROR: Indicated filesize exceeds actual filesize: %s" % self.path)

        self.buf = bytearray(self.buf[:self.filesize])

        if self.convert:
            self.midi = bytearray(self.filesize * 4)
            self.moff = 0

        if self.tracks > 0:

            self.trk_size_tbl = []

            self.trk_off_tbl = []

            self.offset = KDT.OFF_TRACK_SIZES + 2 * self.tracks

            track_size_table = self.buf[KDT.OFF_TRACK_SIZES : self.offset]

            for track_size in struct.iter_unpack("<H", track_size_table):

                self.trk_size_tbl.append(track_size[0])

                self.trk_off_tbl.append(self.offset)

                self.offset += track_size[0]

            self.set_track(0)

    def set_track(self, trknum):
        self.trknum        = trknum
        self.trk_size      = self.trk_size_tbl[trknum]
        self.trk_off_start = self.trk_off_tbl[trknum]
        self.trk_off_end   = self.trk_off_start + self.trk_size
        self.offset        = self.trk_off_start
        self.time          = 0
        self.running       = 0
        self.channel       = 0

    def read_cmd(self):
        cmd = self.buf[self.offset] & 0x7F

        param = None

        if cmd == 0x4A:
            self.running = 0
            self.offset += 1
        elif cmd == 0x4B:
            self.running = 1
            self.offset += 1
        else:
            param = self.buf[self.offset+1] & 0x7F
            self.running = self.buf[self.offset+1] & 0x80
            self.offset += 2

        if self.log:
            print("%-11s" % ("0x%02X" % cmd), end="")
            print("%-24s" % (("0x%02X" % param) if param is not None else ""), end="")

        if cmd == 0x01:
            if self.log: print("Modulation")
            if self.convert:
                self.midi[self.moff+0] = 0xB0 | self.channel
                self.midi[self.moff+1] = 0x01
                self.midi[self.moff+2] = param
                self.moff += 3

        elif cmd == 0x06:
            if self.log: print("Data Entry")
            if self.convert:
                self.midi[self.moff+0] = 0xB0 | self.channel
                self.midi[self.moff+1] = 0x06
                self.midi[self.moff+2] = param
                self.moff += 3

        elif cmd == 0x07:
            if self.log: print("Set Volume (Channel)")
            if self.convert:
                self.midi[self.moff+0] = 0xB0 | self.channel
                self.midi[self.moff+1] = 0x07
                self.midi[self.moff+2] = param
                self.moff += 3

        elif cmd == 0x0A:
            if self.log: print("Set Panning")
            if self.convert:
                self.midi[self.moff+0] = 0xB0 | self.channel
                self.midi[self.moff+1] = 0x0A
                self.midi[self.moff+2] = param
                self.moff += 3

        elif cmd == 0x0B:
            if self.log: print("Set Volume (Expression)")
            if self.convert:
                self.midi[self.moff+0] = 0xB0 | self.channel
                self.midi[self.moff+1] = 0x0B
                self.midi[self.moff+2] = param
                self.moff += 3

        elif cmd == 0x0F:
            if self.log: print("Stereo Widening (?)")
            if self.convert:
                self.midi[self.moff:self.moff+22] = b"\xFF\x01\x13Stereo Widening (?)"
                self.moff += 22

        elif cmd == 0x40:
            if self.log: print("Damper/Sustain Pedal")
            if self.convert:
                self.midi[self.moff+0] = 0xB0 | self.channel
                self.midi[self.moff+1] = 0x40
                self.midi[self.moff+2] = param
                self.moff += 3

        elif cmd == 0x46:
            self.channel = param & 0x0F
            if self.log: print("Set Channel")
            if self.convert:
                # the tenth channel is the "drum channel" and could result in a
                # quiet track (both in Awave and fb2k)
                if self.channel >= 9:
                    self.channel = (self.channel+1) & 0x0F
                self.midi[self.moff:self.moff+14] = b"\xFF\x01\x0BSet Channel"
                self.moff += 14

        elif cmd == 0x47:
            self.bpm = min(10+param*2, 255)
            if self.log: print("Set Tempo (10-255 BPM, divisible by two)")
            if self.convert:
                # microseconds per quarter-note (beat) = microseconds per minute / beats per minute
                mpqn = 60000000 // self.bpm
                self.midi[self.moff+0] = 0xFF
                self.midi[self.moff+1] = 0x51
                self.midi[self.moff+2] = 0x03
                self.midi[self.moff+3] = (mpqn >> 16) & 0xFF
                self.midi[self.moff+4] = (mpqn >>  8) & 0xFF
                self.midi[self.moff+5] = (mpqn >>  0) & 0xFF
                self.moff += 6

        elif cmd == 0x48:
            if self.log: print("Pitch Bend")
            if self.convert:
                self.midi[self.moff+0] = 0xE0 | self.channel
                self.midi[self.moff+1] = 0 # LSB (cents)
                self.midi[self.moff+2] = param # MSB (semitones)
                self.moff += 3

        elif cmd == 0x49:
            if self.log: print("Set Instrument")
            if self.convert:
                self.midi[self.moff+0] = 0xC0 | self.channel
                self.midi[self.moff+1] = param
                self.moff += 2

        elif cmd == 0x4A:
            if self.log: print("Note Off Last Note (Reset Running Status)")
            if self.convert:
                self.midi[self.moff+0] = 0x80 | self.channel
                self.midi[self.moff+1] = self.note
                self.midi[self.moff+2] = 0
                self.moff += 3

        elif cmd == 0x4B:
            if self.log: print("Note Off Last Note (Sustain Running Status)")
            if self.convert:
                self.midi[self.moff+0] = 0x80 | self.channel
                self.midi[self.moff+1] = self.note
                self.midi[self.moff+2] = 0
                self.moff += 3

        elif cmd == 0x4C:
            self.bpm = param & 0x7F
            if self.log: print("Set Tempo (0-127 BPM)")
            if self.convert:
                mpqn = 60000000 // self.bpm
                self.midi[self.moff+0] = 0xFF
                self.midi[self.moff+1] = 0x51
                self.midi[self.moff+2] = 0x03
                self.midi[self.moff+3] = (mpqn >> 16) & 0xFF
                self.midi[self.moff+4] = (mpqn >>  8) & 0xFF
                self.midi[self.moff+5] = (mpqn >>  0) & 0xFF
                self.moff += 6

        elif cmd == 0x4D:
            self.bpm = param | 0x80
            if self.log: print("Set Tempo (128-255 BPM)")
            if self.convert:
                mpqn = 60000000 // self.bpm
                self.midi[self.moff+0] = 0xFF
                self.midi[self.moff+1] = 0x51
                self.midi[self.moff+2] = 0x03
                self.midi[self.moff+3] = (mpqn >> 16) & 0xFF
                self.midi[self.moff+4] = (mpqn >>  8) & 0xFF
                self.midi[self.moff+5] = (mpqn >>  0) & 0xFF
                self.moff += 6

        elif cmd == 0x5B:
            if self.log: print("Set Reverb Depth")
            if self.convert:
                self.midi[self.moff+0] = 0xB0 | self.channel
                self.midi[self.moff+1] = 0x5B
                self.midi[self.moff+2] = param
                self.moff += 3

        elif cmd == 0x62:
            if self.log: print("NRPN (LSB)")
            if self.convert:
                self.midi[self.moff:self.moff+13] = b"\xFF\x01\x0ANRPN (LSB)"
                self.moff += 13

        elif cmd == 0x63:
            if param == 0x14:
                if self.log: print("Loop Start")
                if self.convert:
                    self.midi[self.moff:self.moff+13] = b"\xFF\x01\x0ALoop Start"
                    self.moff += 13
            elif param == 0x1E:
                if self.log: print("Loop End")
                if self.convert:
                    self.midi[self.moff:self.moff+11] = b"\xFF\x01\x08Loop End"
                    self.moff += 11
            else:
                if self.log: print("NRPN (MSB)")
                if self.convert:
                    self.midi[self.moff:self.moff+13] = b"\xFF\x01\x0ANRPN (MSB)"
                    self.moff += 13

        elif cmd == 0x76:
            if self.log: print("Seq Beat")
            if self.convert:
                self.midi[self.moff:self.moff+11] = b"\xFF\x01\x08Seq Beat"
                self.moff += 11

        elif cmd == 0x7F:
            if self.log: print("End of Track")
            if self.convert:
                self.midi[self.moff+0] = 0xFF
                self.midi[self.moff+1] = 0x2F
                self.midi[self.moff+2] = 0x00
                self.moff += 3

        else:
            if self.log: print("Unknown")
            if self.convert:
                self.midi[self.moff:self.moff+4] = b"\xFF\x01\x01\x3F"
                self.moff += 4

    def read_note(self):
        self.note = self.buf[self.offset] & 0x7F
        self.velocity = self.buf[self.offset+1] & 0x7F
        self.running = self.buf[self.offset+1] & 0x80
        self.offset += 2
        if self.log: print(
            "%-11s%s" % (
                "0x%02X" % self.note,
                "0x%02X" % self.velocity
            )
        )
        if self.convert:
            self.midi[self.moff+0] = (0x90 if self.velocity else 0x80) | self.channel
            self.midi[self.moff+1] = self.note
            self.midi[self.moff+2] = self.velocity
            self.moff += 3

    def read_delta_time(self):
        if self.convert:
            self.midi[self.moff] = self.buf[self.offset]
            self.moff += 1
        ticks = self.buf[self.offset] & 0x7F
        more = self.buf[self.offset] & 0x80
        self.offset += 1
        while more:
            if self.convert:
                self.midi[self.moff] = self.buf[self.offset]
                self.moff += 1
            ticks <<= 7
            ticks |= self.buf[self.offset] & 0x7F
            more = self.buf[self.offset] & 0x80
            self.offset += 1
        if self.log: print("%d" % ticks)
        self.time += ticks
        self.running = 1

    def read_seq(self):
        if self.log:
            print("%-10s" % ("0x%04X" % (self.offset - self.trk_off_start)), end="")

            mm, ss = divmod(self.time * 60 / self.tickdiv / self.bpm, 60)

            print("%-22s" % ("%d (%02d:%07.4f)" % (self.time, int(mm), ss)), end="")

        if not self.running:
            if self.log: print("%-11s" % "Time", end="")
            self.read_delta_time()
        else:
            if self.buf[self.offset] & 0x80:
                if self.log: print("%-11s" % "Command", end="")
                self.read_cmd()
            else:
                if self.log: print("%-11s" % "Key", end="")
                self.read_note()

            # instead of having delta-times of 0 between events, KDT1 uses the
            # MSB in the command parameter / note velocity to save some bytes
            if self.convert:
                if self.running:
                    if self.offset < self.trk_off_end:
                        self.midi[self.moff] = 0
                        self.moff += 1

def kdt2midi(path):
    kdt = KDT(path, log=False, convert=True)

    # 0x00: file format identifier
    kdt.midi[kdt.moff:kdt.moff+4] = b"MThd"
    kdt.moff += 4

    # 0x04: size of header: 6
    kdt.midi[kdt.moff:kdt.moff+4] = b"\x00\x00\x00\x06"
    kdt.moff += 4

    # 0x08: MIDI type: 1
    kdt.midi[kdt.moff:kdt.moff+2] = b"\x00\x01"
    kdt.moff += 2

    # 0x0A: number of tracks
    kdt.midi[kdt.moff:kdt.moff+2] = struct.pack(">H", kdt.tracks)
    kdt.moff += 2

    # 0x0C: pulses per quarter-note
    kdt.midi[kdt.moff:kdt.moff+2] = struct.pack(">H", kdt.tickdiv)
    kdt.moff += 2

    for trknum in range(kdt.tracks):
        kdt.set_track(trknum)

        mtrkoff = kdt.moff

        # 0x00: track chunk identifier
        kdt.midi[kdt.moff:kdt.moff+4] = b"MTrk"
        kdt.moff += 4

        # 0x04: track size (temporary)
        kdt.midi[kdt.moff:kdt.moff+4] = b"\x00\x00\x00\x00"
        kdt.moff += 4

        # 0x08: delta time | meta event | meta type: track name | length of track name
        kdt.midi[kdt.moff:kdt.moff+4] = b"\x00\xFF\x03\x08"
        kdt.moff += 4

        # 0x0C: track name
        kdt.midi[kdt.moff:kdt.moff+8] = b"Track %02d" % trknum
        kdt.moff += 8

        while kdt.offset < kdt.trk_off_end:
            kdt.read_seq()

        kdt.midi[mtrkoff+4:mtrkoff+8] = struct.pack(">I", kdt.moff-mtrkoff-8)

    with open(os.path.splitext(kdt.path)[0] + ".midi", "wb") as midi:
        midi.write(kdt.midi[:kdt.moff])

def dump_events(path):
    kdt = KDT(path, log=True, convert=False)

    for trknum in range(kdt.tracks):

        kdt.set_track(trknum)

        print("TRACK %02d (0x%04X)" % (trknum, kdt.offset))
        print("========================================================================================================================")
        print("Offset    Time                  Event      Value      Parameter / Velocity    Description")
        print()

        while kdt.offset < kdt.trk_off_end:

            kdt.read_seq()

        print("\n" * 5)

def main(argc=len(sys.argv), argv=sys.argv):

    if argc != 3:
        script_name = os.path.basename(argv[0])
        print("Usage:")
        print("  Convert to MIDI: %s -c <path>" % script_name)
        print("  Dump event data: %s -l <path>" % script_name)
        return 1

    path = os.path.realpath(argv[-1])

    if not os.path.isfile(path):
        print("ERROR: Invalid path")
        return 1

    if argv[1] == '-c':
        kdt2midi(path)
    elif argv[1] == '-l':
        dump_events(path)
    else:
        print("ERROR: Invalid command line")
        return 1

    return 0

if __name__=="__main__":
    main()
