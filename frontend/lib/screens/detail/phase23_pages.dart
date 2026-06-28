part of xinan_dawang;

class PomodoroPage extends StatefulWidget {
  const PomodoroPage({super.key});
  @override State<PomodoroPage> createState() => _PomodoroPageState();
}

class _PomodoroPageState extends State<PomodoroPage> {
  final _subjects = ['408 数据结构', '408 计组', '英语阅读', '数学高数', '政治马原'];
  final _sounds = ['雨声', '图书馆', '海浪', '白噪音'];
  String _subject = '408 数据结构', _sound = '雨声';
  int _minutes = 25, _remain = 0;
  String? _recordId;
  Timer? _timer;
  Map? _today, _room;
  bool _busy = false;

  @override void initState() { super.initState(); _load(); }
  Future<void> _load() async {
    try { _today = await Api.getPomodoroToday(); } catch (_) {}
    try { _room = await Api.getStudyRoomOnline(); } catch (_) {}
    if (mounted) setState(() {});
  }
  Future<void> _start() async {
    if (_busy) return; setState(() => _busy = true);
    try {
      final r = await Api.startPomodoro(_subject, _minutes);
      _recordId = r['record_id'];
      _remain = _minutes * 60;
      _timer?.cancel();
      _timer = Timer.periodic(const Duration(seconds: 1), (_) {
        if (!mounted) return;
        if (_remain <= 1) { _complete(); } else { setState(() => _remain--); }
      });
    } catch (e) { _msg(e.toString()); }
    if (mounted) setState(() => _busy = false);
  }
  Future<void> _complete() async {
    final id = _recordId;
    if (id == null) return;
    _timer?.cancel();
    _recordId = null;
    setState(() => _remain = 0);
    try {
      final r = await Api.completePomodoro(id);
      await _load();
      _msg('专注完成，+${r['xp_earned'] ?? 0}经验');
    } catch (e) { _msg(e.toString()); }
  }
  Future<void> _abandon() async {
    final id = _recordId;
    if (id == null) return;
    _timer?.cancel();
    _recordId = null;
    setState(() => _remain = 0);
    try { await Api.abandonPomodoro(id); await _load(); } catch (_) {}
  }
  void _msg(String s) { if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(s))); }
  @override Widget build(BuildContext context) {
    final running = _recordId != null;
    final total = _minutes * 60;
    final progress = running ? 1 - (_remain / math.max(total, 1)) : 0.0;
    return Scaffold(appBar: AppBar(title: const Text('番茄钟')), body: ListView(padding: const EdgeInsets.all(20), children: [
      Container(padding: const EdgeInsets.all(22), decoration: BoxDecoration(color: kForest, borderRadius: BorderRadius.circular(18), boxShadow: shadowLevel(2)), child: Column(children: [
        Text(running ? _fmt(_remain) : '准备专注', style: const TextStyle(color: Colors.white, fontSize: 42, fontWeight: FontWeight.w900)),
        const SizedBox(height: 10),
        ClipRRect(borderRadius: BorderRadius.circular(99), child: LinearProgressIndicator(value: progress, minHeight: 10, color: kBrass, backgroundColor: Colors.white24)),
        const SizedBox(height: 16),
        Text('$_subject · $_sound', style: const TextStyle(color: Colors.white70)),
      ])),
      const SizedBox(height: 16),
      _chips('科目', _subjects, _subject, (v) => setState(() => _subject = v)),
      _durationChips(),
      _chips('白噪音', _sounds, _sound, (v) => setState(() => _sound = v)),
      const SizedBox(height: 12),
      Row(children: [
        Expanded(child: FilledButton.icon(onPressed: running ? null : _start, icon: const Icon(Icons.play_arrow), label: Text(_busy ? '启动中' : '开始专注'), style: FilledButton.styleFrom(backgroundColor: kForest, padding: const EdgeInsets.symmetric(vertical: 14)))),
        if (running) ...[const SizedBox(width: 10), Expanded(child: OutlinedButton.icon(onPressed: _abandon, icon: const Icon(Icons.stop), label: const Text('提前结束'), style: OutlinedButton.styleFrom(padding: const EdgeInsets.symmetric(vertical: 14))))],
      ]),
      if (running) TextButton(onPressed: _complete, child: const Text('调试/已完成，立即结算')),
      const SizedBox(height: 18),
      _stats(),
      const SizedBox(height: 18),
      _roomCard(),
    ]));
  }
  Widget _durationChips() => Padding(padding: const EdgeInsets.only(top: 14), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [const Text('时长', style: TextStyle(fontWeight: FontWeight.w800)), const SizedBox(height: 8), Wrap(spacing: 8, children: [for (final m in [25, 45, 60]) ChoiceChip(label: Text('$m分钟'), selected: _minutes == m, onSelected: _recordId == null ? (_) => setState(() => _minutes = m) : null)])]));
  Widget _chips(String title, List<String> items, String cur, ValueChanged<String> onPick) => Padding(padding: const EdgeInsets.only(top: 14), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text(title, style: const TextStyle(fontWeight: FontWeight.w800)), const SizedBox(height: 8), Wrap(spacing: 8, runSpacing: 8, children: [for (final s in items) ChoiceChip(label: Text(s), selected: cur == s, onSelected: _recordId == null ? (_) => onPick(s) : null)])]));
  Widget _stats() => Container(padding: const EdgeInsets.all(16), decoration: BoxDecoration(color: kPaper, borderRadius: BorderRadius.circular(14), boxShadow: shadowLevel(1)), child: Row(children: [Expanded(child: _mini('今日番茄', '${_today?['count'] ?? 0}个')), Expanded(child: _mini('今日专注', '${_today?['total_minutes'] ?? 0}分钟'))]));
  Widget _mini(String a, String b) => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text(a, style: const TextStyle(color: kClay, fontSize: 12)), const SizedBox(height: 4), Text(b, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w900, color: kForest))]);
  Widget _roomCard() { final online = (_room?['online'] as List?) ?? []; return Container(padding: const EdgeInsets.all(16), decoration: BoxDecoration(color: kParchment, borderRadius: BorderRadius.circular(14)), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [const Text('自习室', style: TextStyle(fontWeight: FontWeight.w900)), const SizedBox(height: 8), for (final u in online) ListTile(contentPadding: EdgeInsets.zero, dense: true, leading: const Icon(Icons.person_pin_circle_outlined, color: kForest), title: Text(u['nickname'] ?? ''), subtitle: Text(u['subject'] ?? '专注中'))])); }
  String _fmt(int s) => '${(s ~/ 60).toString().padLeft(2, '0')}:${(s % 60).toString().padLeft(2, '0')}';
  @override void dispose() { _timer?.cancel(); super.dispose(); }
}

class DailyQuestionPage extends StatefulWidget {
  const DailyQuestionPage({super.key});
  @override State<DailyQuestionPage> createState() => _DailyQuestionPageState();
}
class _DailyQuestionPageState extends State<DailyQuestionPage> {
  final _subjects = {'408':'408', 'math':'数学', 'politics':'政治', 'english':'英语'};
  String _subject = '408', _choice = '';
  Map? _q, _result;
  bool _loading = true;
  @override void initState(){ super.initState(); _load(); }
  Future<void> _load() async { setState(() { _loading = true; _result = null; _choice = ''; }); try { _q = await Api.getDailyQuestion(subject: _subject); } catch (e) { _q = {'error': e.toString()}; } if (mounted) setState(() => _loading = false); }
  Future<void> _submit() async { if (_choice.isEmpty || _q == null) return; try { _result = await Api.answerQuestion(_q!['id'], _choice); if (mounted) setState(() {}); } catch (e) { if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString()))); } }
  @override Widget build(BuildContext context) {
    final opts = (_q?['options'] as List?) ?? [];
    return Scaffold(appBar: AppBar(title: const Text('每日一题')), body: _loading ? const Center(child: CircularProgressIndicator(color: kForest)) : ListView(padding: const EdgeInsets.all(20), children: [
      Wrap(spacing: 8, children: [for (final e in _subjects.entries) ChoiceChip(label: Text(e.value), selected: _subject == e.key, onSelected: (_) { _subject = e.key; _load(); })]),
      const SizedBox(height: 14),
      if (_q?['error'] != null) EmptyState(icon: Icons.quiz_outlined, title: '题目加载失败', subtitle: _q!['error']) else Container(padding: const EdgeInsets.all(18), decoration: BoxDecoration(color: kPaper, borderRadius: BorderRadius.circular(16), boxShadow: shadowLevel(2)), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text('${_q?['subject'] ?? ''} · ${_q?['subSubject'] ?? ''} · ${_q?['source'] ?? ''}', style: const TextStyle(color: kClay)),
        const SizedBox(height: 12),
        Text(_q?['content'] ?? '', style: const TextStyle(fontSize: 18, height: 1.5, fontWeight: FontWeight.w800)),
        const SizedBox(height: 14),
        for (final o in opts) RadioListTile<String>(value: o.toString().substring(0, 1), groupValue: _choice, onChanged: _result == null ? (v) => setState(() => _choice = v ?? '') : null, title: Text(o.toString())),
        if (_q?['answered'] == true || _result != null) _answerBox(),
        if (_result == null && _q?['answered'] != true) FilledButton(onPressed: _choice.isEmpty ? null : _submit, style: FilledButton.styleFrom(backgroundColor: kForest), child: const Text('提交答案')),
      ])),
    ]));
  }
  Widget _answerBox() { final data = _result ?? _q ?? {}; final ok = data['is_correct'] ?? data['isCorrect'] ?? false; return Container(margin: const EdgeInsets.only(top: 12), padding: const EdgeInsets.all(14), decoration: BoxDecoration(color: ok ? kForestSoft : kBrassSoft, borderRadius: BorderRadius.circular(12)), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text(ok ? '回答正确' : '回答错误', style: const TextStyle(fontWeight: FontWeight.w900)), const SizedBox(height: 6), Text('正确答案：${data['answer'] ?? ''}'), const SizedBox(height: 6), Text(data['explanation'] ?? '', style: const TextStyle(height: 1.5)), if ((data['xp_earned'] ?? 0) > 0) Text('+${data['xp_earned']}经验', style: const TextStyle(color: kForest, fontWeight: FontWeight.w800))])); }
}

class ErrorNotebookPage extends StatefulWidget { const ErrorNotebookPage({super.key}); @override State<ErrorNotebookPage> createState()=>_ErrorNotebookPageState(); }
class _ErrorNotebookPageState extends State<ErrorNotebookPage>{Map? _stats;List _items=[];bool _loading=true;@override void initState(){super.initState();_load();}Future<void> _load()async{try{_stats=await Api.getErrorStats();final r=await Api.getErrorNotes(status:'todo');_items=(r['items']as List?)??[];}catch(_){}if(mounted)setState(()=>_loading=false);}Future<void> _master(String id)async{await Api.masterErrorNote(id);await _load();}@override Widget build(BuildContext c)=>Scaffold(appBar:AppBar(title:const Text('错题本')),body:_loading?const Center(child:CircularProgressIndicator(color:kForest)):ListView(padding:const EdgeInsets.all(20),children:[Container(padding:const EdgeInsets.all(16),decoration:BoxDecoration(color:kParchment,borderRadius:BorderRadius.circular(14)),child:Row(children:[Expanded(child:_stat('待攻克','${_stats?['todo']??0}')),Expanded(child:_stat('已攻克','${_stats?['mastered']??0}')),Expanded(child:_stat('今日复习','${_stats?['due']??0}'))])),const SizedBox(height:14),if(_items.isEmpty)const EmptyState(icon:Icons.fact_check_outlined,title:'暂无错题',subtitle:'每日一题答错后会自动进入这里')else for(final n in _items)Container(margin:const EdgeInsets.only(bottom:10),padding:const EdgeInsets.all(14),decoration:BoxDecoration(color:kPaper,borderRadius:BorderRadius.circular(12),boxShadow:shadowLevel(1)),child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[Text((n['question']??{})['content']??'',style:const TextStyle(fontWeight:FontWeight.w800)),const SizedBox(height:6),Text('错误答案：${n['wrongAnswer']??''} · 错${n['wrongCount']??1}次',style:const TextStyle(color:kClay)),const SizedBox(height:8),Text('解析：${(n['question']??{})['explanation']??''}',style:const TextStyle(height:1.4)),Align(alignment:Alignment.centerRight,child:TextButton(onPressed:()=>_master(n['id']),child:const Text('标记攻克')))]))]));Widget _stat(String a,String b)=>Column(children:[Text(b,style:const TextStyle(fontSize:20,fontWeight:FontWeight.w900,color:kForest)),Text(a,style:const TextStyle(color:kClay,fontSize:12))]);}

class FlashcardsPage extends StatefulWidget{const FlashcardsPage({super.key});@override State<FlashcardsPage>createState()=>_FlashcardsPageState();}
class _FlashcardsPageState extends State<FlashcardsPage>{
  List _decks=[],_cards=[];Map? _deck,_card;bool _showBack=false,_loading=true;
  final _frontC=TextEditingController(),_backC=TextEditingController();
  String _newSubject='408';int _todayFree=0;
  @override void initState(){super.initState();_loadDecks();}
  Future<void> _loadDecks()async{try{final r=await Api.getFlashcardDecks();_decks=(r["items"]as List?)??[];_todayFree=((r["todayFree"]??0)as int);}catch(_){}if(mounted)setState(()=>_loading=false);}
  Future<void> _openDeck(Map d)async{_deck=d;_showBack=false;try{final r=await Api.getFlashcardStudy(d["id"]);_cards=(r["items"]as List?)??[];_card=_cards.isEmpty?null:_cards.first;}catch(_){}if(mounted)setState((){});}
  Future<void> _rate(int rating)async{if(_card==null)return;await Api.reviewFlashcard(_card!["id"],rating);_cards.removeAt(0);_card=_cards.isEmpty?null:_cards.first;_showBack=false;if(mounted)setState((){});}
  void _showCreateDialog(){showDialog(context:context,builder:(c)=>AlertDialog(title:const Text("创建闪卡"),content:Column(mainAxisSize:MainAxisSize.min,children:[DropdownButtonFormField<String>(value:_newSubject,decoration:const InputDecoration(labelText:"学科"),items:["408","数学","英语","政治"].map((s)=>DropdownMenuItem(value:s,child:Text(s))).toList(),onChanged:(v)=>setState(()=>_newSubject=v??"408")),const SizedBox(height:8),TextField(controller:_frontC,decoration:const InputDecoration(labelText:"正面(问题)")),const SizedBox(height:8),TextField(controller:_backC,decoration:const InputDecoration(labelText:"反面(答案)")),Text("今日免费: ${3-_todayFree}/3次, 超出消耗1研AI币",style:const TextStyle(fontSize:11,color:kClay))]),actions:[TextButton(onPressed:()=>Navigator.pop(c),child:const Text("取消")),FilledButton(onPressed:(){_createCard();Navigator.pop(c);},style:FilledButton.styleFrom(backgroundColor:kForest),child:const Text("创建"))]));}
  Future<void> _createCard()async{final f=_frontC.text.trim(),b=_backC.text.trim();if(f.isEmpty||b.isEmpty){ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content:Text("正反面不能为空")));return;}try{await Api.createFlashcard({"deck_name":"我的闪卡","subject":_newSubject,"front":f,"back":b});_frontC.clear();_backC.clear();if(mounted)ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content:Text("已添加")));}catch(e){if(mounted)ScaffoldMessenger.of(context).showSnackBar(SnackBar(content:Text(e.toString())));}}
  @override Widget build(BuildContext c){return Scaffold(appBar:AppBar(title:Text(_deck==null?"记忆闪卡":_deck!["name"]??""),actions:[if(_deck==null)IconButton(icon:const Icon(Icons.add),onPressed:_showCreateDialog)],leading:_deck==null?null:IconButton(icon:const Icon(Icons.arrow_back),onPressed:()=>setState((){_deck=null;_card=null;}))),body:_loading?const Center(child:CircularProgressIndicator(color:kForest)):_deck==null?ListView(padding:const EdgeInsets.all(20),children:[for(final d in _decks)ListTile(leading:const Icon(Icons.style_outlined,color:kForest),title:Text(d["name"]??""),subtitle:Text("${d["cardCount"]??0}张 · ${d["subject"]??""}"),trailing:const Icon(Icons.chevron_right),onTap:()=>_openDeck(d))]):_study());}
  Widget _study(){if(_card==null)return const EmptyState(icon:Icons.done_all,title:"今日卡片完成",subtitle:"明天继续复习");return Padding(padding:const EdgeInsets.all(20),child:Column(mainAxisAlignment:MainAxisAlignment.center,children:[GestureDetector(onTap:()=>setState(()=>_showBack=!_showBack),child:Container(width:double.infinity,padding:const EdgeInsets.all(28),decoration:BoxDecoration(color:_showBack?kParchment:kPaper,borderRadius:BorderRadius.circular(18),boxShadow:shadowLevel(2)),child:Column(children:[Text(_showBack?"答案":"问题",style:const TextStyle(color:kClay)),const SizedBox(height:16),Text(_showBack?(_card!["back"]??""):(_card!["front"]??""),textAlign:TextAlign.center,style:const TextStyle(fontSize:24,fontWeight:FontWeight.w900,height:1.4)),if(!_showBack&&(_card!["hint"]??"").toString().isNotEmpty)...[const SizedBox(height:12),Text("提示：${_card!["hint"]}",style:const TextStyle(color:kClay))],])),),const SizedBox(height:18),if(!_showBack)OutlinedButton(onPressed:()=>setState(()=>_showBack=true),child:const Text("翻开答案"))else Row(children:[Expanded(child:OutlinedButton(onPressed:()=>_rate(1),child:const Text("忘了"))),const SizedBox(width:8),Expanded(child:OutlinedButton(onPressed:()=>_rate(2),child:const Text("模糊"))),const SizedBox(width:8),Expanded(child:FilledButton(onPressed:()=>_rate(4),style:FilledButton.styleFrom(backgroundColor:kForest),child:const Text("掌握")))])]));}
  @override void dispose(){_frontC.dispose();_backC.dispose();super.dispose();}
}
class SchoolComparePage extends StatefulWidget{const SchoolComparePage({super.key});@override State<SchoolComparePage>createState()=>_SchoolComparePageState();}
class _SchoolComparePageState extends State<SchoolComparePage>{List _schools=[],_selected=[];Map? _compare;bool _loading=true;@override void initState(){super.initState();_load();}Future<void> _load()async{try{final r=await Api.getSchools(page:1);_schools=(r['schools']as List?)??[];}catch(_){}if(mounted)setState(()=>_loading=false);}Future<void> _run()async{try{_compare=await Api.compareSchools(_selected.map((e)=>e['id'].toString()).toList());}catch(e){if(mounted)ScaffoldMessenger.of(context).showSnackBar(SnackBar(content:Text(e.toString())));}if(mounted)setState((){});}@override Widget build(BuildContext c)=>Scaffold(appBar:AppBar(title:const Text('院校对比')),body:_loading?const Center(child:CircularProgressIndicator(color:kForest)):ListView(padding:const EdgeInsets.all(20),children:[Wrap(spacing:8,runSpacing:8,children:[for(final s in _selected)Chip(label:Text(s['name']??''),onDeleted:()=>setState(()=>_selected.remove(s)))]),FilledButton.icon(onPressed:_selected.length>=2?_run:null,icon:const Icon(Icons.compare_arrows),label:const Text('开始对比'),style:FilledButton.styleFrom(backgroundColor:kForest)),const SizedBox(height:14),if(_compare!=null)_compareTable(),const Divider(height:28),const Text('添加院校',style:TextStyle(fontWeight:FontWeight.w900)),for(final s in _schools.take(30))ListTile(title:Text(s['name']??''),subtitle:Text('${s['province']??''} · ${(s['tags']as List?)?.join('/')??''}'),trailing:Icon(_selected.contains(s)?Icons.check_circle:Icons.add_circle_outline,color:kForest),onTap:()=>setState((){if(_selected.contains(s)){_selected.remove(s);}else if(_selected.length<3){_selected.add(s);}}))]));Widget _compareTable(){final ss=(_compare?['schools']as List?)??[];return Container(padding:const EdgeInsets.all(14),decoration:BoxDecoration(color:kPaper,borderRadius:BorderRadius.circular(14),boxShadow:shadowLevel(1)),child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[const Text('对比结果',style:TextStyle(fontWeight:FontWeight.w900)),const SizedBox(height:10),for(final s in ss)Container(margin:const EdgeInsets.only(bottom:10),padding:const EdgeInsets.all(12),decoration:BoxDecoration(color:kParchment,borderRadius:BorderRadius.circular(10)),child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[Text(s['name']??'',style:const TextStyle(fontWeight:FontWeight.w900)),Text('${s['city']??''} · ${s['schoolType']??''} · 专业数${s['programCount']??0}'),Text('最新复试线：${(s['latestLine']??{})['total']??'暂无'}')]))]));}
}
