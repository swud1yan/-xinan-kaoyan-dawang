import 'package:flutter/material.dart';
import 'colors.dart';

ThemeData buildTheme() => ThemeData(
  useMaterial3: true,
  scaffoldBackgroundColor: kParchment,
  colorScheme: ColorScheme.fromSeed(seedColor: kForest, brightness: Brightness.light),
  textTheme: const TextTheme(
    headlineMedium: TextStyle(fontSize: 24, fontWeight: FontWeight.w700, letterSpacing: -0.3, height: 1.2, color: kInk),
    titleLarge: TextStyle(fontSize: 20, fontWeight: FontWeight.w700, height: 1.25, color: kInk),
    titleMedium: TextStyle(fontSize: 16, fontWeight: FontWeight.w600, height: 1.3, color: kInk),
    bodyLarge: TextStyle(fontSize: 15, height: 1.6, color: kInk),
    bodyMedium: TextStyle(fontSize: 13.5, height: 1.55, color: kClay),
  ),
  inputDecorationTheme: InputDecorationTheme(
    filled: true, fillColor: kPaper,
    contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
    border: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: const BorderSide(color: kMist)),
    enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: const BorderSide(color: kMist)),
    focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: const BorderSide(color: kForest, width: 1.5)),
  ),
);
