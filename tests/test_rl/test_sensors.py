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

import unittest

# Lint as: python3
from functools import partial

import numpy as np

import simenv as sm


# TODO add more tests on saving/exporting/loading in gltf files
class ObservationsTest(unittest.TestCase):
    def test_map_sensors_to_spaces(self):
        camera_sensor = sm.CameraSensor(height=64, width=64)
        space = sm.map_sensors_to_spaces(camera_sensor)

        self.assertEqual(space.shape, (3, 64, 64))
        self.assertEqual(space.dtype, np.uint8)

        state_sensor = sm.StateSensor(None, None, properties=["position", "distance", "position.x"])
        space = sm.map_sensors_to_spaces(state_sensor)

        self.assertEqual(space.shape, (5,))
        self.assertEqual(space.dtype, np.float32)

        typo_state_sensor = sm.StateSensor(None, None, properties=["position", "distance", "position,x"])
        f = partial(sm.map_sensors_to_spaces, typo_state_sensor)
        self.assertRaises(KeyError, f)