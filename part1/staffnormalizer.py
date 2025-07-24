import numpy as np
from PIL import Image, ImageDraw
import sys

THRESHOLD = 170
PERCENTAGE = 40
TARGETDISTANCE = 10
REGIONWIDTH = 50
MINGAP = 2

Image.MAX_IMAGE_PIXELS = None

def process_image(input_path, output_path):
    orig_img = np.array(Image.open(input_path).convert("L"))
    temp_thresh = np.where(orig_img < THRESHOLD, 0, 255).astype(np.uint8)
    best_ang = 0
    max_black = 0
    for a in range(180):
        rot = np.array(Image.fromarray(temp_thresh).rotate(a, resample=Image.NEAREST, expand=True, fillcolor=255))
        h = rot.shape[0]
        cnts = []
        for i in range(0, h - 1, 2):
            cnts.append(np.sum(rot[i:i+2, :] == 0))
        cnts = np.array(cnts)
        cur_max = np.max(cnts)
        if cur_max > max_black:
            max_black = cur_max
            best_ang = a
    img_rot = np.array(Image.fromarray(temp_thresh).rotate(best_ang, resample=Image.NEAREST, expand=True, fillcolor=255))
    rs = np.sum(img_rot == 0, axis=1)
    max_rs = np.max(rs)
    fill_th = 0.5 * max_rs
    groups = []
    grp_start = None
    for i in range(len(rs)):
        if rs[i] >= fill_th:
            if grp_start is None:
                grp_start = i
        else:
            if grp_start is not None:
                groups.append((grp_start, i-1))
                grp_start = None
    if grp_start is not None:
        groups.append((grp_start, len(rs)-1))
    for (s, e) in groups:
        grp = list(range(s, e+1))
        best_r = grp[0]
        best_val = rs[best_r]
        for r in grp:
            if rs[r] > best_val:
                best_val = rs[r]
                best_r = r
        for r in grp:
            if r != best_r:
                img_rot[r, :] = 255
            else:
                img_rot[r, :] = 0
    img_rot = np.where(img_rot < THRESHOLD, 0, 255).astype(np.uint8)
    black_counts = np.sum(img_rot == 0, axis=1)
    max_black_counts = np.max(black_counts)
    thresh_line = (PERCENTAGE / 100) * max_black_counts
    pot_lines = np.where(black_counts >= thresh_line)[0]
    staff_lines = []
    i = 0
    while i < len(pot_lines):
        grp = [pot_lines[i]]
        while i+1 < len(pot_lines) and (pot_lines[i+1] - pot_lines[i] <= MINGAP):
            grp.append(pot_lines[i+1])
            i += 1
        best_row = grp[0]
        best_val = black_counts[best_row]
        for r in grp:
            if black_counts[r] > best_val:
                best_val = black_counts[r]
                best_row = r
        staff_lines.append(best_row)
        i += 1
    diffs = np.diff(staff_lines)
    scales = []
    for d in diffs:
        if d > 0:
            scales.append(TARGETDISTANCE / d)
    if len(scales) > 0:
        scale_factor = sum(scales) / len(scales)
    else:
        scale_factor = 1.0
    orig_rot = np.array(Image.fromarray(orig_img).rotate(best_ang, resample=Image.BICUBIC, expand=True, fillcolor=255))
    new_h = int(orig_rot.shape[0] * scale_factor)
    new_w = int(orig_rot.shape[1] * scale_factor)
    orig_resized = np.array(Image.fromarray(orig_rot).resize((new_w, new_h), Image.Resampling.LANCZOS))
    bin_img = np.where(orig_resized < THRESHOLD, 1, 0)
    col_sum = np.sum(bin_img, axis=0)
    left_idx = np.argmax(col_sum > 0)
    reg_end = min(left_idx + REGIONWIDTH, orig_resized.shape[1])
    mass_orig = np.sum(bin_img[:, left_idx:reg_end])
    rotated_img = np.array(Image.fromarray(orig_resized).rotate(180, fillcolor=255))
    bin_rot = np.where(rotated_img < THRESHOLD, 1, 0)
    col_sum_rot = np.sum(bin_rot, axis=0)
    left_idx_rot = np.argmax(col_sum_rot > 0)
    reg_end_rot = min(left_idx_rot + REGIONWIDTH, rotated_img.shape[1])
    mass_rot = np.sum(bin_rot[:, left_idx_rot:reg_end_rot])
    if mass_rot > mass_orig:
        final_img = rotated_img
    else:
        final_img = orig_resized
    Image.fromarray(final_img).save(output_path)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("python staffnormalizer.py <inputimagepath> <outputimagepath>")
        sys.exit(1)
    process_image(sys.argv[1], sys.argv[2])
