# TextGenie Mobile (Android)

Flutter app that captures incoming phone SMS and forwards each to a user-configured
webhook, replacing manual SMS-automation tooling.

## What it does

- Listens for incoming SMS via a manifest `BroadcastReceiver` (`another_telephony`),
  which fires even when the app is killed.
- Persists each SMS to a local sqflite queue (deduped on sender+timestamp+content).
- Flushes the queue to the webhook one message at a time, with up to 5 attempts,
  exponential backoff, and connectivity gating (offline → stays queued, resumes on
  reconnect / app open / a WorkManager periodic tick).
- Home shows the **Queued** list and the last 10 **History** entries with status.
- Settings holds the full webhook URL, a contact-name toggle, and a
  battery-optimization prompt.

## Webhook payload

`POST` to the exact URL from Settings, JSON body:

```json
{ "sender": "+8801712345678", "content": "...", "timestamp": 1719000000000, "contactName": "John Doe" }
```

- `sender` — raw value Android reports (phone number, or alphanumeric ID like `GP`).
- `contactName` — resolved contact name for numeric senders (null otherwise).
- `timestamp` — epoch ms when the SMS was **received**.
- Any 2xx = success; anything else = failure.

## Architecture

`lib/`
- `models/` — `SmsRecord` + status enum, DB and webhook mapping.
- `data/` — sqflite `database`, `sms_repository` (queue/history/claim), `settings_repository`.
- `services/` — `sms_listener`, `contact_resolver`, `webhook_client`, `connectivity_service`,
  `flush_service` (retry/backoff/claim), `background_worker` (WorkManager), `app_services`
  (dependency bundle, also bootstrapped standalone in background isolates), `permissions`.
- `state/` — Riverpod providers.
- `ui/` — Home + Settings, bottom-nav shell, widgets. Catppuccin Macchiato theme.

Background isolates (SMS-while-killed, WorkManager) call
`DartPluginRegistrant.ensureInitialized()` and build their own `AppServices` since they
cannot share the UI isolate's objects. Cross-isolate double-send is prevented by an
atomic queued→sending claim plus stale-row reclaim.

## Develop

```bash
flutter pub get
flutter analyze
flutter test
flutter build apk --debug
```

## Toolchain notes

- `minSdk 24`, `compileSdk 36`, `targetSdk 35`.
- Pinned to AGP `8.9.1` / Kotlin `2.1.0`: the scaffolded AGP 9 stack breaks
  `workmanager_android` (`kotlin()` DSL) and `permission_handler` 13 requires SDK 37.
  `permission_handler` is held at `^12` for the same reason. Flutter prints
  soon-to-be-dropped warnings for this pair; the build still succeeds.

## Known limitation

No foreground service (by design — no persistent notification). Capture is reliable
(system-triggered receiver), but flushing a backlog while offline **and** killed is
best-effort. Aggressive OEM task-killers (Xiaomi/MIUI, etc.) may kill background work;
the Settings battery-optimization prompt mitigates this.
