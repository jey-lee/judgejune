# yourapp/consumers.py

import asyncio
import json
import tempfile

from channels.generic.websocket import AsyncWebsocketConsumer
from google.cloud import speech

class TranscribeConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        
        self.client = speech.SpeechClient()

        self.config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            language_code="en-US",
        )

        self.streaming_config = speech.StreamingRecognitionConfig(
            config=self.config,
            interim_results=True,
        )

        self.requests_queue = asyncio.Queue()

        # Start a background task to stream audio to GCP
        asyncio.create_task(self.transcribe_stream())

    async def disconnect(self, close_code):
        await self.close()

    async def receive(self, bytes_data):
        # When frontend sends mic audio blob, put it in queue
        await self.requests_queue.put(bytes_data)

    async def transcribe_stream(self):
        def request_generator():
            while True:
                chunk = asyncio.run(self.requests_queue.get())
                if chunk is None:
                    break

                # ⚡ TEMP FIX: Save incoming webm chunk to temp file and convert to raw LINEAR16
                with tempfile.NamedTemporaryFile(suffix=".webm", delete=True) as temp_webm:
                    temp_webm.write(chunk)
                    temp_webm.flush()

                    # Convert webm to raw LINEAR16 PCM
                    import subprocess
                    result = subprocess.run(
                        [
                            "ffmpeg", "-i", temp_webm.name,
                            "-f", "s16le", "-acodec", "pcm_s16le",
                            "-ac", "1", "-ar", "16000", "-"
                        ],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE
                    )

                    if result.returncode != 0:
                        continue  # skip bad chunk
                    pcm_data = result.stdout

                    yield speech.StreamingRecognizeRequest(audio_content=pcm_data)

        # Make streaming call to GCP
        responses = self.client.streaming_recognize(
            config=self.streaming_config,
            requests=request_generator()
        )

        for response in responses:
            for result in response.results:
                if result.alternatives:
                    transcript = result.alternatives[0].transcript
                    await self.send(text_data=json.dumps({
                        "transcript": transcript
                    }))
