## Tavus.io — AI Conversational Video Platform

Tavus is an AI research lab based in San Francisco that specializes in real-time, multimodal AI video interactions. They've powered over 2 billion interactions. Their platform enables developers to build AI agents that can **see, hear, and respond** via live video — essentially giving AI a human face and presence.

---

### Core Product: Conversational Video Interface (CVI)

The flagship product is CVI — a full pipeline that turns an AI agent into a real-time video conversation partner. It achieves **~600ms round-trip latency** via a 7-layer architecture:

| Layer | Technology | Function |
|---|---|---|
| **Transport** | WebRTC (Daily) | Bidirectional audio/video streaming |
| **Perception** | Raven model | Interprets expressions, gaze, environment, screen content |
| **Conversational Flow** | Sparrow model | Intelligent turn-taking (when to speak vs. listen) |
| **STT** | Configurable | Real-time speech transcription with context awareness |
| **LLM** | BYO or Tavus-optimized | Processes transcribed speech + visual data |
| **TTS** | Cartesia (default) / ElevenLabs | Converts responses to speech in 30+ languages |
| **Replica Rendering** | Phoenix model | Photorealistic digital avatar with synchronized expressions |

Each layer is modular — developers can swap in their own LLM, TTS engine, etc.

---

### Proprietary AI Models

1. **Phoenix-4** — Gaussian-diffusion rendering model for high-fidelity facial animation with micro-expressions, emotion-driven adjustments, and identity preservation
2. **Raven-1** — Multimodal perception model combining object recognition, emotion detection (sarcasm, frustration, gestures), and adaptive attention across camera, audio, and screenshare
3. **Sparrow-1** — Transformer-based dialogue model for conversational timing, tone/rhythm interpretation, and adaptive turn-taking

---

### API Resources (REST)

Full CRUD APIs for these entities:

- **Conversations** — Create, get, list, end, delete real-time video sessions
- **Personas** — Define agent behavior, tone, knowledge, LLM config, perception settings, TTS voice
- **Replicas** — Create digital twins from a 2-minute training video; also stock replicas available
- **Documents** — Upload knowledge base documents for persona reference; supports recrawling
- **Videos** — Generate async AI videos from a replica + script/audio

---

### Key Features

- **LLM Tool Calling** — Trigger functions from user speech during conversations
- **Perception Tool Calling** — Trigger functions from visual input (via Raven)
- **Knowledge Base** — Upload documents personas can reference
- **Memories** — Personas remember information across conversations
- **Conversation Recordings** — Store recordings in your S3 bucket
- **Private Rooms** — Authenticated conversations with meeting tokens
- **Closed Captions** — Built-in accessibility support
- **Audio-Only Mode** — For voice-only or low-bandwidth scenarios
- **Custom Backgrounds** — Green screen or custom background support
- **Event System** — Rich WebRTC events for speech start/stop, interruptions, utterances, tool calls, perception analysis

---

### Developer Integration

- **React Component Library** — Pre-built components, blocks, and hooks for embedding CVI
- **Embed CVI** — White-label embedding into any site or app
- **LiveKit Integration** — Use Tavus replicas as LiveKit conversational agents
- **Pipecat Integration** — Plug into Pipecat pipelines
- **Webhooks/Callbacks** — Server-side event notifications

---

### Use Cases Highlighted

- AI interviewing / candidate screening
- Educational tutoring
- Sales coaching
- Healthcare consultations
- Customer service agents
- Research assistants

---

### Pricing

- **Free developer tier** available (sign up at platform.tavus.io)
- **Enterprise** — custom pricing with 30+ language support and security features
- **PALs** (consumer product) — Personal AI companions with agentic capabilities (waitlist)
