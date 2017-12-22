# kdt-tool
General-purpose tool for Konami's sequenced music format "KDT1" allowing you to:
* Convert a file to MIDI
* Dump event data in a human-readable format

### Prerequisites
* Python 3

### Usage
* Convert to MIDI: `kdt-tool.py` `-c` `path to .KDT file`
* Dump event data: `kdt-tool.py` `-l` `path to .KDT file`

### Known issues
MIDI conversion is not perfect, but it will get you notes, timing, track configuration and the most basic commands converted. The remaining events which needs support is likely a subset stemming from Sony's SEQp format and should be relatively easy to add hopefully, but I have not had the time to really look into it.

So far I have only tested the script with Silent Hill and Suikoden 2. There may be issues in calculating accurate tempos for other games that use sequence command 0xC7 to set the tempo, as this command appears to be using a (console-specific?) calculation to compensate for some kind of timing delay(?) Both Silent Hill and Suikoden 2 multiplies the tempo parameter by 2 and adds 2 (e.g. (29 * 2) + 2 = 60). However, using this equation (even for Silent Hill or Suikoden 2 themselves), the tempo will still sound off when converted to a standard MIDI and played back on any modern PC. In the KCET driver for Silent Hill 2 (PlayStation 2), the equation was changed to ((x * 2) + 10), which appears to give a more accurate real-world tempo, so I've decided to use it universally. If needed, change it in the sources and report your results please. Thanks!
