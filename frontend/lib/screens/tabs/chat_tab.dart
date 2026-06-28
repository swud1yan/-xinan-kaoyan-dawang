part of xinan_dawang;

// ======================== Tab 3: AI Chat ========================
class _Msg {
  final bool me;
  final String t;
  final int? coinsUsed;
  const _Msg(this.me, this.t, {this.coinsUsed});
}

class ChatTab extends StatefulWidget {
  const ChatTab({super.key});
  @override State<ChatTab> createState() => _ChatTabState();
}

class _ChatTabState extends State<ChatTab> {
  final _msgs = const [
    _Msg(false, '你好！我是西南大王的AI考研助手。\n\n我可以帮你：\n• 分析院校数据\n• 解答专业课疑难\n• 制定复习计划\n• 陪你聊聊备考心态\n\n有什么想聊的？'),
  ].toList();
  final _inp = TextEditingController(), _sc = ScrollController();
  Map? _coins;
  bool _thinking = false, _deepThink = false;

  @override void initState() {
    super.initState();
    _loadCoins();
  }

  Future<void> _loadCoins() async {
    try {
      _coins = await Api.getCoinsStatus();
      if (mounted) setState(() {});
    } catch (_) {}
  }

  void _send() async {
    final t = _inp.text.trim();
    if (t.isEmpty || _thinking) return;
    setState(() {
      _msgs.add(_Msg(true, t));
      _inp.clear();
      _thinking = true;
    });
    _scroll();
    try {
      final r = await Api.chatSend(t, deepThink: _deepThink);
      setState(() {
        _msgs.add(_Msg(false, (r['reply'] ?? '').toString(), coinsUsed: r['coins_used'] as int?));
        _coins = {
          'monthly_coins': r['monthly_remaining'] ?? _coins?['monthly_coins'] ?? 0,
          'monthly_coins_max': _coins?['monthly_coins_max'] ?? 100,
          'purchased_coins': r['purchased_remaining'] ?? _coins?['purchased_coins'] ?? 0,
          'total_coins': r['coins_remaining'] ?? 0,
        };
      });
      await _loadCoins();
    } catch (e) {
      final text = e.toString().contains('402') || e.toString().contains('不足') ? '研AI币不足，请前往VIP会员或兑换中心补充。' : '⚠️ $e';
      setState(() => _msgs.add(_Msg(false, text)));
    }
    if (mounted) setState(() => _thinking = false);
    _scroll();
  }

  void _scroll() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!_sc.hasClients) return;
      _sc.animateTo(_sc.position.maxScrollExtent, duration: const Duration(milliseconds: 300), curve: Curves.easeOut);
    });
  }

  @override Widget build(BuildContext c) => Column(children: [
    Hdr(t: 'AI 考研助手', s: 'DeepSeek驱动 · 随时陪你聊备考'),
    _coinsBar(),
    Expanded(child: ListView.builder(controller: _sc, padding: const EdgeInsets.symmetric(horizontal: 16), itemCount: _msgs.length, itemBuilder: (_, i) => _bub(_msgs[i]))),
    if (_thinking) const Padding(padding: EdgeInsets.only(bottom: 4), child: Text('AI思考中…', style: TextStyle(fontSize: 12, color: kClay))),
    Container(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 12),
      decoration: const BoxDecoration(color: kPaper, border: Border(top: BorderSide(color: kMist))),
      child: Column(children: [
        Row(children: [
          FilterChip(
            selected: _deepThink,
            onSelected: _thinking ? null : (v) => setState(() => _deepThink = v),
            label: const Text('深度思考'),
            avatar: const Icon(Icons.psychology_alt_outlined, size: 16),
            selectedColor: kBrassSoft,
          ),
          const Spacer(),
          Text(_deepThink ? '本次约3币' : '本次约1币', style: const TextStyle(color: kClay, fontSize: 12)),
        ]),
        const SizedBox(height: 8),
        Row(children: [
          Expanded(child: TextField(controller: _inp, decoration: const InputDecoration(hintText: '输入消息…', contentPadding: EdgeInsets.symmetric(horizontal: 14, vertical: 10)), onSubmitted: (_) => _send())),
          const SizedBox(width: 10),
          GestureDetector(onTap: _thinking ? null : _send, child: Container(width: 40, height: 40, decoration: BoxDecoration(color: _thinking ? kClay : kForest, borderRadius: BorderRadius.circular(10)), child: Icon(_thinking ? Icons.hourglass_empty : Icons.send_rounded, color: Colors.white, size: 18))),
        ]),
      ]),
    ),
  ]);

  Widget _coinsBar() {
    final monthly = _coins?['monthly_coins'] ?? 0;
    final max = _coins?['monthly_coins_max'] ?? 100;
    final purchased = _coins?['purchased_coins'] ?? 0;
    return Container(
      margin: const EdgeInsets.fromLTRB(16, 8, 16, 10),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(color: kParchment, borderRadius: BorderRadius.circular(12), border: Border.all(color: kMist)),
      child: Row(children: [
        const Icon(Icons.toll_outlined, color: kBrass, size: 18),
        const SizedBox(width: 8),
        Expanded(child: Text('月度 $monthly/$max · 永久 $purchased', style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: kInk))),
        TextButton(onPressed: _loadCoins, child: const Text('刷新')),
      ]),
    );
  }

  Widget _bub(_Msg m) => Padding(
    padding: const EdgeInsets.only(bottom: 12),
    child: Row(crossAxisAlignment: CrossAxisAlignment.start, mainAxisAlignment: m.me ? MainAxisAlignment.end : MainAxisAlignment.start, children: [
      if (!m.me) Container(width: 32, height: 32, margin: const EdgeInsets.only(top: 2), decoration: BoxDecoration(color: kForest, borderRadius: BorderRadius.circular(8)), child: const Icon(Icons.auto_awesome, color: Colors.white, size: 16)),
      if (!m.me) const SizedBox(width: 10),
      Flexible(child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        decoration: BoxDecoration(color: m.me ? kParchment : kPaper, borderRadius: BorderRadius.circular(12), border: Border.all(color: kMist)),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(m.t, style: const TextStyle(fontSize: 14, height: 1.55)),
          if (m.coinsUsed != null) Padding(padding: const EdgeInsets.only(top: 6), child: Text('本次消耗 ${m.coinsUsed} 研AI币', style: const TextStyle(color: kClay, fontSize: 11))),
        ]),
      )),
      if (m.me) const SizedBox(width: 10),
      if (m.me) Container(width: 32, height: 32, margin: const EdgeInsets.only(top: 2), decoration: BoxDecoration(color: kBrass, borderRadius: BorderRadius.circular(8)), child: const Icon(Icons.person, color: Colors.white, size: 16)),
    ]),
  );

  @override void dispose() {
    _inp.dispose();
    _sc.dispose();
    super.dispose();
  }
}
