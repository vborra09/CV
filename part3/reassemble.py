import sys
import numpy as np
from PIL import Image



def load_scrambled_image(image_path, tile_size):
    #Load the scrambled image and split it into tiles.
    img = Image.open(image_path).convert("L")  # Convert to grayscale
    width, height = img.size

    tiles = []
    positions = []  ## Store tile positions (x, y)

    for y in range(0, height, tile_size):
        for x in range(0, width, tile_size):
            tile = img.crop((x, y, x + tile_size, y + tile_size))
            tiles.append(tile)
            positions.append((x, y))  # Store tile coordinates

    #print("Scrambled Image:")
    #display(img)
    return img, tiles, positions, width, height



def load_template(template_path):

    template = Image.open(template_path).convert("L")
    #print("Template Image:")
    #display(template)
    return template

def binarize_image(img, threshold=128):

    img_arr = np.array(img, dtype=np.uint8)
    return (img_arr < threshold).astype(np.uint8)



def corr_cross_black(m_arr, t_arr):

    H, W = m_arr.shape
    hT, wT = t_arr.shape
    score_map = np.zeros((H - hT + 1, W - wT + 1))  # Ensure valid range

    for r in range(H - hT + 1):
        for c in range(W - wT + 1):
            region = m_arr[r:r+hT, c:c+wT]
            score_map[r, c] = np.sum(region * t_arr)

    return score_map

def find_top_matching_tile(tiles, positions, template_bin):

    match_results = []

    for idx, tile in enumerate(tiles):
        tile_bin = binarize_image(tile)
        score_map = corr_cross_black(tile_bin, template_bin)
        max_score = np.max(score_map)  # Get highest similarity score
        match_results.append((max_score, tile, positions[idx]))  # Store (score, tile, position)

    match_results.sort(reverse=True, key=lambda x: x[0])  # Sort by highest match score
    best_tile, best_position = match_results[0][1], match_results[0][2]
    print(f"Best Match for Top-Left Tile at {best_position}")
    #display(best_tile)
    return best_tile, best_position
    

def compare_staff_edges(tile1, tile2, direction='right'):

    if direction == 'right': #  Top
        edge1 = tile1.crop((tile1.width-2, 0, tile1.width, tile1.height))
        edge2 = tile2.crop((0, 0, 2, tile2.height))
    else:  # 'bottom'
        edge1 = tile1.crop((0, tile1.height-2, tile1.width, tile1.height))
        edge2 = tile2.crop((0, 0, tile2.width, 2))
    diff = sum(abs(p1 - p2) for p1, p2 in zip(edge1.getdata(), edge2.getdata()))
    return diff



def build_first_column(tiles, positions, fixed_tile, fixed_position, tile_size, img_height):

    remaining_tiles = tiles.copy()
    remaining_tiles.remove(fixed_tile)
    current_column = [fixed_tile]

    #print("Building First Column:")
    while len(current_column) < img_height // tile_size:
        best_score = float('inf')
        best_tile = None
        for tile in remaining_tiles:
            score = compare_staff_edges(current_column[-1], tile, 'bottom')
            if score < best_score:
                best_score = score
                best_tile = tile
        current_column.append(best_tile)
        remaining_tiles.remove(best_tile)

        partial = Image.new('L', (tile_size, len(current_column) * tile_size))
        for i, t in enumerate(current_column):
            partial.paste(t, (0, i * tile_size))
        #display(partial)
    return current_column, remaining_tiles


def build_full_grid(first_column, remaining_tiles, tile_size, img_width, img_height):

    total_cols = img_width // tile_size
    total_rows = img_height // tile_size
    # Initialize grid with first column
    grid = [[tile] for tile in first_column]

    #print("Building Full Grid Column-by-Column:")
    for col in range(1, total_cols):
        for row in range(total_rows):
            best_score = float('inf')
            best_tile = None
            for candidate in remaining_tiles:

                score = compare_staff_edges(grid[row][col-1], candidate, 'right')                 ## Always use left edge matching
                if row > 0:                # If not the firstrow in this new column,add top edge matching
                    score += compare_staff_edges(grid[row-1][col], candidate, 'bottom')
                if score < best_score:
                    best_score = score
                    best_tile = candidate
            grid[row].append(best_tile)
            remaining_tiles.remove(best_tile)
        partial = Image.new('L', ((col+1) * tile_size, img_height))
        for r in range(total_rows):
            for c in range(col+1):
                partial.paste(grid[r][c], (c * tile_size, r * tile_size))
        #display(partial)
    return grid




def final_reconstruction(grid, tile_size, img_width, img_height):

    reconstructed = Image.new('L', (img_width, img_height))  ## Ensure correct size
    for row_idx, row in enumerate(grid):
        for col_idx, tile in enumerate(row):
            x = col_idx * tile_size
            y = row_idx * tile_size
            reconstructed.paste(tile, (x, y))
    #print("Final Reconstruction:")
    #display(reconstructed)
    return reconstructed





if __name__ == "__main__":

    if len(sys.argv) != 4:
        print('wrong input')

    scrambled_image_path = sys.argv[1]
    output_image_path = sys.argv[2]
    tile_size = int(sys.argv[3])

    template_image_path = "t3.png"

    scram_img, tiles, positions, img_width, img_height = load_scrambled_image(scrambled_image_path, tile_size)

    template_img = load_template(template_image_path)
    template_bin = binarize_image(template_img)

    top_left_tile, top_left_position = find_top_matching_tile(tiles, positions, template_bin)

    first_column, remaining_tiles = build_first_column(
        tiles, positions, top_left_tile, top_left_position, tile_size, img_height
    )

    full_grid = build_full_grid(first_column, remaining_tiles, tile_size, img_width, img_height)

    final_img = final_reconstruction(full_grid, tile_size, img_width, img_height)

    final_img.save(output_image_path)
    print(f"Reassembled image saved to {output_image_path}")
