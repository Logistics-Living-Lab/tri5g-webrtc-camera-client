import argparse
import asyncio
import logging
import platform

import aiohttp
import av
from aiohttp import ClientConnectorError

from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack, RTCRtpSender
from aiortc.contrib.media import MediaPlayer

pcs = set()


async def publish(player, args):
    offer_url_path = f"{args.url}{args.key}"
    pc = RTCPeerConnection()
    pc.addTrack(player.video)

    @pc.on("datachannel")
    def on_datachannel(channel):
        @channel.on("message")
        def on_message(message):
            if isinstance(message, str) and message.startswith("ping"):
                channel.send("pong" + message[4:])

    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        logging.info("Connection state is %s", pc.connectionState)

    @pc.on("iceconnectionstatechange")
    async def on_connectionstatechange():
        logging.info("ICE connection state is %s", pc.iceConnectionState)

    @pc.on("icegatheringstatechange")
    async def on_connectionstatechange():
        logging.info("ICE Gathering state is %s", pc.iceGatheringState)

    @pc.on("signalingstatechange")
    async def on_connectionstatechange():
        logging.info("Signaling state is %s", pc.signalingState)

    @pc.on("track")
    def on_track(track):
        logging.info("Track %s received", track.kind)

    pcs.add(pc)

    if args.force_h264:
        force_codec(pc, 'video/H264')

    # send offer
    await pc.setLocalDescription(await pc.createOffer())

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(offer_url_path, json={
                'sdp': pc.localDescription.sdp,
                'type': pc.localDescription.type
            }) as response:
                answer = await response.json()
                await pc.setRemoteDescription(RTCSessionDescription(answer['sdp'], answer['type']))
        except ClientConnectorError as e:
            logging.error(f"{e.strerror}: {offer_url_path}")
            exit(-1)


async def run(player, args):
    # send video
    await publish(player=player, args=args)
    print(f"Exchanging media {args.url}")
    await asyncio.Future()


def force_codec(pc, forced_codec):
    codecs = RTCRtpSender.getCapabilities('video').codecs
    h264_codecs = [codec for codec in codecs if codec.mimeType == forced_codec]
    if len(h264_codecs) == 0:
        logging.info("No H264 codecs found.")
        return

    transceiver = next(transceiver for transceiver in pc.getTransceivers() if transceiver.kind == "video")
    transceiver.setCodecPreferences(h264_codecs)


def detect_os():
    if platform.system() == "Darwin":
        return "MacOS"
    elif platform.system() == "Windows":
        return "Windows"
    else:
        return "Linux"


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


def get_default_camera_for_os(operating_system: str):
    if operating_system == "Windows":
        return "Integrated Camera"
    elif operating_system == "Linux":
        return "/dev/video0"
    else:
        logging.error(f"OS [{operating_system} not supported")


if __name__ == "__main__":
    logging.basicConfig(
        format='%(asctime)s.%(msecs)03d %(levelname)-8s %(message)s',
        level=logging.INFO,
        datefmt='%Y-%m-%d %H:%M:%S')

    av.logging.set_level(av.logging.INFO)

    os = detect_os()
    logging.info(f"OS: {os}")

    # Create the parser
    parser = argparse.ArgumentParser(description="Process named arguments.")
    parser.add_argument('--url', type=str, help='WebRTC offer URL', default='http://localhost:9000/offer')
    parser.add_argument('--force-h264', type=bool, help='force H264 codec for transmitting', default=False)
    parser.add_argument('--key', type=str, help='Optional: Key for transmitting data', default='')
    parser.add_argument('--resolution', type=str, help='Video resolution for transmitting', default='800x600')
    parser.add_argument('--fps', type=str, help='Frame rate from camera', default='30')

    default_camera = get_default_camera_for_os(os)
    parser.add_argument('--camera', type=str, help='Key for transmitting data', default=f"{default_camera}")
    args = parser.parse_args()

    player_options = get_media_player_options_for_os(os, args.camera)

    player_options = MediaPlayer(f"{player_options['video_path']}", format=f"{player_options['format']}", options={
        'rtbufsize': '2000M',
        'video_size': f"{args.resolution}",
        'framerate': f"{args.fps}"
    })

    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(run(player=player_options, args=args))
    except KeyboardInterrupt:
        pass
    finally:
        # close peer connections
        coros = [pc.close() for pc in pcs]
        loop.run_until_complete(asyncio.gather(*coros))
