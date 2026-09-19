import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:textgenie/state/providers.dart';
import 'package:textgenie/theme/catppuccin_theme.dart';
import 'package:textgenie/ui/widgets/connect_prompt.dart';

void main() {
  testWidgets('renders the icon, text and Open Settings button', (
    tester,
  ) async {
    await tester.pumpWidget(
      const ProviderScope(
        child: MaterialApp(
          home: Scaffold(
            body: ConnectPrompt(
              icon: Icons.sms_outlined,
              title: 'Connect to send messages',
              message: 'Add your webhook URL in Settings.',
            ),
          ),
        ),
      ),
    );

    expect(find.text('Connect to send messages'), findsOneWidget);
    expect(find.text('Add your webhook URL in Settings.'), findsOneWidget);
    expect(find.widgetWithText(FilledButton, 'Open Settings'), findsOneWidget);
  });

  testWidgets('Open Settings switches to the Settings tab', (tester) async {
    final container = ProviderContainer();
    addTearDown(container.dispose);

    await tester.pumpWidget(
      UncontrolledProviderScope(
        container: container,
        child: MaterialApp(
          theme: AppTheme.theme,
          home: const Scaffold(
            body: ConnectPrompt(
              icon: Icons.account_balance_wallet_outlined,
              title: 'Connect to view Finance',
              message: 'Add your webhook URL in Settings.',
            ),
          ),
        ),
      ),
    );

    expect(container.read(selectedTabProvider), 0);
    await tester.tap(find.text('Open Settings'));
    await tester.pump();
    expect(container.read(selectedTabProvider), kSettingsTabIndex);
  });
}
