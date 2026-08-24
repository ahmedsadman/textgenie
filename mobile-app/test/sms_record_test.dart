import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:textgenie/models/sms_record.dart';

void main() {
  group('toWebhookJson', () {
    test('includes raw sender, content, timestamp and contactName', () {
      final record = SmsRecord(
        sender: '+8801712345678',
        contactName: 'John Doe',
        content: 'hi',
        timestamp: 1719000000000,
      );
      expect(record.toWebhookJson(), {
        'sender': '+8801712345678',
        'content': 'hi',
        'timestamp': 1719000000000,
        'contactName': 'John Doe',
      });
    });

    test('contactName is null when unresolved', () {
      final record = SmsRecord(sender: 'GP', content: 'promo', timestamp: 1);
      expect(record.toWebhookJson()['contactName'], isNull);
    });

    test('encodes content with quotes, newlines and emoji safely', () {
      final record = SmsRecord(
        sender: 'bKash',
        content: 'You "won" 🎉\nReply STOP',
        timestamp: 1,
      );
      final decoded =
          jsonDecode(record.toWebhookBody()) as Map<String, dynamic>;
      expect(decoded['content'], 'You "won" 🎉\nReply STOP');
      expect(decoded['sender'], 'bKash');
    });
  });

  group('db round-trip', () {
    test('survives toDbMap -> fromDbMap', () {
      final record = SmsRecord(
        id: 5,
        sender: '+100',
        contactName: 'Alice',
        content: 'x',
        timestamp: 10,
        status: SmsStatus.failure,
        attempts: 3,
        lastError: 'HTTP 500',
        updatedAt: 99,
        nextAttemptAt: 4242,
      );
      final restored = SmsRecord.fromDbMap(record.toDbMap());
      expect(restored.id, 5);
      expect(restored.status, SmsStatus.failure);
      expect(restored.attempts, 3);
      expect(restored.contactName, 'Alice');
      expect(restored.lastError, 'HTTP 500');
      expect(restored.nextAttemptAt, 4242);
    });
  });
}
