# Questions you will get, and honest answers

**Is this a proof that the photo is real?** No. Anyone with the engine can write a mark. It keeps honest metadata alive after sharing; it is not a tamper-proof seal.

**Can someone remove it?** Heavy denoising, AI retouching, tiny thumbnails (below ~600 px) or large crops can. It is robust against ordinary sharing, not against an attacker.

**Is it visible?** No: median PSNR about 41 dB, SSIM 0.998, at most about 10 grey levels in a few pixels. The README shows the hidden layer magnified.

**What does black & white do?** The colour layer (full record) is lost; the brightness layer keeps the location. 29 of 40 test photos at default strength, 39 of 40 when written at 2x. A grey copy that is also cropped is not found.

**Does it work on a screenshot / photo of a screen?** Screenshots yes. Photos of a monitor or print: yes with four tapped corners, slow (24-55 s on a phone), harsher in real life than in the simulator.

**Why not C2PA / Content Credentials?** C2PA signs metadata and is removed when metadata is stripped; Ghostmark survives the strip but is not cryptographically signed. They complement each other.

**Why not just upload the original?** If you control both ends, do. This is for the copies you do not control.

**Licence?** Apache-2.0. Keep the NOTICE; a credit line is appreciated.

**Is the Android app phone-tested?** The Kotlin engine passed 29 JVM tests and a trial app on a real phone. The Field Camera app that uses it is still in testing.

**Why is the Python engine slower?** Pure numpy, no native code: 2 s to mark and 0.5 s to read a 12 MP photo.
