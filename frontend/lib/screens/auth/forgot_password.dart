part of xinan_dawang;

// ======================== Forgot Password ========================
class ForgotPasswordPage extends StatefulWidget {
  final VoidCallback onBack;
  const ForgotPasswordPage({super.key,required this.onBack});
  @override State<ForgotPasswordPage> createState() => _ForgotPasswordPageState();
}
class _ForgotPasswordPageState extends State<ForgotPasswordPage> {
  final _ph=TextEditingController(),_pw=TextEditingController(); String? _e,_ok; bool _b=false;
  Future<void> _go() async {
    if(_ph.text.trim().length!=11){setState(()=>_e='请输入11位手机号');return;}
    if(_pw.text.length<6){setState(()=>_e='新密码至少6位');return;}
    setState((){_b=true;_e=null;});
    try{await Api.forgotPassword(_ph.text.trim(),_pw.text.trim());setState(()=>_ok='密码已重置，请返回登录');}on ApiError catch(e){setState(()=>_e=e.message);}catch(_){setState(()=>_e='网络连接失败');}
    setState(()=>_b=false);
  }
  @override Widget build(BuildContext c)=>Scaffold(body:SafeArea(child:Center(child:SingleChildScrollView(padding:const EdgeInsets.all(24),child:Container(width:400,padding:const EdgeInsets.all(32),decoration:BoxDecoration(color:kPaper,borderRadius:BorderRadius.circular(16),border:Border.all(color:kMist)),child:Column(mainAxisSize:MainAxisSize.min,crossAxisAlignment:CrossAxisAlignment.stretch,children:[
    const Text('忘记密码',textAlign:TextAlign.center,style:TextStyle(fontSize:24,fontWeight:FontWeight.w800)),const SizedBox(height:8),
    const Text('输入注册时绑定的手机号',textAlign:TextAlign.center,style:TextStyle(color:kClay,fontSize:14)),const SizedBox(height:24),
    TextField(controller:_ph,keyboardType:TextInputType.phone,maxLength:11,decoration:const InputDecoration(labelText:'手机号',prefixIcon:Icon(Icons.phone_android))),
    const SizedBox(height:12),
    TextField(controller:_pw,obscureText:true,decoration:const InputDecoration(labelText:'新密码',prefixIcon:Icon(Icons.lock_outline))),
    if(_e!=null)Padding(padding:const EdgeInsets.only(top:12),child:Text(_e!,style:const TextStyle(color:kRed))),
    if(_ok!=null)Padding(padding:const EdgeInsets.only(top:12),child:Text(_ok!,style:const TextStyle(color:kForest))),
    const SizedBox(height:24),
    FilledButton(onPressed:_b?null:_go,style:FilledButton.styleFrom(backgroundColor:kForest,padding:const EdgeInsets.symmetric(vertical:14),shape:RoundedRectangleBorder(borderRadius:BorderRadius.circular(10))),child:Text(_b?'处理中…':'重置密码',style:const TextStyle(fontSize:16))),
    const SizedBox(height:12),
    OutlinedButton(onPressed:widget.onBack,style:OutlinedButton.styleFrom(padding:const EdgeInsets.symmetric(vertical:14),shape:RoundedRectangleBorder(borderRadius:BorderRadius.circular(10))),child:const Text('返回登录',style:TextStyle(fontSize:16,color:kForest))),
  ]))))));
  @override void dispose(){_ph.dispose();_pw.dispose();super.dispose();}
}


