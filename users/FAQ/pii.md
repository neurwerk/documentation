---
updated_at: 24.08.2026 09:42
---

# Frequently Asked Questions

## Why do I see `<PERSON_xxx>` or `<ENCRYPTED_xxx>` in responses?

Our platform uses **Presidio PII masking** to protect your personal information. Before your message reaches the AI model, any detected personal data (names, emails, phone numbers, etc.) is replaced with placeholder tokens like `<PERSON_a1b2c3d4>` or `<ENCRYPTED_...>`.

### In non-streaming requests (`stream: false`)

After the AI responds, our system automatically reverses these placeholders back to the original values. You should never see them — your response looks completely normal.

**Example:**
- You send: *"Hi, I'm John Smith, email john@example.com"*
- AI receives: *"Hi, I'm `<PERSON_a1b2c3d4>`, email `<ENCRYPTED_A7x...==>`"*
- AI responds: *"Hello `<PERSON_a1b2c3d4>`, your email `<ENCRYPTED_A7x...==>` is confirmed."*
- You see: *"Hello John Smith, your email john@example.com is confirmed."*

### In streaming requests (`stream: true`)

**Placeholder reversal is currently not supported for streaming responses.** You will see the raw placeholders in the streamed output.

This is because the underlying AI gateway (AgentGateway) can inspect streaming responses for harmful content but cannot yet modify the text mid-stream. We are tracking this limitation and plan to support streaming reversal once the upstream gateway adds the capability.

**Technical detail:** With streaming enabled, the response webhook is called per text window, and our PII bridge correctly reverses the placeholders in its response. However, AgentGateway's streaming guardrail currently discards masked/modified results — only blocking (rejection) and pass-through are supported. The cleaned text is thrown away, and the original placeholder text is forwarded to you.

### Which mode should I use?

| Feature | Non-streaming | Streaming |
|---|---|---|
| PII masked before reaching AI | ✅ | ✅ |
| Placeholders reversed in response | ✅ | ❌ (shown raw) |
| Response time | Full response at once | Real-time chunks |

For applications handling personal data, **non-streaming** (`stream: false`) provides full round-trip protection. Streaming is safe for your data (nothing sensitive reaches the AI), but you'll see placeholder tokens in the output.

---

## Is my data safe in streaming mode?

**Yes.** PII masking happens on the **request path** — before your message reaches the AI model — regardless of streaming mode. The AI never sees your actual personal information.

The only difference is what *you* see in the response: clean reversed text (non-streaming) or raw placeholder tokens (streaming).

---

## Is streaming reversal supported?

**Yes.** The AgentGateway external processor validates and restores authorized
request-scoped placeholders in supported Chat Completions and Responses streams.
Unknown, malformed, or incomplete reserved placeholders fail closed. Structured,
tool-only, and unsuccessful outputs do not receive a human-readable PII report.

---

## Does Studio policy evaluation call an AI model?

**No.** Studio policy evaluation is a deterministic simulation. It shows the
request that the configured policy would expose to a model, a controlled echo,
and the restored user view. A blocked request is not simulated.

The result is always marked as simulated and is not a model prediction. Studio
does not send the evaluation to AgentGateway, a model provider, or another
external service, and it never returns the internal reversal map.
