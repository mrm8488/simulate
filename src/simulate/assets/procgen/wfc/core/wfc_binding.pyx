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

# distutils: language=c++

from libcpp cimport bool
from libcpp.string cimport string
from wfcbinding cimport IdPair, Neighbor, PyTile, run_wfc_cpp

import numpy as np

cimport numpy as np


# It's necessary to call "import_array" if you use any part of the
# numpy PyArray_* API. From Cython 3, accessing attributes like
# ".shape" on a typed Numpy array use this API. Therefore we recommend
# always calling "import_array" whenever you "cimport numpy"
np.import_array()

# Data type of arrays
DTYPE = int

def build_neighbor(string left, string right, unsigned left_or=0, unsigned right_or=0):
    return Neighbor(left=left, left_or=left_or, right=right, right_or=right_or)

def build_tile(list tile, string name, string symmetry=b"L", double weight=1, unsigned size=0):
    if size == 0:
        size = np.sqrt(len(tile))
    
    for i in range(len(tile)):
        tile[i] = IdPair(uid=tile[i], rotation=0, reflected=0)
    
    return PyTile(size=size, tile=tile, name=name, symmetry=symmetry, weight=weight)

def transform_to_id_pair(uid, rotation=0, reflected=0):
    return IdPair(uid=uid, rotation=rotation, reflected=0)

def run_wfc(unsigned width, unsigned height, int sample_type, list input_img=None, 
            unsigned input_width=0, unsigned input_height=0, bool periodic_output=True, unsigned N=3,
            bool periodic_input=False, bool ground=False, unsigned nb_samples=1, unsigned symmetry=8, unsigned seed=0, 
             bool verbose=False, unsigned nb_tries=100, list tiles=None,
             list neighbors=None):

    if neighbors == None:
        neighbors = []

    if tiles == None:
        tiles = []

    if input_img == None:
        input_img = []

    # As we are using a different convention from the library, we pass width as height and height as width.
    # The same applies to the input image.
    result = run_wfc_cpp(seed, height, width, sample_type, periodic_output, N, periodic_input, ground, 
                nb_samples, symmetry, input_img, input_height, input_width,
                verbose, nb_tries, tiles, neighbors)
    
    if len(result) == 0:
        raise SystemExit("ERROR: Wave Function Collapse failed. \nTips: Use smaller width / height; Use larger " \
        "image as input (overlapping case); or relax restrictions (simpletiled) by increasing the number " \
        "of possible neighbors.")

    cdef np.ndarray np_results = np.array(
        [list(r.values()) for r in result], dtype=DTYPE).reshape(nb_samples, width, height, -1)

    return np_results