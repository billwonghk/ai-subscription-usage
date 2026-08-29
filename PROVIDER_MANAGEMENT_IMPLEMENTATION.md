# Platform management implementation

This change keeps the existing ChatGPT, Claude, Gemini, and Grok adapters and adds user-controlled platform selection. Existing installations migrate with all four current platforms enabled, so an update does not silently remove a previously visible platform. The user can add or remove any current platform from Settings at any time.

Only enabled platforms enter collection, aggregation, subscription-plan display, top summary calculations, provider details, and DeepSeek comparison calculations. Disabled platforms are not parsed. Enabled platforms with no records remain visible in Settings and provider details, but do not create chart legends, chart lines, baselines, or hover rows.

Subscription cards and provider-detail tabs use equal-width columns based on the number of enabled platforms. Existing provider colors continue to come from the single `PROVIDER_META` registry; no duplicate color configuration was introduced.

Settings reports read-only discovery status for each current platform. When a source is missing or unsupported, the user can copy the existing safe local-AI setup prompt. The prompt permits only read-only diagnostics and validated source configuration. It forbids OAuth, auth tokens, cookies, Keychain access, conversation-content access, and AI-client modification.

MiniMax was checked on this Mac without reading credentials or conversation content. Its local `token_usage` table provides model, timestamp, input, output, reasoning, cache-read, and cache-write counters. MiniMax is therefore selectable and its real local accounting data is included. The parser selects only those accounting columns and never reads the raw payload or message tables. The two locally observed model identifiers are mapped to their exact current OpenRouter model IDs.

Kimi, GLM, and Alibaba Bailian are selectable and have read-only installation/data-directory detection. No verified local records are available on this Mac, so they do not yet parse or report Token usage. A detected but unverified format is shown explicitly instead of fabricating data. Cursor is not part of this change.

The existing date semantics remain unchanged. This change does not add a new distinction between a true daily zero and an unavailable daily scan, because that is a separate data-quality feature rather than part of provider selection.
