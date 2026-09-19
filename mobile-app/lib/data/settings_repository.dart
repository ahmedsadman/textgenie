import 'package:shared_preferences/shared_preferences.dart';

/// Persists user settings: the full webhook URL and the contact-name toggle.
class SettingsRepository {
  SettingsRepository(this._prefs);

  final SharedPreferences _prefs;

  static const _kWebhookUrl = 'webhook_url';
  static const _kResolveContacts = 'resolve_contacts';
  static const _kSummaryRange = 'summary_range';
  static const _kTxRange = 'tx_range';
  static const _kTxTypes = 'tx_types';
  static const _kTxSort = 'tx_sort';
  static const _kHideBalance = 'hide_balance';

  /// Full webhook URL typed by the user, or null when unset.
  String? get webhookUrl {
    final value = _prefs.getString(_kWebhookUrl)?.trim();
    return (value == null || value.isEmpty) ? null : value;
  }

  Future<void> setWebhookUrl(String url) =>
      _prefs.setString(_kWebhookUrl, url.trim());

  bool get hasWebhookUrl => webhookUrl != null;

  /// Whether to look up contact names for numeric senders (default on).
  bool get resolveContacts => _prefs.getBool(_kResolveContacts) ?? true;

  Future<void> setResolveContacts(bool value) =>
      _prefs.setBool(_kResolveContacts, value);

  // Persisted finance filters, so the user's date ranges and transaction
  // filters survive app restarts. Stored as raw preset/sort keys; callers map
  // them back to enums. Null means "not set yet" (use the widget's default).

  /// Preset key for the summary graph's date range.
  String? get summaryRange => _prefs.getString(_kSummaryRange);

  Future<void> setSummaryRange(String key) =>
      _prefs.setString(_kSummaryRange, key);

  /// Preset key for the transactions date range.
  String? get txRange => _prefs.getString(_kTxRange);

  Future<void> setTxRange(String key) => _prefs.setString(_kTxRange, key);

  /// Selected transaction type filter values (empty means "all").
  List<String> get txTypes {
    final raw = _prefs.getString(_kTxTypes);
    if (raw == null || raw.isEmpty) return const [];
    return raw.split(',');
  }

  Future<void> setTxTypes(List<String> values) =>
      _prefs.setString(_kTxTypes, values.join(','));

  /// Sort key for the transactions list (e.g. `date-desc`).
  String? get txSort => _prefs.getString(_kTxSort);

  Future<void> setTxSort(String key) => _prefs.setString(_kTxSort, key);

  /// Whether monetary values are masked across the Finance tab (default off).
  bool get hideBalance => _prefs.getBool(_kHideBalance) ?? false;

  Future<void> setHideBalance(bool value) =>
      _prefs.setBool(_kHideBalance, value);
}
