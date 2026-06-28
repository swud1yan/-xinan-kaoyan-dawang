part of xinan_dawang;

// ======================== Tab 6: My ========================
class MyTab extends StatefulWidget {
  final Map user;
  final VoidCallback onLogout;
  const MyTab({super.key, required this.user, required this.onLogout});
  @override State<MyTab> createState() => _MyTabState();
}

class _MyTabState extends State<MyTab> {
  Map? _me, _ai, _coins, _signIn, _exam, _motto;
  bool _signing = false;

  @override void initState() {
    super.initState();
    _me = widget.user;
    _load();
  }

  Future<Map?> _tryMap(Future<Map> future) async {
    try { return await future; } catch (_) { return null; }
  }

  Future<void> _load({bool includeAi = true}) async {
    final futures = <Future<Map?>>[
      _tryMap(Api.getMe()),
      _tryMap(Api.getCoinsStatus()),
      _tryMap(Api.getSignInStatus()),
      _tryMap(Api.getExamDate()),
      _tryMap(Api.getDailyMotto()),
      if (includeAi) _tryMap(Api.getAiSummary()),
    ];
    final r = await Future.wait(futures);
    if (r[0] != null) _me = r[0];
    if (r[1] != null) _coins = r[1];
    if (r[2] != null) _signIn = r[2];
    if (r[3] != null) _exam = r[3];
    if (r[4] != null) _motto = r[4];
    if (includeAi && r.length > 5 && r[5] != null) _ai = r[5];
    if (mounted) setState(() {});
  }

  Future<void> _doSignIn() async {
    if (_signing) return;
    setState(() => _signing = true);
    try {
      final r = await Api.dailySignIn();
      final user = Map<String, dynamic>.from(_me ?? widget.user);
      user['xp'] = r['total_xp'] ?? user['xp'] ?? 0;
      user['level'] = r['new_level'] ?? user['level'] ?? 1;
      user['levelTitle'] = r['new_title'] ?? user['levelTitle'];
      _me = user;
      _signIn = {...?_signIn, 'today_signed': true, 'streak': r['streak'] ?? _signIn?['streak'] ?? 0};
      if (mounted) {
        setState(() {});
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('签到成功，+${r['xp_earned'] ?? 0}经验')));
      }
      await _load(includeAi: false);
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
    }
    if (mounted) setState(() => _signing = false);
  }

  String _initial(String? s) => (s == null || s.isEmpty) ? '?' : s.substring(0, 1);

  @override Widget build(BuildContext c) {
    final user = _me ?? widget.user;
    final xp = (user['xp'] ?? 0) as int;
    final level = user['level'] ?? 1;
    final vip = user['vipLevel'] ?? 0;
    final monthly = _coins?['monthly_coins'] ?? user['monthlyCoins'] ?? 0;
    final monthlyMax = _coins?['monthly_coins_max'] ?? user['monthlyCoinsMax'] ?? 100;
    final purchased = _coins?['purchased_coins'] ?? user['purchasedCoins'] ?? 0;
    final signed = _signIn?['today_signed'] == true;
    final xpInfo = _xpInfo(xp);

    return SingleChildScrollView(padding: const EdgeInsets.only(bottom: 32), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Hdr(t: '我的', s: '个人中心'),
      _countdownCard(),
      Container(
        margin: const EdgeInsets.all(20),
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(color: kPaper, borderRadius: BorderRadius.circular(16), boxShadow: shadowLevel(2)),
        child: Column(children: [
          CircleAvatar(radius: 40, backgroundColor: kParchment, child: Text(_initial(user['nickname']?.toString()), style: const TextStyle(fontSize: 32, fontWeight: FontWeight.w800, color: kForest))),
          const SizedBox(height: 12),
          Text(user['nickname'] ?? '', style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w700)),
          const SizedBox(height: 4),
          Text('大王号: ${user['dawangId'] ?? ''}', style: const TextStyle(color: kClay)),
          if ((user['targetSchool']?.toString() ?? '').isNotEmpty) ...[
            const SizedBox(height: 4),
            Text('🎯 ${user['targetSchool']}${(user['major']?.toString() ?? '').isNotEmpty ? ' · ${user['major']}' : ''}', style: const TextStyle(color: kForest, fontWeight: FontWeight.w600)),
          ],
          if ((user['undergradSchool']?.toString() ?? '').isNotEmpty) ...[
            const SizedBox(height: 2),
            Text('🏫 ${user['undergradSchool']}', style: const TextStyle(color: kClay, fontSize: 13)),
          ],
          const SizedBox(height: 12),
          Row(mainAxisAlignment: MainAxisAlignment.center, children: [
            if (user['isWhitelist'] == true) _pill('管理员', kBrass),
            if (user['isWhitelist'] == true) const SizedBox(width: 8),
            _pill('Lv.$level', kForest),
            const SizedBox(width: 8),
            _pill(vip == 99 ? '研王爷' : vip > 0 ? 'VIP$vip' : '免费用户', kBrass),
          ]),
          const SizedBox(height: 14),
          ClipRRect(borderRadius: BorderRadius.circular(999), child: LinearProgressIndicator(value: xpInfo['progress'] as double, minHeight: 8, backgroundColor: kMist, color: kForest)),
          const SizedBox(height: 6),
          Text('${xpInfo['current']}/${xpInfo['needed']} XP · 距下一级 ${xpInfo['left']} XP', style: const TextStyle(color: kClay, fontSize: 12)),
        ]),
      ),
      Padding(padding: const EdgeInsets.symmetric(horizontal: 20), child: Row(children: [
        Expanded(child: _statCard(Icons.toll_outlined, '月度币', '$monthly/$monthlyMax')),
        const SizedBox(width: 10),
        Expanded(child: _statCard(Icons.savings_outlined, '永久币', '$purchased')),
      ])),
      const SizedBox(height: 14),
      Padding(padding: const EdgeInsets.symmetric(horizontal: 20), child: Row(children: [
        Expanded(child: FilledButton.icon(onPressed: signed || _signing ? null : _doSignIn, icon: Icon(signed ? Icons.check_circle_outline : Icons.event_available_outlined), label: Text(signed ? '今日已签到' : _signing ? '签到中' : '每日签到'), style: FilledButton.styleFrom(backgroundColor: kForest, padding: const EdgeInsets.symmetric(vertical: 12)))),
        const SizedBox(width: 10),
        Expanded(child: OutlinedButton.icon(onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => LevelPage(user: user))), icon: const Icon(Icons.military_tech_outlined), label: const Text('等级详情'), style: OutlinedButton.styleFrom(padding: const EdgeInsets.symmetric(vertical: 12)))),
      ])),
      const SizedBox(height: 18),
      _aiCard(),
      const SizedBox(height: 20),
      const Padding(padding: EdgeInsets.symmetric(horizontal: 20), child: Text('学习工具', style: TextStyle(fontSize: 15, fontWeight: FontWeight.w700))),
      _entry(Icons.timer_outlined, '番茄钟', '专注计时、自习室和白噪音', () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => const PomodoroPage()))),
      _entry(Icons.quiz_outlined, '每日一题', '真题练习，答错自动进错题本', () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => const DailyQuestionPage()))),
      _entry(Icons.fact_check_outlined, '错题本', '复习错题并标记攻克', () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => const ErrorNotebookPage()))),
      _entry(Icons.style_outlined, '记忆闪卡', '政治概念和英语词汇间隔复习', () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => const FlashcardsPage()))),
      _entry(Icons.compare_arrows, '院校对比', '最多3所院校并排比较', () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => const SchoolComparePage()))),
      _entry(Icons.workspace_premium, '成就徽章', '自动解锁学习、坚持和成长徽章', () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => const AchievementsPage()))),
      _entry(Icons.emoji_events_outlined, '西南卷王榜', '周番茄、总经验和签到排行榜', () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => const LeaderboardPage()))),
      _entry(Icons.edit_note_outlined, '考研日记', '记录每日复盘和AI一句话反馈', () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => const DiaryPage()))),
      _entry(Icons.groups_outlined, '研友匹配', '按目标院校、专业和节奏推荐研友', () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => const MatchPage()))),
      _entry(Icons.auto_awesome_outlined, '锦鲤运势', '每日考研运势和好运加成', () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => const FortunePage()))),
      _entry(Icons.assignment_outlined, '模拟考试', '限时模考、交卷评分和AI分析', () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => const MockExamPage()))),
      _entry(Icons.record_voice_over_outlined, 'AI复试面试', '文字版复试模拟问答和点评', () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => InterviewPage(user: user)))),
      _entry(Icons.manage_search_outlined, '调剂监控', '调剂信息检索和AI匹配分析', () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => const TransferPage()))),
      _entry(Icons.event_note_outlined, 'AI学习计划', '生成周计划并跟踪任务完成率', () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => const StudyPlanPage()))),
      const Padding(padding: EdgeInsets.symmetric(horizontal: 20, vertical: 8), child: Text('权益与设置', style: TextStyle(fontSize: 15, fontWeight: FontWeight.w700))),
      _entry(Icons.event_available_outlined, '签到日历', '查看本月签到和连续奖励', () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => SignInPage(onChanged: () => _load(includeAi: false))))),
      _entry(Icons.workspace_premium_outlined, 'VIP 会员', '月度VIP、研王爷与永久币包', () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => VipPage(onRedeemChanged: () => _load(includeAi: false))))),
      _entry(Icons.confirmation_number_outlined, '兑换中心', '输入兑换码激活VIP或币包', () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => RedeemPage(onChanged: () => _load(includeAi: false))))),
      _entry(Icons.lock_outline, '账号安全', '修改密码和大王号', () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => AccountSecurityPage(user: user)))),
      _entry(Icons.support_agent_outlined, '帮助与客服', 'AI助手解答APP使用问题', () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => const HelpPage()))),
      _entry(Icons.info_outline, '关于我们', '西南大王版本与版权信息', () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => AboutUsPage(user: user, onChanged: () => _load(includeAi: false))))),
      ListTile(leading: const Icon(Icons.logout, color: kRed), title: const Text('退出登录', style: TextStyle(color: kRed)), onTap: () => showDialog(context: context, builder: (c) => AlertDialog(title: const Text('退出登录'), content: const Text('确定退出？'), actions: [TextButton(onPressed: () => Navigator.pop(c), child: const Text('取消')), TextButton(onPressed: () { Navigator.pop(c); widget.onLogout(); }, child: const Text('退出', style: TextStyle(color: kRed)))]))),
    ]));
  }

  Widget _countdownCard() => Container(
    margin: const EdgeInsets.fromLTRB(20, 4, 20, 0),
    padding: const EdgeInsets.all(16),
    decoration: BoxDecoration(color: kForest, borderRadius: BorderRadius.circular(16), boxShadow: shadowLevel(2)),
    child: Row(children: [
      Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text(_exam?['title'] ?? '考研倒计时', style: const TextStyle(color: Colors.white70)), const SizedBox(height: 6), Text('还有 ${_exam?['days_remaining'] ?? '--'} 天', style: const TextStyle(color: Colors.white, fontSize: 28, fontWeight: FontWeight.w900)), const SizedBox(height: 4), Text(_motto?['motto'] ?? '今天也推进一点。', style: const TextStyle(color: Colors.white70, fontSize: 12))])),
      const Icon(Icons.hourglass_bottom, color: kBrass, size: 42),
    ]),
  );

  Widget _pill(String text, Color color) => Container(padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4), decoration: BoxDecoration(color: color.withAlpha(22), borderRadius: BorderRadius.circular(20)), child: Text(text, style: TextStyle(fontSize: 12, color: color, fontWeight: FontWeight.w700)));
  Widget _statCard(IconData icon, String label, String value) => Container(padding: const EdgeInsets.all(14), decoration: BoxDecoration(color: kParchment, borderRadius: BorderRadius.circular(14), border: Border.all(color: kMist)), child: Row(children: [Icon(icon, color: kBrass), const SizedBox(width: 10), Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text(label, style: const TextStyle(color: kClay, fontSize: 12)), const SizedBox(height: 3), Text(value, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16))]))]));
  Widget _entry(IconData icon, String title, String subtitle, VoidCallback onTap) => ListTile(leading: Icon(icon, color: kForest), title: Text(title), subtitle: Text(subtitle), trailing: const Icon(Icons.chevron_right), onTap: onTap);
  Widget _aiCard() { if (_ai == null || _ai!['summary'] == null) return const SizedBox.shrink(); final tags = (_ai!['tags'] as List?) ?? []; return Container(margin: const EdgeInsets.symmetric(horizontal: 20), padding: const EdgeInsets.all(16), decoration: BoxDecoration(color: kParchment, borderRadius: BorderRadius.circular(14), boxShadow: shadowLevel(1)), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [const Row(children: [Icon(Icons.auto_awesome, color: kBrass, size: 16), SizedBox(width: 6), Text('AI 学情分析', style: TextStyle(fontWeight: FontWeight.w700, color: kForest))]), const SizedBox(height: 8), Text(_ai!['summary'] ?? '', style: const TextStyle(fontSize: 13, height: 1.5)), if (tags.isNotEmpty) const SizedBox(height: 8), if (tags.isNotEmpty) Wrap(spacing: 6, children: [for (final t in tags) Chip(label: Text(t, style: const TextStyle(fontSize: 11)), backgroundColor: kPaper)])])); }

  Map<String, Object> _xpInfo(int xp) {
    var level = 1;
    int totalFor(int lv) { var total = 0; for (var i = 1; i < lv; i++) { total += (100 * math.pow(1.15, i - 1)).round(); } return total; }
    while (level < 100 && xp >= totalFor(level + 1)) { level++; }
    final curTotal = totalFor(level);
    final nextTotal = totalFor(level + 1);
    final current = math.max(0, xp - curTotal);
    final needed = math.max(1, nextTotal - curTotal);
    return {'current': current, 'needed': needed, 'left': math.max(0, needed - current), 'progress': (current / needed).clamp(0, 1).toDouble()};
  }
}
