import 'package:flutter/material.dart';

import '../../theme/catppuccin_theme.dart';

/// Warning banner shown on Home when no webhook URL is configured.
class WebhookBanner extends StatelessWidget {
  const WebhookBanner({super.key});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final peach = AppTheme.flavor.peach;
    return Container(
      width: double.infinity,
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: peach.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: peach.withValues(alpha: 0.5)),
      ),
      child: Row(
        children: [
          Icon(Icons.warning_amber_rounded, color: peach),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              'No webhook URL configured. Go to Settings to add one before '
              'messages can be sent.',
              style: theme.textTheme.bodyMedium,
            ),
          ),
        ],
      ),
    );
  }
}
