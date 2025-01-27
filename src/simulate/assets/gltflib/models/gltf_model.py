import json
from dataclasses import asdict, dataclass
from typing import Any, List, Optional

from dataclasses_json import DataClassJsonMixin

from ..utils import replace_unique_id_and_remove_none
from .accessor import Accessor
from .animation import Animation
from .asset import Asset
from .base_model import BaseModel
from .buffer import Buffer
from .buffer_view import BufferView
from .camera import Camera
from .image import Image
from .material import Material
from .mesh import Mesh
from .node import Node
from .sampler import Sampler
from .scene import Scene
from .skin import Skin
from .texture import Texture


@dataclass
class GLTFModel(DataClassJsonMixin, BaseModel):
    accessors: Optional[List[Accessor]] = None
    animations: Optional[List[Animation]] = None
    asset: Optional[Asset] = None
    buffers: Optional[List[Buffer]] = None
    bufferViews: Optional[List[BufferView]] = None
    cameras: Optional[List[Camera]] = None
    images: Optional[List[Image]] = None
    materials: Optional[List[Material]] = None
    meshes: Optional[List[Mesh]] = None
    nodes: Optional[List[Node]] = None
    samplers: Optional[List[Sampler]] = None
    scene: Optional[int] = None
    scenes: Optional[List[Scene]] = None
    skins: Optional[List[Skin]] = None
    textures: Optional[List[Texture]] = None
    extensionsRequired: Optional[List[str]] = None
    extensionsUsed: Optional[List[str]] = None

    def to_json(self, **kwargs: Any) -> str:
        data = replace_unique_id_and_remove_none(asdict(self))
        return json.dumps(data, **kwargs)
