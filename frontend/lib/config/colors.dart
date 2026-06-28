import 'package:flutter/material.dart';

// Primary greens
const kForestDeep = Color(0xFF0F2A1E);
const kForest = Color(0xFF1B3A2D);
const kForestLight = Color(0xFF2D5A4B);
const kForestSoft = Color(0xFFE8F0EB);

// Brass / VIP
const kBrass = Color(0xFFC4956A);
const kBrassLight = Color(0xFFD4B896);
const kBrassSoft = Color(0xFFF5EDE3);

// Red
const kRed = Color(0xFFB91C1C);

// Base
const kInk = Color(0xFF1C1917);
const kPaper = Color(0xFFFDFBF7);
const kParchment = Color(0xFFF5F2EB);
const kMoss = Color(0xFF2D5A4B);
const kClay = Color(0xFF8B6F5E);
const kMist = Color(0xFFE8E3D7);

// Shadows (opacity applied at use site)
const _shadowBase = 0xFF1B3A2D;
List<BoxShadow> shadowLevel(int level) {
  final opacities = [0.04, 0.06, 0.08, 0.12];
  final blurs = [6.0, 12.0, 20.0, 32.0];
  final offsets = [2.0, 4.0, 8.0, 16.0];
  return [
    BoxShadow(
      color: Color(_shadowBase).withAlpha((opacities[level - 1] * 255).toInt()),
      blurRadius: blurs[level - 1],
      offset: Offset(0, offsets[level - 1]),
    ),
  ];
}
