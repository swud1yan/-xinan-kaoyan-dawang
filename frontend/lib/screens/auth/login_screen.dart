part of xinan_dawang;

// ======================== Login ========================
class LoginPage extends StatefulWidget {
  final ValueChanged<Map> onLogin; final VoidCallback onReg, onForgot;
  const LoginPage({super.key,required this.onLogin,required this.onReg,required this.onForgot});
  @override State<LoginPage> createState() => _LoginPageState();
}
class _LoginPageState extends State<LoginPage> {
  final _u=TextEditingController(),_p=TextEditingController(); String? _e; bool _b=false;
  Future<void> _go() async {
    if(_u.text.trim().isEmpty||_p.text.length<6){setState(()=>_e='用户名不能为空，密码至少6位');return;}
    setState((){_b=true;_e=null;});
    try{final r=await Api.login(_u.text.trim(),_p.text.trim());widget.onLogin(r);}on ApiError catch(e){setState(()=>_e=e.message);}catch(_){setState(()=>_e='网络连接失败');}
    setState(()=>_b=false);
  }
  @override Widget build(BuildContext c)=>Scaffold(body:SafeArea(child:Center(child:SingleChildScrollView(padding:const EdgeInsets.all(24),child:Container(width:400,padding:const EdgeInsets.all(32),decoration:BoxDecoration(color:kPaper,borderRadius:BorderRadius.circular(16),border:Border.all(color:kMist)),child:Column(mainAxisSize:MainAxisSize.min,crossAxisAlignment:CrossAxisAlignment.stretch,children:[
    const Icon(Icons.castle_outlined,color:kForest,size:40),const SizedBox(height:16),
    const Text('西南大王',textAlign:TextAlign.center,style:TextStyle(fontSize:28,fontWeight:FontWeight.w800,color:kInk,letterSpacing:-0.5)),
    const SizedBox(height:4),const Text('考研人的一站式伙伴',textAlign:TextAlign.center,style:TextStyle(color:kClay,fontSize:14)),
    const SizedBox(height:32),
    TextField(controller:_u,decoration:const InputDecoration(labelText:'用户名',prefixIcon:Icon(Icons.person_outline))),
    const SizedBox(height:14),
    TextField(controller:_p,obscureText:true,decoration:const InputDecoration(labelText:'密码',prefixIcon:Icon(Icons.lock_outline)),onSubmitted:(_)=>_go()),
    if(_e!=null)Padding(padding:const EdgeInsets.only(top:12),child:Text(_e!,style:const TextStyle(color:kRed,fontSize:13))),
    const SizedBox(height:24),
    FilledButton(onPressed:_b?null:_go,style:FilledButton.styleFrom(backgroundColor:kForest,padding:const EdgeInsets.symmetric(vertical:14),shape:RoundedRectangleBorder(borderRadius:BorderRadius.circular(10))),child:Text(_b?'登录中…':'登录',style:const TextStyle(fontSize:16))),
    const SizedBox(height:12),
    OutlinedButton(onPressed:widget.onReg,style:OutlinedButton.styleFrom(padding:const EdgeInsets.symmetric(vertical:14),shape:RoundedRectangleBorder(borderRadius:BorderRadius.circular(10))),child:const Text('注册新账号',style:TextStyle(fontSize:16,color:kForest))),
    TextButton(onPressed:widget.onForgot,child:const Text('忘记密码？',style:TextStyle(color:kClay))),
  ]))))));
  @override void dispose(){_u.dispose();_p.dispose();super.dispose();}
}


