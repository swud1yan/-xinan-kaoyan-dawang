part of xinan_dawang;

// ======================== App ========================
class XinanApp extends StatelessWidget {
  const XinanApp({super.key});
  @override Widget build(BuildContext c) => MaterialApp(
    debugShowCheckedModeBanner: false, title: '西南大王',
    theme: ThemeData(
      useMaterial3: true, scaffoldBackgroundColor: kParchment,
      colorScheme: ColorScheme.fromSeed(seedColor: kForest, brightness: Brightness.light),
      textTheme: const TextTheme(
        headlineMedium: TextStyle(fontSize:24,fontWeight:FontWeight.w700,letterSpacing:-0.3,height:1.2,color:kInk),
        titleLarge: TextStyle(fontSize:20,fontWeight:FontWeight.w700,height:1.25,color:kInk),
        titleMedium: TextStyle(fontSize:16,fontWeight:FontWeight.w600,height:1.3,color:kInk),
        bodyLarge: TextStyle(fontSize:15,height:1.6,color:kInk),
        bodyMedium: TextStyle(fontSize:13.5,height:1.55,color:kClay),
      ),
      inputDecorationTheme: InputDecorationTheme(filled:true,fillColor:kPaper,contentPadding:const EdgeInsets.symmetric(horizontal:16,vertical:14),border:OutlineInputBorder(borderRadius:BorderRadius.circular(10),borderSide:const BorderSide(color:kMist)),enabledBorder:OutlineInputBorder(borderRadius:BorderRadius.circular(10),borderSide:const BorderSide(color:kMist)),focusedBorder:OutlineInputBorder(borderRadius:BorderRadius.circular(10),borderSide:const BorderSide(color:kForest,width:1.5))),
    ),
    home: const SplashGate(),
  );
}

// ======================== Splash Gate ========================
class SplashGate extends StatefulWidget {
  const SplashGate({super.key});
  @override State<SplashGate> createState() => _SplashGateState();
}

class _SplashGateState extends State<SplashGate> with SingleTickerProviderStateMixin {
  int _countdown = 3;
  bool _showSkip = true;
  late AnimationController _fadeCtrl;
  late Animation<double> _fadeAnim;
  bool _isVip = false;
  Map? _user;

  @override void initState() {
    super.initState();
    _fadeCtrl = AnimationController(duration: const Duration(milliseconds: 600), vsync: this);
    _fadeAnim = CurvedAnimation(parent: _fadeCtrl, curve: Curves.easeIn);
    _fadeCtrl.forward();
    _loadUser();
  }

  Future<void> _loadUser() async {
    final p = await SharedPreferences.getInstance();
    final token = p.getString('xinan_token');
    final u = p.getString('xinan_user');
    if (token != null && u != null) {
      Api._token = token;
      try { _user = jsonDecode(u); } catch (_) {}
      if (_user != null) {
        final vip = _user!['vipLevel'] ?? 0;
        if (vip > 0) {
          // VIP用户：1秒进入
          setState(() { _isVip = true; _showSkip = false; });
          _fadeCtrl.forward().then((_) {
            Future.delayed(const Duration(seconds: 1), () => _enter());
          });
          return;
        }
      }
    }
    _startCountdown();
  }

  void _startCountdown() {
    Future.delayed(const Duration(seconds: 1), () {
      if (!mounted) return;
      setState(() => _countdown = 2);
      Future.delayed(const Duration(seconds: 1), () {
        if (!mounted) return;
        setState(() => _countdown = 1);
        Future.delayed(const Duration(seconds: 1), () {
          if (!mounted) return;
          _enter();
        });
      });
    });
  }

  void _enter() {
    _fadeCtrl.reverse().then((_) {
      if (!mounted) return;
      Navigator.of(context).pushReplacement(
        PageRouteBuilder(
          pageBuilder: (_, __, ___) => const AppRoot(),
          transitionDuration: const Duration(milliseconds: 300),
          transitionsBuilder: (_, a, __, child) => FadeTransition(opacity: a, child: child),
        ),
      );
    });
  }

  @override void dispose() {
    _fadeCtrl.dispose();
    super.dispose();
  }

  @override Widget build(BuildContext c) {
    final vip = _isVip;
    return Scaffold(
      backgroundColor: kForest,
      body: FadeTransition(
        opacity: _fadeAnim,
        child: Stack(
          fit: StackFit.expand,
          children: [
            // 主内容区
            SafeArea(
              child: Column(
                children: [
                  // 顶部广告预留区
                  if (!vip)
                    Container(
                      height: 120,
                      margin: const EdgeInsets.all(16),
                      decoration: BoxDecoration(
                        color: kForestLight.withAlpha(80),
                        borderRadius: BorderRadius.circular(14),
                        border: Border.all(color: kBrass.withAlpha(60)),
                      ),
                      child: const Center(
                        child: Text('广告位', style: TextStyle(color: Colors.white38, fontSize: 13)),
                      ),
                    ),
                  if (vip) const Spacer(),
                  // 中间: 图标 + 标题 + 副标题
                  Expanded(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Container(
                              width: 72,
                              height: 72,
                              decoration: BoxDecoration(
                                color: kBrass,
                                borderRadius: BorderRadius.circular(20),
                                boxShadow: [BoxShadow(color: kBrass.withAlpha(80), blurRadius: 20, offset: const Offset(0, 8))],
                              ),
                              child: const Icon(Icons.castle, color: Colors.white, size: 40),
                            ),
                            if (!vip) const SizedBox(width: 20),
                            if (!vip)
                              Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  const Text('西南大王', style: TextStyle(fontSize: 36, fontWeight: FontWeight.w900, color: Colors.white, letterSpacing: 2)),
                                  const SizedBox(height: 6),
                                  Text('你的云贵川渝一站式考研APP', style: TextStyle(fontSize: 14, color: Colors.white.withAlpha(180), letterSpacing: 1)),
                                ],
                              ),
                          ],
                        ),
                        if (vip) ...[
                          const SizedBox(height: 16),
                          const Text('西南大王', style: TextStyle(fontSize: 32, fontWeight: FontWeight.w900, color: Colors.white, letterSpacing: 2)),
                          const SizedBox(height: 6),
                          Row(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                                decoration: BoxDecoration(color: kBrass, borderRadius: BorderRadius.circular(20)),
                                child: Text(vipLabel(_user?['vipLevel'] ?? 1), style: const TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.w700)),
                              ),
                              const SizedBox(width: 8),
                              Text('正在进入…', style: TextStyle(fontSize: 13, color: Colors.white.withAlpha(150))),
                            ],
                          ),
                        ],
                      ],
                    ),
                  ),
                  if (!vip)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 40),
                      child: Text('V0.2.1 beta · d1yan ©', style: TextStyle(color: Colors.white.withAlpha(80), fontSize: 11)),
                    ),
                ],
              ),
            ),
            // 右上角跳过按钮（非VIP）
            if (_showSkip && !vip)
              Positioned(
                top: MediaQuery.of(c).padding.top + 12,
                right: 16,
                child: GestureDetector(
                  onTap: _enter,
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 7),
                    decoration: BoxDecoration(
                      color: Colors.white.withAlpha(30),
                      borderRadius: BorderRadius.circular(20),
                      border: Border.all(color: Colors.white.withAlpha(50)),
                    ),
                    child: Text('${_countdown}s 跳过', style: const TextStyle(color: Colors.white70, fontSize: 13)),
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

String vipLabel(int level) {
  switch (level) {
    case 99: return '研王爷';
    case 3: return '黑卡';
    case 2: return '金卡';
    case 1: return '银卡';
    default: return 'VIP';
  }
}

// ======================== Root ========================
class AppRoot extends StatefulWidget { const AppRoot({super.key}); @override State<AppRoot> createState() => _AppRootState(); }
class _AppRootState extends State<AppRoot> {
  Map? _user; bool _loading=true;
  @override void initState() { super.initState(); _load(); }
  Future<void> _load() async {
    final p = await SharedPreferences.getInstance();
    final token = p.getString('xinan_token');
    final u = p.getString('xinan_user');
    if (token != null && u != null) { Api._token = token; try { _user = jsonDecode(u); } catch(_) {} }
    if (mounted) setState(()=>_loading=false);
  }
  Future<void> _saveLogin(Map r) async {
    final p = await SharedPreferences.getInstance();
    await p.setString('xinan_token', r['token']);
    await p.setString('xinan_user', jsonEncode(r['user']));
    Api._token = r['token'];
    if (mounted) setState(()=>_user=r['user']);
  }
  Future<void> _logout() async {
    final p = await SharedPreferences.getInstance();
    await p.remove('xinan_token'); await p.remove('xinan_user');
    Api._token = null; if (mounted) setState(()=>_user=null);
  }
  @override Widget build(BuildContext c) {
    if (_loading) return const Scaffold(body:Center(child:CircularProgressIndicator(color:kForest)));
    if (_user==null) return AuthGate(onLogin:(r)=>_saveLogin(r));
    return MainShell(user:_user!, onLogout:_logout);
  }
}


