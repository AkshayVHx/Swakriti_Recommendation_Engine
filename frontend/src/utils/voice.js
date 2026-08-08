const BACKEND_URL = import.meta.env.VITE_BACKEND_URL;

if (!BACKEND_URL) {
  throw new Error('VITE_BACKEND_URL is not set — check your .env file');
}

let ws = null;
let onFinalTranscriptCallback = null;
let micAudioContext = null;
let micStream = null;
let playbackAudioContext = null;
let isPausedForSpeech = false;
let isListeningEnabled = false; 


async function getEphemeralToken() {
  const res = await fetch(`${BACKEND_URL}/live-token`, { method: 'POST' });
  const data = await res.json();
  return data.token;
}


export async function connectVoice(onFinalTranscript) {
  if (ws) return; // already connected, don't reconnect
  onFinalTranscriptCallback = onFinalTranscript;
  const token = await getEphemeralToken();

  ws = new WebSocket(
    `wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContentConstrained?access_token=${token}`
  );

  ws.onopen = () => {
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
      if (transcript && isListeningEnabled && onFinalTranscriptCallback && !isPausedForSpeech) {
        onFinalTranscriptCallback(transcript);
      }
    }
    
  };

  ws.onerror = (e) => console.warn('Live API error', e);
  ws.onclose = (e) => {
    console.warn('Live API connection closed', 'code:', e.code, 'reason:', e.reason);
    ws = null;
  };

  // wait until the socket is actually OPEN before returning
  await new Promise((resolve) => {
    const check = setInterval(() => {
      if (ws?.readyState === WebSocket.OPEN) {
        clearInterval(check);
        resolve();
      }
    }, 50);
  });
}

// starts mic capture on the already-open socket
export function enableListening() {
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
  navigator.mediaDevices.getUserMedia({ audio: true }).then((stream) => {
    micStream = stream;
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
  }).catch((e) => console.warn('Mic permission error', e));
}


export async function speak(text, onDone) {
  pauseListeningForSpeech(); // mute mic input while we talk

  try {
    const res = await fetch(`${BACKEND_URL}/tts`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text })
    });
    const data = await res.json();

    if (!data.audio) {
      console.warn('TTS returned no audio');
      resumeListeningAfterSpeech();
      onDone?.();
      return;
    }

    playAudioFully(data.audio, () => {
      resumeListeningAfterSpeech();
      onDone?.();
    });
  } catch (e) {
    console.warn('TTS failed', e);
    resumeListeningAfterSpeech();
    onDone?.();
  }
}


function playAudioFully(base64Audio, onDone) {
  if (!playbackAudioContext) {
    playbackAudioContext = new AudioContext({ sampleRate: 24000 });
  }
  const pcmBuffer = base64ToArrayBuffer(base64Audio);
  const int16 = new Int16Array(pcmBuffer);
  const float32 = new Float32Array(int16.length);
  for (let i = 0; i < int16.length; i++) float32[i] = int16[i] / 0x8000;

  const audioBuffer = playbackAudioContext.createBuffer(1, float32.length, 24000);
  audioBuffer.copyToChannel(float32, 0);

  const source = playbackAudioContext.createBufferSource();
  source.buffer = audioBuffer;
  source.connect(playbackAudioContext.destination);
  source.onended = () => onDone?.();
  source.start();
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

function base64ToArrayBuffer(base64) {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  return bytes.buffer;
}