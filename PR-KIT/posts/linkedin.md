# LinkedIn post

(attach `media/bw_demo.gif`, or upload the GIF as a video; first line is what shows before "see more")

---
Your photo can still know where it was taken, even after WhatsApp and a black-and-white filter.

Most people lose the GPS and time of a photo the moment it is shared: chat apps and screenshots strip the metadata. For anyone whose photos are evidence (site inspections, surveys, insurance) that is a real loss.

So I built Ghostmark: it hides the location, altitude and UTC time inside the pixels, invisibly, with error correction, in two independent layers. The colour layer carries the full record. The brightness layer carries the location, so it survives when someone turns the photo black & white.

I tested it on 40 real photos from 11 cameras (iPhones, OnePlus, vivo, realme, DJI drones): 480 edited copies, 0 wrong values, 0 false alarms. It also tells you honestly where it fails (fog, night, flat sky).

It is open source (Apache-2.0), with an Android library (Kotlin, 97 KB, no dependencies), a Python version for servers and scripts, and a JavaScript reference.

Everything, including the failures, is in the README with 18 charts and an animated reel for every photo:
github.com/thevijayparmar/Ghostmark-Image

Built with Prathvi Bhatti. If you work with field photos, I would love to hear what would make it useful for you.

#opensource #android #python #computervision #photography #engineering
