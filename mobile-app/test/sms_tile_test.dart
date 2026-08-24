import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:textgenie/models/sms_record.dart';
import 'package:textgenie/theme/catppuccin_theme.dart';
import 'package:textgenie/ui/widgets/sms_tile.dart';

Future<void> _pumpTile(WidgetTester tester, SmsRecord record) async {
  await tester.pumpWidget(
    MaterialApp(
      theme: AppTheme.theme,
      home: Scaffold(body: SmsTile(record)),
    ),
  );
  await tester.pumpAndSettle();
}

SmsRecord _rec({required int timestamp}) => SmsRecord(
  sender: '+8801712345678',
  content: 'hello world',
  timestamp: timestamp,
);

void main() {
  testWidgets('renders the timestamp in 12-hour AM/PM format', (tester) async {
    await _pumpTile(tester, _rec(timestamp: 1719000000000));
    expect(
      find.textContaining(RegExp(r'\d{1,2}:\d{2} (AM|PM)$')),
      findsOneWidget,
    );
  });

  testWidgets('uses 12 (not 0) for midnight and PM after noon', (tester) async {
    // Build local-midnight and local-noon instants so the assertion is
    // timezone-independent.
    final midnight = DateTime(2024, 1, 1, 0, 5).millisecondsSinceEpoch;
    await _pumpTile(tester, _rec(timestamp: midnight));
    expect(find.textContaining('12:05 AM'), findsOneWidget);

    final noon = DateTime(2024, 1, 1, 12, 5).millisecondsSinceEpoch;
    await _pumpTile(tester, _rec(timestamp: noon));
    expect(find.textContaining('12:05 PM'), findsOneWidget);
  });
}
