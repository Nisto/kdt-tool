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

### Support ❤️

As of June 2024, my monthly salary has been cut by 50%. This has had a significant impact on my freedom and ability to spend as much time working on my projects, especially due to electricity bills. I don't like asking for favors or owing people anything, but if you do appreciate this work and happen to have some funds to spare, I would greatly appreciate any and all donations. All of your contributions goes towards essential everyday expenses. Every little bit helps! Thank you ❤️

**PayPal:** https://paypal.me/nisto7777  
**Buy Me a Coffee:** https://buymeacoffee.com/nisto  
**Bitcoin:** 18LiBhQzHiwFmTaf2z3zwpLG7ALg7TtYkg
