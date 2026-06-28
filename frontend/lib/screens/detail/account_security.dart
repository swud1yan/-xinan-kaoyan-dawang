part of xinan_dawang;

class AccountSecurityPage extends StatefulWidget{final Map user;const AccountSecurityPage({super.key,required this.user});@override State<AccountSecurityPage>createState()=>_AccountSecurityPageState();}
class _AccountSecurityPageState extends State<AccountSecurityPage>{
  @override Widget build(BuildContext c)=>Scaffold(appBar:AppBar(title:const Text('账号安全')),body:ListView(children:[
    ListTile(title:const Text('修改密码'),subtitle:const Text('输入原密码后设置新密码'),onTap:_changePw),
    ListTile(title:const Text('修改大王号'),subtitle:Text('当前: ${widget.user['dawangId']??''}（每月限一次）'),onTap:_changeDid),
  ]));
  void _changePw(){final o=TextEditingController(),n=TextEditingController();showDialog(context:context,builder:(c)=>AlertDialog(title:const Text('修改密码'),content:Column(mainAxisSize:MainAxisSize.min,children:[TextField(controller:o,obscureText:true,decoration:const InputDecoration(labelText:'原密码')),const SizedBox(height:8),TextField(controller:n,obscureText:true,decoration:const InputDecoration(labelText:'新密码（至少6位）'))]),actions:[TextButton(onPressed:()=>Navigator.pop(c),child:const Text('取消')),TextButton(onPressed:()async{try{await Api.changePassword(o.text,n.text);if(mounted){Navigator.pop(c);ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content:Text('密码已修改')));}}catch(e){ScaffoldMessenger.of(context).showSnackBar(SnackBar(content:Text(e.toString())));}},child:const Text('确认'))]));}
  void _changeDid(){final ctrl=TextEditingController();showDialog(context:context,builder:(c)=>AlertDialog(title:const Text('修改大王号'),content:Column(mainAxisSize:MainAxisSize.min,children:[TextField(controller:ctrl,decoration:const InputDecoration(labelText:'新大王号（4-15字符）',helperText:'每月只能修改一次'))]),actions:[TextButton(onPressed:()=>Navigator.pop(c),child:const Text('取消')),TextButton(onPressed:()async{try{await Api.changeDawangId(ctrl.text);if(mounted){Navigator.pop(c);ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content:Text('大王号已修改')));}}catch(e){ScaffoldMessenger.of(context).showSnackBar(SnackBar(content:Text(e.toString())));}},child:const Text('确认'))]));}
}

