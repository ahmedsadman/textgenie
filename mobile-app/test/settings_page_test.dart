import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:textgenie/data/settings_repository.dart';
import 'package:textgenie/state/providers.dart';
import 'package:textgenie/theme/catppuccin_theme.dart';
import 'package:textgenie/ui/settings_page.dart';

Future<void> _pumpSettings(WidgetTester tester, SettingsRepository repo) async {
  await tester.pumpWidget(
    ProviderScope(
      overrides: [settingsRepositoryProvider.overrideWithValue(repo)],
      child: MaterialApp(theme: AppTheme.theme, home: const SettingsPage()),
    ),
  );
  await tester.pumpAndSettle();
}

void main() {
  late SettingsRepository repo;

  setUp(() async {
    SharedPreferences.setMockInitialValues({});
    repo = SettingsRepository(await SharedPreferences.getInstance());
  });

  testWidgets('rejects an invalid URL', (tester) async {
    await _pumpSettings(tester, repo);
    await tester.enterText(find.byType(TextFormField), 'not-a-url');
    await tester.tap(find.text('Save'));
    await tester.pumpAndSettle();

    expect(find.textContaining('valid URL'), findsOneWidget);
    expect(repo.webhookUrl, isNull);
  });

  testWidgets('saves a valid URL and confirms', (tester) async {
    await _pumpSettings(tester, repo);
    await tester.enterText(
      find.byType(TextFormField),
      'https://example.com/webhook/abc',
    );
    await tester.tap(find.text('Save'));
    await tester.pumpAndSettle();

    expect(find.text('Webhook URL saved'), findsOneWidget);
    expect(repo.webhookUrl, 'https://example.com/webhook/abc');
  });

  testWidgets('shows a Scan QR button in the webhook section', (tester) async {
    await _pumpSettings(tester, repo);
    expect(find.widgetWithText(OutlinedButton, 'Scan QR'), findsOneWidget);
  });

  testWidgets('toggles contact resolution', (tester) async {
    await _pumpSettings(tester, repo);
    expect(repo.resolveContacts, isTrue); // default on

    await tester.tap(find.byType(Switch));
    await tester.pumpAndSettle();

    expect(repo.resolveContacts, isFalse);
  });
}
