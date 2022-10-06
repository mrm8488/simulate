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
from libcpp.vector cimport vector


cdef extern from "cpp/include/id_pair.hpp":
    cdef struct IdPair:
        unsigned uid, rotation, reflected

cdef extern from "cpp/src/run_wfc.cpp":
    pass

cdef extern from "cpp/include/run_wfc.hpp":
    cdef struct Neighbor:
        string left, right
        unsigned left_or, right_or

    cdef struct PyTile:
        unsigned size
        vector[IdPair] tile
        string name
        string symmetry
        double weight

    cdef vector[IdPair] run_wfc_cpp(unsigned seed, unsigned width, unsigned height, int sample_type, bool periodic_output, 
                    unsigned N, bool periodic_input, bool ground, unsigned nb_samples,
                    unsigned symmetry, vector[IdPair] input_img, 
                    unsigned input_width, unsigned input_height, bool verbose, 
                    unsigned nb_tries, vector[PyTile] tiles,
                    vector[Neighbor] neighbors)
