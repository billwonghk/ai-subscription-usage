# Configure AI Subscription Usage with your local AI

This file is intended for ChatGPT, Claude Code, Gemini CLI, or another local AI that can run commands and inspect file names. The application itself does not require an AI model.

The application first detects supported records in registered default folders automatically. If the report already shows usage, no connection step is required. Use this guide only when an installed client or existing records were not detected. The assistant must be able to inspect files and run the packaged application's local commands on the same computer; a web chat without local computer access cannot perform this setup.

## Complete prompt to give your local AI

Copy the following prompt into your own local Codex, Claude Code, WorkBuddy, Gemini CLI, or another assistant that can inspect files and run commands on this computer:

```text
Help me connect the installed AI Subscription Usage application to supported usage records on this computer.

Work only with the installed AI Subscription Usage application and existing local usage-log directories. Do not install software. Do not read or display OAuth files, auth tokens, API keys, cookies, browser profiles, Keychain entries, credentials, prompts, replies, or conversation content. Do not modify any AI client or its configuration. Do not scan the whole disk.

1. Locate the installed AI Subscription Usage executable. On macOS it is inside the application bundle at /path/to/AI Subscription Usage.app/Contents/MacOS/AI Subscription Usage. On Windows use the installed or portable AI Subscription Usage.exe.
2. Run that executable with --doctor --json.
3. Review only provider, surface, format, status, path, usage_support, and matching_files. A source with status ready is already connected and must not be changed.
4. For each source that is not ready, check only its standard directory reported by --doctor and other existing directories that I explicitly identify. If a supported source exists outside its default path, register it with the same executable using --configure-source --provider PROVIDER --surface SURFACE --format FORMAT --path DIRECTORY. Use only an allowed provider, surface, and format returned by --doctor, and only an existing readable directory inside my user profile. Never guess a format or register a mixed-provider directory.
5. Run --verify-sources --json. If at least one source is ready, run --refresh once.
6. Report only each provider's status, surface, format, and matching file count. State clearly which sources are ready, which have no records, which need permission, and which formats are unsupported. Do not claim that a detected-only or unsupported source is connected, and do not estimate missing Token values.
```

The same prompt is available inside the application under **Configuration and User Guide**. The remaining sections below define the commands and safety limits the assistant must follow.

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
