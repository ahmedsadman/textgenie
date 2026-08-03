import 'dart:ui';

import 'package:flutter/widgets.dart';
import 'package:workmanager/workmanager.dart';

import 'app_services.dart';

const String _flushTask = 'textgenie.flush';
const String _periodicName = 'textgenie.flush.periodic';

/// WorkManager entry point. Best-effort catch-up flush when the app is killed
/// (e.g. a backlog queued while offline). Must be top-level.
@pragma('vm:entry-point')
void callbackDispatcher() {
  Workmanager().executeTask((task, _) async {
    WidgetsFlutterBinding.ensureInitialized();
    DartPluginRegistrant.ensureInitialized();
    try {
      final services = await AppServices.bootstrap();
      await services.flushService.flush();
      return true;
    } catch (_) {
      return false; // let WorkManager reschedule
    }
  });
}

/// Initializes WorkManager and schedules the periodic flush.
class BackgroundWorker {
  const BackgroundWorker._();

  static Future<void> initialize() async {
    await Workmanager().initialize(callbackDispatcher);
    await Workmanager().registerPeriodicTask(
      _periodicName,
      _flushTask,
      frequency: const Duration(minutes: 15), // Android minimum
      constraints: Constraints(networkType: NetworkType.connected),
      existingWorkPolicy: ExistingPeriodicWorkPolicy.keep,
    );
  }
}
