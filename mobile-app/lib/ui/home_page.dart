import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/sms_repository.dart';
import '../models/sms_record.dart';
import '../state/providers.dart';
import 'widgets/section_header.dart';
import 'widgets/sms_tile.dart';
import 'widgets/webhook_banner.dart';

/// Home tab: the webhook banner (when unset), Queued and History sections.
class HomePage extends ConsumerWidget {
  const HomePage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final settings = ref.watch(settingsControllerProvider);
    final queued = ref.watch(queuedProvider);
    final history = ref.watch(historyProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('TextGenie'),
        actions: [
          IconButton(
            tooltip: 'Send queued now',
            icon: const Icon(Icons.sync),
            onPressed: settings.hasWebhookUrl
                ? () => ref.read(flushServiceProvider).flush()
                : null,
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () async {
          ref.invalidate(queuedProvider);
          ref.invalidate(historyProvider);
          await ref.read(flushServiceProvider).flush();
        },
        child: ListView(
          padding: const EdgeInsets.all(12),
          children: [
            if (!settings.hasWebhookUrl) const WebhookBanner(),
            _Section(
              title: 'Queued',
              async: queued,
              emptyMessage: 'Nothing queued.',
              showCount: true,
            ),
            _Section(
              title: 'History',
              async: history,
              emptyMessage: 'No messages sent yet.',
              showCount: false,
              footer: 'Showing last $kHistoryLimit records',
            ),
          ],
        ),
      ),
    );
  }
}

class _Section extends StatelessWidget {
  const _Section({
    required this.title,
    required this.async,
    required this.emptyMessage,
    required this.showCount,
    this.footer,
  });

  final String title;
  final AsyncValue<List<SmsRecord>> async;
  final String emptyMessage;
  final bool showCount;
  final String? footer;

  @override
  Widget build(BuildContext context) {
    final records = async.value ?? const [];
    final theme = Theme.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        SectionHeader(title, count: showCount ? records.length : null),
        if (async.isLoading && async.value == null)
          const Padding(
            padding: EdgeInsets.all(16),
            child: Center(child: CircularProgressIndicator()),
          )
        else if (records.isEmpty)
          EmptyHint(emptyMessage)
        else ...[
          ...records.map((r) => SmsTile(r)),
          if (footer != null)
            Padding(
              padding: const EdgeInsets.only(top: 8, bottom: 4),
              child: Text(
                footer!,
                textAlign: TextAlign.center,
                style: theme.textTheme.bodySmall?.copyWith(
                  color: theme.colorScheme.outline,
                ),
              ),
            ),
        ],
      ],
    );
  }
}
