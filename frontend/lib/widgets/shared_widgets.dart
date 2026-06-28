part of xinan_dawang;

// ======================== Shared Widgets ========================
class Hdr extends StatelessWidget {final String t,s;const Hdr({super.key,required this.t,required this.s});@override Widget build(BuildContext c)=>Padding(padding:const EdgeInsets.fromLTRB(20,20,20,4),child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[Text(t,style:Theme.of(c).textTheme.headlineMedium),const SizedBox(height:4),Text(s,style:Theme.of(c).textTheme.bodyMedium)]));}
Widget tag(String l,{bool a=false,VoidCallback? on})=>GestureDetector(onTap:on,child:Container(padding:const EdgeInsets.symmetric(horizontal:12,vertical:6),decoration:BoxDecoration(color:a?kForest:kPaper,borderRadius:BorderRadius.circular(20),border:Border.all(color:a?kForest:kMist)),child:Text(l,style:TextStyle(fontSize:13,fontWeight:FontWeight.w500,color:a?kPaper:kClay))));

// ── User Badge Row ──
Widget userBadges(Map author) {
  final isAdmin = author['isWhitelist'] == true;
  final vipLevel = (author['vipLevel'] ?? 0) as int;
  final level = author['level'] ?? 1;
  final title = author['levelTitle']?.toString() ?? '';
  final widgets = <Widget>[];
  if (isAdmin) widgets.add(_badge('管理员', const Color(0xFFC4956A)));
  if (vipLevel == 99) {
    widgets.add(_badge('研王爷', kBrass));
  } else if (vipLevel >= 3) {
    widgets.add(_badge('黑卡', const Color(0xFF666666)));
  } else if (vipLevel >= 2) {
    widgets.add(_badge('金卡', kBrass));
  } else if (vipLevel >= 1) {
    widgets.add(_badge('银卡', const Color(0xFF9E9E9E)));
  }
  if (title.isNotEmpty) widgets.add(_badge(title, kForest));
  if (widgets.isEmpty) return const SizedBox.shrink();
  return Wrap(spacing: 4, children: widgets);
}

Widget _badge(String text, Color color) => Container(
  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
  decoration: BoxDecoration(color: color.withAlpha(20), borderRadius: BorderRadius.circular(4)),
  child: Text(text, style: TextStyle(fontSize: 10, fontWeight: FontWeight.w700, color: color)),
);

String vipName(int level) {
  switch (level) {
    case 99: return '研王爷';
    case 3: return '黑卡';
    case 2: return '金卡';
    case 1: return '银卡';
    default: return '';
  }
}


