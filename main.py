import argparse
import asyncio
import logging
import av
from aiortc.contrib.media import MediaPlayer

from util import Util
from cam_client import CamClient

if __name__ == "__main__":
    logging.basicConfig(
        format='%(asctime)s.%(msecs)03d | %(name)s | %(levelname)-8s %(message)s',
        level=logging.INFO,
        datefmt='%Y-%m-%d %H:%M:%S')

    av.logging.set_level(av.logging.CRITICAL)
    logging.getLogger("aioice.ice").setLevel(logging.ERROR)

    os = Util.detect_os()
    logging.info(f"OS: {os}")

    # Create the parser
    parser = argparse.ArgumentParser(description="Process named arguments.")
    parser.add_argument('--url', type=str, help='WebRTC offer URL', default='http://localhost:9000/offer')
    parser.add_argument('--force-h264', type=bool, help='force H264 codec for transmitting', default=False)
    parser.add_argument('--resolution', type=str, help='Video resolution for transmitting', default='800x600')
    parser.add_argument('--fps', type=str, help='Frame rate from camera', default='30')
    parser.add_argument("--username", help="Username", type=str)
    parser.add_argument("--password", help="password", type=str)
    parser.add_argument("--modelId", help="Model id", type=str, default=None)

    parser.add_argument("--videoFile", help="Video File", type=str, default=None)
    parser.add_argument("--rtspUrl", help="RTSP Server URL", type=str, default=None)

    default_camera = Util.get_default_camera_for_os(os)
    parser.add_argument('--camera', type=str, help='Key for transmitting data', default=f"{default_camera}")
    args = parser.parse_args()

    player_options = Util.get_media_player_options_for_os(os, args.camera)

    cam_client = CamClient(player_options=player_options, args=args)

    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(cam_client.run())
        loop.run_until_complete(asyncio.Future())
    except KeyboardInterrupt:
        pass
    finally:
        # close peer connections
        coros = cam_client.shutdown()
        loop.run_until_complete(asyncio.gather(*coros))
