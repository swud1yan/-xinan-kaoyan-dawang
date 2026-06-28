import 'package:flutter/material.dart';
import 'config/theme.dart';

class XinanApp extends StatelessWidget {
  final Widget home;
  const XinanApp({super.key, required this.home});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: '西南大王',
      theme: buildTheme(),
      home: home,
    );
  }
}
