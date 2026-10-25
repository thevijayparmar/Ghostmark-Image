# Social images v3: use-cases (1920x1080)

Field inspection, surveys, site reports, evidence, travel: what it looks like when the location *stays*. Every value on every image is decoded from a real marked, compressed copy. Inspection/site/drone images carry **demo coordinates** (stated on the image); travel images (07, 08) carry the photos' own GPS and time. Rebuild: `cd tools && PYTHONPATH=../python python make_social_v3.py`.

| # | File | Use case | Caption |
|---|---|---|---|
| 1 | `01_inspector-hud.png` | structural inspection | Found the defect. The photo carries its own location: lat, lon, altitude, UTC time. Still there after a chat app. |
| 2 | `02_site-map.png` | multi-site progress | 8 site photos, 8 pins on the map. Nobody typed a coordinate. |
| 3 | `03_stamp.png` | evidence / claims | Sent on chat, stamped by the pixels. No EXIF needed. |
| 4 | `04_one-flight.png` | drone survey | One flight, 8 frames, 8 locations, read from the pixels (not from the metadata). |
| 5 | `05_group-chat.png` | team on a group chat | The site photos came in on the group chat. The locations came with them. |
| 6 | `06_site-report.png` | reporting | Six photos from the chat, six captions that were read, not typed. |
| 7 | `07_lower-third.png` | journalism / verification | A photo that arrived through a chat, with no metadata, and its location and time recovered. |
| 8 | `08_contact-sheet.png` | travel memories | Every frame remembers where and when. The stamp was read from the photo, not printed on it. |
| 9 | `09_forwarded-four-times.png` | real-life sharing | Forwarded four times, resized and recompressed each time: still knows where it is (copy 4: location only, shown honestly). |
| 10 | `10_safety-board.png` | safety-culture humour | Safety first. Also: know where the photo was taken. 0 wrong locations in 480 edited copies. |

Post tip: use 5 and 2 for field teams, 4 for drone people, 1 and 3 for inspectors/insurance, 7 for journalists, 8 and 9 for general audience, 10 for a smile.
