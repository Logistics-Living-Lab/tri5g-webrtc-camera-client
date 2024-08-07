import argparse
import logging
import os
from aiortc.contrib.media import MediaPlayer

from util import Util

if __name__ == '__main__':
    logging.basicConfig(
        format='%(asctime)s.%(msecs)03d | %(name)s | %(levelname)-8s %(message)s',
        level=logging.INFO,
        datefmt='%Y-%m-%d %H:%M:%S')

    parser = argparse.ArgumentParser(
        description="Test connections Tri5G"
    )
    parser.add_argument("--url", help="URL", type=str)
    parser.add_argument("--username", help="Username", type=str)
    parser.add_argument("--password", help="Password", type=str)

    parser.add_argument('--resolution', type=str, help='Video resolution for transmitting', default='800x600')
    parser.add_argument('--fps', type=str, help='Frame rate from camera', default='30')

    detected_os = Util.detect_os()
    logging.info(f"OS: {detected_os}")
    default_camera = Util.get_default_camera_for_os(detected_os)
    parser.add_argument('--camera', type=str, help='Key for transmitting data', default=f"{default_camera}")

    args = parser.parse_args()

    root_path = os.path.dirname(os.path.abspath(__file__))

    ffmpeg_options = {
        'rtbufsize': "2000M",
        'video_size': args.resolution,
        'framerate': args.fps,
        'preset': "veryfast",
        'bufsize': "1000k"
    }

    try:
        player_options = Util.get_media_player_options_for_os(detected_os, args.camera)
        player = MediaPlayer(f"{player_options['video_path']}", format=f"{player_options['format']}",
                             options=ffmpeg_options)
        logging.info("Success")
    except Exception as e:
        if hasattr(e, 'log'):
            logging.error(e.log)
        else:
            logging.error(e)
        exit(-1)
