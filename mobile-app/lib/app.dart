import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'services/permissions.dart';
import 'state/providers.dart';
import 'theme/catppuccin_theme.dart';
import 'ui/home_page.dart';
import 'ui/settings_page.dart';

class TextGenieApp extends StatelessWidget {
  const TextGenieApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'TextGenie',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.theme,
      home: const _HomeShell(),
    );
  }
}

/// Persistent bottom-nav shell. Also requests permissions, starts the SMS
/// listener, and flushes the queue when the app returns to the foreground.
class _HomeShell extends ConsumerStatefulWidget {
  const _HomeShell();

  @override
  ConsumerState<_HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends ConsumerState<_HomeShell>
    with WidgetsBindingObserver {
  int _index = 0;

  static const _pages = [HomePage(), SettingsPage()];

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    WidgetsBinding.instance.addPostFrameCallback((_) => _bootstrap());
  }

  Future<void> _bootstrap() async {
    await AppPermissions.requestAll();
    ref.read(smsListenerProvider).start();
    await ref.read(flushServiceProvider).flush();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      ref.read(flushServiceProvider).flush();
    }
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: IndexedStack(index: _index, children: _pages),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: (i) => setState(() => _index = i),
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.home_outlined),
            selectedIcon: Icon(Icons.home),
            label: 'Home',
          ),
          NavigationDestination(
            icon: Icon(Icons.settings_outlined),
            selectedIcon: Icon(Icons.settings),
            label: 'Settings',
          ),
        ],
      ),
    );
  }
}
