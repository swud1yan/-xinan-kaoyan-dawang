part of xinan_dawang;

class UserProfilePage extends StatefulWidget {
  final String userId;
  const UserProfilePage({super.key, required this.userId});
  @override State<UserProfilePage> createState() => _UserProfilePageState();
}

class _UserProfilePageState extends State<UserProfilePage> {
  Map? _profile; bool _loading = true;

  @override void initState() { super.initState(); _load(); }

  Future<void> _load() async {
    try { final d = await Api._get('/auth/user/${widget.userId}/profile'); _profile = d as Map; } catch (_) {}
    if (mounted) setState(() => _loading = false);
  }

  @override Widget build(BuildContext c) => Scaffold(
    appBar: AppBar(title: Text(_profile?['nickname']?.toString() ?? '用户主页')),
    body: _loading ? const Center(child: CircularProgressIndicator(color: kForest))
      : _profile == null ? const EmptyState(icon: Icons.person_off, title: '用户不存在', subtitle: '')
      : SingleChildScrollView(padding: const EdgeInsets.all(20), child: Column(children: [
        CircleAvatar(radius: 40, backgroundColor: kParchment,
          child: Text((_profile!['nickname']?.toString() ?? '?')[0], style: const TextStyle(fontSize: 32, fontWeight: FontWeight.w800, color: kForest))),
        const SizedBox(height: 12),
        Text(_profile!['nickname']?.toString() ?? '', style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w700)),
        const SizedBox(height: 4),
        Row(mainAxisAlignment: MainAxisAlignment.center, children: [
          if (_profile!['isWhitelist'] == true) _pill('管理员', kBrass),
          if (_profile!['isWhitelist'] == true) const SizedBox(width: 8),
          _pill('Lv.${_profile!['level']}', kForest),
          const SizedBox(width: 8),
          _pill(vipName(_profile!['vipLevel'] ?? 0), kBrass),
        ]),
        const SizedBox(height: 16),
        _row('大王号', _profile!['dawangId']),
        if (_profile!['targetSchool'] != null) _row('目标院校', _profile!['targetSchool']),
        if (_profile!['major'] != null) _row('目标专业', _profile!['major']),
        if (_profile!['undergradSchool'] != null) _row('本科院校', _profile!['undergradSchool']),
        _row('番茄数', '${_profile!['pomodoroCount'] ?? 0}'),
        _row('连续签到', '${_profile!['signInStreak'] ?? 0}天'),
        const SizedBox(height: 20),
        const Text('最近帖子', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700)),
        const SizedBox(height: 8),
        ...(_profile!['posts'] as List? ?? []).map((p) => Container(
          margin: const EdgeInsets.only(bottom: 8), padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(color: kPaper, borderRadius: BorderRadius.circular(10), boxShadow: shadowLevel(1)),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(p['content']?.toString() ?? '', style: const TextStyle(height: 1.5)),
            const SizedBox(height: 6),
            Text('👍 ${p['likesCount']} · ${(p['createdAt']?.toString() ?? '').substring(0, 10)}', style: const TextStyle(fontSize: 11, color: kClay)),
          ]),
        )),
      ])),
  );

  Widget _row(String label, String? value) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 4),
    child: Row(children: [Text('$label: ', style: const TextStyle(color: kClay)), Text(value ?? '-')]),
  );
  Widget _pill(String text, Color color) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
    decoration: BoxDecoration(color: color.withAlpha(22), borderRadius: BorderRadius.circular(20)),
    child: Text(text, style: TextStyle(fontSize: 12, color: color, fontWeight: FontWeight.w700)),
  );
}
