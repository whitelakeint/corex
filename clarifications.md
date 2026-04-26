# Clarifications & Open Questions

## Tavus Configuration

1. **Replica selection**: We defaulted to Rose (`r1af76e94d00`). Is this the intended avatar, or should a different replica be used? Tavus offers stock replicas and custom ones (created from a 2-minute training video).

2. **LLM model**: We used `tavus-gpt-oss` as specified in the plan. Should this be swapped for a different model (e.g., a BYO OpenAI/Anthropic model via `base_url` + `api_key` in the LLM layer)?

3. **Tool call callback URL**: Currently set to `http://localhost:8001/webhooks/tavus`. For Tavus to actually deliver tool call webhooks during a live conversation, this URL must be publicly reachable. Options:
   - Use a tunneling service (ngrok, cloudflared) during development
   - Deploy to a public server
   - What is the intended deployment target?

4. **Document upload URLs**: `scripts/upload_documents.py` requires public URLs for both `building_info.txt` and `AI Avatar Interactions.docx`. Where should these be hosted? (S3, GitHub raw, temporary file hosting?)

## Tool Call Flow

5. **How do tool calls reach the backend?** The current setup defines tools in the persona and sets a `callback_url` on conversation creation. Does Tavus POST tool call invocations to the callback URL automatically, or do tool call events come through as webhook events that need to be parsed and dispatched? The webhook handler currently logs generic events — it may need to detect tool call events and route them to the appropriate stub handler.

6. **Tool call response feedback**: When a tool like `notify_resident` is triggered, the backend logs and returns a response. Does Tavus expect the webhook response body to contain the tool result (so the LLM can use it in its next reply), or is the tool result communicated back through a separate API call?

## Business Logic

7. **Resident confirmation flow**: The system prompt says "never unlock without resident confirmation." In the stubbed version, `notify_resident` always returns `"notified (simulated)"`. In production, how should this work?
   - Does the concierge wait for a real-time callback from the resident (phone call, app notification)?
   - Is there a timeout before telling the visitor the resident is unavailable?
   - Should the avatar poll for confirmation or receive a push event?

8. **Building information accuracy**: `knowledge-base/building_info.txt` contains fabricated data for "The Meridian" (address, pricing, contacts, etc.). Should this be replaced with real building data? If so, from what source?

9. **Conversation duration limits**: We set `max_call_duration: 600` (10 minutes). Is this appropriate, or should it be longer/shorter for a lobby concierge use case?

## Frontend & Deployment

10. **Frontend hosting**: Currently the FastAPI server serves `frontend/index.html` at `/`. Is this sufficient, or should the frontend be deployed separately (e.g., on a CDN, as a kiosk app)?

11. **Authentication**: The web portal is completely open — anyone who can reach the server can start a conversation (which consumes Tavus API credits). Should there be any access control? Options:
    - API key or password for the portal
    - Tavus private rooms (`require_auth: true` + meeting tokens)
    - Rate limiting

12. **CORS policy**: Currently set to `allow_origins=["*"]`. Should this be restricted to specific domains for production?

## AI Avatar Interactions Document

13. **Document content**: The `AI Avatar Interactions.docx` is a binary Word file that couldn't be read programmatically during development. The system prompt was written based on the plan's description of 9 Q&A categories and 31 pairs. Should the exact Q&A pairs from the document be cross-checked against the system prompt to ensure nothing was missed?

14. **Tone calibration**: The system prompt instructs "warm, professional, concise — like a five-star hotel concierge." Are there specific tone adjustments needed (more formal, more casual, specific phrases to use or avoid)?
