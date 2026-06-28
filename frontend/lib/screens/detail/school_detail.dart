part of xinan_dawang;

class SchoolDetailPage extends StatefulWidget {
  final String schoolId, schoolName;
  final String? userMajor;
  final VoidCallback? onTargetChanged;
  const SchoolDetailPage({super.key, required this.schoolId, required this.schoolName, this.userMajor, this.onTargetChanged});
  @override State<SchoolDetailPage> createState() => _SchoolDetailPageState();
}

class _SchoolDetailPageState extends State<SchoolDetailPage> {
  Map? _detail; bool _loading = true, _saving = false;

  @override void initState() { super.initState(); _load(); }
  Future<void> _load() async { try { _detail = await Api.getSchoolDetail(widget.schoolId, userMajor: widget.userMajor); } catch (_) {} setState(() => _loading = false); }

  Future<void> _setTarget(String major) async {
    if (_saving) return;
    final has = widget.userMajor != null && widget.userMajor!.isNotEmpty;
    final ok = await showDialog<bool>(context: context, builder: (c) => AlertDialog(
      title: Text(has ? '修改目标' : '设为我的目标'),
      content: Text(has ? '确定将目标修改为「${widget.schoolName} - $major」？' : '确定将目标设为「${widget.schoolName} - $major」？'),
      actions: [TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('取消')),
        FilledButton(onPressed: () => Navigator.pop(c, true), style: FilledButton.styleFrom(backgroundColor: kForest), child: const Text('确认'))]));
    if (ok != true) return;
    setState(() => _saving = true);
    try { await Api._put('/auth/set-target', {'target_school': widget.schoolName, 'major': major}); widget.onTargetChanged?.call();
      if (mounted) { ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('目标已更新'))); _load(); }
    } catch (e) { if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString()))); }
    setState(() => _saving = false);
  }

  @override Widget build(BuildContext c) => Scaffold(appBar: AppBar(title: Text(widget.schoolName), backgroundColor: kPaper),
    body: _loading ? const Center(child: CircularProgressIndicator(color: kForest))
      : _detail == null ? const Center(child: Text('加载失败'))
      : SingleChildScrollView(padding: const EdgeInsets.all(20), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
    Text(widget.schoolName, style: const TextStyle(fontSize: 24, fontWeight: FontWeight.w800)),
    const SizedBox(height: 4), Text('${_detail!['province'] ?? ''} · ${_detail!['schoolType'] ?? ''} · ${(_detail!['tags'] as List?)?.join(',') ?? ''}', style: const TextStyle(color: kClay)),
    const SizedBox(height: 20), const Text('硕士专业', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
    for (final p in (_detail!['programs'] as List?) ?? [])
      Container(margin: const EdgeInsets.only(top: 12), padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(color: kPaper, borderRadius: BorderRadius.circular(12), border: Border.all(color: kMist)),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Expanded(child: Text(p['name'] ?? '', style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 16))),
            Container(padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3), decoration: BoxDecoration(color: kParchment, borderRadius: BorderRadius.circular(4)), child: Text(p['degreeType'] ?? '', style: const TextStyle(fontSize: 12, color: kBrass))),
            if (p['isUnified'] == true) ...[const SizedBox(width: 6), Container(padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3), decoration: BoxDecoration(color: kForest.withAlpha(30), borderRadius: BorderRadius.circular(4)), child: Text(p['unifiedName'] ?? '统考', style: const TextStyle(fontSize: 11, color: kForest)))],
          ]),
          const SizedBox(height: 8), Text('考试科目: ${p['subjects'] ?? ''}', style: const TextStyle(fontSize: 13, color: kClay)),
          if ((p['lines'] as List?)?.isNotEmpty == true) ...[
            const SizedBox(height: 12),
            SizedBox(height: 120, child: Row(crossAxisAlignment: CrossAxisAlignment.end, children: [
              for (final l in (p['lines'] as List).reversed.toList())
                Expanded(child: Padding(padding: const EdgeInsets.symmetric(horizontal: 4), child: Column(mainAxisAlignment: MainAxisAlignment.end, children: [
                  Text('${l['total']}', style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: kForest)),
                  Container(height: 80 * (l['total'] - 250) / 200, color: kForest.withAlpha(120)),
                  const SizedBox(height: 4), Text('${l['year']}', style: const TextStyle(fontSize: 11, color: kClay)),
                ]))),
            ])),
          ],
          Padding(padding: const EdgeInsets.only(top: 8), child: OutlinedButton.icon(
            onPressed: _saving ? null : () => _setTarget(p['name']?.toString() ?? ''),
            icon: Icon(widget.userMajor != null ? Icons.edit : Icons.flag_outlined, size: 16),
            label: Text(widget.userMajor != null ? '修改目标' : '设为我的目标'),
            style: OutlinedButton.styleFrom(foregroundColor: kForest))),
        ])),
  ])));
}
