import 'package:flutter_contacts/flutter_contacts.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:textgenie/services/contact_resolver.dart';

void main() {
  ContactResolver resolverWith(List<Contact> contacts) =>
      ContactResolver(contactsLoader: () async => contacts);

  final contacts = [
    Contact(
      displayName: 'John Doe',
      phones: [Phone(number: '+8801712345678')],
    ),
    Contact(
      displayName: 'Alice',
      phones: [Phone(number: '01911-000111')],
    ),
  ];

  test('returns null for alphanumeric sender IDs', () async {
    final resolver = resolverWith(contacts);
    expect(await resolver.nameFor('GP'), isNull);
    expect(await resolver.nameFor('bKash'), isNull);
  });

  test('resolves a matching contact by number', () async {
    final resolver = resolverWith(contacts);
    expect(await resolver.nameFor('+8801712345678'), 'John Doe');
  });

  test('matches ignoring formatting and country-code differences', () async {
    final resolver = resolverWith(contacts);
    // Stored as local format, incoming with country code.
    expect(await resolver.nameFor('+8801911000111'), 'Alice');
  });

  test('returns null for an unmatched number', () async {
    final resolver = resolverWith(contacts);
    expect(await resolver.nameFor('+8809999999999'), isNull);
  });

  test('returns null and does not throw when loading fails', () async {
    final resolver = ContactResolver(
      contactsLoader: () async => throw Exception('denied'),
    );
    expect(await resolver.nameFor('+8801712345678'), isNull);
  });
}
