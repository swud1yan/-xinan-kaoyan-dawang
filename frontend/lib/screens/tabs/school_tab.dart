part of xinan_dawang;

// ======================== Tab 1: Schools ========================
class SchoolTab extends StatefulWidget {final Map user;final VoidCallback? onUserChanged;const SchoolTab({super.key,required this.user,this.onUserChanged});@override State<SchoolTab>createState()=>_SchoolTabState();}
class _SchoolTabState extends State<SchoolTab>{
  String? _province,_tag,_search; List _schools=[]; bool _loading=true; int _page=1;
  Map? _me; List<String> _quotes = ['日拱一卒，功不唐捐', '考研不是因为有希望才坚持，而是坚持了才有希望', '每一个优秀的人都有一段沉默的时光', '你背不下来的书，总有人能背下来', '今天也是离梦想更近的一天', '乾坤未定，你我皆是黑马', '星光不问赶路人，时光不负有心人', '你所热爱的，终将成就你'];
  @override void initState(){super.initState();_load();_loadMe();}
  Future<void> _loadMe() async { try { _me = await Api.getMe(); if (mounted) setState(() {}); } catch (_) {} }
  Future<void> _load()async{try{final r=await Api.getSchools(province:_province,tag:_tag,search:_search,page:_page);setState((){_schools=(r['schools']as List?)??[];_loading=false;});}catch(_){setState(()=>_loading=false);}}
  String _randomQuote() => _quotes[DateTime.now().millisecondsSinceEpoch % _quotes.length];
  @override Widget build(BuildContext c){
    final user = _me ?? widget.user;
    final hasTarget = (user['targetSchool']?.toString() ?? '').isNotEmpty;
    final major = user['major']?.toString() ?? '';
    return SingleChildScrollView(padding:const EdgeInsets.only(bottom:32),child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[
    // 加油横幅
    if (hasTarget)
      Container(
        width: double.infinity, margin: const EdgeInsets.fromLTRB(20, 16, 20, 4),
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(gradient: const LinearGradient(colors: [kForest, kForestLight]), borderRadius: BorderRadius.circular(16), boxShadow: shadowLevel(2)),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('加油，${user['nickname'] ?? '考研人'}！', style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w900, color: Colors.white, height: 1.3)),
          const SizedBox(height: 4),
          Text('你一定能上岸${user['targetSchool']}${major.isNotEmpty ? ' $major' : ''}硕士研究生！', style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700, color: kBrass, height: 1.3)),
          const SizedBox(height: 8),
          Text('✨ ${_randomQuote()}', style: TextStyle(fontSize: 12, color: Colors.white.withOpacity(0.7))),
        ]),
      )
    else
      Hdr(t:'择校',s:'全国116所985/211院校'),
    if (hasTarget)
      Padding(padding: const EdgeInsets.fromLTRB(20, 12, 20, 0), child: Row(children: [
        const Icon(Icons.flag_outlined, size: 14, color: kBrass),
        const SizedBox(width: 4),
        Expanded(child: Text('择校 · 目标: ${user['targetSchool']}${major.isNotEmpty ? ' - $major' : ''}', style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: kForest))),
      ])),
    Padding(padding:const EdgeInsets.symmetric(horizontal:20),child:TextField(decoration:const InputDecoration(hintText:'搜索院校…',prefixIcon:Icon(Icons.search,color:kClay)),onChanged:(v){_search=v.isNotEmpty?v:null;_page=1;_load();})),
    const SizedBox(height:12),
    SizedBox(height:34,child:ListView(scrollDirection:Axis.horizontal,padding:const EdgeInsets.symmetric(horizontal:20),children:[for(final x in [null,'985','211','双一流','C9','北京','上海','江苏','湖北','陕西','四川'])Padding(padding:const EdgeInsets.only(right:8),child:tag(x??'全部',a:_tag==x,on:(){setState((){_tag=x;_page=1;_load();});}))])),
    const SizedBox(height:14),
    if (_loading)
      const SkeletonList(count: 5)
    else if (_schools.isEmpty)
      EmptyState(icon: Icons.account_balance_outlined, title: '没有找到匹配的院校', subtitle: '调整筛选条件后再试试', actionLabel: '清空筛选', onAction: () { setState(() { _tag = null; _search = null; _page = 1; _loading = true; }); _load(); })
    else
      for (final s in _schools) _schoolCard(s),
  ]));}

  Widget _schoolCard(Map s) {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 20, vertical: 5),
      decoration: BoxDecoration(color: kPaper, borderRadius: BorderRadius.circular(14), boxShadow: [BoxShadow(color: kForest.withAlpha(10), blurRadius: 6, offset: Offset(0, 2))]),
      child: ListTile(
        contentPadding: const EdgeInsets.fromLTRB(16, 8, 8, 8),
        leading: Container(width: 40, height: 40, decoration: BoxDecoration(color: kParchment, borderRadius: BorderRadius.circular(10)), child: Center(child: Text((s['name'] ?? '').toString()[0], style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w800, color: kForest)))),
        title: Text(s['name'] ?? '', style: const TextStyle(fontWeight: FontWeight.w700)),
        subtitle: Text('${s['province'] ?? ''} · ${(s['tags'] as List?)?.join(',') ?? ''}', style: const TextStyle(fontSize: 12, color: kClay)),
        trailing: const Icon(Icons.chevron_right, color: kClay),
        onTap: () async { await Navigator.of(context).push(MaterialPageRoute(builder: (_) => SchoolDetailPage(schoolId: s['id'] ?? '', schoolName: s['name'] ?? '', userMajor: (_me ?? widget.user)['major']?.toString(), onTargetChanged: _loadMe))); _loadMe(); },
      ),
    );
  }
}



