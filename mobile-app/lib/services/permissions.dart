import 'package:permission_handler/permission_handler.dart';

/// Runtime permission requests for SMS reading and contact lookup.
class AppPermissions {
  const AppPermissions._();

  /// Requests SMS + contacts up front. Contacts is optional — denial only
  /// disables contact-name resolution, it does not block SMS capture.
  static Future<void> requestAll() async {
    await [Permission.sms, Permission.contacts].request();
  }

  static Future<bool> hasSms() => Permission.sms.isGranted;

  static Future<bool> hasContacts() => Permission.contacts.isGranted;

  static Future<bool> requestBatteryExemption() async {
    final status = await Permission.ignoreBatteryOptimizations.request();
    return status.isGranted;
  }

  static Future<bool> ensureCamera() async {
    final status = await Permission.camera.request();
    return status.isGranted;
  }
}
