part of xinan_dawang;

// ======================== Tab 4: Study Circle ========================
class CircleTab extends StatefulWidget{final Map user;const CircleTab({super.key,required this.user});@override State<CircleTab>createState()=>_CircleTabState();}
class _CircleTabState extends State<CircleTab>{List _posts=[];bool _loading=true;final _inp=TextEditingController();
  @override void initState(){super.initState();_load();}
  Future<void> _load()async{try{final r=await Api.getPosts();setState((){_posts=(r['posts']as List?)??[];_loading=false;});}catch(_){setState(()=>_loading=false);}}
  Future<void> _post()async{final c=_inp.text.trim();if(c.isEmpty)return;
    // Check ban/mute status first
    try {
      final me = await Api.getMe();
      if (me['isBanned'] == true) {
        final exp = me['banExpireAt'];
        final msg = exp != null ? '你的账号已被封禁至 ${exp.toString().substring(0,10)}' : '你的账号已被封禁';
        if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(msg))); return;
      }
      if (me['mutedUntil'] != null) {
        final until = DateTime.parse(me['mutedUntil']);
        if (until.isAfter(DateTime.now())) {
          if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('你已被禁言至 ${until.toString().substring(0,16)}'))); return;
        }
      }
    } catch (_) {}
    try{final p=await Api.createPost(c);setState((){_posts.insert(0,p);_inp.clear();});final xp=p['xpEarned']??0;if(xp>0&&mounted)ScaffoldMessenger.of(context).showSnackBar(SnackBar(content:Text('发布成功，+$xp经验')));}catch(e){if(mounted)ScaffoldMessenger.of(context).showSnackBar(SnackBar(content:Text(e.toString())));}}
  Future<void> _like(Map p)async{try{final r=await Api.toggleLike(p['id']??'');final i=_posts.indexOf(p);if(i>=0){final np=Map.from(_posts[i]);np['likesCount']=r['likesCount'];_posts[i]=np;setState((){});}}catch(_){}}
  void _comment(Map p) {
    showModalBottomSheet(context: context, isScrollControlled: true,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(16))),
      builder: (_) => _CommentSheet(post: p));
  }
  @override Widget build(BuildContext c) {
    final inputRow = Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(color: kPaper, borderRadius: BorderRadius.circular(14), boxShadow: [BoxShadow(color: kForest.withAlpha(10), blurRadius: 6, offset: Offset(0, 2))]),
      child: Row(children: [
        Container(width: 36, height: 36, decoration: BoxDecoration(color: kParchment, borderRadius: BorderRadius.circular(18)), child: const Icon(Icons.edit_outlined, size: 18, color: kClay)),
        const SizedBox(width: 10),
        Expanded(child: TextField(controller: _inp, decoration: const InputDecoration(hintText: '分享你的考研动态…', border: InputBorder.none, contentPadding: EdgeInsets.symmetric(vertical: 8)), onSubmitted: (_) => _post())),
        GestureDetector(onTap: _post, child: Container(padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6), decoration: BoxDecoration(color: kForest, borderRadius: BorderRadius.circular(8)), child: const Text('发布', style: TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.w600)))),
      ]),
    );
    return SingleChildScrollView(padding: const EdgeInsets.only(bottom: 32), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Hdr(t: '研友圈', s: '考研人的互助社区'),
      Padding(padding: const EdgeInsets.fromLTRB(20, 0, 20, 12), child: inputRow),
      if (_loading) const SkeletonList(count: 4)
      else if (_posts.isEmpty) EmptyState(icon: Icons.groups_outlined, title: '还没有人发帖', subtitle: '发布第一条动态，给后来的人点亮一点路', actionLabel: '发布第一条动态', onAction: _post)
      else for (final p in _posts) _postCard(p),
    ]));
  }
  Widget _postCard(Map p) {
    final author = (p['author'] ?? {}) as Map;
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 20, vertical: 5),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(color: kPaper, borderRadius: BorderRadius.circular(14), boxShadow: [BoxShadow(color: kForest.withAlpha(10), blurRadius: 6, offset: Offset(0, 2))]),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          GestureDetector(onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => UserProfilePage(userId: author['id']?.toString() ?? ''))), child: Container(width: 36, height: 36, decoration: BoxDecoration(color: kParchment, borderRadius: BorderRadius.circular(10)), child: Center(child: Text((author['username'] ?? '?').toString()[0], style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w700, color: kForest))))),
          const SizedBox(width: 10),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Flexible(child: Text(author['nickname'] ?? author['username'] ?? '', style: const TextStyle(fontWeight: FontWeight.w700))),
              const SizedBox(width: 6),
              userBadges(author),
            ]),
            Text(author['school'] ?? '考研人', style: const TextStyle(fontSize: 12, color: kClay)),
          ])),
        ]),
        const SizedBox(height: 12),
        Text(p['content'] ?? '', style: const TextStyle(height: 1.6)),
        const SizedBox(height: 10),
        Row(children: [
          GestureDetector(onTap: () => _like(p), child: Row(children: [const Icon(Icons.favorite_border_outlined, size: 17, color: kClay), const SizedBox(width: 4), Text('${p['likesCount'] ?? 0}', style: const TextStyle(fontSize: 13, color: kClay))])),
          const SizedBox(width: 20),
          GestureDetector(onTap: () => _comment(p), child: Row(children: [const Icon(Icons.chat_bubble_outline, size: 17, color: kClay), const SizedBox(width: 4), Text('${p['commentCount'] ?? 0}', style: const TextStyle(fontSize: 13, color: kClay))])),
        ]),
      ]),
    );
  }
  @override void dispose(){_inp.dispose();super.dispose();}
}
class _CommentSheet extends StatefulWidget{final Map post;const _CommentSheet({required this.post});@override State<_CommentSheet>createState()=>_CommentSheetState();}
class _CommentSheetState extends State<_CommentSheet>{
  List? _c;final _inp=TextEditingController();bool _loading=true;String? _replyToId,_replyToName;
  @override void initState(){super.initState();_load();}
  Future<void> _load()async{try{_c=await Api.getComments(widget.post['id']??'');}catch(_){}if(mounted)setState(()=>_loading=false);}
  void _replyTo(Map cmt){final a=cmt['author'] as Map? ?? {};final n=(a['nickname']??a['username']??'').toString();setState((){_replyToId=cmt['id']?.toString();_replyToName=n;_inp.text='回复 $n: ';});}
  void _cancelReply(){setState((){_replyToId=null;_replyToName=null;_inp.clear();});}
  Future<void> _add()async{
    final c=_inp.text.trim();if(c.isEmpty)return;
    try{
      final cmt=await Api.addComment(widget.post['id']??'',c,replyTo:_replyToId);
      setState((){_c=[...(_c??[]),cmt];_inp.clear();_replyToId=null;_replyToName=null;});
      final xp=cmt['xpEarned']??0;if(xp>0&&mounted)ScaffoldMessenger.of(context).showSnackBar(SnackBar(content:Text('评论成功，+$xp经验')));
    }catch(_){}
  }
  @override Widget build(BuildContext c){
    return Container(height:MediaQuery.of(c).size.height*0.5,padding:const EdgeInsets.all(16),child:Column(children:[
      Container(width:40,height:4,decoration:BoxDecoration(color:kMist,borderRadius:BorderRadius.circular(2))),
      const SizedBox(height:12),const Text('评论',style:TextStyle(fontWeight:FontWeight.w700,fontSize:16)),const Divider(),
      Expanded(child:_loading?const Center(child:CircularProgressIndicator(color:kForest))
        :_c==null||_c!.isEmpty?const Center(child:Text('暂无评论',style:TextStyle(color:kClay)))
        :ListView.builder(itemCount:_c!.length,itemBuilder:(_,i){
          final cmt=_c![i];final author=cmt['author'] as Map? ?? {};
          return ListTile(
            leading: GestureDetector(
              onTap: ()=>Navigator.of(context).push(MaterialPageRoute(builder:(_)=>UserProfilePage(userId:author['id']?.toString()??''))),
              child: CircleAvatar(backgroundColor:kParchment,child:Text((author['nickname']??author['username']??'?').toString()[0],style:const TextStyle(color:kForest)))),
            title: Text(author['nickname']?.toString()??author['username']?.toString()??'',style:const TextStyle(fontWeight:FontWeight.w600,fontSize:13)),
            subtitle: Text(cmt['content']??'',style:const TextStyle(fontSize:13)),
            trailing: TextButton(onPressed:()=>_replyTo(cmt),child:const Text('回复',style:TextStyle(fontSize:11))),
          );
        })),
      if(_replyToName!=null)Padding(padding:const EdgeInsets.only(bottom:4),child:Row(children:[
        Text('回复 $_replyToName',style:const TextStyle(color:kBrass,fontSize:12)),
        const SizedBox(width:8),GestureDetector(onTap:_cancelReply,child:const Icon(Icons.close,size:16,color:kClay))
      ])),
      Container(padding:const EdgeInsets.only(top:8),decoration:const BoxDecoration(border:Border(top:BorderSide(color:kMist))),child:Row(children:[
        Expanded(child:TextField(controller:_inp,decoration:const InputDecoration(hintText:'写评论…',border:InputBorder.none),onSubmitted:(_)=>_add())),
        GestureDetector(onTap:_add,child:Container(padding:const EdgeInsets.symmetric(horizontal:12,vertical:6),decoration:BoxDecoration(color:kForest,borderRadius:BorderRadius.circular(8)),child:const Text('发送',style:TextStyle(color:Colors.white,fontSize:13)))),
      ])),
    ]));
  }
  @override void dispose(){_inp.dispose();super.dispose();}
}



