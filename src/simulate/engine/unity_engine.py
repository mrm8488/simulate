import atexit
import base64
import json
import os
import signal
import socket
import subprocess
import tarfile
import time
from sys import platform
from typing import TYPE_CHECKING, Any, Dict, Optional, Union

from huggingface_hub import hf_hub_download
from huggingface_hub.constants import hf_cache_home

from ..utils import logging
from .engine import Engine


if TYPE_CHECKING:
    from ..assets.asset import Asset
    from ..scene import Scene


logger = logging.get_logger(__name__)


NUM_BIND_RETRIES = 20
BIND_RETRIES_DELAY = 2.0
SOCKET_TIME_OUT = 30.0  # Timeout in seconds

UNITY_BUILD_REPO = "simulate-tests/unity-test"
UNITY_SUBFOLDER = "builds"

if platform == "linux" or platform == "linux2":
    UNITY_SUBFOLDER += "/Build-StandaloneLinux64"
    UNITY_COMPRESSED_FILENAME = "StandaloneLinux64.tar.gz"
    UNITY_EXECUTABLE_PATH = "StandaloneLinux64"
elif platform == "darwin":
    UNITY_SUBFOLDER += "/Build-StandaloneOSX"
    UNITY_COMPRESSED_FILENAME = "StandaloneOSX.tar.gz"
    UNITY_EXECUTABLE_PATH = "StandaloneOSX.app/Contents/MacOS/Simulate"
elif platform == "win32":
    UNITY_SUBFOLDER += "/Build-StandaloneWindows"
    UNITY_COMPRESSED_FILENAME = "StandaloneWindows.tar.gz"
    UNITY_EXECUTABLE_PATH = "StandaloneWindows.exe"
elif platform == "win64":
    UNITY_SUBFOLDER += "/Build-StandaloneWindows64"
    UNITY_COMPRESSED_FILENAME = "StandaloneWindows64.tar.gz"
    UNITY_EXECUTABLE_PATH = "StandaloneWindows64.exe"

default_cache_path = os.path.join(hf_cache_home, "unity")

HUGGINGFACE_UNITY_CACHE = os.getenv("HUGGINGFACE_UNITY_CACHE", default_cache_path)


class UnityEngine(Engine):
    def __init__(
        self,
        scene: "Scene",
        auto_update: bool = True,
        engine_exe: str = "",
        engine_host="127.0.0.1",
        engine_port: int = 55001,
        engine_headless: bool = False,
    ):
        super().__init__(scene=scene, auto_update=auto_update)

        self._initialize_server(
            engine_exe=engine_exe, engine_host=engine_host, engine_port=engine_port, engine_headless=engine_headless
        )

        atexit.register(self._close)
        signal.signal(signal.SIGTERM, self._close)
        signal.signal(signal.SIGINT, self._close)

        self._map_pool = False

    @staticmethod
    def _get_unity_from_hub() -> str:
        unity_compressed = hf_hub_download(
            repo_id=UNITY_BUILD_REPO,
            filename=UNITY_COMPRESSED_FILENAME,
            subfolder=UNITY_SUBFOLDER,
            revision=None,
            repo_type="space",
        )

        # open file
        archive = tarfile.open(unity_compressed)
        main_dir = os.path.commonpath(archive.getnames())

        archive.extractall(HUGGINGFACE_UNITY_CACHE)
        archive.close()
        return os.path.join(HUGGINGFACE_UNITY_CACHE, main_dir, UNITY_EXECUTABLE_PATH)

    def _launch_executable(self, executable: str, port: str, headless: bool):
        # TODO: improve headless training check on a headless machine
        if headless:
            logger.info("launching env headless")
            launch_command = f"{executable} -batchmode -nographics --args port {port}".split(" ")
        else:
            launch_command = f"{executable} --args port {port}".split(" ")
        environ = os.environ.copy()
        environ["PATH"] = "/usr/sbin:/sbin:" + environ["PATH"]

        self.proc = subprocess.Popen(launch_command, env=environ)

    @staticmethod
    def _find_port_number(starting_engine_port: int) -> int:
        """use a different port in each xdist worker"""
        port_tests = list(range(starting_engine_port, starting_engine_port + 1024))
        for port in port_tests:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                if s.connect_ex(("localhost", port)) == 0:
                    continue
                else:
                    return port
        raise RuntimeError("Could not find a free port")

    def _initialize_server(self, engine_exe: str, engine_host: str, engine_port: int, engine_headless: bool):
        """Initialize the local server and launch the Unity executable and
        connect to it.
        """
        # Initializing on our side
        self.host = engine_host
        self.port = self._find_port_number(engine_port)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        logger.info(f"Starting the server. Waiting for connection on {self.host} {self.port}...")
        try:
            self.socket.bind((self.host, self.port))
        except OSError:
            for n in range(NUM_BIND_RETRIES):
                time.sleep(BIND_RETRIES_DELAY)
                try:
                    self.socket.bind((self.host, self.port))
                    break
                except OSError:
                    logger.error(f"port {self.port} is still in use, trying again")
            raise logger.error(f"Could not bind to port {self.port}")

        self.socket.listen()

        # Starting the Unity executable
        logger.info(f"Starting Unity executable {engine_exe}...")
        if engine_exe is None or engine_exe == "debug":
            pass  # We run with the editor
        elif engine_exe:
            self._launch_executable(executable=engine_exe, port=str(engine_port), headless=engine_headless)
        elif engine_exe == "":
            engine_exe = self._get_unity_from_hub()
            self._launch_executable(executable=engine_exe, port=str(engine_port), headless=engine_headless)
        else:
            raise ValueError("engine_exe must be a string, None or empty")

        # Connecting both
        logger.info(f"Connecting to Unity executable on {self.host} {self.port}...")
        self.client, self.client_address = self.socket.accept()
        # self.client.setblocking(0)  # Set to non-blocking
        self.client.settimeout(SOCKET_TIME_OUT)  # Set a timeout
        logger.info(f"Connection from {self.client_address}")

    def _get_response(self) -> str:
        while True:

            data_length = self.client.recv(4)
            data_length = int.from_bytes(data_length, "little")

            if data_length:
                response = ""  # TODO: string concatenation may be slow
                while len(response) < data_length:
                    response += self.client.recv(data_length - len(response)).decode()

                return response

    def update_asset(self, root_node: "Asset"):
        # TODO update and make this API more consistent with all the
        # update_asset, update, show
        raise NotImplementedError()

    def update_all_assets(self):
        raise NotImplementedError()

    def show(self, **kwargs: Any) -> Union[Dict, str]:
        bytes_data = self._scene.as_glb_bytes()
        b64_bytes = base64.b64encode(bytes_data).decode("ascii")
        kwargs.update({"b64bytes": b64_bytes})
        return self.run_command("Initialize", **kwargs)

    def step(self, action: Optional[Dict] = None, **kwargs: Any) -> Union[Dict, str]:
        """Step the environment with the given action.

        Args:
            action (dict): The action to take in the environment.
                If the action is None, we don't send an action to the environment.
                We then only send the Step command to Unity to step the physics engine.
        """
        if action is not None:
            kwargs.update({"action": action})
        return self.run_command("Step", **kwargs)

    def step_send_async(self, **kwargs: Any):
        self.run_command_async("Step", **kwargs)

    def step_recv_async(self) -> str:
        return self.get_response_async()

    def reset(self):
        return self.run_command("Reset")

    def run_command(self, command: str, wait_for_response: bool = True, **kwargs: Any) -> Union[Dict, str]:
        message = json.dumps({"type": command, **kwargs})
        message_bytes = len(message).to_bytes(4, "little") + bytes(message.encode())
        self.client.sendall(message_bytes)
        if wait_for_response:
            response = self._get_response()
            try:
                return json.loads(response)
            except Exception as e:
                logger.warning(f"Exception loading response json data: {e}")
                return response

    def run_command_async(self, command: str, **kwargs: Any):
        message = json.dumps({"type": command, **kwargs})
        message_bytes = len(message).to_bytes(4, "little") + bytes(message.encode())
        self.client.sendall(message_bytes)

    def get_response_async(self) -> Union[Dict, str]:
        response = self._get_response()
        try:
            return json.loads(response)
        except Exception as e:
            logger.warning(f"Exception loading response json data: {e}")
            return response

    def _close(self):
        self.close()

    def close(self):
        try:
            self.run_command("Close", wait_for_response=False)
        except Exception as e:
            logger.error(f"Exception sending close message: {e}")

        # self.client.shutdown(socket.SHUT_RDWR)
        self.client.close()
        self.socket.close()

        try:
            atexit.unregister(self._close)
        except Exception as e:
            logger.error(f"Exception unregistering close method: {e}")
