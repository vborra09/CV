#!/usr/bin/env python3


import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont



def image_pad(bin_img, pad_h, pad_w):

    H, W = bin_img.shape
    out = np.zeros((H + 2*pad_h, W + 2*pad_w), dtype=np.uint8)
    out[pad_h:pad_h+H, pad_w:pad_w+W] = bin_img
    return out


def morph_erosion(bin_img, struct):


    H, W = bin_img.shape
    sh, sw = struct.shape
    
    pad_h = sh // 2
    pad_w = sw // 2
    
    padded = image_pad(bin_img, pad_h, pad_w)
    
    out = np.zeros_like(bin_img)
    
    # Erosion
    for r in range(H):
        for c in range(W):
 
            region = padded[r:r+sh, c:c+sw]

            if np.sum(region * struct) == np.sum(struct):
                out[r, c] = 1
            else:
                out[r, c] = 0
    return out

def morph_dilation(bin_img, struct):

    H, W = bin_img.shape
    sh, sw = struct.shape
    
    pad_h = sh // 2
    pad_w = sw // 2
    padded = image_pad(bin_img, pad_h, pad_w)
    
    out = np.zeros_like(bin_img)
    
    # Dilation
    for r in range(H):
        for c in range(W):
            region = padded[r:r+sh, c:c+sw]

            if np.sum(region * struct) > 0:
                out[r, c] = 1
            else:
                out[r, c] = 0
    return out

def morph_closing(bin_img, struct):

    eroded = morph_erosion(bin_img, struct)
    closed = morph_dilation(eroded, struct)
    return closed


class s_bol:

    def __init__(self, x, y, w, h, sym_type, conf=0.0, pitch='_'):

        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.sym_type = sym_type
        self.conf = conf
        self.pitch = pitch
    
    def info_str(self):

        return f"{self.y} {self.x} {self.h} {self.w} {self.pitch} {self.conf}"


def staffl_detection(gray_img, close_len=25, gap_thresh=9):

    bin_img = (gray_img < 128).astype(np.uint8)
    
    struct = np.ones((1, close_len), dtype=np.uint8)
    closed_img = morph_closing(bin_img, struct)
    
    H, W = closed_img.shape
    line_rows = []
    for r in range(H):
        black_count = np.sum(closed_img[r, :] == 1)
        if black_count > (0.5 * W):
            line_rows.append(r)
    
    merged = []
    if line_rows:
        merged.append(line_rows[0])
        for i in range(1, len(line_rows)):
            if (line_rows[i] - line_rows[i-1]) >= gap_thresh:
                merged.append(line_rows[i])
    return merged

def treble_bass_grp(lines, big_jump=50):

    sorted_rows = sorted(lines)
    treble, bass = [], []
    if not sorted_rows:
        return treble, bass
    
    use_treble = True
    treble.append(sorted_rows[0])
    
    for i in range(1, len(sorted_rows)):
        if (sorted_rows[i] - sorted_rows[i-1]) > big_jump:

            use_treble = not use_treble
        if use_treble:
            treble.append(sorted_rows[i])
        else:
            bass.append(sorted_rows[i])
    return treble, bass

def lin_sp_estimation(lines):

    if len(lines) < 2:
        return 10
    first_four = sorted(lines)[:4]
    gaps = []
    for i in range(len(first_four) - 1):
        gaps.append(first_four[i+1] - first_four[i])
    if not gaps:
        return 10
    return int(sum(gaps)/len(gaps))


def inv_norm(pil_img):

    arr = np.array(pil_img.convert('L'), dtype=np.float32) / 255.0
    return 1.0 - arr



def corr_cross(m_arr, t_arr):

    H, W = m_arr.shape
    hT, wT = t_arr.shape
    
    score_map = np.zeros_like(m_arr)
    for r in range(H - hT):
        for c in range(W - wT):
            region = m_arr[r:r+hT, c:c+wT]
            score_map[r, c] = np.sum(region * t_arr)
    return score_map

def dtct_symbols(m_arr, t_arr, label, conf_thresh=0.9):

    score_map = corr_cross(m_arr, t_arr)
    max_val = score_map.max()
    if max_val <= 0:
        return []
    
    hT, wT = t_arr.shape
    found = []
    for r in range(score_map.shape[0]):
        for c in range(score_map.shape[1]):
            if score_map[r, c] >= (conf_thresh * max_val):
                confidence = (score_map[r, c] / max_val) * 100.0
                found.append(s_bol(x=c, y=r, w=wT, h=hT, 
                                    sym_type=label, 
                                    conf=round(confidence,2)))
    return found


def comp_iou(s_a, s_b):

    xA = max(s_a.x, s_b.x)
    yA = max(s_a.y, s_b.y)
    xB = min(s_a.x+s_a.w, s_b.x+s_b.w)
    yB = min(s_a.y+s_a.h, s_b.y+s_b.h)
    inter = max(0, xB - xA) * max(0, yB - yA)
    union = (s_a.w*s_a.h) + (s_b.w*s_b.h) - inter
    if union == 0:
        return 0.0
    return inter / union



def non_max_suppression(sym_list, comp_iou_thresh=0.05):

    sym_list = sorted(sym_list, key=lambda s: s.conf, reverse=True)
    final_list = []
    for s in sym_list:
        if not final_list:
            final_list.append(s)
        else:
            overlaps = [comp_iou(s, f) for f in final_list]
            if max(overlaps) < comp_iou_thresh:
                final_list.append(s)
    return final_list


filled  = 'H1.png'   # e.g. Filled note head
r_img = 'R1.png'   # Quarter rest
r_img2  = 'R2.png'   # Eighth rest

# (3.5, 'G') G is cutting 2nd line fron below
# (5.0, 'D') B is below 1st line from below.
# (4.5, 'D'),D is cutting 4th line from below.
# (2.5, 'A'), Middle one
# (1.0, 'D') 2nd line from top
# (2.0, 'B') middle line cutting

#treble_list =[(5.5,'B'),(5.0, 'D'),(3.5, 'G'),(2.5, 'A'),(2.0, 'B'),(1.0, 'D')]
#treble_list = [(5.5,'B'),(5.0, 'D'),(3.5, 'G'),(2.5, 'A'),(2.0, 'B'),(1.0, 'D'),(-2.0, 'D'), (-1.5, 'A'), (-1.0, 'G'), (-0.5, 'F'), (0.0, 'G'), (0.5, 'D'), (1.0, 'D'), (1.5, 'B'), (3.0, 'F'), (4.0, 'D'), (4.5, 'D'), (5.0, 'D')]
#bass_list = [(-1.5, 'C'), (1.0, 'E'), (-2.0, 'D'), (1.5, 'D'), (4.0, 'F'), (2.5, 'B'), (3.0, 'A'), (3.5, 'G'), (-1.0, 'B'), (5.0, 'D'), (2.0, 'D'), (-0.5, 'B'), (0.0, 'F'), (0.5, 'G'), (-2.0, 'C'), (-0.25, 'C'), (4.5, 'G')]

treble_list = [(5.5,'B'),(5.0, 'D'),(3.5, 'G'),(2.5, 'A'),
               (2.0, 'B'),(1.0, 'D'),(-2.0, 'D'), (-1.5, 'A'),
               (-1.0, 'G'), (-0.5, 'F'), (0.0, 'G'), (0.5, 'D'),
               (1.0, 'D'), (1.5, 'B'), (3.0, 'F'), (4.0, 'D'),
               (4.5, 'D'), (5.0, 'D')]
bass_list = [(-1.5, 'C'), (1.0, 'E'), (-2.0, 'D'), (1.5, 'D'),
             (4.0, 'F'), (2.5, 'B'), (3.0, 'A'), (3.5, 'G'),
             (-1.0, 'B'), (5.0, 'D'), (2.0, 'D'), (-0.5, 'B'),
             (0.0, 'F'), (0.5, 'G'), (-2.0, 'C'), (-0.25, 'C'),
             (4.5, 'G')]
             

def assign_pitch(s_bols, treble_rows, bass_rows, spacing):

    for s in s_bols:
        if s.sym_type != 'filled_note':
            continue
        
        center_y = s.y + (s.h // 2)
        
        assigned = False
        # Check treble lines first
        for t_row in treble_rows:
            if abs(center_y - t_row) < 6 * spacing:
                ratio_val = (center_y - t_row) / float(s.h)
                s.pitch = nearest_pitch(ratio_val, dict(treble_list))
                assigned = True
                break
        # If still not assigned, check bass
        if not assigned:
            for b_row in bass_rows:
                if abs(center_y - b_row) < 6 * spacing:
                    ratio_val = (center_y - b_row) / float(s.h)
                    s.pitch = nearest_pitch(ratio_val, dict(bass_list))
                    break
    return s_bols


def nearest_pitch(value, pitch_dict):

    best_key = None
    best_dist = 10000

    for i in range(-40, 101):
        candidate = i / 2.0  
        dist = abs(value - candidate)
        if dist < best_dist:
            best_dist = dist
            best_key = candidate
    return pitch_dict.get(best_key, '_')


def annotate_s_bols(pil_img, s_bols):
    if pil_img.mode != 'RGB':
        pil_img = pil_img.convert('RGB')

    draw_ctx = ImageDraw.Draw(pil_img)
    font = ImageFont.load_default()

    for sym in s_bols:

        if sym.sym_type == 'filled_note':
            rect_color = 'red'
        elif sym.sym_type == 'quarter_rest':
            rect_color = 'green'
        elif sym.sym_type == 'eighth_rest':
            rect_color = 'blue'
        else:

            rect_color = 'red'

        draw_ctx.rectangle([sym.x, sym.y, sym.x + sym.w, sym.y + sym.h],
                           outline=rect_color, width=2)

        if sym.sym_type == 'filled_note' and sym.pitch != '_':
            
            text_x = sym.x - 12 #text_x = sym.x - 15
            text_y = sym.y
            draw_ctx.text((text_x, text_y), sym.pitch, fill='red', font=font)

    return pil_img


def save_results(sym_list, out_txt="detected.txt"):

    with open(out_txt, 'w') as f:
        for s in sym_list:
            f.write(s.info_str() + "\n")




def main(input_image_path):

    original = Image.open(input_image_path)
    gray_arr = np.array(original.convert('L'), dtype=np.uint8)
    

    lines_found = staffl_detection(gray_arr, close_len=25, gap_thresh=8)
    treble_rows, bass_rows = treble_bass_grp(lines_found, big_jump=50)
    spacing = lin_sp_estimation(lines_found)

    

    m_arr = inv_norm(original)
    
    all_s_bols = []
    
       
    tmpl_fill = Image.open(filled)
    fill_arr = inv_norm(tmpl_fill)
    syms_f = dtct_symbols(m_arr, fill_arr, label='filled_note', conf_thresh=.98)
    syms_f = non_max_suppression(syms_f)
    all_s_bols.extend(syms_f)
    

    tmpl_quarter = Image.open(r_img)
    q_arr = inv_norm(tmpl_quarter)
    syms_q = dtct_symbols(m_arr, q_arr, label='quarter_rest', conf_thresh=0.98)
    syms_q = non_max_suppression(syms_q)
    all_s_bols.extend(syms_q)
    

    tmpl_eighth = Image.open(r_img2)
    e_arr = inv_norm(tmpl_eighth)
    syms_e = dtct_symbols(m_arr, e_arr, label='eighth_rest', conf_thresh=0.86)
    syms_e = non_max_suppression(syms_e)
    all_s_bols.extend(syms_e)
    

    final_syms = assign_pitch(all_s_bols, treble_rows, bass_rows, spacing)
    

    annotated = annotate_s_bols(original, final_syms)
    annotated.save("detected.png")
    save_results(final_syms, "detected.txt")
    print("\n Files saved as 'detected.png' and 'detected.txt'.")

if __name__ == '__main__':
    
    main(sys.argv[1])
