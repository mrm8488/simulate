# flake8: noqa
# Copyright 2020 The HuggingFace Simulate Authors.
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
# pylint: enable=line-too-long
# pylint: disable=g-import-not-at-top,g-bad-import-order,wrong-import-position

__version__ = "0.0.0.1.dev0"

from .assets import *
from .assets.utils import *
from .config import Config
from .engine import *
from .rl import ParallelRLEnv, RLEnv
from .scene import Scene
from .utils import logging


logger = logging.get_logger(__name__)

# Set Hugging Face hub debug verbosity (TODO remove)
logging.set_verbosity_debug()
