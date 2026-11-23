"""tools/photo_grid.py — measure face landmarks on a new presenter photo (for engine/photo2d.js).

  python tools/photo_grid.py --image path/to/photo.jpg [--out grid.png] [--box x0,y0,x1,y1] [--step 50]

Draws a labelled pixel grid over the face area. Open the PNG, read the pixel coordinates, and write them to
projects/<slug>/assets/mentor-landmarks.json (copy assets/mentor/landmarks.json as the template):
  image: file name next to it (put the photo in projects/<slug>/assets/)     size: [width, height] of the photo
  face: [x, y] centre of the face (between the eyes and mouth)
  eyeL / eyeR: [centreX, centreY, halfWidth, halfHeight] of each visible eye opening (viewer's left eye = eyeL)
  mouth: [centreX, lipLineY, halfWidth]   lipLineY = the line where the closed lips meet
Then render a still with "debug": true in drawPhotoMentor to check the cyan (eyes) and magenta (mouth) markers sit right.
Works for a front-facing, closed-mouth, neutral portrait. Open mouths, glasses covering the eyes, or turned heads will not animate well.
"""
import argparse
from PIL import Image, ImageDraw
ap = argparse.ArgumentParser(); ap.add_argument("--image", required=True); ap.add_argument("--out", default="photo_grid.png")
ap.add_argument("--box"); ap.add_argument("--step", type=int, default=50); a = ap.parse_args()
im = Image.open(a.image).convert("RGB"); W, H = im.size
box = tuple(int(v) for v in a.box.split(",")) if a.box else (int(W * 0.15), int(H * 0.15), int(W * 0.85), int(H * 0.6))
c = im.crop(box); k = min(1.6, 1400 / c.width); c = c.resize((int(c.width * k), int(c.height * k))); d = ImageDraw.Draw(c)
x0 = box[0] - box[0] % a.step + a.step
for x in range(x0, box[2], a.step):
    X = (x - box[0]) * k; d.line([(X, 0), (X, c.height)], fill=(0, 255, 255) if x % (a.step * 2) == 0 else (0, 120, 120)); d.text((X + 2, 2), str(x), fill=(255, 255, 0))
y0 = box[1] - box[1] % a.step + a.step
for y in range(y0, box[3], a.step):
    Y = (y - box[1]) * k; d.line([(0, Y), (c.width, Y)], fill=(0, 255, 255) if y % (a.step * 2) == 0 else (0, 120, 120)); d.text((2, Y + 2), str(y), fill=(255, 255, 0))
c.save(a.out); print(f"photo {W}x{H}; wrote {a.out} (crop {box}, scale {k:.2f}). Read the coordinates and fill in assets/mentor-landmarks.json")
