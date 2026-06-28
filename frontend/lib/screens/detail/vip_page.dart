part of xinan_dawang;

class VipPage extends StatefulWidget {
  final VoidCallback? onRedeemChanged;
  const VipPage({super.key, this.onRedeemChanged});
  @override State<VipPage> createState() => _VipPageState();
}

class _VipPageState extends State<VipPage> with SingleTickerProviderStateMixin {
  late final TabController _tabs;
  Map? _products;
  bool _loading = true;

  @override void initState() {
    super.initState();
    _tabs = TabController(length: 3, vsync: this);
    _load();
  }

  Future<void> _load() async {
    try {
      _products = await Api.getRedeemProducts();
    } catch (_) {}
    if (mounted) setState(() => _loading = false);
  }

  void _showContact(String name) {
    showDialog(
      context: context,
      builder: (c) => AlertDialog(
        title: Text('获取$name兑换码'),
        content: const Text('当前采用兑换码模式。请联系客服购买后，在兑换中心输入兑换码完成激活。\n\n客服微信/QQ：xndw-kefu'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c), child: const Text('稍后')),
          FilledButton(
            onPressed: () {
              Navigator.pop(c);
              Navigator.of(context).push(MaterialPageRoute(builder: (_) => RedeemPage(onChanged: widget.onRedeemChanged)));
            },
            style: FilledButton.styleFrom(backgroundColor: kForest),
            child: const Text('去兑换'),
          ),
        ],
      ),
    );
  }

  @override Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('VIP 会员'),
        bottom: TabBar(
          controller: _tabs,
          labelColor: kForest,
          indicatorColor: kForest,
          tabs: const [Tab(text: '月度VIP'), Tab(text: '研王爷'), Tab(text: '币包')],
        ),
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator(color: kForest))
          : TabBarView(controller: _tabs, children: [_vipPlans(), _yanwang(), _coinPacks()]),
    );
  }

  Widget _vipPlans() {
    final plans = ((_products?['vip_plans'] as List?) ?? []).where((e) => (e['vip_level'] ?? e['vipLevel']) != 99).toList();
    return ListView(padding: const EdgeInsets.all(16), children: [
      for (final p in plans)
        _PlanCard(
          icon: Icons.workspace_premium_outlined,
          title: p['name']?.toString() ?? 'VIP 套餐',
          subtitle: '${p['coins_per_month'] ?? p['coinsPerMonth'] ?? 0} 研AI币/月',
          price: '￥${p['price'] ?? '-'} / 月',
          recommended: (p['id'] ?? '') == 'gold',
          lines: const ['学习工具权益升级', '真题/报告/计划能力按等级开放', '社交展示不加权，内容排序保持公平'],
          onTap: () => _showContact(p['name']?.toString() ?? 'VIP'),
        ),
    ]);
  }

  Widget _yanwang() {
    final plans = ((_products?['vip_plans'] as List?) ?? []);
    Map? p;
    for (final item in plans) {
      if ((item['vip_level'] ?? item['vipLevel']) == 99) {
        p = item as Map;
        break;
      }
    }
    return ListView(padding: const EdgeInsets.all(16), children: [
      Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(color: kForest, borderRadius: BorderRadius.circular(16), boxShadow: shadowLevel(2)),
        child: const Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('研王爷', style: TextStyle(fontSize: 24, fontWeight: FontWeight.w900, color: Colors.white)),
          SizedBox(height: 8),
          Text('一次付费，陪你直到上岸。', style: TextStyle(color: Colors.white70, height: 1.5)),
        ]),
      ),
      const SizedBox(height: 14),
      _BenefitTile(icon: Icons.psychology_alt_outlined, title: '深度思考模式', text: '可开启更高成本的 AI 回复模式，处理难题和长上下文。'),
      _BenefitTile(icon: Icons.verified_outlined, title: '2年保障', text: '两年内未上岸可按规则申请退款。'),
      _BenefitTile(icon: Icons.school_outlined, title: '上岸身份', text: '考上后可确认上岸，转为学长学姐身份。'),
      const SizedBox(height: 16),
      FilledButton(
        onPressed: () => _showContact('研王爷'),
        style: FilledButton.styleFrom(backgroundColor: kForest, padding: const EdgeInsets.symmetric(vertical: 14), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10))),
        child: Text('成为研王爷 ￥${p?['price'] ?? 298}'),
      ),
    ]);
  }

  Widget _coinPacks() {
    final packs = (_products?['coin_packs'] as List?) ?? [];
    return ListView(padding: const EdgeInsets.all(16), children: [
      const Text('永久币包', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800)),
      const SizedBox(height: 6),
      const Text('充值币永久不过期，月度币用完后自动启用。', style: TextStyle(color: kClay)),
      const SizedBox(height: 14),
      for (final p in packs)
        _PlanCard(
          icon: Icons.toll_outlined,
          title: p['name']?.toString() ?? '${p['coins']} 研AI币',
          subtitle: '永久有效',
          price: '￥${p['price'] ?? '-'}',
          lines: ['${p['coins'] ?? 0} 枚研AI币', '优先扣月度币，再扣永久币'],
          onTap: () => _showContact(p['name']?.toString() ?? '币包'),
        ),
    ]);
  }

  @override void dispose() {
    _tabs.dispose();
    super.dispose();
  }
}

class _PlanCard extends StatelessWidget {
  final IconData icon;
  final String title, subtitle, price;
  final List<String> lines;
  final VoidCallback onTap;
  final bool recommended;
  const _PlanCard({required this.icon, required this.title, required this.subtitle, required this.price, required this.lines, required this.onTap, this.recommended = false});

  @override Widget build(BuildContext context) => Container(
    margin: const EdgeInsets.only(bottom: 12),
    padding: const EdgeInsets.all(16),
    decoration: BoxDecoration(color: kPaper, borderRadius: BorderRadius.circular(14), border: Border.all(color: recommended ? kBrass : kMist), boxShadow: shadowLevel(1)),
    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Row(children: [
        Container(width: 42, height: 42, decoration: BoxDecoration(color: recommended ? kBrassSoft : kParchment, borderRadius: BorderRadius.circular(10)), child: Icon(icon, color: recommended ? kBrass : kForest)),
        const SizedBox(width: 12),
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [Expanded(child: Text(title, style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w800))), if (recommended) const Text('推荐', style: TextStyle(color: kBrass, fontWeight: FontWeight.w700, fontSize: 12))]),
          const SizedBox(height: 2),
          Text(subtitle, style: const TextStyle(color: kClay, fontSize: 13)),
        ])),
      ]),
      const SizedBox(height: 12),
      for (final l in lines) Padding(padding: const EdgeInsets.only(bottom: 5), child: Row(children: [const Icon(Icons.check, size: 15, color: kForest), const SizedBox(width: 8), Expanded(child: Text(l, style: const TextStyle(fontSize: 13, color: kInk)))])),
      const SizedBox(height: 10),
      Row(children: [
        Expanded(child: Text(price, style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w900, color: kForest))),
        FilledButton(onPressed: onTap, style: FilledButton.styleFrom(backgroundColor: kForest), child: const Text('获取兑换码')),
      ]),
    ]),
  );
}

class _BenefitTile extends StatelessWidget {
  final IconData icon;
  final String title, text;
  const _BenefitTile({required this.icon, required this.title, required this.text});
  @override Widget build(BuildContext context) => Container(
    margin: const EdgeInsets.only(top: 12),
    padding: const EdgeInsets.all(14),
    decoration: BoxDecoration(color: kPaper, borderRadius: BorderRadius.circular(14), boxShadow: shadowLevel(1)),
    child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Icon(icon, color: kForest),
      const SizedBox(width: 12),
      Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text(title, style: const TextStyle(fontWeight: FontWeight.w800)), const SizedBox(height: 4), Text(text, style: const TextStyle(color: kClay, height: 1.4))])),
    ]),
  );
}
