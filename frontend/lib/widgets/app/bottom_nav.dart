part of xinan_dawang;

class BottomNav extends StatelessWidget {
  final int currentIndex;
  final ValueChanged<int> onTap;
  const BottomNav({super.key, required this.currentIndex, required this.onTap});

  static const _labels = ['择校', '专业课', 'AI陪聊', '研友圈', '好友', '我的'];
  static const _icons = [
    Icons.account_balance_outlined, Icons.menu_book_outlined, Icons.auto_awesome,
    Icons.groups_outlined, Icons.people_outline, Icons.person_outline,
  ];

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        color: kPaper,
        border: Border(top: BorderSide(color: kMist, width: 0.5)),
      ),
      padding: const EdgeInsets.only(bottom: 4, top: 6),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceAround,
        children: List.generate(6, (i) {
          final active = currentIndex == i;
          return GestureDetector(
            onTap: () => onTap(i),
            behavior: HitTestBehavior.opaque,
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 200),
              width: 58,
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  if (active)
                    Container(width: 20, height: 2,
                      decoration: BoxDecoration(color: kForest, borderRadius: BorderRadius.circular(2))),
                  if (!active) const SizedBox(height: 2),
                  const SizedBox(height: 3),
                  AnimatedScale(
                    scale: active ? 1.1 : 1.0,
                    duration: const Duration(milliseconds: 200),
                    child: Icon(_icons[i], size: 22, color: active ? kForest : kClay),
                  ),
                  const SizedBox(height: 3),
                  AnimatedDefaultTextStyle(
                    duration: const Duration(milliseconds: 200),
                    style: TextStyle(fontSize: 10.5, fontWeight: active ? FontWeight.w700 : FontWeight.w400, color: active ? kForest : kClay),
                    child: Text(_labels[i]),
                  ),
                ],
              ),
            ),
          );
        }),
      ),
    );
  }
}

