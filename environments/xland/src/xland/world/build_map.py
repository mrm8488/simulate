"""
Builds map using Wave Function Collapse.
"""

import os

import numpy as np
from PIL import Image
from wfc_binding import run_wfc

import simenv as sm

from ..utils import GRANULARITY, decode_rgb


def get_sides_and_bottom(x, y, z, down):
    """
    Get a bottom basis for the structured grid.

    The main goal of this function is to avoid having a surface
    floating. So, we add a ground a side meshs.

    Args:
        x: x coordinates
        y: y coordinates
        z: z coordinates
        down: z coordinates of the bottom
    """
    # TODO: generate 3d mesh with all of this
    # TODO: all of this is being done by hand. Ideally, we want a function
    # that handles all the cases without writing too much code.
    # We calculate the coordinates for each of the sides:
    xx_0 = x[0, :]
    yx_0 = [y[0, 0]] * 2
    xx_0, yx_0 = np.meshgrid(xx_0, yx_0)
    zx_0 = np.zeros(xx_0.shape)
    zx_0[0, :] = z[0, :]
    zx_0[1, :] = down

    xx_1 = x[-1, :]
    yx_1 = [y[-1, 0]] * 2
    xx_1, yx_1 = np.meshgrid(xx_1, yx_1)
    zx_1 = np.zeros(xx_1.shape)
    zx_1[0, :] = z[-1, :]
    zx_1[1, :] = down

    yy_0 = y[:, 0]
    xy_0 = [x[0, 0]] * 2
    xy_0, yy_0 = np.meshgrid(xy_0, yy_0)
    zy_0 = np.zeros(xy_0.shape)
    zy_0[:, 0] = z[:, 0]
    zy_0[:, 1] = down

    yy_1 = y[:, -1]
    xy_1 = [x[0, -1]] * 2
    xy_1, yy_1 = np.meshgrid(xy_1, yy_1)
    zy_1 = np.zeros(xy_1.shape)
    zy_1[:, 0] = z[:, -1]
    zy_1[:, 1] = down

    # Down base
    x_down = [x[0, 0], x[0, -1]]
    y_down = [y[0, 0], y[-1, 0]]
    x_down, y_down = np.meshgrid(x_down, y_down)
    z_down = np.full(x_down.shape, down)

    # We get each of the extra structures
    structures = [
        sm.StructuredGrid(x=x_down, y=y_down, z=z_down, name="bottom_surface"),
        sm.StructuredGrid(x=xx_0, y=yx_0, z=zx_0),
        sm.StructuredGrid(x=xx_1, y=yx_1, z=zx_1),
        sm.StructuredGrid(x=xy_0, y=yy_0, z=zy_0),
        sm.StructuredGrid(x=xy_1, y=yy_1, z=zy_1),
    ]

    return structures


def generate_2d_map(
    width,
    height,
    gen_folder,
    periodic_output=True,
    N=2,
    periodic_input=False,
    ground=False,
    nb_samples=1,
    symmetry=1,
    sample_from=None,
    seed=None,
):
    """
    Generate 2d map.

    Args:
        More information on the Args can be found on generate_map below.

    Returns:
        image: PIL image
    """
    # TODO: Open image if it's cached

    # Check if seed should be used
    if seed is not None:
        use_seed = True
    else:
        use_seed = False
        seed = 0

    # Otherwise, generate it
    if sample_from is not None:
        # Overlapping routine
        # Creates a new map from a previous one by sampling patterns from it
        # Need to transform string into bytes for the c++ function
        run_wfc(
            width,
            height,
            sample_type=1,
            input_img=sample_from.encode("utf-8"),
            periodic_output=periodic_output,
            N=N,
            periodic_input=periodic_input,
            ground=ground,
            nb_samples=nb_samples,
            symmetry=symmetry,
            use_seed=use_seed,
            seed=seed,
            dir_path=gen_folder.encode("utf-8"),
        )
        img_path = os.path.join(gen_folder, "maps/sample_0.png")

    else:
        # Simpletiled routine
        # Builds map from generated tiles and respective constraints
        run_wfc(
            width,
            height,
            sample_type=0,
            periodic_output=periodic_output,
            use_seed=use_seed,
            seed=seed,
            dir_path=gen_folder.encode("utf-8"),
        )
        img_path = os.path.join(gen_folder, "maps/tiles.png")

    # Read file
    img = Image.open(img_path)

    return img


def generate_map(
    width=None,
    height=None,
    periodic_output=False,
    final_tile_size=10,
    gen_folder=".gen_files",
    specific_map=None,
    sample_from=None,
    max_height=8,
    N=2,
    periodic_input=False,
    ground=False,
    nb_samples=1,
    symmetry=1,
    seed=None,
    engine=None,
):
    """
    Generate the map.

    Args:
        width: The width of the map.
        height: The height of the map.
        periodic_output: Whether the output should be toric (WFC param).
        final_tile_size: The size of the resulting tiles.
        gen_folder: where to find all generation necessary files.
        specific_map: if not None, use this map instead of generating one.
        sample_from: if not None, use this map as a sample from.
        max_height: maximum height of the map. For example, max_height=8 means that the map has
            8 different heights.
        N: size of patterns to be used by WFC.
        periodic_input: Whether the input is toric (WFC param).
        ground: Whether to use the lowest middle pattern to initialize the bottom of the map (WFC param).
        nb_samples: Number of samples to generate at once (WFC param).
        symmetry: Levels of symmetry to be used when sampling from a map. Values
            larger than one might imply in new tiles, which might be a unwanted behaviour
            (WFC param).
        seed: The seed to use for the generation of the map.
        engine: which engine to use on the scene.
    """

    if specific_map is not None:
        img = Image.open(os.path.join(gen_folder, "maps", specific_map + ".png"))
        width = img.width
        height = img.height

    else:
        img = generate_2d_map(
            width,
            height,
            gen_folder,
            sample_from=sample_from,
            periodic_output=periodic_output,
            N=N,
            periodic_input=periodic_input,
            ground=ground,
            nb_samples=nb_samples,
            symmetry=symmetry,
            seed=seed,
        )

    img_np = decode_rgb(img, specific_map=specific_map, sample_from=sample_from, max_height=max_height)

    # Let's say we want tiles of final_tile_size x final_tile_size pixels
    # TODO: change variables and make this clearer

    # We create the mesh centered in (0,0)
    x = np.linspace(-width * final_tile_size // 2, width * final_tile_size // 2, GRANULARITY * width)
    y = np.linspace(-height * final_tile_size // 2, height * final_tile_size // 2, GRANULARITY * height)

    # Create mesh grid
    x, y = np.meshgrid(x, y)

    # Nowm we create the z coordinates
    # First we split the procedurally generated image into tiles a format (:,:,2,2) in order to
    # do the interpolation and get the z values on our grid
    # TODO: this considers tiles of different sizes?
    img_np = np.array(np.hsplit(np.array(np.hsplit(img_np, width)), height))

    # Here, we create the mesh
    # As we are using tiles of two by two, first we have to find a interpolation on
    # the x axis for each tile
    # and then on the y axis for each tile
    # In order to do so, we can use np.linspace, and then transpose the tensor and
    # get the right order
    z_grid = np.linspace(img_np[:, :, :, 0], img_np[:, :, :, 1], GRANULARITY)
    z_grid = np.linspace(z_grid[:, :, :, 0], z_grid[:, :, :, 1], GRANULARITY)
    z_grid = np.transpose(z_grid, (2, 0, 3, 1)).reshape((height * GRANULARITY, width * GRANULARITY), order="A")

    # Create the mesh
    scene = sm.Scene(engine=engine)
    scene += sm.StructuredGrid(x=x, y=y, z=z_grid, name="top_surface")
    scene += get_sides_and_bottom(x, y, z_grid, down=-10)

    return (x, y, z_grid), np.array(img), scene