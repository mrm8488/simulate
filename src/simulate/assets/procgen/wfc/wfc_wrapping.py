# Copyright 2022 The HuggingFace Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Lint as: python3
"""Python wrapper for constructors of C++ classes."""

from typing import Any, List, Optional, Tuple

import numpy as np

from wfc_binding import build_neighbor, build_tile, run_wfc, transform_to_id_pair


def build_wfc_neighbor(left: str, right: str, left_or: int = 0, right_or: int = 0) -> Any:
    """
    Builds neighbors.
    """
    return build_neighbor(left=bytes(left, "UTF_8"), left_or=left_or, right=bytes(right, "UTF_8"), right_or=right_or)


def build_wfc_tile(tile: List[int], name: str, symmetry: str = "L", weight: int = 1, size: int = 0) -> np.ndarray:
    """
    Builds tiles.
    """
    return build_tile(
        size=size, tile=tile, name=bytes(name, "UTF_8"), symmetry=bytes(symmetry, "UTF_8"), weight=weight
    )


def preprocess_tiles(
    tiles: np.ndarray, symmetries: Optional[np.ndarray] = None, weights: Optional[np.ndarray] = None
) -> Tuple[list, dict, dict, tuple]:
    n_tiles, tile_w, tile_h = tiles.shape
    tile_shape = tile_w, tile_h

    if symmetries is None:
        symmetries = ["L"] * n_tiles

    if weights is None:
        weights = [1] * n_tiles

    tiles = [tuple(map(tuple, tile)) for tile in tiles]

    idx_to_tile = {i: tiles[i] for i in range(n_tiles)}
    tile_to_idx = {tiles[i]: i for i in range(n_tiles)}

    converted_tiles = [
        build_wfc_tile(
            size=1,
            tile=[i],
            name=str(i),
            symmetry=symmetries[i],
            weight=weights[i],
        )
        for i in range(n_tiles)
    ]

    return converted_tiles, idx_to_tile, tile_to_idx, tile_shape


def preprocess_neighbors(neighbors: np.ndarray, tile_to_idx: dict) -> list:
    """
    Preprocesses tiles.
    """
    preprocessed_neighbors = []

    for neighbor in neighbors:
        preprocessed_neighbor = (
            str(tile_to_idx[tuple(map(tuple, neighbor[0]))]),
            str(tile_to_idx[tuple(map(tuple, neighbor[1]))]),
            *neighbor[2:],
        )

        preprocessed_neighbors.append(build_wfc_neighbor(*preprocessed_neighbor))

    return preprocessed_neighbors


def preprocess_tiles_and_neighbors(
    tiles: np.ndarray,
    neighbors: np.ndarray,
    symmetries: Optional[np.ndarray] = None,
    weights: Optional[np.ndarray] = None,
) -> Tuple[list, list, dict, tuple]:
    """
    Preprocesses tiles.
    """
    converted_tiles, idx_to_tile, tile_to_idx, tile_shape = preprocess_tiles(tiles, symmetries, weights)
    converted_neighbors = preprocess_neighbors(neighbors, tile_to_idx)

    return converted_tiles, converted_neighbors, idx_to_tile, tile_shape


def preprocess_input_img(input_img: np.ndarray) -> Tuple[list, dict, tuple]:
    """
    Preprocesses input image by extracting the tiles.
    """
    w, h, tile_w, tile_h = input_img.shape
    tile_shape = tile_w, tile_h
    input_img = np.reshape(input_img, (-1, tile_w, tile_h))
    tuple_input_img = [tuple(map(tuple, tile)) for tile in input_img]

    tile_to_idx = {}
    idx_to_tile = {}

    counter = 0
    for i in range(w * h):
        if tuple_input_img[i] not in tile_to_idx:
            tile_to_idx[tuple_input_img[i]] = counter
            idx_to_tile[counter] = input_img[i]
            counter += 1

    converted_input_img = [transform_to_id_pair(tile_to_idx[tile]) for tile in tuple_input_img]

    return converted_input_img, idx_to_tile, tile_shape


def get_tiles_back(
    gen_map: np.ndarray, tile_conversion: dict, nb_samples: int, width: int, height: int, tile_shape: tuple
) -> np.ndarray:
    """
    Returns tiles back.
    """
    gen_map = np.reshape(gen_map, (nb_samples * width * height, 3))
    converted_map = []

    for i in range(nb_samples * width * height):
        # Rotate and reflect single tiles / patterns
        converted_tile = np.rot90(tile_conversion[gen_map[i][0]], gen_map[i][1])
        if gen_map[i][2] == 1:
            converted_tile = np.fliplr(converted_tile)
        converted_map.append(converted_tile)

    return np.reshape(np.array(converted_map), (nb_samples, width, height, *tile_shape))


def apply_wfc(
    width: int,
    height: int,
    input_img: Optional[np.ndarray] = None,
    tiles: Optional[np.ndarray] = None,
    neighbors: Optional[np.ndarray] = None,
    periodic_output: bool = True,
    N: int = 3,
    periodic_input: bool = False,
    ground: bool = False,
    nb_samples: int = 1,
    symmetry: int = 8,
    seed: int = 0,
    verbose: bool = False,
    nb_tries: int = 100,
    symmetries: Optional[np.ndarray] = None,
    weights: Optional[np.ndarray] = None,
) -> Optional[np.ndarray]:
    if (tiles is not None and neighbors is not None) or input_img is not None:
        if input_img is not None:
            input_width, input_height = input_img.shape[:2]
            input_img, tile_conversion, tile_shape = preprocess_input_img(input_img)
            sample_type = 1

        else:
            input_width, input_height = 0, 0
            tiles, neighbors, tile_conversion, tile_shape = preprocess_tiles_and_neighbors(
                tiles, neighbors, symmetries, weights
            )
            sample_type = 0

        gen_map = run_wfc(
            width=width,
            height=height,
            sample_type=sample_type,
            input_img=input_img,
            input_width=input_width,
            input_height=input_height,
            periodic_output=periodic_output,
            N=N,
            periodic_input=periodic_input,
            ground=ground,
            nb_samples=nb_samples,
            symmetry=symmetry,
            seed=seed,
            verbose=verbose,
            nb_tries=nb_tries,
            tiles=tiles,
            neighbors=neighbors,
        )

        gen_map = get_tiles_back(gen_map, tile_conversion, nb_samples, width, height, tile_shape)
        return gen_map

    else:
        raise ValueError("Either input_img or tiles and neighbors must be provided.")
