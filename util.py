import logging
import os
import platform


class Util:

    @staticmethod
    def detect_os():
        if platform.system() == "Darwin":
            return "MacOS"
        elif platform.system() == "Windows":
            return "Windows"
        else:
            return "Linux"

    @staticmethod
    def get_media_player_options_for_os(operating_system: str, camera_path):
        if operating_system == "Windows":
            return {
                'video_path': f"video={camera_path}",
                'format': "dshow"
            }
        elif operating_system == "Linux":
            return {
                'video_path': f"{camera_path}",
                'format': "v4l2"
            }
        else:
            logging.error(f"OS [{operating_system} not supported")

    @staticmethod
    def get_default_camera_for_os(operating_system: str):
        if operating_system == "Windows":
            return "Integrated Camera"
        elif operating_system == "Linux":
            return "/dev/video0"
        else:
            logging.error(f"OS [{operating_system} not supported")

    @staticmethod
    def get_root_path():
        return os.path.dirname(os.path.abspath(__file__))
