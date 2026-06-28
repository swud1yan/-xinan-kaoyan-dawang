part of xinan_dawang;

class SignInPage extends StatefulWidget {
  final VoidCallback? onChanged;
  const SignInPage({super.key, this.onChanged});
  @override State<SignInPage> createState() => _SignInPageState();
}

class _SignInPageState extends State<SignInPage> {
  Map? _status;
  bool _loading = true, _signing = false;
  @override void initState() { super.initState(); _load(); }
  Future<void> _load() async { try { _status = await Api.getSignInStatus(); } catch (_) {} if (mounted) setState(() => _loading = false); }
  Future<void> _signIn() async {
    if (_signing) return; setState(() => _signing = true);
    try { final r = await Api.dailySignIn(); await _load(); widget.onChanged?.call(); if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('签到成功，+${r['xp_earned']}经验'))); }
    catch (e) { if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString()))); }
    if (mounted) setState(() => _signing = false);
  }
  @override Widget build(BuildContext context) {
    final now = DateTime.now();
    final records = ((_status?['this_month_records'] as List?) ?? []).map((e) => e['date'].toString()).toSet();
    final days = DateUtils.getDaysInMonth(now.year, now.month);
    return Scaffold(appBar: AppBar(title: const Text('每日签到')), body: _loading ? const Center(child: CircularProgressIndicator(color: kForest)) : SingleChildScrollView(padding: const EdgeInsets.all(20), child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      Container(padding: const EdgeInsets.all(18), decoration: BoxDecoration(color: kPaper, borderRadius: BorderRadius.circular(16), boxShadow: shadowLevel(2)), child: Column(children: [
        Text('${now.month}月签到', style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w800, color: kInk)),
        const SizedBox(height: 14),
        GridView.builder(shrinkWrap: true, physics: const NeverScrollableScrollPhysics(), itemCount: days, gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(crossAxisCount: 7, mainAxisSpacing: 8, crossAxisSpacing: 8), itemBuilder: (_, i) { final day = i + 1; final key = DateTime(now.year, now.month, day).toIso8601String().substring(0, 10); final signed = records.contains(key); final today = day == now.day; return Container(decoration: BoxDecoration(color: signed ? kForest : today ? kBrassSoft : kParchment, borderRadius: BorderRadius.circular(10)), child: Center(child: Text(signed ? '✓' : '$day', style: TextStyle(color: signed ? Colors.white : kInk, fontWeight: today ? FontWeight.w800 : FontWeight.w500)))); }),
        const SizedBox(height: 18), Text('已连续签到: ${_status?['streak'] ?? 0}天', style: const TextStyle(fontWeight: FontWeight.w700, color: kForest)), const SizedBox(height: 4), Text('本月累计: ${_status?['this_month_days'] ?? 0}天', style: const TextStyle(color: kClay)),
      ])),
      const SizedBox(height: 16), _nextBonus(), const SizedBox(height: 20),
      FilledButton(onPressed: (_status?['today_signed'] == true || _signing) ? null : _signIn, style: FilledButton.styleFrom(backgroundColor: kForest, padding: const EdgeInsets.symmetric(vertical: 14), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10))), child: Text(_status?['today_signed'] == true ? '今日已签到' : _signing ? '签到中…' : '今日签到')),
    ])));
  }
  Widget _nextBonus() { final b = (_status?['next_bonus'] as Map?) ?? {}; return Container(padding: const EdgeInsets.all(16), decoration: BoxDecoration(color: kBrassSoft, borderRadius: BorderRadius.circular(14)), child: Text('连续${b['day'] ?? 7}天可获: +${b['xp'] ?? 25}经验${b['extra'] != null ? ' + ${b['extra']}' : ''}\n还差 ${b['remaining_days'] ?? 0} 天，继续坚持。', style: const TextStyle(color: kInk, height: 1.5))); }
}
