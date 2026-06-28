part of xinan_dawang;

// ======================== Main Shell ========================
class MainShell extends StatefulWidget {
  final Map user; final VoidCallback onLogout;
  const MainShell({super.key,required this.user,required this.onLogout});
  @override State<MainShell> createState() => _MainShellState();
}
class _MainShellState extends State<MainShell> {
  int _tab=0; int _unread=0;
  Timer? _pollTimer;

  @override void initState() {
    super.initState();
    _checkUnread();
    _pollTimer = Timer.periodic(const Duration(seconds: 15), (_) => _checkUnread());
  }

  Future<void> _checkUnread() async {
    try {
      final r = await Api.get('/notifications/unread-count');
      if (mounted) setState(() => _unread = (r['unread_count'] as int?) ?? 0);
    } catch (_) {}
  }

  @override void dispose() { _pollTimer?.cancel(); super.dispose(); }

  @override Widget build(BuildContext c){
    final pages=[SchoolTab(user:widget.user),CourseExamTab(user:widget.user),const ChatTab(),CircleTab(user:widget.user),FriendsTab(user:widget.user),MyTab(user:widget.user,onLogout:widget.onLogout)];
    return Scaffold(
      body: SafeArea(
        child: Stack(
          children: [
            IndexedStack(index:_tab,children:pages),
            // Notification bell - top right
            Positioned(
              top: 4, right: 12,
              child: GestureDetector(
                onTap: () async {
                  await Navigator.of(context).push(MaterialPageRoute(builder: (_) => NotificationsPage(onCountChanged: _checkUnread)));
                  _checkUnread();
                },
                child: Container(
                  width: 38, height: 38,
                  decoration: BoxDecoration(color: kPaper, borderRadius: BorderRadius.circular(19), boxShadow: [BoxShadow(color: kInk.withAlpha(15), blurRadius: 6)]),
                  child: Stack(children: [
                    const Center(child: Icon(Icons.notifications_outlined, color: kForest, size: 20)),
                    if (_unread > 0)
                      Positioned(top: 4, right: 4, child: Container(width: 16, height: 16, decoration: const BoxDecoration(color: kRed, shape: BoxShape.circle), child: Center(child: Text('${_unread > 99 ? '99+' : _unread}', style: const TextStyle(color: Colors.white, fontSize: 9, fontWeight: FontWeight.w700))))),
                  ]),
                ),
              ),
            ),
          ],
        ),
      ),
      bottomNavigationBar: BottomNav(currentIndex: _tab, onTap: (i) => setState(() => _tab = i)),
    );
  }
}


