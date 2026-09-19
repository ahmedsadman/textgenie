import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:textgenie/data/settings_repository.dart';

Future<SettingsRepository> _repo([Map<String, Object> seed = const {}]) async {
  SharedPreferences.setMockInitialValues(seed);
  return SettingsRepository(await SharedPreferences.getInstance());
}

void main() {
  test('finance filters default to null/empty when unset', () async {
    final repo = await _repo();
    expect(repo.summaryRange, isNull);
    expect(repo.txRange, isNull);
    expect(repo.txSort, isNull);
    expect(repo.txTypes, isEmpty);
  });

  test('persists and reads back the summary range', () async {
    final repo = await _repo();
    await repo.setSummaryRange('this_year');
    expect(repo.summaryRange, 'this_year');
  });

  test('persists and reads back transaction filters', () async {
    final repo = await _repo();
    await repo.setTxRange('last_3_months');
    await repo.setTxSort('amount-desc');
    await repo.setTxTypes(['income', 'transfer']);

    expect(repo.txRange, 'last_3_months');
    expect(repo.txSort, 'amount-desc');
    expect(repo.txTypes, ['income', 'transfer']);
  });

  test('an empty type list round-trips to empty (not [""])', () async {
    final repo = await _repo();
    await repo.setTxTypes(const []);
    expect(repo.txTypes, isEmpty);
  });
}
