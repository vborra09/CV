
from PIL import Image, ImageDraw
import numpy as np
import sys

THRESHOLD = 128
HIGH_THRESH = 0.99
LOW_THRESH = 0.95
DIFF_LIMIT = 3
MAX_BLACK_MARGIN = 3

def process(imagePath, tileSize):
   
    img = Image.open(imagePath).convert("L")
    img = img.point(lambda p: 1 if p > THRESHOLD else 0)
    arr = np.array(img)
    rows = arr.shape[0] // tileSize
    cols = arr.shape[1] // tileSize
    tiles = []
    for r in range(rows):
        for c in range(cols):
            t = arr[r * tileSize:(r + 1) * tileSize, c * tileSize:(c + 1) * tileSize]
            tiles.append({'tile': t, 'pos': (r, c)})
    
    
    ideals = []
    for t in tiles:
        tile = t['tile']
        if np.sum(tile[:, :1]) >= tileSize and (not np.all(tile == 1)) and np.any(tile[:, 1:] == 0):
            ideals.append(t)
    if len(ideals) > rows:
        for t in ideals:
            topBlack = np.sum(t['tile'][0, :] == 0)
            bottomBlack = np.sum(t['tile'][-1, :] == 0)
            t['tb_black'] = topBlack + bottomBlack
        base = max(ideals, key=lambda t: t['tb_black'])
        basetop = base['tile'][0, :]
        basebottom = base['tile'][-1, :]
        basetopidx = np.where(basetop == 0)[0]
        basebottomidx = np.where(basebottom == 0)[0]
        filtered = []
        later = []
        for t in ideals:
            if t is base:
                filtered.append(t)
                continue
            candtop = t['tile'][0, :]
            candbottom = t['tile'][-1, :]
            if len(basetopidx) > 0:
                if np.all(candtop == 1):
                    ratiotop = 0.0
                else:
                    ratiotop = np.sum(candtop[basetopidx] == 0) / len(basetopidx)
            else:
                ratiotop = 1.0
            if len(basebottomidx) > 0:
                if np.all(candbottom == 1):
                    ratiobottom = 0.0
                else:
                    ratiobottom = np.sum(candbottom[basebottomidx] == 0) / len(basebottomidx)
            else:
                ratiobottom = 1.0
            avgratio = (ratiotop + ratiobottom) / 2.0
            difftop = np.sum(np.abs(basetop[basetopidx] - candtop[basetopidx]))
            diffbottom = np.sum(np.abs(basebottom[basebottomidx] - candbottom[basebottomidx]))
            totaldiff = difftop + diffbottom
            if avgratio >= HIGH_THRESH and totaldiff <= DIFF_LIMIT:
                filtered.append(t)
            elif avgratio < LOW_THRESH:
                later.append(t)
            else:
                filtered.append(t)
        ideals = filtered
        if len(ideals) > rows:
            def vertCenter(info):
                tile = info['tile']
                black = np.where(tile[:, 0] == 0)[0]
                return np.mean(black) if len(black) > 0 else tile.shape[0] / 2
            ideals.sort(key=lambda t: vertCenter(t))
            ideals = ideals[:rows]
    used = {t['pos'] for t in ideals}
    remaining = [t for t in tiles if t['pos'] not in used]
    
    assembled = [[None for _ in range(cols)] for _ in range(rows)]
    for r in range(rows):
        if r < len(ideals):
            assembled[r][0] = ideals[r]
        elif remaining:
            assembled[r][0] = remaining.pop(0)
    def backtrack(pos):
        total = rows * cols
        while pos < total:
            r, c = divmod(pos, cols)
            if assembled[r][c] is not None:
                pos += 1
            else:
                break
        if pos >= total:
            return True
        r, c = divmod(pos, cols)
        candidates = []
        if c > 0:
            leftTile = assembled[r][c - 1]
            leftEdge = leftTile['tile'][:, -1]
            for t in remaining:
                candLeft = t['tile'][:, 0]
                diff = np.sum(np.abs(leftEdge - candLeft))
                candidates.append((t, diff))
            candidates.sort(key=lambda x: (x[1], -int(np.sum(x[0]['tile']))))
        else:
            for t in remaining:
                candidates.append((t, 0))
        for cand, diff in candidates:
            if c == cols - 1:
                rightEdge = cand['tile'][:, -1]
                if np.sum(rightEdge == 0) > MAX_BLACK_MARGIN:
                    continue
            assembled[r][c] = cand
            remCopy = remaining.copy()
            for i, t in enumerate(remaining):
                if id(t) == id(cand):
                    del remaining[i]
                    break
            if backtrack(pos + 1):
                return True
            assembled[r][c] = None
            remaining[:] = remCopy
        return False
    backtrack(0)
    
    newImg = Image.new('L', (cols * tileSize, rows * tileSize))
    for r in range(rows):
        for c in range(cols):
            if assembled[r][c] is not None:
                tileArr = assembled[r][c]['tile'] * 255
                tileImg = Image.fromarray(np.uint8(tileArr), mode='L')
                newImg.paste(tileImg, (c * tileSize, r * tileSize))
    newImg.show()

if __name__ == '__main__':
    if len(sys.argv) < 3:
        sys.exit()
    imagePath = sys.argv[1]
    tileSize = int(sys.argv[2])
    process(imagePath, tileSize)
