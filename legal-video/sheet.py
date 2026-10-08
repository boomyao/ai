# Tile stills into a contact sheet for quick visual review.
import sys, glob, os
from PIL import Image, ImageDraw
files = sys.argv[2:] or sorted(glob.glob('out/stills/*.png'))
cols = 3; w, h = 640, 360
rows = (len(files) + cols - 1) // cols
sheet = Image.new('RGB', (cols * w, rows * (h + 24)), (40, 40, 40))
d = ImageDraw.Draw(sheet)
for i, f in enumerate(files):
    im = Image.open(f).convert('RGB').resize((w, h), Image.LANCZOS)
    x, y = (i % cols) * w, (i // cols) * (h + 24)
    sheet.paste(im, (x, y + 24))
    d.text((x + 6, y + 4), os.path.basename(f), fill=(255, 255, 0))
sheet.save(sys.argv[1])
