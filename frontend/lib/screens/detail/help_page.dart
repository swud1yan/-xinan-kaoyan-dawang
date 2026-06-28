part of xinan_dawang;

// ======================== AI Help Page ========================
class HelpPage extends StatefulWidget {
  const HelpPage({super.key});
  @override State<HelpPage> createState() => _HelpPageState();
}

class _HelpPageState extends State<HelpPage> {
  final _msgs = <_HelpMsg>[_HelpMsg(false, '你好！我是西南大王的智能客服助手。\n\n我可以帮你解答APP使用相关的问题，比如：\n• 功能介绍和使用方法\n• VIP和研AI币\n• 账号相关\n• 各种工具怎么用\n\n有什么可以帮你的？')];
  final _inp = TextEditingController();
  final _sc = ScrollController();
  bool _thinking = false;
  int _strikes = 0;
  bool _banned = false;
  String? _banRemaining;

  @override void initState() { super.initState(); _loadStatus(); }

  Future<void> _loadStatus() async {
    try {
      final r = await Api.get('/help/status');
      if (mounted) setState(() {
        _strikes = (r['strikes'] as int?) ?? 0;
        _banned = r['banned_remaining_minutes'] != null;
        if (_banned) _banRemaining = '${r['banned_remaining_minutes']} 分钟';
      });
    } catch (_) {}
  }

  Future<void> _send() async {
    final t = _inp.text.trim();
    if (t.isEmpty || _thinking || _banned) return;
    setState(() { _msgs.add(_HelpMsg(true, t)); _inp.clear(); _thinking = true; });
    _scroll();
    // Check for feedback trigger
    if (t.contains('我要反馈') || t.contains('反馈问题') || t.contains('提交反馈')) {
      setState(() { _msgs.add(_HelpMsg(false, '已为你打开反馈页面，请详细描述你的问题或建议。')); _thinking = false; });
      Navigator.of(context).push(MaterialPageRoute(builder: (_) => const FeedbackPage()));
      return;
    }
    try {
      final r = await Api.post('/help/ask', {'message': t});
      final reply = r['reply']?.toString() ?? '系统异常';
      final s = (r['strikes'] as int?) ?? 0;
      final b = r['banned'] == true;
      setState(() {
        _msgs.add(_HelpMsg(false, reply));
        _strikes = s;
        _banned = b;
        if (b) _banRemaining = '60 分钟';
      });
    } catch (e) {
      setState(() => _msgs.add(_HelpMsg(false, '⚠️ ${e.toString()}')));
    }
    setState(() => _thinking = false);
    _scroll();
  }

  void _scroll() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_sc.hasClients) _sc.animateTo(_sc.position.maxScrollExtent, duration: const Duration(milliseconds: 300), curve: Curves.easeOut);
    });
  }

  @override Widget build(BuildContext c) => Scaffold(
    appBar: AppBar(
      title: const Text('帮助与客服'),
      actions: [
        if (_strikes > 0)
          Padding(
            padding: const EdgeInsets.only(right: 12),
            child: Chip(
              label: Text(_banned ? '已禁用($_banRemaining)' : '警告 $_strikes/3', style: TextStyle(color: _banned ? Colors.white : kRed, fontSize: 11)),
              backgroundColor: _banned ? kRed : kRed.withAlpha(25),
            ),
          ),
      ],
    ),
    body: Column(children: [
      if (_banned)
        Container(
          width: double.infinity, padding: const EdgeInsets.all(12),
          color: kRed.withAlpha(25),
          child: Text('帮助功能已被暂时禁用，剩余 $_banRemaining。请等待解禁后再使用。', style: const TextStyle(color: kRed, fontSize: 13), textAlign: TextAlign.center),
        ),
      Expanded(
        child: ListView.builder(
          controller: _sc, padding: const EdgeInsets.all(16),
          itemCount: _msgs.length,
          itemBuilder: (_, i) => _bub(_msgs[i]),
        ),
      ),
      if (_thinking)
        const Padding(padding: EdgeInsets.only(bottom: 4), child: Text('客服思考中…', style: TextStyle(fontSize: 12, color: kClay))),
      Container(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 12),
        decoration: const BoxDecoration(color: kPaper, border: Border(top: BorderSide(color: kMist))),
        child: Row(children: [
          Expanded(
            child: TextField(
              controller: _inp,
              enabled: !_banned,
              decoration: InputDecoration(
                hintText: _banned ? '帮助已被禁用' : '描述你的问题…',
                contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
              ),
              onSubmitted: (_) => _send(),
            ),
          ),
          const SizedBox(width: 10),
          GestureDetector(
            onTap: (_thinking || _banned) ? null : _send,
            child: Container(
              width: 40, height: 40,
              decoration: BoxDecoration(color: (_thinking || _banned) ? kClay : kForest, borderRadius: BorderRadius.circular(10)),
              child: Icon(_thinking ? Icons.hourglass_empty : Icons.send_rounded, color: Colors.white, size: 18),
            ),
          ),
        ]),
      ),
    ]),
  );

  Widget _bub(_HelpMsg m) => Padding(
    padding: const EdgeInsets.only(bottom: 10),
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisAlignment: m.me ? MainAxisAlignment.end : MainAxisAlignment.start,
      children: [
        if (!m.me) Container(
          width: 30, height: 30,
          margin: const EdgeInsets.only(top: 2),
          decoration: BoxDecoration(color: kBrass, borderRadius: BorderRadius.circular(8)),
          child: const Icon(Icons.support_agent, color: Colors.white, size: 15),
        ),
        if (!m.me) const SizedBox(width: 10),
        Flexible(
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
            decoration: BoxDecoration(
              color: m.me ? kParchment : kPaper,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: kMist),
            ),
            child: Text(m.t, style: const TextStyle(fontSize: 14, height: 1.55)),
          ),
        ),
        if (m.me) const SizedBox(width: 10),
        if (m.me) Container(
          width: 30, height: 30,
          margin: const EdgeInsets.only(top: 2),
          decoration: BoxDecoration(color: kForest, borderRadius: BorderRadius.circular(8)),
          child: const Icon(Icons.person, color: Colors.white, size: 15),
        ),
      ],
    ),
  );

  @override void dispose() { _inp.dispose(); _sc.dispose(); super.dispose(); }
}

class _HelpMsg { final bool me; final String t; const _HelpMsg(this.me, this.t); }
