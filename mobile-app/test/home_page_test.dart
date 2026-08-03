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
}) async {
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        settingsControllerProvider.overrideWith(() => _StubSettings(settings)),
        queuedProvider.overrideWith((ref) => Stream.value(queued)),
        historyProvider.overrideWith((ref) => Stream.value(history)),
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

  testWidgets('renders history with success/failure badges', (tester) async {
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
  });
}
