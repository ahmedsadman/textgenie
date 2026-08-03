import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../services/permissions.dart';
import '../state/providers.dart';

/// Settings tab: webhook URL, contact-name toggle, battery-optimization prompt.
class SettingsPage extends ConsumerStatefulWidget {
  const SettingsPage({super.key});

  @override
  ConsumerState<SettingsPage> createState() => _SettingsPageState();
}

class _SettingsPageState extends ConsumerState<SettingsPage> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _urlController;

  @override
  void initState() {
    super.initState();
    _urlController = TextEditingController(
      text: ref.read(settingsControllerProvider).webhookUrl ?? '',
    );
  }

  @override
  void dispose() {
    _urlController.dispose();
    super.dispose();
  }

  static String? _validateUrl(String? value) {
    final text = value?.trim() ?? '';
    if (text.isEmpty) return 'Webhook URL is required';
    final uri = Uri.tryParse(text);
    if (uri == null || !uri.isAbsolute || !uri.hasScheme || uri.host.isEmpty) {
      return 'Enter a valid URL (including https://)';
    }
    if (uri.scheme != 'http' && uri.scheme != 'https') {
      return 'URL must start with http:// or https://';
    }
    return null;
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
              validator: _validateUrl,
            ),
          ),
          const SizedBox(height: 12),
          Align(
            alignment: Alignment.centerRight,
            child: FilledButton.icon(
              onPressed: _saveUrl,
              icon: const Icon(Icons.save),
              label: const Text('Save'),
            ),
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
        ],
      ),
    );
  }
}
