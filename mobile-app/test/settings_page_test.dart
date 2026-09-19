import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_riverpod/misc.dart' show Override;
import 'package:flutter_test/flutter_test.dart';
import 'package:package_info_plus/package_info_plus.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:textgenie/data/settings_repository.dart';
import 'package:textgenie/state/providers.dart';
import 'package:textgenie/theme/catppuccin_theme.dart';
import 'package:textgenie/ui/settings_page.dart';

import 'support/auth_test_overrides.dart';

Future<void> _pumpSettings(
  WidgetTester tester,
  SettingsRepository repo, {
  List<Override>? authOverrides,
}) async {
  // Tall viewport so the whole settings list is built (no lazy off-screen rows).
  tester.view.physicalSize = const Size(1200, 3000);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        settingsRepositoryProvider.overrideWithValue(repo),
        ...(authOverrides ?? authTestOverrides().overrides),
      ],
      child: MaterialApp(theme: AppTheme.theme, home: const SettingsPage()),
    ),
  );
  await tester.pumpAndSettle();
}

void main() {
  late SettingsRepository repo;

  setUp(() async {
    SharedPreferences.setMockInitialValues({});
    PackageInfo.setMockInitialValues(
      appName: 'TextGenie',
      packageName: 'com.example.textgenie',
      version: '1.1.0',
      buildNumber: '123',
      buildSignature: '',
    );
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

  testWidgets('shows the app version with build number', (tester) async {
    await _pumpSettings(tester, repo);
    expect(find.text('Version 1.1.0 (build 123)'), findsOneWidget);
  });

  testWidgets('shows a Change PIN entry in the Security section', (
    tester,
  ) async {
    await _pumpSettings(tester, repo);
    expect(find.text('Security'), findsOneWidget);
    expect(find.text('Change PIN'), findsOneWidget);
  });

  testWidgets('hides the biometric toggle when unavailable', (tester) async {
    await _pumpSettings(
      tester,
      repo,
      authOverrides: authTestOverrides(biometricAvailable: false).overrides,
    );
    expect(find.text('Unlock with biometrics'), findsNothing);
  });

  testWidgets('shows the biometric toggle when available', (tester) async {
    await _pumpSettings(
      tester,
      repo,
      authOverrides: authTestOverrides(biometricAvailable: true).overrides,
    );
    expect(find.text('Unlock with biometrics'), findsOneWidget);
  });
}
