# Configure AI Subscription Usage with your local AI

This file is intended for ChatGPT, Claude Code, Gemini CLI, or another local AI that can run commands and inspect file names. The application itself does not require an AI model.

Work only with the installed AI Subscription Usage application. Do not read OAuth files, auth tokens, cookies, browser profiles, Keychain, credentials, or conversation content. Do not modify ChatGPT, Claude, Gemini, Antigravity, Grok, or their configuration. Do not install software or execute downloaded scripts.

Run the bundled application with `--doctor --json`. Review only the returned provider, surface, format, status, path, and matching file count. A `ready` source is already connected. `not_found` means the expected directory does not exist. `no_records` means the directory exists without supported records. `permission_required` means the person must grant access. `unsupported_format` means the client is installed or records exist, but the current application cannot safely calculate Token usage from that format.

If a supported source is stored in a non-default directory, call the validated command below. Substitute only values listed by `--doctor`; the path must be an existing readable directory inside the current user's profile.

```text
AI Subscription Usage --configure-source --provider PROVIDER --surface SURFACE --format FORMAT --path DIRECTORY
```

Finish by running `AI Subscription Usage --verify-sources --json`. Report the status and file count for each provider. After verification succeeds, run `AI Subscription Usage --refresh` to generate the current user's report in the application data directory. Never claim that an unsupported source is connected, never estimate missing Token values, never place a credential or command inside `sources.json`, and never copy the generated report into a source repository or release package.

On macOS, the executable inside the downloaded application bundle can be called as:

```text
/path/to/AI Subscription Usage.app/Contents/MacOS/AI Subscription Usage --doctor --json
```

On Windows, call the downloaded `AI Subscription Usage.exe` with the same arguments.

## Coding Plan sources in the unreleased working version

Kimi Code's persisted `wire.jsonl` records expose per-step `StatusUpdate.token_usage` counters and timestamps. The parser reads these counters, not the context-window size. The official persisted status format does not include a model ID; those records remain unpriced until a verified historical model identity is available. Never infer a past model from the client's current settings.

For Kimi, GLM or Alibaba Bailian used through Claude Code, `--configure-source` accepts provider `kimi`, `glm` or `bailian`, surface `claude-code`, and format `claude-jsonl`. Bind only a directory whose entire history belongs to that subscription. A model name is not proof of subscription ownership: Bailian can serve other vendors' models. Do not bind a mixed-provider directory. Do not change a binding to represent only a new provider while leaving the old provider's history in that directory. No third-party client configuration is modified by this command.

Explicitly bound directories are excluded from the default Claude scan even when the assigned provider is disabled. Overlapping third-party source bindings are rejected. Existing message IDs are deduplicated within each bound scan. Cross-client copies without a shared identity are not globally deduplicated, so select one authoritative source for each set of requests.

These adapters have format-based automated tests; real Kimi, GLM and Bailian client acceptance is pending. A successfully configured path proves readable matching files, not complete pricing or verified subscription ownership.
