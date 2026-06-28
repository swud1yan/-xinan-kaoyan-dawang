part of xinan_dawang;

// ======================== Notifications Page ========================
class NotificationsPage extends StatefulWidget {
  final VoidCallback? onCountChanged;
  const NotificationsPage({super.key, this.onCountChanged});
  @override State<NotificationsPage> createState() => _NotificationsPageState();
}

class _NotificationsPageState extends State<NotificationsPage> {
  List _items = []; int _unread = 0; bool _loading = true;

  @override void initState() { super.initState(); _load(); }

  Future<void> _load() async {
    try {
      final r = await Api.get('/notifications');
      _items = (r['notifications'] as List?) ?? [];
      _unread = (r['unread_count'] as int?) ?? 0;
      widget.onCountChanged?.call();
    } catch (_) {}
    if (mounted) setState(() => _loading = false);
  }

  Future<void> _markRead(String id) async {
    try { await Api.post('/notifications/$id/read', {}); _load(); } catch (_) {}
  }

  Future<void> _deleteItem(String id) async {
    try { await Api.del('/notifications/$id'); _load(); } catch (_) {}
  }

  Future<void> _markAllRead() async {
    try { await Api.post('/notifications/read-all', {}); _load(); } catch (_) {}
  }

  void _onTap(Map item) {
    _markRead(item['id'] ?? '');
    final data = item['data'] as Map?;
    if (item['type'] == 'friend_message' && data != null && data['friend_id'] != null) {
      // Navigate to chat - find friend in list (handled by FriendsTab)
      Navigator.of(context).pop();
      // Post a message to switch to friends tab
    } else {
      // Mark as read, show detail or pop
      showDialog(
        context: context,
        builder: (_) => AlertDialog(
          title: Text(item['title']?.toString() ?? ''),
          content: Text(item['body']?.toString() ?? ''),
          actions: [TextButton(onPressed: () => Navigator.pop(context), child: const Text('知道了'))],
        ),
      );
    }
  }

  @override Widget build(BuildContext c) => Scaffold(
    appBar: AppBar(
      title: Row(children: [
        const Text('消息通知'),
        if (_unread > 0) ...[const SizedBox(width: 8), Container(padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2), decoration: BoxDecoration(color: kRed, borderRadius: BorderRadius.circular(10)), child: Text('$_unread', style: const TextStyle(color: Colors.white, fontSize: 12)))]
      ]),
      actions: [
        if (_unread > 0) TextButton(onPressed: _markAllRead, child: const Text('全部已读')),
      ],
    ),
    body: _loading
      ? const Center(child: CircularProgressIndicator(color: kForest))
      : _items.isEmpty
        ? const EmptyState(icon: Icons.notifications_none, title: '暂无通知', subtitle: '好友消息和管理员通知会出现在这里')
        : ListView.builder(
            itemCount: _items.length,
            itemBuilder: (_, i) {
              final item = _items[i] as Map;
              final read = item['is_read'] == true;
              final type = item['type']?.toString() ?? '';
              final icon = type == 'friend_message' ? Icons.person_outline : Icons.campaign_outlined;
              return Dismissible(
                key: Key(item['id']?.toString() ?? '$i'),
                direction: DismissDirection.endToStart,
                background: Container(color: kRed, alignment: Alignment.centerRight, padding: const EdgeInsets.only(right: 20), child: const Icon(Icons.delete, color: Colors.white)),
                onDismissed: (_) => _deleteItem(item['id'] ?? ''),
                child: ListTile(
                  leading: Container(
                    width: 40, height: 40,
                    decoration: BoxDecoration(color: read ? kParchment : kForest.withAlpha(20), borderRadius: BorderRadius.circular(10)),
                    child: Icon(icon, color: read ? kClay : kForest, size: 20),
                  ),
                  title: Text(item['title']?.toString() ?? '', style: TextStyle(fontWeight: read ? FontWeight.w400 : FontWeight.w700)),
                  subtitle: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(item['body']?.toString() ?? '', maxLines: 1, overflow: TextOverflow.ellipsis),
                    const SizedBox(height: 2),
                    Text(_fmtTime(item['created_at']?.toString()), style: const TextStyle(fontSize: 11, color: kClay)),
                  ]),
                  trailing: read ? null : Container(width: 8, height: 8, decoration: const BoxDecoration(color: kRed, shape: BoxShape.circle)),
                  tileColor: read ? null : kPaper,
                  onTap: () => _onTap(item),
                ),
              );
            },
          ),
  );

  String _fmtTime(String? iso) {
    if (iso == null) return '';
    try {
      final dt = DateTime.parse(iso);
      final now = DateTime.now();
      final diff = now.difference(dt);
      if (diff.inMinutes < 1) return '刚刚';
      if (diff.inMinutes < 60) return '${diff.inMinutes}分钟前';
      if (diff.inHours < 24) return '${diff.inHours}小时前';
      if (diff.inDays < 7) return '${diff.inDays}天前';
      return '${dt.month}/${dt.day}';
    } catch (_) { return ''; }
  }
}
