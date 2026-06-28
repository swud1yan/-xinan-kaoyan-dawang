part of xinan_dawang;

// ======================== Auth Gate ========================
class AuthGate extends StatefulWidget {
  final ValueChanged<Map> onLogin;
  const AuthGate({super.key,required this.onLogin});
  @override State<AuthGate> createState() => _AuthGateState();
}
class _AuthGateState extends State<AuthGate> {
  bool _reg=false, _forgot=false;
  @override Widget build(BuildContext c) {
    if (_forgot) return ForgotPasswordPage(onBack:()=>setState(()=>_forgot=false));
    if (_reg) return RegisterFlow(onDone:(r){widget.onLogin(r);});
    return LoginPage(onLogin:(r){widget.onLogin(r);},onReg:()=>setState(()=>_reg=true),onForgot:()=>setState(()=>_forgot=true));
  }
}


