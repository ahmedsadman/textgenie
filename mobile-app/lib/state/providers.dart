import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sqflite/sqflite.dart';

import '../data/settings_repository.dart';
import '../data/sms_repository.dart';
import '../models/sms_record.dart';
import '../services/app_services.dart';
import '../services/flush_service.dart';
import '../services/sms_listener.dart';

/// Overridden in `main()` once async initialization completes.
final sharedPreferencesProvider = Provider<SharedPreferences>(
  (ref) =>
      throw UnimplementedError('sharedPreferencesProvider must be overridden'),
);
final databaseProvider = Provider<Database>(
  (ref) => throw UnimplementedError('databaseProvider must be overridden'),
);

final appServicesProvider = Provider<AppServices>(
  (ref) => AppServices.from(
    database: ref.watch(databaseProvider),
    prefs: ref.watch(sharedPreferencesProvider),
  ),
);

final smsRepositoryProvider = Provider<SmsRepository>(
  (ref) => ref.watch(appServicesProvider).smsRepository,
);

final settingsRepositoryProvider = Provider<SettingsRepository>(
  (ref) => ref.watch(appServicesProvider).settings,
);

final flushServiceProvider = Provider<FlushService>(
  (ref) => ref.watch(appServicesProvider).flushService,
);

final smsListenerProvider = Provider<SmsListener>(
  (ref) => SmsListener(ref.watch(appServicesProvider)),
);

/// Polls the queue so the UI reflects writes from any isolate.
final queuedProvider = StreamProvider.autoDispose<List<SmsRecord>>((ref) {
  final repo = ref.watch(smsRepositoryProvider);
  return _poll(() => repo.queued());
});

final historyProvider = StreamProvider.autoDispose<List<SmsRecord>>((ref) {
  final repo = ref.watch(smsRepositoryProvider);
  return _poll(() => repo.history());
});

/// Number of failed records, polled so the History retry affordance appears and
/// clears in step with background delivery.
final failedCountProvider = StreamProvider.autoDispose<int>((ref) {
  final repo = ref.watch(smsRepositoryProvider);
  return _poll(() => repo.countFailed());
});

Stream<T> _poll<T>(Future<T> Function() read) async* {
  yield await read();
  yield* Stream.periodic(const Duration(seconds: 2)).asyncMap((_) => read());
}

/// Reactive view of user settings.
class SettingsState {
  const SettingsState({
    required this.webhookUrl,
    required this.resolveContacts,
  });

  final String? webhookUrl;
  final bool resolveContacts;

  bool get hasWebhookUrl => webhookUrl != null;
}

class SettingsController extends Notifier<SettingsState> {
  @override
  SettingsState build() {
    final repo = ref.watch(settingsRepositoryProvider);
    return SettingsState(
      webhookUrl: repo.webhookUrl,
      resolveContacts: repo.resolveContacts,
    );
  }

  Future<void> setWebhookUrl(String url) async {
    await ref.read(settingsRepositoryProvider).setWebhookUrl(url);
    final trimmed = url.trim();
    state = SettingsState(
      webhookUrl: trimmed.isEmpty ? null : trimmed,
      resolveContacts: state.resolveContacts,
    );
  }

  Future<void> setResolveContacts(bool value) async {
    await ref.read(settingsRepositoryProvider).setResolveContacts(value);
    state = SettingsState(webhookUrl: state.webhookUrl, resolveContacts: value);
  }
}

final settingsControllerProvider =
    NotifierProvider<SettingsController, SettingsState>(SettingsController.new);

/// Index of the Settings tab in the bottom navigation (Finance, Messages,
/// Settings). Used by pages that deep-link to Settings.
const int kSettingsTabIndex = 2;

/// The selected bottom-nav tab. Held in a provider (not local shell state) so
/// any page can switch tabs — e.g. a "connect" prompt jumping to Settings.
class SelectedTab extends Notifier<int> {
  @override
  int build() => 0;

  void select(int index) => state = index;
}

final selectedTabProvider = NotifierProvider<SelectedTab, int>(SelectedTab.new);

/// Whether monetary values are masked across the Finance tab. Persisted locally
/// so the choice survives restarts.
class BalanceHidden extends Notifier<bool> {
  @override
  bool build() => ref.watch(settingsRepositoryProvider).hideBalance;

  Future<void> toggle() async {
    final value = !state;
    await ref.read(settingsRepositoryProvider).setHideBalance(value);
    state = value;
  }
}

final balanceHiddenProvider = NotifierProvider<BalanceHidden, bool>(
  BalanceHidden.new,
);
