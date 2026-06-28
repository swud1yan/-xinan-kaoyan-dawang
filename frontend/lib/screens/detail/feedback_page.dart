part of xinan_dawang;

// ======================== Feedback Page ========================
class FeedbackPage extends StatefulWidget {
  const FeedbackPage({super.key});
  @override State<FeedbackPage> createState() => _FeedbackPageState();
}

class _FeedbackPageState extends State<FeedbackPage> {
  final _content = TextEditingController();
  final _contact = TextEditingController();
  bool _sending = false;

  Future<void> _submit() async {
    final c = _content.text.trim();
    if (c.isEmpty) return;
    setState(() => _sending = true);
    try {
      await Api.post('/feedback', {'content': c, 'contact': _contact.text.trim()});
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('反馈已提交，感谢你的建议！')));
        Navigator.of(context).pop();
      }
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
    }
    if (mounted) setState(() => _sending = false);
  }

  @override Widget build(BuildContext c) => Scaffold(
    appBar: AppBar(title: const Text('意见反馈')),
    body: Padding(padding: const EdgeInsets.all(20), child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      const Text('请描述你的问题或建议', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 16)),
      const SizedBox(height: 8),
      TextField(controller: _content, maxLines: 8, maxLength: 2000,
        decoration: const InputDecoration(hintText: '写下你的反馈内容…（最多2000字）', border: OutlineInputBorder())),
      const SizedBox(height: 16),
      TextField(controller: _contact, maxLength: 100,
        decoration: const InputDecoration(hintText: '联系方式（选填，方便我们回复）', border: OutlineInputBorder())),
      const SizedBox(height: 24),
      FilledButton(onPressed: _sending ? null : _submit,
        style: FilledButton.styleFrom(backgroundColor: kForest, padding: const EdgeInsets.symmetric(vertical: 14)),
        child: Text(_sending ? '提交中…' : '提交反馈')),
    ])),
  );

  @override void dispose() { _content.dispose(); _contact.dispose(); super.dispose(); }
}
