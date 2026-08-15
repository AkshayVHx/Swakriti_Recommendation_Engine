const BACKEND_URL = import.meta.env.VITE_BACKEND_URL;

if (!BACKEND_URL) {
  throw new Error('VITE_BACKEND_URL is not set — check your .env file');
}

let ws = null;
let onFinalTranscriptCallback = null;
let micAudioContext = null;
let micStream = null;
let playbackAudioContext = null;
let currentAudioSources = [];
let speechGeneration = 0;

let isPausedForSpeech = false;
let isListeningEnabled = false; 


async function getEphemeralToken() {
  console.log('[voice] Requesting ephemeral token from', BACKEND_URL + '/live-token');
  try {
    const res = await fetch(`${BACKEND_URL}/live-token`, { method: 'POST' });
    if (!res.ok) {
      throw new Error(`Token request failed: HTTP ${res.status}`);
    }
    const data = await res.json();
    console.log('[voice] Token received successfully');
    return data.token;
  } catch (e) {
    console.error('[voice] Token request error:', e);
    throw e;
  }
}


export async function connectVoice(onFinalTranscript) {
  if (ws) return; // already connected, don't reconnect
  console.log('[voice] connectVoice: Getting ephemeral token');
  onFinalTranscriptCallback = onFinalTranscript;
  const token = await getEphemeralToken();
  console.log('[voice] Token acquired, establishing WebSocket connection');

  ws = new WebSocket(
    `wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContentConstrained?access_token=${token}`
  );

  ws.onopen = () => {
    console.log('[voice] WebSocket OPEN, sending setup config');
    ws.send(JSON.stringify({
      setup: {
        generationConfig: { responseModalities: ["TEXT"] },  
        inputAudioTranscription: {}
        
      }
    }));
    
  };

  ws.onmessage = async (event) => {
    const text = event.data instanceof Blob ? await event.data.text() : event.data;
    const msg = JSON.parse(text);

    // user speech -> text
    if (msg.serverContent?.inputTranscription?.text) {
      const transcript = msg.serverContent.inputTranscription.text.trim();
      console.log('[voice] Received transcript:', transcript);
      if (transcript && isListeningEnabled && onFinalTranscriptCallback && !isPausedForSpeech) {
        onFinalTranscriptCallback(transcript);
      }
    }
    
  };

  ws.onerror = (e) => {
    console.error('[voice] WebSocket ERROR:', e);
  };
  ws.onclose = (e) => {
    console.warn('[voice] WebSocket CLOSED - code:', e.code, 'reason:', e.reason);
    ws = null;
  };

  // wait until the socket is actually OPEN before returning
  await new Promise((resolve) => {
    const check = setInterval(() => {
      if (ws?.readyState === WebSocket.OPEN) {
        console.log('[voice] WebSocket connection verified OPEN');
        clearInterval(check);
        resolve();
      }
    }, 50);
  });
}

// starts mic capture on the already-open socket
export function enableListening() {
  console.log('[voice] enableListening called, isListeningEnabled set to true');
  isListeningEnabled = true;
  startMicStreaming();
}

export function stopContinuousListening() {
  isListeningEnabled = false;
  micStream?.getTracks().forEach(t => t.stop());
  micAudioContext?.close();
  ws?.close();
  ws = null;
  micStream = null;
  micAudioContext = null;
}


function startMicStreaming() {
  console.log('[voice] startMicStreaming: requesting microphone access');
  navigator.mediaDevices.getUserMedia({ audio: true }).then((stream) => {
    console.log('[voice] Microphone access granted, stream active:', stream.active);
    micStream = stream;
    
    // Check WebSocket is open before starting
    if (ws?.readyState !== WebSocket.OPEN) {
      console.error('[voice] WebSocket not OPEN when starting mic streaming. State:', ws?.readyState);
      stream.getTracks().forEach(t => t.stop());
      return;
    }
    
    micAudioContext = new AudioContext({ sampleRate: 16000 });
    const source = micAudioContext.createMediaStreamSource(stream);
    const processor = micAudioContext.createScriptProcessor(4096, 1, 1);

    source.connect(processor);
    processor.connect(micAudioContext.destination);

    processor.onaudioprocess = (e) => {
      if (ws?.readyState !== WebSocket.OPEN || isPausedForSpeech) return;
      const input = e.inputBuffer.getChannelData(0);
      const pcm16 = floatTo16BitPCM(input);
      const base64 = arrayBufferToBase64(pcm16.buffer);
      ws.send(JSON.stringify({
        realtimeInput: { audio: { data: base64, mimeType: "audio/pcm;rate=16000" } }
      }));
    };
    console.log('[voice] Mic streaming started successfully');
  }).catch((e) => {
    console.error('[voice] Microphone access failed:', e.name, e.message);
    if (e.name === 'NotAllowedError') {
      console.error('[voice] User denied microphone permission');
    } else if (e.name === 'NotFoundError') {
      console.error('[voice] No microphone device found');
    }
  });
}


export async function speak(text, onDone) {
  if (!text?.trim()) {
    onDone?.();
    return;
  }

  // IMPORTANT:
  // Stop any previous question that is still being spoken.
  stopSpeaking();

  pauseListeningForSpeech();

  try {
    const res = await fetch(`${BACKEND_URL}/tts`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text })
    });

    if (!res.ok) {
      throw new Error(`TTS HTTP ${res.status}`);
    }

    if (!res.body) {
      throw new Error('TTS response has no streaming body');
    }

    await playAudioStream(res.body, () => {
      resumeListeningAfterSpeech();
      onDone?.();
    });

  } catch (e) {
    console.warn('[tts] failed', e);
    resumeListeningAfterSpeech();
    onDone?.();
  }
}


export function stopSpeaking() {
  // Invalidate the currently running stream
  speechGeneration++;

  // Stop every audio chunk that has been scheduled
  for (const source of currentAudioSources) {
    try {
      source.onended = null;
      source.stop();
    } catch (e) {
      // Already stopped
    }
  }

  currentAudioSources = [];

  resumeListeningAfterSpeech();
}


async function playAudioStream(stream, onDone) {
  if (!playbackAudioContext) {
    playbackAudioContext = new AudioContext({
      sampleRate: 24000
    });
  }

  if (playbackAudioContext.state === 'suspended') {
    await playbackAudioContext.resume();
  }

  const reader = stream.getReader();

  const myGeneration = speechGeneration;

  let nextStartTime = playbackAudioContext.currentTime;
  let receivedAnyAudio = false;

  try {
    while (true) {
      // If another question started speaking, stop this stream.
      if (myGeneration !== speechGeneration) {
        try {
          await reader.cancel();
        } catch (e) {}

        return;
      }

      const { value, done } = await reader.read();

      if (done) {
        break;
      }

      if (!value || value.length === 0) {
        continue;
      }

      receivedAnyAudio = true;

      const sampleCount = Math.floor(value.byteLength / 2);

      if (sampleCount <= 0) {
        continue;
      }

      const int16 = new Int16Array(
        value.buffer,
        value.byteOffset,
        sampleCount
      );

      const float32 = new Float32Array(sampleCount);

      for (let i = 0; i < sampleCount; i++) {
        float32[i] = int16[i] / 32768;
      }

      const audioBuffer = playbackAudioContext.createBuffer(
        1,
        sampleCount,
        24000
      );

      audioBuffer.copyToChannel(float32, 0);

      const source = playbackAudioContext.createBufferSource();

      source.buffer = audioBuffer;
      source.connect(playbackAudioContext.destination);

      currentAudioSources.push(source);

      source.onended = () => {
        currentAudioSources =
          currentAudioSources.filter(s => s !== source);
      };

      const now = playbackAudioContext.currentTime;

      if (nextStartTime < now) {
        nextStartTime = now;
      }

      source.start(nextStartTime);

      nextStartTime += audioBuffer.duration;
    }

    if (receivedAnyAudio && myGeneration === speechGeneration) {
      const remaining = Math.max(
        0,
        nextStartTime - playbackAudioContext.currentTime
      );

      if (remaining > 0) {
        await new Promise(resolve =>
          setTimeout(resolve, remaining * 1000)
        );
      }
    }

  } finally {
    if (myGeneration === speechGeneration) {
      onDone?.();
    }
  }
}
function pauseListeningForSpeech() {
  isPausedForSpeech = true;
}
function resumeListeningAfterSpeech() {
  isPausedForSpeech = false;
}

export function updateTranscriptCallback(onFinalTranscript) {
  onFinalTranscriptCallback = onFinalTranscript;
}


function floatTo16BitPCM(input) {
  const output = new Int16Array(input.length);
  for (let i = 0; i < input.length; i++) {
    const s = Math.max(-1, Math.min(1, input[i]));
    output[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
  }
  return output;
}

function arrayBufferToBase64(buffer) {
  let binary = '';
  const bytes = new Uint8Array(buffer);
  bytes.forEach(b => binary += String.fromCharCode(b));
  return btoa(binary);
}

