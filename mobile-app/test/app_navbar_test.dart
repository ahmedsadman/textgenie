import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:textgenie/app.dart';
import 'package:textgenie/theme/catppuccin_theme.dart';

Future<void> _pumpShell(WidgetTester tester) async {
  await tester.pumpWidget(
    ProviderScope(
      child: MaterialApp(
        theme: AppTheme.theme,
        home: const RootShell.withPages([
          Center(child: Text('FINANCE PAGE')),
          Center(child: Text('MESSAGES PAGE')),
          Center(child: Text('SETTINGS PAGE')),
        ]),
      ),
    ),
  );
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('shows tabs in order Finance, Messages, Settings', (
    tester,
  ) async {
    await _pumpShell(tester);

    expect(find.text('Finance'), findsOneWidget);
    expect(find.text('Messages'), findsOneWidget);
    expect(find.text('Settings'), findsOneWidget);

    final financeX = tester.getCenter(find.text('Finance')).dx;
    final messagesX = tester.getCenter(find.text('Messages')).dx;
    final settingsX = tester.getCenter(find.text('Settings')).dx;
    expect(financeX, lessThan(messagesX));
    expect(messagesX, lessThan(settingsX));
  });

  testWidgets('defaults to the Finance tab', (tester) async {
    await _pumpShell(tester);
    expect(find.text('FINANCE PAGE'), findsOneWidget);
    expect(find.text('MESSAGES PAGE'), findsNothing);
  });

  testWidgets('switches tabs when a destination is tapped', (tester) async {
    await _pumpShell(tester);

    await tester.tap(find.text('Messages'));
    await tester.pumpAndSettle();
    expect(find.text('MESSAGES PAGE'), findsOneWidget);
    expect(find.text('FINANCE PAGE'), findsNothing);

    await tester.tap(find.text('Settings'));
    await tester.pumpAndSettle();
    expect(find.text('SETTINGS PAGE'), findsOneWidget);
  });
}
