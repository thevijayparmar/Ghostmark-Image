# X / Twitter thread (attach media/bw_demo.gif to tweet 1)

1/ Turn a photo black & white, send it on WhatsApp... and it can still tell you where it was taken. 👻
Ghostmark hides location + time inside the pixels. Open source. 🧵

2/ Why: chat apps and screenshots strip EXIF. The photo becomes "just a picture". For site inspections, surveys and insurance that is a real loss.

3/ How: two invisible layers. Colour = full record (lat, lon, altitude, UTC time). Brightness = location only, so it survives a B&W filter. Error-correcting code: it returns the right record or an honest "damaged", never a guess.

4/ Tested on 40 real photos from 11 cameras (iPhones, OnePlus, vivo, realme, DJI drones): 480 edited copies, 371 full reads, 0 wrong values, 0 false alarms. Failures are in the README too (fog, night, small crops). [attach media/photo_wall.jpg]

5/ Android (Kotlin, 97 KB, zero deps) + Python (numpy) + JS. Same format; they read each other's marks.
Apache-2.0 → github.com/thevijayparmar/Ghostmark-Image
