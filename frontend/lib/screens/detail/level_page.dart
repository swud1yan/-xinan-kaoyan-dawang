part of xinan_dawang;

class LevelPage extends StatefulWidget {
  final Map user;
  const LevelPage({super.key, required this.user});
  @override State<LevelPage> createState() => _LevelPageState();
}

class _LevelPageState extends State<LevelPage> {
  Map? _user;
  bool _loading = true;

  static const _titles = [
    [1, '西南娃娃'],
    [6, '西南萌新'],
    [11, '西南学童'],
    [16, '西南少年'],
    [21, '西南学子'],
    [26, '西南书生'],
    [31, '西南秀才'],
    [36, '西南举人'],
    [41, '西南进士'],
    [46, '西南探花'],
    [51, '西南榜眼'],
    [56, '西南状元'],
    [61, '西南学霸'],
    [66, '西南卷王'],
    [71, '西南学神'],
    [76, '西南小王'],
    [81, '西南大王'],
    [86, '西南霸王'],
    [91, '西南圣王'],
    [96, '西南皇帝'],
  ];

  @override void initState() {
    super.initState();
    _user = widget.user;
    _load();
  }

  Future<void> _load() async {
    try {
      _user = await Api.getMe();
    } catch (_) {}
    if (mounted) setState(() => _loading = false);
  }

  @override Widget build(BuildContext context) {
    final xp = (_user?['xp'] ?? 0) as int;
    final level = (_user?['level'] ?? 1) as int;
    final info = _levelInfo(xp);
    final progress = info['progress'] as double;
    final title = info['title'] as String;
    return Scaffold(
      appBar: AppBar(title: const Text('等级详情')),
      body: _loading
          ? const Center(child: CircularProgressIndicator(color: kForest))
          : ListView(padding: const EdgeInsets.all(20), children: [
              Container(
                padding: const EdgeInsets.all(18),
                decoration: BoxDecoration(color: kPaper, borderRadius: BorderRadius.circular(16), boxShadow: shadowLevel(2)),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Row(children: [
                    Container(width: 54, height: 54, decoration: BoxDecoration(color: kForest, borderRadius: BorderRadius.circular(14)), child: Center(child: Text('$level', style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w900, color: Colors.white)))),
                    const SizedBox(width: 14),
                    Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Text(title, style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w900)),
                      const SizedBox(height: 4),
                      Text('$xp 经验 · 距下一级 ${info['xpToNext']} XP', style: const TextStyle(color: kClay)),
                    ])),
                  ]),
                  const SizedBox(height: 18),
                  ClipRRect(borderRadius: BorderRadius.circular(999), child: LinearProgressIndicator(value: progress.clamp(0, 1), minHeight: 10, backgroundColor: kMist, color: kForest)),
                ]),
              ),
              const SizedBox(height: 18),
              const Text('经验获取', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w800)),
              const SizedBox(height: 8),
              _rule(Icons.event_available_outlined, '每日签到', '10-50 XP，每天一次'),
              _rule(Icons.edit_note_outlined, '发布帖子', '+20 XP，每天最多5次'),
              _rule(Icons.mode_comment_outlined, '评论交流', '+5 XP，每天最多20次'),
              _rule(Icons.thumb_up_alt_outlined, '点赞互动', '点赞他人+2，被点赞+3'),
              const SizedBox(height: 18),
              const Text('称号路线', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w800)),
              const SizedBox(height: 8),
              for (final row in _titles)
                _TitleRow(level: row[0] as int, title: row[1] as String, current: level >= (row[0] as int) && level < ((row[0] as int) + 5)),
            ]),
    );
  }

  Widget _rule(IconData icon, String title, String text) => Container(
    margin: const EdgeInsets.only(bottom: 8),
    padding: const EdgeInsets.all(12),
    decoration: BoxDecoration(color: kPaper, borderRadius: BorderRadius.circular(12), border: Border.all(color: kMist)),
    child: Row(children: [Icon(icon, color: kForest), const SizedBox(width: 12), Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text(title, style: const TextStyle(fontWeight: FontWeight.w700)), const SizedBox(height: 2), Text(text, style: const TextStyle(color: kClay, fontSize: 13))]))]),
  );

  Map<String, Object> _levelInfo(int xp) {
    var level = 1;
    while (level < 100 && xp >= _totalXpForLevel(level + 1)) {
      level++;
    }
    final current = _totalXpForLevel(level);
    final next = _totalXpForLevel(level + 1);
    var title = '西南娃娃';
    for (final row in _titles.reversed) {
      if (level >= (row[0] as int)) {
        title = row[1] as String;
        break;
      }
    }
    return {'level': level, 'title': title, 'progress': (xp - current) / math.max(1, next - current), 'xpToNext': math.max(0, next - xp)};
  }

  int _xpForLevel(int level) => (100 * math.pow(1.15, level - 1)).round();
  int _totalXpForLevel(int level) {
    var total = 0;
    for (var i = 1; i < level; i++) {
      total += _xpForLevel(i);
    }
    return total;
  }
}

class _TitleRow extends StatelessWidget {
  final int level;
  final String title;
  final bool current;
  const _TitleRow({required this.level, required this.title, required this.current});
  @override Widget build(BuildContext context) => Container(
    margin: const EdgeInsets.only(bottom: 8),
    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
    decoration: BoxDecoration(color: current ? kForestSoft : kPaper, borderRadius: BorderRadius.circular(12), border: Border.all(color: current ? kForest : kMist)),
    child: Row(children: [
      SizedBox(width: 52, child: Text('Lv.$level', style: TextStyle(fontWeight: FontWeight.w800, color: current ? kForest : kClay))),
      Expanded(child: Text(title, style: TextStyle(fontWeight: current ? FontWeight.w800 : FontWeight.w500))),
      if (current) const Icon(Icons.check_circle, color: kForest, size: 18),
    ]),
  );
}
