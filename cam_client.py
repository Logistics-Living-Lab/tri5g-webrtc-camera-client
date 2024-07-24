import asyncio
import logging

import aiohttp
from aiohttp import ClientConnectorError

from aiortc import RTCPeerConnection, RTCSessionDescription, RTCRtpSender
from aiortc.contrib.media import MediaPlayer


class CamClient:
    def __init__(self, player_options, args):
        self.peer_connections = set()
        self.task = None
        self.player = None
        self.player_options = player_options
        self.args = args

    async def publish(self):
        self.player = MediaPlayer(f"{self.player_options['video_path']}", format=f"{self.player_options['format']}",
                                  options={
                                      'rtbufsize': '2000M',
                                      'video_size': f"{self.args.resolution}",
                                      'framerate': f"{self.args.fps}"
                                  })

        offer_url_path = f"{self.args.url}{self.args.key}"
        pc = self._create_peer_connection()
        pc.addTrack(self.player.video)

        if self.args.force_h264:
            self._force_codec(pc, 'video/H264')

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

    def _create_peer_connection(self):
        pc = RTCPeerConnection()

        @pc.on("datachannel")
        def on_datachannel(channel):
            @channel.on("message")
            def on_message(message):
                if isinstance(message, str) and message.startswith("ping"):
                    channel.send("pong" + message[4:])

        @pc.on("connectionstatechange")
        async def on_connectionstatechange():
            logging.info("Connection state is %s", pc.connectionState)
            if pc.connectionState == 'closed':
                # Reconnects
                self.task.cancel()
                await pc.close()
                self.peer_connections.discard(pc)
                await asyncio.sleep(10)
                logging.info("Reconnecting...")
                await self.run()


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

        self.peer_connections.add(pc)
        return pc

    async def run(self):
        self.task = asyncio.create_task(self._create_task())
        try:
            await self.task
        except asyncio.CancelledError:
            logging.info("Task cancelled")

    async def _create_task(self):
        await self.publish()
        logging.info(f"Exchanging media {self.args.url}")

    def shutdown(self):
        return [pc.close() for pc in self.peer_connections]

    def _force_codec(self, pc, forced_codec):
        codecs = RTCRtpSender.getCapabilities('video').codecs
        h264_codecs = [codec for codec in codecs if codec.mimeType == forced_codec]
        if len(h264_codecs) == 0:
            logging.info("No H264 codecs found.")
            return

        transceiver = next(transceiver for transceiver in pc.getTransceivers() if transceiver.kind == "video")
        transceiver.setCodecPreferences(h264_codecs)
