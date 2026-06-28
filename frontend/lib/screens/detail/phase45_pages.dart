part of xinan_dawang;

Widget _pageLoading() => const Center(child: CircularProgressIndicator(color: kForest));

void _toast(BuildContext context, Object msg) {
  ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(msg.toString())));
}

class AchievementsPage extends StatefulWidget {
  const AchievementsPage({super.key});
  @override State<AchievementsPage> createState() => _AchievementsPageState();
}

class _AchievementsPageState extends State<AchievementsPage> {
  Map? _data;
  bool _loading = true;
  @override void initState() { super.initState(); _load(); }
  Future<void> _load() async { try { _data = await Api.getAchievements(); } catch (e) { if (mounted) _toast(context, e); } if (mounted) setState(() => _loading = false); }
  @override Widget build(BuildContext context) {
    final items = (_data?['items'] as List?) ?? [];
    return Scaffold(appBar: AppBar(title: const Text('成就徽章')), body: _loading ? _pageLoading() : RefreshIndicator(
      onRefresh: _load,
      child: ListView(padding: const EdgeInsets.all(20), children: [
        Text('已解锁 ${_data?['unlockedCount'] ?? 0}/${_data?['totalCount'] ?? items.length}', style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w900, color: kForest)),
        const SizedBox(height: 14),
        GridView.builder(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          itemCount: items.length,
          gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(crossAxisCount: 2, mainAxisSpacing: 10, crossAxisSpacing: 10, childAspectRatio: 1.05),
          itemBuilder: (_, i) {
            final a = items[i] as Map;
            final ok = a['isUnlocked'] == true;
            return Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(color: ok ? kPaper : kParchment, borderRadius: BorderRadius.circular(12), border: Border.all(color: ok ? kBrassSoft : kMist), boxShadow: ok ? shadowLevel(1) : null),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(a['icon']?.toString() ?? '？', style: TextStyle(fontSize: 28, color: ok ? null : kClay)),
                const Spacer(),
                Text(a['name']?.toString() ?? '', maxLines: 1, overflow: TextOverflow.ellipsis, style: TextStyle(fontWeight: FontWeight.w900, color: ok ? kInk : kClay)),
                const SizedBox(height: 4),
                Text(a['description']?.toString() ?? '', maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(color: kClay, fontSize: 12)),
                const SizedBox(height: 8),
                LinearProgressIndicator(value: (a['progress'] as num? ?? 0).toDouble(), minHeight: 6, backgroundColor: kMist, color: ok ? kBrass : kForest),
              ]),
            );
          },
        ),
      ]),
    ));
  }
}

class LeaderboardPage extends StatelessWidget {
  const LeaderboardPage({super.key});
  @override Widget build(BuildContext context) => DefaultTabController(
    length: 3,
    child: Scaffold(
      appBar: AppBar(title: const Text('西南卷王榜'), bottom: const TabBar(tabs: [Tab(text: '周番茄'), Tab(text: '总经验'), Tab(text: '签到王')])),
      body: const TabBarView(children: [
        _LeaderboardList(type: 'weekly-pomodoro'),
        _LeaderboardList(type: 'total-xp'),
        _LeaderboardList(type: 'streak'),
      ]),
    ),
  );
}

class _LeaderboardList extends StatefulWidget {
  final String type;
  const _LeaderboardList({required this.type});
  @override State<_LeaderboardList> createState() => _LeaderboardListState();
}

class _LeaderboardListState extends State<_LeaderboardList> {
  Map? _data;
  @override void initState() { super.initState(); _load(); }
  Future<void> _load() async { try { _data = await Api.getLeaderboard(widget.type); } catch (e) { if (mounted) _toast(context, e); } if (mounted) setState(() {}); }
  @override Widget build(BuildContext context) {
    if (_data == null) return _pageLoading();
    final items = (_data!['items'] as List?) ?? [];
    final self = _data!['self'] as Map?;
    return RefreshIndicator(onRefresh: _load, child: ListView(padding: const EdgeInsets.all(16), children: [
      for (final item in items) _rankTile(item as Map),
      if (items.isEmpty) const EmptyState(icon: Icons.emoji_events_outlined, title: '暂无排行', subtitle: '完成学习任务后会出现在这里'),
      if (self != null && self['rank'] != null && !items.any((e) => (e as Map)['isSelf'] == true)) ...[
        const Divider(height: 28),
        const Text('我的位置', style: TextStyle(fontWeight: FontWeight.w900)),
        _rankTile(self),
      ],
    ]));
  }
  Widget _rankTile(Map item) => Container(
    margin: const EdgeInsets.only(bottom: 10),
    padding: const EdgeInsets.all(14),
    decoration: BoxDecoration(color: item['isSelf'] == true ? kParchment : kPaper, borderRadius: BorderRadius.circular(12), border: Border.all(color: item['rank'] == 1 ? kBrass : kMist)),
    child: Row(children: [
      SizedBox(width: 42, child: Text('#${item['rank']}', style: const TextStyle(fontWeight: FontWeight.w900, color: kForest))),
      Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(item['nickname']?.toString() ?? '', style: const TextStyle(fontWeight: FontWeight.w800)),
        Text('Lv.${item['level'] ?? 1} · ${item['dawangId'] ?? ''}', style: const TextStyle(color: kClay, fontSize: 12)),
      ])),
      Text('${item['value'] ?? 0}${item['label'] ?? ''}', style: const TextStyle(fontWeight: FontWeight.w900, color: kBrass)),
    ]),
  );
}

class DiaryPage extends StatefulWidget {
  const DiaryPage({super.key});
  @override State<DiaryPage> createState() => _DiaryPageState();
}

class _DiaryPageState extends State<DiaryPage> {
  final _content = TextEditingController();
  String _mood = 'neutral';
  bool _public = false, _loading = true;
  List _items = [];
  @override void initState() { super.initState(); _load(); }
  Future<void> _load() async { try { final r = await Api.getDiaryList(); _items = (r['items'] as List?) ?? []; } catch (e) { if (mounted) _toast(context, e); } if (mounted) setState(() => _loading = false); }
  Future<void> _save() async {
    try {
      await Api.saveDiary({'date': DateTime.now().toIso8601String().substring(0, 10), 'content': _content.text, 'mood': _mood, 'is_public': _public});
      _content.clear();
      await _load();
      if (mounted) _toast(context, '日记已保存');
    } catch (e) { if (mounted) _toast(context, e); }
  }
  @override Widget build(BuildContext context) => Scaffold(appBar: AppBar(title: const Text('考研日记')), body: _loading ? _pageLoading() : ListView(padding: const EdgeInsets.all(20), children: [
    TextField(controller: _content, maxLines: 5, maxLength: 600, decoration: const InputDecoration(labelText: '今天完成了什么', alignLabelWithHint: true)),
    const SizedBox(height: 8),
    Wrap(spacing: 8, children: [
      for (final m in const {'happy':'开心','anxious':'焦虑','tired':'疲惫','motivated':'有动力','neutral':'平静'}.entries)
        ChoiceChip(label: Text(m.value), selected: _mood == m.key, onSelected: (_) => setState(() => _mood = m.key)),
    ]),
    SwitchListTile.adaptive(contentPadding: EdgeInsets.zero, value: _public, title: const Text('公开到研友圈'), onChanged: (v) => setState(() => _public = v)),
    FilledButton.icon(onPressed: _save, icon: const Icon(Icons.save_outlined), label: const Text('保存日记'), style: FilledButton.styleFrom(backgroundColor: kForest)),
    const Divider(height: 34),
    for (final item in _items) _diaryTile(item as Map),
    if (_items.isEmpty) const EmptyState(icon: Icons.edit_note_outlined, title: '还没有日记', subtitle: '今天先写一句也算开始'),
  ]));
  Widget _diaryTile(Map item) => Container(
    margin: const EdgeInsets.only(bottom: 10),
    padding: const EdgeInsets.all(14),
    decoration: BoxDecoration(color: kPaper, borderRadius: BorderRadius.circular(12), boxShadow: shadowLevel(1)),
    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Text('${item['date'] ?? ''} · ${item['mood'] ?? ''}', style: const TextStyle(fontWeight: FontWeight.w900, color: kForest)),
      const SizedBox(height: 6),
      Text(item['content']?.toString() ?? '', style: const TextStyle(height: 1.5)),
      if ((item['aiReply'] ?? '').toString().isNotEmpty) Padding(padding: const EdgeInsets.only(top: 8), child: Text('AI：${item['aiReply']}', style: const TextStyle(color: kClay, fontSize: 12))),
    ]),
  );
  @override void dispose() { _content.dispose(); super.dispose(); }
}

class MatchPage extends StatefulWidget {
  const MatchPage({super.key});
  @override State<MatchPage> createState() => _MatchPageState();
}

class _MatchPageState extends State<MatchPage> {
  List _items = []; bool _loading = true;
  @override void initState() { super.initState(); _load(); }
  Future<void> _load() async { try { final r = await Api.getMatchRecommendations(); _items = (r['items'] as List?) ?? []; } catch (e) { if (mounted) _toast(context, e); } if (mounted) setState(() => _loading = false); }
  Future<void> _addFriend(Map item) async {
    try {
      await Api.sendFriendRequest(item['dawangId']?.toString() ?? '');
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('已向 ${item['nickname']} 发送好友申请')));
    } catch (e) { if (mounted) _toast(context, e); }
  }
  @override Widget build(BuildContext context) => Scaffold(appBar: AppBar(title: const Text('研友匹配')), body: RefreshIndicator(onRefresh: _load, child: _loading ? const Center(child: CircularProgressIndicator(color: kForest)) : ListView(padding: const EdgeInsets.all(20), children: [
    for (final item in _items) Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(padding: const EdgeInsets.all(14), child: Row(children: [
        GestureDetector(
          onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => UserProfilePage(userId: item['userId']?.toString() ?? ''))),
          child: CircleAvatar(radius: 24, backgroundColor: kParchment, child: Text((item['nickname']?.toString() ?? '?')[0], style: const TextStyle(fontWeight: FontWeight.w700, color: kForest))),
        ),
        const SizedBox(width: 12),
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(item['nickname']?.toString() ?? '', style: const TextStyle(fontWeight: FontWeight.w700)),
          Text('${item['targetSchool'] ?? '目标待定'} · Lv.${item['level'] ?? 1}', style: const TextStyle(fontSize: 12, color: kClay)),
          if (item['matchSource'] != null) Text(item['matchSource']?.toString() ?? '', style: const TextStyle(fontSize: 11, color: kBrass)),
        ])),
        OutlinedButton(onPressed: () => _addFriend(item), style: OutlinedButton.styleFrom(foregroundColor: kForest, padding: const EdgeInsets.symmetric(horizontal: 12)), child: const Text('加好友', style: TextStyle(fontSize: 12))),
      ])),
    ),
    if (_items.isEmpty && !_loading) const EmptyState(icon: Icons.groups_outlined, title: '暂未匹配到研友', subtitle: '完善目标院校和专业后再试试'),
  ])));
}

class FortunePage extends StatefulWidget {
  const FortunePage({super.key});
  @override State<FortunePage> createState() => _FortunePageState();
}

class _FortunePageState extends State<FortunePage> {
  Map? _fortune, _stats;
  @override void initState() { super.initState(); _load(); }
  Future<void> _load() async { try { _fortune = await Api.getTodayFortune(); _stats = await Api.getFortuneStats(); } catch (e) { if (mounted) _toast(context, e); } if (mounted) setState(() {}); }
  Future<void> _bless() async { try { final r = await Api.blessFortune(); _fortune = r['fortune'] as Map?; if (mounted) _toast(context, r['message'] ?? '好运已加成'); } catch (e) { if (mounted) _toast(context, e); } if (mounted) setState(() {}); }
  @override Widget build(BuildContext context) => Scaffold(appBar: AppBar(title: const Text('锦鲤运势')), body: _fortune == null ? _pageLoading() : ListView(padding: const EdgeInsets.all(24), children: [
    Container(padding: const EdgeInsets.all(22), decoration: BoxDecoration(color: kForest, borderRadius: BorderRadius.circular(18), boxShadow: shadowLevel(2)), child: Column(children: [
      Text(_fortune!['level']?.toString() ?? '', style: const TextStyle(color: Colors.white, fontSize: 32, fontWeight: FontWeight.w900)),
      const SizedBox(height: 8),
      Text('${_fortune!['score']}分 · 幸运色 ${_fortune!['color']} · 幸运数 ${_fortune!['number']}', style: const TextStyle(color: Colors.white70)),
      const Divider(color: Colors.white24, height: 28),
      Text('宜：${_fortune!['good']}    忌：${_fortune!['bad']}', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w700)),
      const SizedBox(height: 14),
      Text(_fortune!['quote']?.toString() ?? '', textAlign: TextAlign.center, style: const TextStyle(color: Colors.white70, height: 1.5)),
    ])),
    const SizedBox(height: 16),
    FilledButton.icon(onPressed: _bless, icon: const Icon(Icons.favorite_border), label: const Text('给今天加好运'), style: FilledButton.styleFrom(backgroundColor: kBrass)),
    const SizedBox(height: 12),
    Text('已抽取 ${_stats?['days'] ?? 0} 天，平均 ${_stats?['avgScore'] ?? 0} 分', textAlign: TextAlign.center, style: const TextStyle(color: kClay)),
  ]));
}

class MockExamPage extends StatefulWidget {
  const MockExamPage({super.key});
  @override State<MockExamPage> createState() => _MockExamPageState();
}

class _MockExamPageState extends State<MockExamPage> {
  List _items = [];
  bool _loading = true;
  @override void initState() { super.initState(); _load(); }
  Future<void> _load() async { try { final r = await Api.getMockExams(); _items = (r['items'] as List?) ?? []; } catch (e) { if (mounted) _toast(context, e); } if (mounted) setState(() => _loading = false); }
  Future<void> _start(Map exam) async {
    try {
      final r = await Api.startMockExam(exam['id']);
      if (!mounted) return;
      Navigator.of(context).push(MaterialPageRoute(builder: (_) => MockExamAttemptPage(data: r)));
    } catch (e) { if (mounted) _toast(context, e); }
  }
  @override Widget build(BuildContext context) => Scaffold(appBar: AppBar(title: const Text('模拟考试')), body: _loading ? _pageLoading() : ListView(padding: const EdgeInsets.all(20), children: [
    for (final exam in _items) Container(margin: const EdgeInsets.only(bottom: 12), decoration: BoxDecoration(color: kPaper, borderRadius: BorderRadius.circular(12), boxShadow: shadowLevel(1)), child: ListTile(
      title: Text(exam['title']?.toString() ?? '', style: const TextStyle(fontWeight: FontWeight.w900)),
      subtitle: Text('${exam['questionCount']}题 · ${exam['timeLimitMinutes']}分钟 · 满分${exam['totalScore']}'),
      trailing: FilledButton(onPressed: () => _start(exam as Map), style: FilledButton.styleFrom(backgroundColor: kForest), child: const Text('开始')),
    )),
    if (_items.isEmpty) const EmptyState(icon: Icons.assignment_outlined, title: '暂无模拟卷', subtitle: '稍后再来看看'),
  ]));
}

class MockExamAttemptPage extends StatefulWidget {
  final Map data;
  const MockExamAttemptPage({super.key, required this.data});
  @override State<MockExamAttemptPage> createState() => _MockExamAttemptPageState();
}

class _MockExamAttemptPageState extends State<MockExamAttemptPage> {
  late Map _attempt;
  late Map _exam;
  final Map<String, TextEditingController> _controllers = {};
  List get _questions => ((_exam['sections'] as List?) ?? []).expand((s) => ((s as Map)['questions'] as List?) ?? const []).toList();
  @override void initState() { super.initState(); _attempt = widget.data['attempt'] as Map; _exam = widget.data['exam'] as Map; }
  Future<void> _answer(String qid, String value) async { await Api.answerMockExam(_attempt['attemptId'], qid, value); }
  Future<void> _submit() async {
    try {
      final r = await Api.submitMockExam(_attempt['attemptId']);
      if (!mounted) return;
      showDialog(context: context, builder: (_) => AlertDialog(title: const Text('考试成绩'), content: Text('${(r['result'] as Map)['totalScore']}/${(r['result'] as Map)['maxScore']}\n${(r['result'] as Map)['aiAnalysis'] ?? ''}'), actions: [TextButton(onPressed: () { Navigator.pop(context); Navigator.pop(context); }, child: const Text('完成'))]));
    } catch (e) { if (mounted) _toast(context, e); }
  }
  @override Widget build(BuildContext context) => Scaffold(appBar: AppBar(title: Text(_exam['title']?.toString() ?? '模拟考试')), body: ListView(padding: const EdgeInsets.all(20), children: [
    for (final raw in _questions) _questionCard(raw as Map),
    const SizedBox(height: 12),
    FilledButton.icon(onPressed: _submit, icon: const Icon(Icons.assignment_turned_in_outlined), label: const Text('交卷'), style: FilledButton.styleFrom(backgroundColor: kForest, padding: const EdgeInsets.symmetric(vertical: 14))),
  ]));
  Widget _questionCard(Map q) {
    final id = q['id'].toString();
    final options = (q['options'] as List?) ?? [];
    if (q['type'] == 'essay') {
      final c = _controllers.putIfAbsent(id, () => TextEditingController());
      return Container(margin: const EdgeInsets.only(bottom: 12), padding: const EdgeInsets.all(14), decoration: BoxDecoration(color: kPaper, borderRadius: BorderRadius.circular(12), boxShadow: shadowLevel(1)), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(q['content']?.toString() ?? '', style: const TextStyle(fontWeight: FontWeight.w900)),
        const SizedBox(height: 10),
        TextField(controller: c, maxLines: 4, decoration: const InputDecoration(hintText: '输入作答'), onChanged: (v) => _answer(id, v)),
      ]));
    }
    return Container(margin: const EdgeInsets.only(bottom: 12), padding: const EdgeInsets.all(14), decoration: BoxDecoration(color: kPaper, borderRadius: BorderRadius.circular(12), boxShadow: shadowLevel(1)), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Text(q['content']?.toString() ?? '', style: const TextStyle(fontWeight: FontWeight.w900)),
      for (final opt in options) RadioListTile<String>(value: opt.toString().substring(0, 1), groupValue: null, title: Text(opt.toString()), onChanged: (v) { if (v != null) _answer(id, v); }),
    ]));
  }
  @override void dispose() { for (final c in _controllers.values) { c.dispose(); } super.dispose(); }
}

class InterviewPage extends StatefulWidget {
  final Map user;
  const InterviewPage({super.key, required this.user});
  @override State<InterviewPage> createState() => _InterviewPageState();
}

class _InterviewPageState extends State<InterviewPage> {
  final _answer = TextEditingController();
  Map? _session, _question, _current;
  List _allFeedback = [];
  Future<void> _start(String type) async {
    try {
      final r = await Api.startInterview({'type': type, 'targetSchool': widget.user['targetSchool'], 'targetMajor': widget.user['major']});
      _session = r['session'] as Map?;
      _question = r['question'] as Map?;
      _current = null; _allFeedback = []; _answer.clear();
      if (mounted) setState(() {});
    } catch (e) { if (mounted) _toast(context, e); }
  }
  Future<void> _submit() async {
    if (_session == null || _question == null) return;
    try {
      final r = await Api.answerInterview(_session!['sessionId'], {'question_id': _question!['id'], 'answer': _answer.text});
      _current = r['current'] as Map?;
      if (_current != null) _allFeedback.add(_current);
      _question = r['next'] as Map?;
      _session = r['session'] as Map?;
      _answer.clear();
      if (mounted) setState(() {});
    } catch (e) { if (mounted) _toast(context, e); }
  }
  @override Widget build(BuildContext context) => Scaffold(appBar: AppBar(title: const Text('AI复试面试')), body: ListView(padding: const EdgeInsets.all(20), children: [
    Wrap(spacing: 8, runSpacing: 8, children: [
      for (final item in const {'english':'英文自我介绍','professional':'专业面试','comprehensive':'综合面试','full':'全真模拟'}.entries)
        ActionChip(label: Text(item.value), onPressed: () => _start(item.key)),
    ]),
    const SizedBox(height: 16),
    if (_session == null) const EmptyState(icon: Icons.record_voice_over_outlined, title: '选择一种面试类型开始', subtitle: '文字版AI模拟问答，DeepSeek个性化出题和评分'),
    if (_session != null) ...[
      Text('进度 ${_session!['answeredCount']}/${_session!['questionCount']} · ${_session!['status']}', style: const TextStyle(color: kClay)),
      if (_session!['status'] == 'completed') ...[
        const SizedBox(height: 8),
        Text('综合评分: ${_session!['totalScore']}分', style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w900, color: kForest)),
      ]
    ],
    if (_question != null) ...[
      const SizedBox(height: 12),
      Container(padding: const EdgeInsets.all(16), decoration: BoxDecoration(color: kParchment, borderRadius: BorderRadius.circular(14)), child: Text(_question!['question']?.toString() ?? '', style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w900, height: 1.5))),
      const SizedBox(height: 12),
      TextField(controller: _answer, maxLines: 6, decoration: const InputDecoration(labelText: '你的回答', alignLabelWithHint: true)),
      const SizedBox(height: 10),
      FilledButton(onPressed: _submit, style: FilledButton.styleFrom(backgroundColor: kForest), child: const Text('提交回答')),
    ],
    if (_current != null) Container(margin: const EdgeInsets.only(top: 16), padding: const EdgeInsets.all(14), decoration: BoxDecoration(color: kPaper, borderRadius: BorderRadius.circular(12), boxShadow: shadowLevel(1)), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Text('内容:${_current!['scoreContent']} 表达:${_current!['scoreExpression']} 专业:${_current!['scoreConfidence']}', style: const TextStyle(fontWeight: FontWeight.w700, color: kForest)),
      const SizedBox(height: 4), Text('${_current!['feedback'] ?? ''}', style: const TextStyle(height: 1.5)),
      if ((_current!['suggestedAnswer'] ?? '').toString().isNotEmpty) ...[const SizedBox(height: 4), Text('💡 ${_current!['suggestedAnswer']}', style: const TextStyle(color: kBrass))],
    ])),
  ]));
  @override void dispose() { _answer.dispose(); super.dispose(); }
}

class TransferPage extends StatefulWidget {
  const TransferPage({super.key});
  @override State<TransferPage> createState() => _TransferPageState();
}

class _TransferPageState extends State<TransferPage> {
  final _kw = TextEditingController();
  List _items = [];
  @override void initState() { super.initState(); _load(); }
  Future<void> _load() async { try { final r = await Api.getTransferInfos(keyword: _kw.text); _items = (r['items'] as List?) ?? []; } catch (e) { if (mounted) _toast(context, e); } if (mounted) setState(() {}); }
  Future<void> _analysis(Map item) async { try { final r = await Api.getTransferAnalysis(item['id']); if (mounted) showDialog(context: context, builder: (_) => AlertDialog(title: Text(item['schoolName'] ?? ''), content: Text(r['analysis']?.toString() ?? ''), actions: [TextButton(onPressed: () => Navigator.pop(context), child: const Text('知道了'))])); } catch (e) { if (mounted) _toast(context, e); } }
  @override Widget build(BuildContext context) => Scaffold(appBar: AppBar(title: const Text('调剂监控')), body: ListView(padding: const EdgeInsets.all(20), children: [
    Row(children: [Expanded(child: TextField(controller: _kw, decoration: const InputDecoration(hintText: '搜索学校/专业'))), const SizedBox(width: 8), IconButton(onPressed: _load, icon: const Icon(Icons.search))]),
    const SizedBox(height: 12),
    for (final item in _items) Container(margin: const EdgeInsets.only(bottom: 10), decoration: BoxDecoration(color: kPaper, borderRadius: BorderRadius.circular(12), boxShadow: shadowLevel(1)), child: ListTile(
      title: Text('${item['schoolName']} · ${item['major']}', style: const TextStyle(fontWeight: FontWeight.w900)),
      subtitle: Text('最低分 ${item['minScore'] ?? '-'} · ${item['publishDate'] ?? ''}\n${item['requirement'] ?? ''}'),
      isThreeLine: true,
      trailing: TextButton(onPressed: () => _analysis(item as Map), child: const Text('AI分析')),
    )),
    if (_items.isEmpty) const EmptyState(icon: Icons.manage_search_outlined, title: '暂无调剂信息', subtitle: '换个关键词再试试'),
  ]));
  @override void dispose() { _kw.dispose(); super.dispose(); }
}

class StudyPlanPage extends StatefulWidget {
  const StudyPlanPage({super.key});
  @override State<StudyPlanPage> createState() => _StudyPlanPageState();
}

class _StudyPlanPageState extends State<StudyPlanPage> {
  Map? _plan;
  @override void initState() { super.initState(); _load(); }
  Future<void> _load() async { try { final r = await Api.getCurrentStudyPlan(); _plan = r['plan'] as Map?; } catch (e) { if (mounted) _toast(context, e); } if (mounted) setState(() {}); }
  Future<void> _generate() async { try { _plan = await Api.generateStudyPlan({'type': 'weekly', 'days': 7}); if (mounted) setState(() {}); } catch (e) { if (mounted) _toast(context, e); } }
  Future<void> _toggle(Map task, bool done) async { try { _plan = await Api.updateStudyTask(task['id'], done); if (mounted) setState(() {}); } catch (e) { if (mounted) _toast(context, e); } }
  @override Widget build(BuildContext context) {
    final content = (_plan?['content'] as Map?) ?? {};
    final tasks = (content['tasks'] as List?) ?? [];
    return Scaffold(appBar: AppBar(title: const Text('AI学习计划')), body: ListView(padding: const EdgeInsets.all(20), children: [
      FilledButton.icon(onPressed: _generate, icon: const Icon(Icons.auto_awesome), label: Text(_plan == null ? '生成本周计划' : '重新生成计划'), style: FilledButton.styleFrom(backgroundColor: kForest)),
      if (_plan == null) const EmptyState(icon: Icons.event_note_outlined, title: '还没有学习计划', subtitle: '生成后会按天拆成小任务'),
      if (_plan != null) ...[
        const SizedBox(height: 14),
        Text(content['summary']?.toString() ?? '', style: const TextStyle(color: kClay, height: 1.5)),
        const SizedBox(height: 10),
        LinearProgressIndicator(value: (_plan!['completionRate'] as num? ?? 0).toDouble(), minHeight: 8, backgroundColor: kMist, color: kForest),
        const SizedBox(height: 14),
        for (final task in tasks) CheckboxListTile(
          contentPadding: EdgeInsets.zero,
          value: (task as Map)['completed'] == true,
          title: Text(task['title']?.toString() ?? ''),
          subtitle: Text('${task['date']} · ${task['minutes']}分钟 · ${task['detail']}'),
          onChanged: (v) => _toggle(task, v == true),
        ),
      ],
    ]));
  }
}

class AboutUsPage extends StatefulWidget {
  final Map user;
  final VoidCallback? onChanged;
  const AboutUsPage({super.key, required this.user, this.onChanged});
  @override State<AboutUsPage> createState() => _AboutUsPageState();
}

class _AboutUsPageState extends State<AboutUsPage> {
  int _taps = 0;
  DateTime _lastTap = DateTime.now();
  bool _checking = false;

  void _tap() {
    final now = DateTime.now();
    // 2秒内未连点则重置计数
    if (now.difference(_lastTap).inSeconds > 2) {
      _taps = 0;
    }
    _lastTap = now;
    _taps++;
    if (_taps >= 5 && !_checking) {
      _taps = 0;
      _verifyAndEnter();
    }
  }

  Future<void> _verifyAndEnter() async {
    if (_checking) return;
    setState(() => _checking = true);
    try {
      // 向服务器验证白名单状态
      final me = await Api.getMe();
      final isWhitelist = me['isWhitelist'] == true;
      if (isWhitelist && mounted) {
        Navigator.of(context).push(MaterialPageRoute(builder: (_) => DebugUserEditPage(user: me, onChanged: widget.onChanged)));
      } else if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('仅白名单用户可访问测试修改界面')));
      }
    } catch (_) {
      // 网络错误时的后备：使用本地数据判断
      if (mounted && widget.user['isWhitelist'] == true) {
        Navigator.of(context).push(MaterialPageRoute(builder: (_) => DebugUserEditPage(user: widget.user, onChanged: widget.onChanged)));
      } else if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('验证失败，请检查网络')));
      }
    }
    if (mounted) setState(() => _checking = false);
  }
  @override Widget build(BuildContext context) => Scaffold(appBar: AppBar(title: const Text('关于我们')), body: GestureDetector(
    behavior: HitTestBehavior.opaque,
    onTap: _tap,
    child: const Center(child: Text('西南大王V0.2.1beta\nd1yan版权所有©', textAlign: TextAlign.center, style: TextStyle(fontSize: 18, height: 1.8, fontWeight: FontWeight.w700))),
  ));
}

class DebugUserEditPage extends StatefulWidget {
  final Map user;
  final VoidCallback? onChanged;
  const DebugUserEditPage({super.key, required this.user, this.onChanged});
  @override State<DebugUserEditPage> createState() => _DebugUserEditPageState();
}

class _DebugUserEditPageState extends State<DebugUserEditPage> {
  final _xp = TextEditingController(text: '0');
  final _monthly = TextEditingController(text: '0');
  final _purchased = TextEditingController(text: '0');
  int _vip = 0;
  bool _deep = false, _saving = false;
  @override void initState() { super.initState(); _vip = widget.user['vipLevel'] ?? 0; _deep = widget.user['deepThinkEnabled'] == true; }
  int _num(TextEditingController c) => int.tryParse(c.text.trim()) ?? 0;
  Future<void> _save() async {
    if (_saving) return;
    setState(() => _saving = true);
    try {
      await Api.debugSelfUpdate({'xp_delta': _num(_xp), 'monthly_coins_delta': _num(_monthly), 'purchased_coins_delta': _num(_purchased), 'vip_level': _vip, 'deep_think_enabled': _deep});
      widget.onChanged?.call();
      if (mounted) _toast(context, '测试数据已更新');
    } catch (e) { if (mounted) _toast(context, e); }
    if (mounted) setState(() => _saving = false);
  }
  @override Widget build(BuildContext context) => Scaffold(appBar: AppBar(title: const Text('测试数据修改')), body: ListView(padding: const EdgeInsets.all(20), children: [
    const Text('仅白名单用户可用', style: TextStyle(color: kClay)),
    const SizedBox(height: 16),
    DropdownButtonFormField<int>(value: _vip, decoration: const InputDecoration(labelText: 'VIP等级'), items: const [
      DropdownMenuItem(value: 0, child: Text('免费')),
      DropdownMenuItem(value: 1, child: Text('银卡')),
      DropdownMenuItem(value: 2, child: Text('金卡')),
      DropdownMenuItem(value: 3, child: Text('黑卡')),
      DropdownMenuItem(value: 17, child: Text('上岸')),
      DropdownMenuItem(value: 99, child: Text('研王爷')),
    ], onChanged: (v) => setState(() => _vip = v ?? 0)),
    const SizedBox(height: 12),
    TextField(controller: _xp, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: '经验增减，例如 100 或 -50')),
    const SizedBox(height: 12),
    TextField(controller: _monthly, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: '月度研AI币增减')),
    const SizedBox(height: 12),
    TextField(controller: _purchased, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: '永久研AI币增减')),
    SwitchListTile.adaptive(contentPadding: EdgeInsets.zero, value: _deep, title: const Text('开启深度思考'), onChanged: (v) => setState(() => _deep = v)),
    const SizedBox(height: 12),
    FilledButton.icon(onPressed: _saving ? null : _save, icon: const Icon(Icons.save_outlined), label: Text(_saving ? '保存中' : '保存修改'), style: FilledButton.styleFrom(backgroundColor: kForest)),
  ]));
  @override void dispose() { _xp.dispose(); _monthly.dispose(); _purchased.dispose(); super.dispose(); }
}
