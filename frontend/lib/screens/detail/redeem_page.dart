part of xinan_dawang;

class RedeemPage extends StatefulWidget {
  final VoidCallback? onChanged;
  const RedeemPage({super.key, this.onChanged});
  @override State<RedeemPage> createState() => _RedeemPageState();
}
class _RedeemPageState extends State<RedeemPage> {
  final _code = TextEditingController();
  List _history = [];
  bool _loading = true, _busy = false;
  @override void initState() { super.initState(); _load(); }
  Future<void> _load() async { try { _history = await Api.getRedeemHistory(); } catch (_) {} if (mounted) setState(() => _loading = false); }
  Future<void> _redeem() async {
    final code = _code.text.trim();
    if (code.length < 10) { ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('请输入完整兑换码'))); return; }
    setState(() => _busy = true);
    try { final r = await Api.redeemCode(code); _code.clear(); await _load(); widget.onChanged?.call(); if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(r['type'] == 'coins' ? '兑换成功，${r['coins_added']}研AI币已到账' : 'VIP已激活'))); }
    catch (e) { if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString()))); }
    if (mounted) setState(() => _busy = false);
  }
  @override Widget build(BuildContext context) => Scaffold(appBar: AppBar(title: const Text('兑换中心')), body: SingleChildScrollView(padding: const EdgeInsets.all(20), child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
    Container(padding: const EdgeInsets.all(18), decoration: BoxDecoration(color: kPaper, borderRadius: BorderRadius.circular(16), boxShadow: shadowLevel(2)), child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [const Text('输入兑换码', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800)), const SizedBox(height: 12), TextField(controller: _code, textCapitalization: TextCapitalization.characters, decoration: const InputDecoration(hintText: 'XNDW-____-____', prefixIcon: Icon(Icons.confirmation_number_outlined))), const SizedBox(height: 14), FilledButton(onPressed: _busy ? null : _redeem, style: FilledButton.styleFrom(backgroundColor: kForest, padding: const EdgeInsets.symmetric(vertical: 14)), child: Text(_busy ? '兑换中…' : '立即兑换'))])),
    const SizedBox(height: 22), const Text('兑换记录', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w800)), const SizedBox(height: 8),
    if (_loading) const SkeletonList(count: 3) else if (_history.isEmpty) const EmptyState(icon: Icons.receipt_long_outlined, title: '暂无兑换记录', subtitle: '兑换成功后会显示在这里') else for (final r in _history) ListTile(contentPadding: EdgeInsets.zero, leading: const Icon(Icons.check_circle, color: kForest), title: Text(r['productName'] ?? r['productType'] ?? ''), subtitle: Text(r['createdAt'] ?? ''), trailing: Text(r['coinsAdded'] == 0 ? 'VIP' : '+${r['coinsAdded']}币', style: const TextStyle(color: kBrass, fontWeight: FontWeight.w700))),
  ])));
  @override void dispose() { _code.dispose(); super.dispose(); }
}
