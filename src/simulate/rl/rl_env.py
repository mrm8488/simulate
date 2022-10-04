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
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Type, Union

import gym
import numpy as np


try:
    from stable_baselines3.common.vec_env.base_vec_env import VecEnv, VecEnvIndices, VecEnvStepReturn
except ImportError:

    class VecEnv:
        pass  # Dummy class if SB3 is not installed

    class VecEnvIndices:
        pass  # Dummy class if SB3 is not installed

    class VecEnvStepReturn:
        pass  # Dummy class if SB3 is not installed


import simulate as sm

# Lint as: python3
from simulate.scene import Scene


class RLEnv(VecEnv):
    """
    RL environment wrapper for Simulate scene. Uses functionality from the VecEnv in stable baselines 3
    For more information on VecEnv, see the source
    https://stable-baselines3.readthedocs.io/en/master/guide/vec_envs.html

    Args:
        scene_or_map_fn (`Callable` or `Scene`):
            A Simulate Scene or a generator function for generating instances of the desired environment.
        n_maps (`int`, *optional*, defaults to `1`):
            The number of map instances to create.
        n_show (`int`, *optional*, defaults to `1`):
            Optionally show a subset of the maps during training and dequeue a new map at the end of each episode.
        time_step (`float`, *optional*, defaults to `1/30.0`):
            The physics timestep of the environment.
        frame_skip (`int`, *optional*, defaults to `4`):
            The number of times an action is repeated in the backend simulation before the next observation is returned.
    """

    def __init__(
        self,
        scene_or_map_fn: Union[Callable, Scene],
        n_maps: Optional[int] = 1,
        n_show: Optional[int] = 1,
        time_step: Optional[float] = 1 / 30.0,
        frame_skip: Optional[int] = 4,
        **engine_kwargs,
    ):

        if hasattr(scene_or_map_fn, "__call__"):
            scene_config = sm.Config(
                time_step=time_step,
                frame_skip=frame_skip,
                return_frames=False,
                return_nodes=False,
            )
            self.scene = Scene(engine="Unity", config=scene_config, **engine_kwargs)
            self.scene += sm.LightSun(name="sun", position=[0, 20, 0], intensity=0.9)
            self.map_roots = []
            for i in range(n_maps):
                map_root = scene_or_map_fn(i)
                self.scene += map_root
                self.map_roots.append(map_root)
        else:
            self.scene = scene_or_map_fn
            self.map_roots = [self.scene]

        self.actors = {actor.name: actor for actor in self.scene.actors}
        self.n_actors = len(self.actors)
        if self.n_actors == 0:
            raise ValueError(
                "No actors found in scene. At least one of your Assets should have the is_actor=True property."
            )
        self.n_maps = n_maps
        self.n_show = n_show
        self.n_actors_per_map = self.n_actors // self.n_maps

        self.actor = next(iter(self.actors.values()))

        self.action_space = self.scene.actors[0].action_space
        self.observation_space = self.scene.actors[0].observation_space
        self.action_tags = self.scene.actors[0].action_tags

        super().__init__(n_show, self.observation_space, self.action_space)

        # Don't return simulation data, since minimal/faster data will be returned by agent sensors
        self.scene.config.time_step = time_step
        self.scene.config.frame_skip = frame_skip
        self.scene.config.return_frames = False
        self.scene.config.return_nodes = False

        # Pass maps kwarg to enable map pooling
        maps = [root.name for root in self.map_roots]
        self.scene.show(
            maps=maps,
            n_show=n_show,
        )

    def step(self, action: Union[Dict, List, np.ndarray]) -> Tuple[Dict, np.ndarray, np.ndarray, List[Dict]]:
        """
        The step function for the environment, follows the API from OpenAI Gym.

        TODO verify, a dict with actuator tags as keys and as values a Tensor of shape (n_show, n_actors, n_actions)
        Args:
            action (`Dict` or `List`):
                The action to be taken by the environment.

        Returns:
            observation (`Dict`):
                A dictionary of observations from the environment.
            reward (`float`):
                The reward for the action.
            done (`bool`):
                Whether the episode has ended.
            info (`Dict`):
                A dictionary of additional information.
        """

        self.step_send_async(action=action)
        return self.step_recv_async()

    def step_send_async(self, action: Union[Dict, List, np.ndarray]):
        """
        Send action for execution asynchronously.

        Args:
            action (`Dict` or `List` or `ndarray`):
                The action to be executed in the environment.
        """

        if not isinstance(action, dict):
            if len(self.action_tags) != 1:
                raise ValueError(
                    f"Action must be a dict with keys {self.action_tags} when there are multiple action tags."
                )
            action = {self.action_tags[0]: action}

        # Check that the keys are in the action tags
        # Add maps/actor dimension to action if single map/actor
        for key, value in action.items():
            if key not in self.action_tags:
                raise ValueError(f"Action tag {key} not found in action tags: {self.action_tags}.")
            if isinstance(value, (int, float)):
                # A single value for the action – we add the map/actor/action-list dimensions
                if self.n_show == 1 and self.n_actors == 1:
                    action[key] = [[[value]]]
                else:
                    raise ValueError(
                        f"All actions must be list (maps) of list (actors) of list of floats/int (action). "
                        f"if the number of maps or actors is greater than 1 (in our case n_show: {self.n_show} "
                        f"and n_actors {self.n_actors})."
                    )
            elif isinstance(value, (list, tuple)) and len(value) > 0 and isinstance(value[0], (int, float)):
                # A list value for the action – we add the map/actor dimensions
                if self.n_show == 1 and self.n_actors == 1:
                    action[key] = [[value]]
                else:
                    raise ValueError(
                        f"All actions must be list (maps) of list (actors) of list of floats/int (action). "
                        f"if the number of maps or actors is greater than 1 (in our case n_show: {self.n_show} "
                        f"and n_actors {self.n_actors})."
                    )
            elif isinstance(value, np.ndarray) and len(value) > 0 and isinstance(value[0], (np.int64, np.float32)):
                # actions are a number array
                value = value.reshape((self.n_show, self.n_actors_per_map, -1))
                action[key] = value.tolist()

        self.scene.engine.step_send_async(action=action)

    def step_recv_async(self) -> Tuple[Dict, np.ndarray, np.ndarray, List[Dict]]:
        """
        Receive the response from the environment asynchronously.

        Returns:
            observation (`Dict`):
                A dictionary containing the observation from the environment.
            reward (`float`):
                The reward for the action.
            done (`bool`):
                Whether the episode has ended.
            info (`Dict`):
                A dictionary of additional information.
        """

        event = self.scene.engine.step_recv_async()

        # Extract observations, reward, and done from event data
        # TODO nathan thinks we should make this for 1 agent, have a separate one for multiple agents.
        obs = self._extract_sensor_obs(event["actor_sensor_buffers"])
        reward = self._convert_to_numpy(event["actor_reward_buffer"]).flatten()
        done = self._convert_to_numpy(event["actor_done_buffer"]).flatten()

        obs = self._squeeze_actor_dimension(obs)

        return obs, reward, done, [{}] * len(done)

    def _squeeze_actor_dimension(self, obs: Dict) -> Dict:
        """
        Squeeze the observations.

        Args:
            obs (`Dict`): The observation received from the environment.

        Returns:
            obs (`Dict`): Squeezed observation.
        """

        for k, v in obs.items():
            obs[k] = obs[k].reshape((self.n_show * self.n_actors_per_map, *obs[k].shape[2:]))
        return obs

    def reset(self) -> Dict:
        """
        Resets the actors and the scene of the environment.

        Returns:
            obs (`Dict`): the observation of the environment after reset.
        """

        self.scene.reset()

        # To extract observations, we do a "fake" step (no actual simulation with frame_skip=0)
        event = self.scene.step(return_frames=True, frame_skip=0)
        obs = self._extract_sensor_obs(event["actor_sensor_buffers"])
        obs = self._squeeze_actor_dimension(obs)
        return obs

    @staticmethod
    def _convert_to_numpy(event_data: Dict) -> np.ndarray:
        """
        Convert the event data to numpy array.

        Args:
            event_data (`Dict`): The event data to be converted.

        Returns:
            event_data (`ndarray`): The converted event data.
        """

        if event_data["type"] == "uint8":
            shape = event_data["shape"]
            return np.array(event_data["uintBuffer"], dtype=np.uint8).reshape(shape)
        elif event_data["type"] == "float":
            shape = event_data["shape"]
            return np.array(event_data["floatBuffer"], dtype=np.float32).reshape(shape)
        else:
            raise TypeError

    def _extract_sensor_obs(self, sim_event_data: Dict) -> Dict:
        """
        Extract the observations from the event data.

        Args:
            sim_event_data (`Dict`): The full event data.

        Returns:
            sensor_obs (`Dict`): The sensors observation
        """

        sensor_obs = {}
        for sensor_tag, sensor_data in sim_event_data.items():
            sensor_obs[sensor_tag] = self._convert_to_numpy(sensor_data)
        return sensor_obs

    def close(self):
        """Close the scene."""
        self.scene.close()

    def sample_action(self) -> np.ndarray:
        """
        Samples an action from the actors in the environment. This function loads the configuration of maps and actors
        to return the correct shape across multiple configurations.

        Returns:
            action (`ndarray`): action sampled from the environment's action space.
        """

        if self.n_actors_per_map > 1:
            raise NotImplementedError("TODO: add sampling mechanism for multi-agent spaces.")
        else:
            action = [self.action_space.sample() for _ in range(self.n_show)]
        return np.array(action)

    def env_is_wrapped(self, wrapper_class: Type[gym.Wrapper], indices: Optional[VecEnvIndices] = None) -> List[bool]:
        """Returns if environment is wrapped."""
        return [False] * self.n_agents * self.n_parallel

    # required abstract methods

    def step_async(self, actions: np.ndarray) -> None:
        """Step the environment asynchronously."""
        raise NotImplementedError()

    def get_attr(self, attr_name: str, indices: VecEnvIndices = None) -> List[Any]:
        """Return a class attribute by name."""
        raise NotImplementedError()

    def env_method(self, method_name: str, *method_args, indices: VecEnvIndices = None, **method_kwargs) -> List[Any]:
        raise NotImplementedError()

    def seed(self, seed: Optional[int] = None):  # -> List[Union[None, int]]:
        # this should be done when the env is initialized
        return
        # raise NotImplementedError()

    def set_attr(self, attr_name: str, value: Any, indices: VecEnvIndices = None) -> None:
        raise NotImplementedError()

    def step_send(self) -> Any:
        raise NotImplementedError()

    def step_wait(self) -> VecEnvStepReturn:
        raise NotImplementedError()

    def get_images(self) -> Sequence[np.ndarray]:
        raise NotImplementedError()
