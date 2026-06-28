part of xinan_dawang;

// ======================== Register Flow ========================
enum StudyStyle { fast, steady, slow }
String styleLabel(StudyStyle s) => const {'fast':'速战速决','steady':'稳扎稳打','slow':'慢慢来'}[s.name]!;
String styleDesc(StudyStyle s) => const {'fast':'集中火力，高强度短期冲刺','steady':'按部就班，半年到一年系统备考','slow':'细水长流，拉长战线从容准备'}[s.name]!;

class RegisterFlow extends StatefulWidget {
  final ValueChanged<Map> onDone;
  const RegisterFlow({super.key,required this.onDone});
  @override State<RegisterFlow> createState() => _RegisterFlowState();
}
class _RegisterFlowState extends State<RegisterFlow> {
  final _pc=PageController(); int _step=0; bool _anim=false,_loading=false;
  final _did=TextEditingController(),_nick=TextEditingController(),_pw=TextEditingController(),_phone=TextEditingController();
  bool _didOk=false,_checkingDid=false; String? _didErr;
  String _ugProvince='',_ugSchool='',_grade='',_major='';
  bool _hasTarget=false,_ugPrivate=false; String? _target,_direction,_progress,_score; StudyStyle _style=StudyStyle.steady;

  @override void initState(){super.initState();WidgetsBinding.instance.addPostFrameCallback((_)=>setState(()=>_anim=true));}
  void _next(){
    if (_step == 0) {
      final did = _did.text.trim();
      if (did.length < 4 || did.length > 15) { _showErr('大王号需要4-15个字符'); return; }
      if (_checkingDid) { _showErr('正在检查大王号，请稍等'); return; }
      if (!_didOk) { _showErr(_didErr ?? '请先填写可用的大王号'); return; }
      if (_nick.text.trim().isEmpty) { _showErr('请填写昵称'); return; }
      if (_pw.text.length < 6) { _showErr('密码至少6位'); return; }
    }
    if (_step == 1) {
      final phone = _phone.text.trim();
      if (phone.isNotEmpty && phone.length != 11) { _showErr('手机号需要11位，或留空跳过'); return; }
    }
    if(_step<8){_pc.nextPage(duration:const Duration(milliseconds:500),curve:Curves.easeInOut);setState(()=>_step++);}
  }
  void _prev(){if(_step>0){_pc.previousPage(duration:const Duration(milliseconds:400),curve:Curves.easeInOut);setState(()=>_step--);}}
  void _showErr(String msg) { ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(msg), duration: const Duration(seconds: 2))); }

  Future<void> _checkDid() async {
    final t=_did.text.trim();
    if(t.length<4||t.length>15){setState((){_didOk=false;_checkingDid=false;_didErr=null;});return;}
    setState((){_checkingDid=true;_didOk=false;_didErr=null;});
    try{final r=await Api.checkDawangId(t);if(mounted)setState((){_didOk=r['available']==true;_didErr=_didOk?null:'该大王号已被占用';});}catch(_){if(mounted)setState(()=>_didErr='网络错误请重试');}
    if(mounted)setState(()=>_checkingDid=false);
  }

  Future<void> _finish() async {
    if(_loading)return;setState(()=>_loading=true);
    try{
      final body={'dawang_id':_did.text.trim(),'nickname':_nick.text.trim(),'username':_did.text.trim(),'password':_pw.text.trim(),
        'phone':_phone.text.trim().isNotEmpty?_phone.text.trim():null,'grade':_grade.isNotEmpty?_grade:null,'major':_major.isNotEmpty?_major:null,
        'hasTarget':_hasTarget,'targetSchool':_target,'direction':_direction,'currentProgress':_progress,'estimatedScore':_score,
        'studyStyle':_style.name,'undergradProvince':_ugProvince.isNotEmpty?_ugProvince:null,'undergradSchool':_ugSchool.isNotEmpty?_ugSchool:null,
        'undergradPrivate':_ugPrivate};
      final r=await Api.register(body);
      try{await Api.generateAiSummary();}catch(_){}
      widget.onDone(r);
    }on ApiError catch(e){if(mounted)ScaffoldMessenger.of(context).showSnackBar(SnackBar(content:Text(e.message)));}
    catch(_){if(mounted)ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content:Text('网络连接失败')));}
    setState(()=>_loading=false);
  }

  @override Widget build(BuildContext c)=>Scaffold(body:SafeArea(child:Column(children:[
    Padding(padding:const EdgeInsets.fromLTRB(24,16,24,0),child:Row(children:[if(_step>0)IconButton(icon:const Icon(Icons.arrow_back),onPressed:_prev,iconSize:20),const Spacer(),Text('${_step+1}/9',style:const TextStyle(color:kClay,fontSize:13))])),
    Expanded(child:PageView(controller:_pc,physics:const NeverScrollableScrollPhysics(),children:[_s0(),_s1(),_s2(),_s3(),_s4(),_s5(),_s6(),_s7(),_s8()])),
  ])));

  Widget _wrap(Widget? icon,String t,String sub,Widget body,{bool anim=false,bool expand=false})=>Padding(padding:const EdgeInsets.symmetric(horizontal:24),child:expand?Column(crossAxisAlignment:CrossAxisAlignment.start,children:[const SizedBox(height:20),if(icon!=null)icon,if(icon!=null)const SizedBox(height:16),Text(t,style:const TextStyle(fontSize:26,fontWeight:FontWeight.w800,color:kInk)),if(sub.isNotEmpty)const SizedBox(height:6),Text(sub,style:const TextStyle(fontSize:14,color:kClay)),const SizedBox(height:16),Expanded(child:body)]):SingleChildScrollView(child:AnimatedOpacity(opacity:_anim?1:0,duration:Duration(milliseconds:anim?1000:300),child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[const SizedBox(height:20),if(icon!=null)icon,if(icon!=null)const SizedBox(height:16),Text(t,style:const TextStyle(fontSize:26,fontWeight:FontWeight.w800,color:kInk)),if(sub.isNotEmpty)const SizedBox(height:6),Text(sub,style:const TextStyle(fontSize:14,color:kClay)),const SizedBox(height:24),body]))));
  final _btn=FilledButton.styleFrom(backgroundColor:kForest,padding:const EdgeInsets.symmetric(vertical:14),shape:RoundedRectangleBorder(borderRadius:BorderRadius.circular(10)));

  Widget _s0()=>_wrap(null,'创建大王号','大王号是你在西南大王的唯一标识，4-15字符，用于添加好友',Column(children:[
    TextField(controller:_did,onChanged:(_)=>_checkDid(),decoration:InputDecoration(labelText:'大王号',prefixIcon:const Icon(Icons.tag),
      suffixIcon:_checkingDid?const SizedBox(width:20,height:20,child:Center(child:SizedBox(width:18,height:18,child:CircularProgressIndicator(strokeWidth:2)))):_didOk?const Icon(Icons.check_circle,color:kForest):_did.text.trim().length>=4?const Icon(Icons.cancel,color:kRed):null,
      helperText:_didErr??'4-15个字符，英文字母或数字',helperStyle:TextStyle(color:_didErr!=null?kRed:kClay))),
    const SizedBox(height:14),
    TextField(controller:_nick,decoration:const InputDecoration(labelText:'昵称',prefixIcon:Icon(Icons.face),helperText:'对外展示的名字')),
    const SizedBox(height:14),
    TextField(controller:_pw,obscureText:true,decoration:const InputDecoration(labelText:'密码（至少6位）',prefixIcon:Icon(Icons.lock_outline))),
    const SizedBox(height:24),
    FilledButton(onPressed: _next, style: _btn, child: const Text('下一步')),
  ]));

  Widget _s1()=>_wrap(null,'绑定手机号','用于找回密码，可不填',Column(children:[
    TextField(controller:_phone,keyboardType:TextInputType.phone,maxLength:11,decoration:const InputDecoration(labelText:'手机号（选填）',prefixIcon:Icon(Icons.phone_android))),const SizedBox(height:24),
    FilledButton(onPressed:_next,style:_btn,child:const Text('下一步')),
  ]));

  Widget _s2()=>_wrap(null,'本科院校','选择你在云贵川渝的本科院校',Column(children:[
    if(_ugProvince.isEmpty)Column(children:[for(final p in ['重庆','四川','云南','贵州'])ListTile(title:Text(p),leading:const Icon(Icons.location_on_outlined,color:kForest),onTap:()=>setState(()=>_ugProvince=p),shape:RoundedRectangleBorder(borderRadius:BorderRadius.circular(8)))]),
    if(_ugProvince.isNotEmpty&&_ugSchool.isEmpty)...[
      ListTile(title:Text('省份: $_ugProvince',style:const TextStyle(fontWeight:FontWeight.w700)),leading:const Icon(Icons.check_circle,color:kForest),trailing:TextButton(onPressed:()=>setState((){_ugProvince='';}),child:const Text('重选'))),
      FutureBuilder<Map>(future:Api.getUndergradSchools(_ugProvince),builder:(c,snap){
        if(!snap.hasData)return const Center(child:CircularProgressIndicator(color:kForest));
        final schools=(snap.data!['schools']?[_ugProvince]??[]) as List;
        return Column(children:schools.map((s)=>ListTile(title:Text(s['name']??''),subtitle:Text('${s['city']??''} · ${s['type']??''}'),onTap:(){setState(()=>_ugSchool=s['name']??'');},shape:RoundedRectangleBorder(borderRadius:BorderRadius.circular(8)))).toList());
      }),
    ],
    if(_ugSchool.isNotEmpty)...[
      ListTile(title:Text(_ugSchool,style:const TextStyle(fontWeight:FontWeight.w700)),subtitle:Text(_ugProvince),
        leading:const Icon(Icons.school,color:kForest),trailing:TextButton(onPressed:()=>setState((){_ugSchool='';}),child:const Text('重选'))),
      SwitchListTile(title:const Text('保密我的本科院校'),value:_ugPrivate,onChanged:(v)=>setState(()=>_ugPrivate=v)),
      const SizedBox(height:16),FilledButton(onPressed:_next,style:_btn,child:const Text('下一步')),
    ],
  ]));

  Widget _s3()=>_wrap(null,'您目前大几？','',Column(children:[
    for(final x in ['大一','大二','大三','大四 / 应届','已毕业 / 往届生'])Padding(padding:const EdgeInsets.only(bottom:10),child:ListTile(title:Text(x,style:TextStyle(fontWeight:FontWeight.w600,fontSize:16,color:_grade==x?kForest:kInk)),leading:Container(width:22,height:22,decoration:BoxDecoration(shape:BoxShape.circle,color:_grade==x?kForest:Colors.transparent,border:Border.all(color:_grade==x?kForest:kMist,width:2)),child:_grade==x?const Icon(Icons.check,size:13,color:Colors.white):null),onTap:(){_grade=x;_next();},shape:RoundedRectangleBorder(borderRadius:BorderRadius.circular(10)),tileColor:_grade==x?kParchment:kPaper)),
  ]));

  Widget _s4()=>_wrap(null,'专业方向','选择你的考研学科方向',Column(children:[
    Expanded(child:FutureBuilder<List>(future:Api.getSubjectTree(),builder:(c,snap){
      if(!snap.hasData)return const Center(child:CircularProgressIndicator(color:kForest));
      return ListView(children:snap.data!.map((cat)=>ExpansionTile(title:Text(cat['name']??'',style:const TextStyle(fontWeight:FontWeight.w700)),children:(cat['children']as List?)?.map((ch)=>ListTile(title:Text(ch['name']??''),onTap:(){setState(()=>_major=(ch['name']??''));_next();})).toList()??[])).toList());
    })),
  ]),expand:true);

  Widget _s5()=>_wrap(null,'目标院校','设定考研目标院校（可在择校页面随时更改）',Column(children:[
    ListTile(title:const Text('有明确目标院校'),leading:const Icon(Icons.school_outlined,color:kForest),onTap:(){_hasTarget=true;_next();},shape:RoundedRectangleBorder(borderRadius:BorderRadius.circular(8))),
    ListTile(title:const Text('还没有，帮我推荐'),leading:const Icon(Icons.search_outlined,color:kClay),onTap:(){_hasTarget=false;_next();},shape:RoundedRectangleBorder(borderRadius:BorderRadius.circular(8))),
  ]));

  Widget _s6()=>_hasTarget?_targetPicker():_wrap(null,'考研方向与现状','',Column(children:[
    _q('想报考的方向？',['计算机/软件/AI','电子信息/通信','数学/物理','文科/教育','经管/金融','不确定'],_direction??'',(v)=>_direction=v),
    const SizedBox(height:20),_q('当前备考进度？',['还没开始','刚开始了解','已确定院校','专业课也开始了','已进入刷题阶段'],_progress??'',(v)=>_progress=v),
    const SizedBox(height:20),_q('预估当前水平？',['基础薄弱','有一定基础','基础较好','基础扎实'],_score??'',(v)=>_score=v),
    const SizedBox(height:24),FilledButton(onPressed:_direction!=null&&_progress!=null&&_score!=null?_next:null,style:_btn,child:const Text('下一步')),
  ]));

  Widget _targetPicker()=>_wrap(null,'选择目标院校','',Column(children:[
    Expanded(child:FutureBuilder<Map>(future:Api.getSchools(page:1),builder:(c,snap){
      if(!snap.hasData)return const Center(child:CircularProgressIndicator(color:kForest));
      final schools=(snap.data!['schools'] as List?)??[];
      return ListView(children:schools.map((s)=>ListTile(title:Text(s['name']??''),subtitle:Text('${s['province']??''} · ${(s['tags'] as List?)?.join(',')??''}'),onTap:(){setState(()=>_target=s['name']);_next();})).toList());
    })),
  ]),expand:true);

  Widget _s7()=>_wrap(null,'您想怎么备考？','选择备考节奏',Column(children:[
    for(final s in [{'k':'fast','l':'速战速决','d':'集中火力，高强度短期冲刺'},{'k':'steady','l':'稳扎稳打','d':'按部就班，半年到一年系统备考'},{'k':'slow','l':'慢慢来','d':'细水长流，拉长战线从容准备'}])
      Container(margin:const EdgeInsets.only(bottom:12),child:ListTile(contentPadding:const EdgeInsets.symmetric(horizontal:16,vertical:8),title:Text(s['l']!,style:TextStyle(fontWeight:FontWeight.w700,fontSize:17,color:_style.name==s['k']?kForest:kInk)),subtitle:Text(s['d']!,style:const TextStyle(fontSize:13,color:kClay)),leading:Container(width:24,height:24,decoration:BoxDecoration(shape:BoxShape.circle,color:_style.name==s['k']?kForest:Colors.transparent,border:Border.all(color:_style.name==s['k']?kForest:kMist,width:2)),child:_style.name==s['k']?const Icon(Icons.check,size:14,color:Colors.white):null),onTap:()=>setState((){_style=s['k']=='fast'?StudyStyle.fast:s['k']=='slow'?StudyStyle.slow:StudyStyle.steady;}),shape:RoundedRectangleBorder(borderRadius:BorderRadius.circular(12)),tileColor:_style.name==s['k']?kParchment:kPaper)),
    const SizedBox(height:16),FilledButton(onPressed:_next,style:_btn,child:const Text('下一步')),
  ]));

  Widget _s8()=>_wrap(const Icon(Icons.auto_awesome,color:kBrass,size:48),'准备完毕！','AI将为你分析考研方向并提供个性化推荐',Column(children:[
    const SizedBox(height:8),const Text('注册完成后AI将分析你的考研方向',style:TextStyle(color:kClay,fontSize:14)),const SizedBox(height:32),
    FilledButton(onPressed:_loading?null:_finish,style:_btn,child:Text(_loading?'注册中…':'完成注册，开启考研之旅')),
  ]),anim:true);

  Widget _q(String t,List<String> o,String cur,ValueChanged<String> on)=>Column(crossAxisAlignment:CrossAxisAlignment.start,children:[Text(t,style:const TextStyle(fontSize:14,fontWeight:FontWeight.w600,color:kInk)),const SizedBox(height:8),Wrap(spacing:8,runSpacing:8,children:o.map((x)=>GestureDetector(onTap:(){setState(()=>on(x));},child:Container(padding:const EdgeInsets.symmetric(horizontal:14,vertical:8),decoration:BoxDecoration(color:cur==x?kForest:kPaper,borderRadius:BorderRadius.circular(20),border:Border.all(color:cur==x?kForest:kMist)),child:Text(x,style:TextStyle(fontSize:13,color:cur==x?Colors.white:kClay,fontWeight:cur==x?FontWeight.w600:FontWeight.w400))))).toList())]);

  @override void dispose(){_did.dispose();_nick.dispose();_pw.dispose();_phone.dispose();_pc.dispose();super.dispose();}
}



