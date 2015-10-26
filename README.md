# kdt-tool
General-purpose tool for Konami's sequenced music format "KDT1". Functions include:
- MIDI converter: converts KDT to MIDI
- Event parser: prints sequence events as human-readable text
- Track splitter: demutes and isolates all tracks to separate files, or specified tracks to a single file
- Some miscellaneous minor stuff

### Prerequisites
All you need is Python 3. The tool was developed under Python 3.4.2 and has NOT been tested with any other version.

### Usage
Simply download kdt-tool.py, then (provided you're on Windows and installed Python 3 using the official MSI installer, you should be able to) simply drop any valid KDT1 file onto the script file to convert it to MIDI.

The script currently takes no arguments other than a filepath. So for now, you will have to hard-code calls to the other available functions if you so desire to use them.
