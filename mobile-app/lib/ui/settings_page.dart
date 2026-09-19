import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:package_info_plus/package_info_plus.dart';

import '../services/permissions.dart';
import '../state/auth_providers.dart';
import '../state/providers.dart';
import '../utils/webhook_qr.dart';
import 'qr_scan_page.dart';
import 'security/change_pin_screen.dart';

/// Settings tab: webhook URL, contact-name toggle, battery-optimization prompt.
class SettingsPage extends ConsumerStatefulWidget {
  const SettingsPage({super.key});

  @override
  ConsumerState<SettingsPage> createState() => _SettingsPageState();
}

class _SettingsPageState extends ConsumerState<SettingsPage> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _urlController;
  String? _version;

  @override
  void initState() {
    super.initState();
    _urlController = TextEditingController(
      text: ref.read(settingsControllerProvider).webhookUrl ?? '',
    );
    _loadVersion();
  }

  Future<void> _loadVersion() async {
    try {
      final info = await PackageInfo.fromPlatform();
      if (!mounted) return;
      // buildNumber reflects the CI --build-number for store builds (pubspec's
      // +N only for local dev builds).
      setState(
        () => _version = 'Version ${info.version} (build ${info.buildNumber})',
      );
    } catch (_) {
      // Version is informational; ignore if the plugin is unavailable.
    }
  }

  @override
  void dispose() {
    _urlController.dispose();
    super.dispose();
  }

  Future<void> _saveUrl() async {
    if (!_formKey.currentState!.validate()) return;
    await ref
        .read(settingsControllerProvider.notifier)
        .setWebhookUrl(_urlController.text);
    if (!mounted) return;
    FocusScope.of(context).unfocus();
    ScaffoldMessenger.of(
      context,
    ).showSnackBar(const SnackBar(content: Text('Webhook URL saved')));
  }

  Future<void> _scanQr() async {
    final granted = await AppPermissions.ensureCamera();
    if (!mounted) return;
    if (!granted) {
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text('Camera permission denied')));
      return;
    }
    final scanned = await Navigator.of(
      context,
    ).push<String>(MaterialPageRoute(builder: (_) => const QrScanPage()));
    if (!mounted || scanned == null) return;
    _urlController.text = scanned;
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Webhook URL updated from QR')),
    );
  }

  Future<void> _setBiometric(bool value) async {
    final ok = await ref
        .read(authControllerProvider.notifier)
        .setBiometricEnabled(value);
    if (!mounted) return;
    if (!ok && value) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Biometric verification failed')),
      );
    }
  }

  Future<void> _requestBattery() async {
    final granted = await AppPermissions.requestBatteryExemption();
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          granted
              ? 'Battery optimization disabled for TextGenie'
              : 'Permission not granted',
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final settings = ref.watch(settingsControllerProvider);
    final auth = ref.watch(authControllerProvider);
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(title: const Text('Settings')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text('Webhook', style: theme.textTheme.titleMedium),
          const SizedBox(height: 8),
          Form(
            key: _formKey,
            child: TextFormField(
              controller: _urlController,
              keyboardType: TextInputType.url,
              autocorrect: false,
              decoration: const InputDecoration(
                labelText: 'Webhook URL',
                hintText: 'https://example.com/webhook/...',
              ),
              validator: validateWebhookUrl,
            ),
          ),
          const SizedBox(height: 12),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              OutlinedButton.icon(
                onPressed: _scanQr,
                icon: const Icon(Icons.qr_code_scanner),
                label: const Text('Scan QR'),
              ),
              FilledButton.icon(
                onPressed: _saveUrl,
                icon: const Icon(Icons.save),
                label: const Text('Save'),
              ),
            ],
          ),
          const Divider(height: 32),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text('Resolve contact names'),
            subtitle: const Text(
              'Attach your saved contact name for numeric senders (sent as a '
              'separate field). Requires Contacts permission.',
            ),
            value: settings.resolveContacts,
            onChanged: (value) => ref
                .read(settingsControllerProvider.notifier)
                .setResolveContacts(value),
          ),
          const Divider(height: 32),
          Text('Background delivery', style: theme.textTheme.titleMedium),
          const SizedBox(height: 8),
          Text(
            'Disable battery optimization so the app can keep sending queued '
            'messages when it is in the background.',
            style: theme.textTheme.bodyMedium?.copyWith(
              color: theme.colorScheme.outline,
            ),
          ),
          const SizedBox(height: 12),
          OutlinedButton.icon(
            onPressed: _requestBattery,
            icon: const Icon(Icons.battery_saver),
            label: const Text('Disable battery optimization'),
          ),
          const Divider(height: 32),
          Text('Security', style: theme.textTheme.titleMedium),
          const SizedBox(height: 8),
          ListTile(
            contentPadding: EdgeInsets.zero,
            leading: const Icon(Icons.pin_outlined),
            title: const Text('Change PIN'),
            subtitle: const Text('Update your 4-digit app PIN'),
            trailing: const Icon(Icons.chevron_right),
            onTap: () => Navigator.of(
              context,
            ).push(MaterialPageRoute(builder: (_) => const ChangePinScreen())),
          ),
          if (auth.biometricAvailable)
            SwitchListTile(
              contentPadding: EdgeInsets.zero,
              title: const Text('Unlock with biometrics'),
              subtitle: const Text(
                'Use your fingerprint or face to unlock the app.',
              ),
              value: auth.biometricEnabled,
              onChanged: _setBiometric,
            ),
          if (_version != null) ...[
            const Divider(height: 32),
            Center(
              child: Text(
                _version!,
                style: theme.textTheme.bodySmall?.copyWith(
                  color: theme.colorScheme.outline,
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }
}
