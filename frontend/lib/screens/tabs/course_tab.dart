part of xinan_dawang;

// ======================== Tab 2: Course + Exam ========================
class CourseExamTab extends StatefulWidget {final Map user;const CourseExamTab({super.key,required this.user});@override State<CourseExamTab>createState()=>_CourseExamTabState();}
class _CourseExamTabState extends State<CourseExamTab>{int _sub=0;
  @override Widget build(BuildContext c)=>SingleChildScrollView(padding:const EdgeInsets.only(bottom:32),child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[
    Hdr(t:'专业课与真题',s:widget.user['targetSchool']!=null?'目标: ${widget.user['targetSchool']}':'考研科目与历年真题'),
    Padding(padding:const EdgeInsets.fromLTRB(20,0,20,14),child:GridView.count(crossAxisCount:2,shrinkWrap:true,physics:const NeverScrollableScrollPhysics(),mainAxisSpacing:10,crossAxisSpacing:10,childAspectRatio:2.8,children:[
      _tool(Icons.timer_outlined,'番茄钟',()=>Navigator.of(context).push(MaterialPageRoute(builder:(_)=>const PomodoroPage()))),
      _tool(Icons.quiz_outlined,'每日一题',()=>Navigator.of(context).push(MaterialPageRoute(builder:(_)=>const DailyQuestionPage()))),
      _tool(Icons.fact_check_outlined,'错题本',()=>Navigator.of(context).push(MaterialPageRoute(builder:(_)=>const ErrorNotebookPage()))),
      _tool(Icons.style_outlined,'记忆闪卡',()=>Navigator.of(context).push(MaterialPageRoute(builder:(_)=>const FlashcardsPage()))),
      _tool(Icons.assignment_outlined,'模拟考试',()=>Navigator.of(context).push(MaterialPageRoute(builder:(_)=>const MockExamPage()))),
      _tool(Icons.record_voice_over_outlined,'AI复试面试',()=>Navigator.of(context).push(MaterialPageRoute(builder:(_)=>InterviewPage(user:widget.user)))),
    ])),
    Padding(padding:const EdgeInsets.symmetric(horizontal:20),child:Row(children:[
      Expanded(child:FilterChip(label:const Text('专业课'),selected:_sub==0,onSelected:(_)=>setState(()=>_sub=0))),
      Expanded(child:FilterChip(label:const Text('公共课真题'),selected:_sub==1,onSelected:(_)=>setState(()=>_sub=1))),
      if(widget.user['hasTarget']==true)Expanded(child:FilterChip(label:const Text('目标院校专业课'),selected:_sub==2,onSelected:(_)=>setState(()=>_sub=2))),
    ])),
    if(_sub==0)...[_courseCard('408计算机学科专业基础综合','全国统考',['数据结构','计算机组成原理','操作系统','计算机网络'],['《数据结构》严蔚敏','《计算机组成原理》唐朔飞','《计算机操作系统》汤子瀛','《计算机网络》谢希仁'],'满分150分，选择题80分+综合题70分'),_courseCard('思想政治理论','全国统考',['马原','毛中特','史纲','思修法基'],['《大纲解析》','《肖秀荣1000题》','《肖八》','《肖四》'],'满分100分'),_courseCard('英语一','全国统考',['完形填空','阅读理解','新题型','翻译','写作'],['《红宝书》','《张剑黄皮书》','《王江涛写作》'],'满分100分'),_courseCard('数学一','全国统考',['高等数学(60%)','线性代数(20%)','概率论(20%)'],['《高等数学》同济版','《线性代数》同济版','《概率论》浙大版','《李永乐复习全书》'],'满分150分')],
    if(_sub==1)_examList(),if(_sub==2)_examList(),
  ]));
  Widget _tool(IconData icon,String text,VoidCallback onTap)=>InkWell(onTap:onTap,borderRadius:BorderRadius.circular(12),child:Container(padding:const EdgeInsets.symmetric(horizontal:12),decoration:BoxDecoration(color:kParchment,borderRadius:BorderRadius.circular(12),border:Border.all(color:kMist)),child:Row(children:[Icon(icon,color:kForest,size:20),const SizedBox(width:8),Expanded(child:Text(text,style:const TextStyle(fontWeight:FontWeight.w800)))])));
  Widget _courseCard(String n, String tp, List<String> top, List<String> bks, String desc) {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 20, vertical: 6),
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(color: kPaper, borderRadius: BorderRadius.circular(14), boxShadow: [BoxShadow(color: kForest.withAlpha(10), blurRadius: 6, offset: Offset(0, 2))]),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Expanded(child: Text(n, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 17))),
          Container(padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3), decoration: BoxDecoration(color: kParchment, borderRadius: BorderRadius.circular(4)), child: Text(tp, style: const TextStyle(fontSize: 12, color: kBrass))),
        ]),
        const SizedBox(height: 10),
        Text(desc, style: const TextStyle(fontSize: 13, color: kClay)),
        const SizedBox(height: 10),
        Wrap(spacing: 6, children: top.map((t) => Container(padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5), decoration: BoxDecoration(color: kParchment, borderRadius: BorderRadius.circular(6)), child: Text(t, style: const TextStyle(fontSize: 13)))).toList()),
        const SizedBox(height: 12),
        const Text('推荐书目', style: TextStyle(fontWeight: FontWeight.w600, color: kForest)),
        ...bks.map((b) => Padding(padding: const EdgeInsets.only(bottom: 4), child: Row(children: [const Icon(Icons.menu_book_outlined, size: 15, color: kBrass), const SizedBox(width: 8), Text(b, style: const TextStyle(fontSize: 13))]))),
      ]),
    );
  }
  Widget _examList() {
    return FutureBuilder<List>(
      future: Api.getExamPapers(),
      builder: (c, snap) {
        if (!snap.hasData) return const SkeletonList(count: 4);
        final papers = snap.data!;
        if (papers.isEmpty) return const EmptyState(icon: Icons.description_outlined, title: '该科目暂无真题', subtitle: '稍后再来看看，或联系管理员补充资料');
        final years = <int, List>{};
        for (final p in papers) {
          final y = (p['year'] as int?) ?? 0;
          years[y] = years[y] ?? [];
          years[y]!.add(p);
        }
        final ys = years.keys.toList()..sort((a, b) => b.compareTo(a));
        final children = <Widget>[];
        for (final y in ys) {
          children.add(Padding(padding: const EdgeInsets.fromLTRB(20, 12, 20, 8), child: Text('$y 年', style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700))));
          for (final p in years[y]!) {
            children.add(Container(
              margin: const EdgeInsets.symmetric(horizontal: 20, vertical: 3),
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(color: kPaper, borderRadius: BorderRadius.circular(10), boxShadow: [BoxShadow(color: kForest.withAlpha(10), blurRadius: 6, offset: Offset(0, 2))]),
              child: InkWell(
                onTap: () => _showDetail(p),
                child: Row(children: [
                  Container(width: 38, height: 38, decoration: BoxDecoration(color: kParchment, borderRadius: BorderRadius.circular(8)), child: Center(child: Text((p['subject'] ?? '').toString().length > 4 ? p['subject'].toString().substring(0, 3) : (p['subject'] ?? ''), style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: kForest)))),
                  const SizedBox(width: 12),
                  Expanded(child: Text(p['title'] ?? '', style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600))),
                  if (p['hasAnswer'] == true) Container(padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2), decoration: BoxDecoration(color: kParchment, borderRadius: BorderRadius.circular(4)), child: const Text('含答案', style: TextStyle(fontSize: 11, color: kForest))),
                  const Icon(Icons.chevron_right, color: kClay),
                ]),
              ),
            ));
          }
        }
        return Column(crossAxisAlignment: CrossAxisAlignment.start, children: children);
      },
    );
  }
  void _showDetail(Map p) async {
    Map? d;
    try { d = await Api.getExamDetail(p['id'] ?? ''); } catch (_) {}
    if (!mounted) return;
    showDialog(
      context: context,
      builder: (c) {
        final w = <Widget>[
          Text(p['title'] ?? '', style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
          const Divider(height: 24),
        ];
        if (d != null && d!['content'] != null) {
          w.add(const Text('【题目内容】', style: TextStyle(fontWeight: FontWeight.w700, color: kForest)));
          w.add(const SizedBox(height: 8));
          w.add(Text(d!['content'] ?? '', style: const TextStyle(height: 1.6)));
        }
        if (d != null && d!['answer'] != null) {
          w.add(const SizedBox(height: 16));
          w.add(const Text('【答案与解析】', style: TextStyle(fontWeight: FontWeight.w700, color: kBrass)));
          w.add(const SizedBox(height: 8));
          w.add(Text(d!['answer'] ?? '', style: const TextStyle(height: 1.6)));
        }
        return Dialog(
          child: Container(
            constraints: const BoxConstraints(maxWidth: 600, maxHeight: 500),
            padding: const EdgeInsets.all(20),
            child: SingleChildScrollView(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: w)),
          ),
        );
      },
    );
  }
}



