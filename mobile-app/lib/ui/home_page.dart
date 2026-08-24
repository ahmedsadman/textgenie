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
    final failedCount = ref.watch(failedCountProvider).value ?? 0;
    final canRetryFailed = failedCount > 0 && settings.hasWebhookUrl;
    final hasQueued = queued.value?.isNotEmpty ?? false;
    final canSendQueued = hasQueued && settings.hasWebhookUrl;

    return Scaffold(
      appBar: AppBar(title: const Text('TextGenie')),
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
              action: canSendQueued
                  ? IconButton(
                      tooltip: 'Send queued now',
                      icon: const Icon(Icons.sync),
                      onPressed: () => ref.read(flushServiceProvider).flush(),
                    )
                  : null,
            ),
            _Section(
              title: 'History',
              async: history,
              emptyMessage: 'No messages sent yet.',
              showCount: false,
              footer: 'Showing last $kHistoryLimit records',
              action: canRetryFailed
                  ? IconButton(
                      tooltip: 'Retry failed',
                      icon: const Icon(Icons.refresh),
                      onPressed: () async {
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(
                            content: Text('Retrying failed messages'),
                          ),
                        );
                        await ref.read(appServicesProvider).requeueFailed();
                        ref.invalidate(historyProvider);
                        ref.invalidate(failedCountProvider);
                      },
                    )
                  : null,
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
    this.action,
  });

  final String title;
  final AsyncValue<List<SmsRecord>> async;
  final String emptyMessage;
  final bool showCount;
  final String? footer;
  final Widget? action;

  @override
  Widget build(BuildContext context) {
    final records = async.value ?? const [];
    final theme = Theme.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        SectionHeader(
          title,
          count: showCount ? records.length : null,
          action: action,
        ),
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
