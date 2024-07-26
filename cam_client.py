import asyncio
import json
import logging
import time

import aiohttp
from aiohttp import ClientConnectorError, BasicAuth

from aiortc import RTCPeerConnection, RTCSessionDescription, RTCRtpSender, RTCDataChannel
from aiortc.contrib.media import MediaPlayer


class CamClient:
    RT_BUFFER_SIZE = "2000M"

    def __init__(self, player_options, args):
        self.peer_connections = list()
        self.data_connections = list()

        self.task = None
        self.player = None
        self.player_options = player_options
        self.args = args

    async def publish(self):
        self.player = MediaPlayer(f"{self.player_options['video_path']}", format=f"{self.player_options['format']}",
                                  options={
                                      'rtbufsize': f"{CamClient.RT_BUFFER_SIZE}",
                                      'video_size': f"{self.args.resolution}",
                                      'framerate': f"{self.args.fps}"
                                  })

        offer_url_path = f"{self.args.url}"
        pc = self.__create_peer_connection()
        pc.addTrack(self.player.video)

        if self.args.force_h264:
            self.__force_codec(pc, 'video/H264')

        # send offer
        await pc.setLocalDescription(await pc.createOffer())

        auth = None
        if self.args.username and self.args.password:
            logging.info(f"Authenticating as {self.args.username}...")
            auth = BasicAuth(self.args.username, self.args.password)

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(offer_url_path, auth=auth, json={
                    'sdp': pc.localDescription.sdp,
                    'type': pc.localDescription.type
                }) as response:
                    if response.status == 200:
                        answer = await response.json()
                        await pc.setRemoteDescription(RTCSessionDescription(answer['sdp'], answer['type']))
                    else:
                        logging.error(f"Response Status: {response.status} - {response.reason}")
                        exit(-1)
            except ClientConnectorError as e:
                logging.error(f"{e.strerror}: {offer_url_path}")
                exit(-1)

    def __create_peer_connection(self):
        pc = RTCPeerConnection()
        client_data_channel = pc.createDataChannel('client-channel')
        self.data_connections.append(client_data_channel)

        @client_data_channel.on("message")
        def on_message(message):
            logging.info(f"Message received on '{client_data_channel.label}'")
            logging.info(message)

        @pc.on("datachannel")
        def on_datachannel(server_channel: RTCDataChannel):
            @server_channel.on("message")
            def on_message(message):
                if isinstance(message, str):
                    message_json = json.loads(message)
                    if message_json['type'] == 'rtt-packet' and server_channel.readyState == 'open':
                        server_channel.send(message)

        @pc.on("connectionstatechange")
        async def on_connectionstatechange():
            logging.info("Connection state is %s", pc.connectionState)

            if pc.connectionState == 'closed':
                # Reconnects
                self.task.cancel()
                await pc.close()
                self.peer_connections.remove(pc)
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

        self.peer_connections.append(pc)
        return pc

    async def run(self):
        self.task = asyncio.create_task(self.__create_task())
        try:
            await self.task
        except asyncio.CancelledError:
            logging.info("Task cancelled")

    async def __create_task(self):
        await self.publish()
        logging.info(f"Exchanging media {self.args.url}")

    def shutdown(self):
        return [pc.close() for pc in self.peer_connections]

    def __force_codec(self, pc, forced_codec):
        codecs = RTCRtpSender.getCapabilities('video').codecs
        h264_codecs = [codec for codec in codecs if codec.mimeType == forced_codec]
        if len(h264_codecs) == 0:
            logging.info("No H264 codecs found.")
            return

        transceiver = next(transceiver for transceiver in pc.getTransceivers() if transceiver.kind == "video")
        transceiver.setCodecPreferences(h264_codecs)
