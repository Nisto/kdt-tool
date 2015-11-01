# kdt-tool
General-purpose tool for Konami's sequenced music format "KDT1". Functions include:
- MIDI converter: converts KDT to MIDI
- Event parser: prints sequence events as human-readable text
- Track splitter: demutes and isolates all tracks to separate files, or specified tracks to a single file
- Some miscellaneous minor stuff

### Prerequisites
Python 3. The tool was developed under Python 3.4.2 and has NOT been tested with any other version.

### Usage
Simply download kdt-tool.py, then (at least if you're on Windows and installed Python 3 using the official MSI installer) you should be able to simply drop any valid KDT1 file onto the script file to convert it to MIDI.

The script currently takes no arguments other than a filepath, as it is currently set up only to convert, with ease of use in mind. So for now, you will have to hard-code calls to the other available functions if you so desire to use them.

`demute_and_isolate_all_tracks_to_separate_files` takes one argument (drag-n-drop possible):
- the path to a KDT1 file

Command-line example: kdt-tool.py FOO.KDT

<br>

`demute_and_isolate_specified_tracks_to_single_file` takes two arguments (must be called via a command-line):
- the path to a KDT1 file
- one or more arguments with tracks to demute and isolate

Command-line example: kdt-tool.py FOO.KDT 2 4 6-8 (combines tracks 2, 4, 6, 7 and 8)

### Known issues
MIDI conversion is not perfect, but it will get you notes, timing, track configuration and the most basic commands converted.

So far I have only tested the script with Silent Hill and Suikoden 2. There may be issues in calculating accurate tempos for other games that use sequence command 0xC7 to set the tempo, as this command appears to be using a (console-specific?) calculation to compensate for some kind of timing delay(?) Both Silent Hill and Suikoden 2 multiplies the tempo parameter by 2 and adds 2 (e.g. (29 * 2) + 2 = 60). However, using this equation (even for Silent Hill or Suikoden 2 themselves), the tempo will still sound off when converted to a standard MIDI and played back on any modern PC. In the KCET driver for Silent Hill 2 (PlayStation 2), the equation was changed to ((x * 2) + 10), which appears to give a more accurate real-world tempo, so I've decided to use it universally. If needed, change it in the sources and report your results please. Thanks!

For some reason, most conversions won't play well with Renoise. The main issue being that notes stop playing sooner than they should. I don't know what causes this and I have tried troubleshooting it without luck. I have examined the converted MIDIs, and even done some conversions manually from scratch, by hand (i.e. in a hex editor), and I'm left clueless.
