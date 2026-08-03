import 'package:shared_preferences/shared_preferences.dart';

/// Persists user settings: the full webhook URL and the contact-name toggle.
class SettingsRepository {
  SettingsRepository(this._prefs);

  final SharedPreferences _prefs;

  static const _kWebhookUrl = 'webhook_url';
  static const _kResolveContacts = 'resolve_contacts';

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
}
