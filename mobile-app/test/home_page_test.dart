import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:textgenie/models/sms_record.dart';
import 'package:textgenie/state/providers.dart';
import 'package:textgenie/theme/catppuccin_theme.dart';
import 'package:textgenie/ui/home_page.dart';

class _StubSettings extends SettingsController {
  _StubSettings(this._state);
  final SettingsState _state;
  @override
  SettingsState build() => _state;
}

Future<void> _pumpHome(
  WidgetTester tester, {
  required SettingsState settings,
  List<SmsRecord> queued = const [],
  List<SmsRecord> history = const [],
  int failedCount = 0,
}) async {
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        settingsControllerProvider.overrideWith(() => _StubSettings(settings)),
        queuedProvider.overrideWith((ref) => Stream.value(queued)),
        historyProvider.overrideWith((ref) => Stream.value(history)),
        failedCountProvider.overrideWith((ref) => Stream.value(failedCount)),
      ],
      child: MaterialApp(theme: AppTheme.theme, home: const HomePage()),
    ),
  );
  await tester.pumpAndSettle();
}

SmsRecord _rec({
  String sender = '+8801712345678',
  String? contactName,
  SmsStatus status = SmsStatus.queued,
}) => SmsRecord(
  sender: sender,
  contactName: contactName,
  content: 'hello world',
  timestamp: 1719000000000,
  status: status,
);

void main() {
  testWidgets('shows webhook banner when no URL configured', (tester) async {
    await _pumpHome(
      tester,
      settings: const SettingsState(webhookUrl: null, resolveContacts: true),
    );
    expect(find.textContaining('No webhook URL configured'), findsOneWidget);
  });

  testWidgets('hides banner when URL configured', (tester) async {
    await _pumpHome(
      tester,
      settings: const SettingsState(
        webhookUrl: 'https://x.dev',
        resolveContacts: true,
      ),
    );
    expect(find.textContaining('No webhook URL configured'), findsNothing);
  });

  testWidgets('renders queued messages with contact name and status', (
    tester,
  ) async {
    await _pumpHome(
      tester,
      settings: const SettingsState(
        webhookUrl: 'https://x.dev',
        resolveContacts: true,
      ),
      queued: [_rec(contactName: 'John Doe')],
    );
    expect(find.text('John Doe (+8801712345678)'), findsOneWidget);
    expect(find.text('hello world'), findsOneWidget);
    expect(find.text('Queued'), findsWidgets); // section header + badge
  });

  testWidgets('history footer notes failures when a failure is present', (
    tester,
  ) async {
    await _pumpHome(
      tester,
      settings: const SettingsState(
        webhookUrl: 'https://x.dev',
        resolveContacts: true,
      ),
      history: [
        _rec(status: SmsStatus.success),
        _rec(sender: 'GP', status: SmsStatus.failure),
      ],
    );
    expect(find.text('Success'), findsOneWidget);
    expect(find.text('Failure'), findsOneWidget);
    expect(find.text('No messages sent yet.'), findsNothing);
    expect(
      find.text('Showing recent history only, including failures'),
      findsOneWidget,
    );
  });

  testWidgets('history footer omits failures note with only successes', (
    tester,
  ) async {
    await _pumpHome(
      tester,
      settings: const SettingsState(
        webhookUrl: 'https://x.dev',
        resolveContacts: true,
      ),
      history: [_rec(status: SmsStatus.success)],
    );
    expect(find.text('Showing recent history only'), findsOneWidget);
    expect(
      find.text('Showing recent history only, including failures'),
      findsNothing,
    );
  });

  testWidgets('hides history footer when history is empty', (tester) async {
    await _pumpHome(
      tester,
      settings: const SettingsState(
        webhookUrl: 'https://x.dev',
        resolveContacts: true,
      ),
    );
    expect(find.text('No messages sent yet.'), findsOneWidget);
    expect(find.textContaining('Showing recent history only'), findsNothing);
  });

  testWidgets('shows retry icon when failures exist and webhook set', (
    tester,
  ) async {
    await _pumpHome(
      tester,
      settings: const SettingsState(
        webhookUrl: 'https://x.dev',
        resolveContacts: true,
      ),
      history: [_rec(status: SmsStatus.failure)],
      failedCount: 1,
    );
    expect(find.byTooltip('Retry failed'), findsOneWidget);
  });

  testWidgets('hides retry icon when there are no failures', (tester) async {
    await _pumpHome(
      tester,
      settings: const SettingsState(
        webhookUrl: 'https://x.dev',
        resolveContacts: true,
      ),
      history: [_rec(status: SmsStatus.success)],
    );
    expect(find.byTooltip('Retry failed'), findsNothing);
  });

  testWidgets('hides retry icon when no webhook configured', (tester) async {
    await _pumpHome(
      tester,
      settings: const SettingsState(webhookUrl: null, resolveContacts: true),
      history: [_rec(status: SmsStatus.failure)],
      failedCount: 1,
    );
    expect(find.byTooltip('Retry failed'), findsNothing);
  });

  testWidgets('shows send-queued icon when queue has items and webhook set', (
    tester,
  ) async {
    await _pumpHome(
      tester,
      settings: const SettingsState(
        webhookUrl: 'https://x.dev',
        resolveContacts: true,
      ),
      queued: [_rec()],
    );
    expect(find.byTooltip('Send queued now'), findsOneWidget);
  });

  testWidgets('hides send-queued icon when the queue is empty', (tester) async {
    await _pumpHome(
      tester,
      settings: const SettingsState(
        webhookUrl: 'https://x.dev',
        resolveContacts: true,
      ),
    );
    expect(find.byTooltip('Send queued now'), findsNothing);
  });

  testWidgets('hides send-queued icon when no webhook configured', (
    tester,
  ) async {
    await _pumpHome(
      tester,
      settings: const SettingsState(webhookUrl: null, resolveContacts: true),
      queued: [_rec()],
    );
    expect(find.byTooltip('Send queued now'), findsNothing);
  });
}
