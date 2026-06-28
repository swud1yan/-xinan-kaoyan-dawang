import 'package:flutter/material.dart';
import 'skeleton_card.dart';

class SkeletonList extends StatelessWidget {
  final int count;
  const SkeletonList({super.key, this.count = 5});

  @override
  Widget build(BuildContext context) {
    return Column(children: List.generate(count, (_) => const SkeletonCard()));
  }
}
