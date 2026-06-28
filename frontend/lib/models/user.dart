class UserInfo {
  final String id, username, nickname, dawangId;
  final String? phone, grade, major, targetSchool, direction;
  final String? currentProgress, estimatedScore, studyStyle;
  final String? avatar, school, undergradProvince, undergradSchool;
  final bool hasTarget, undergradPrivate, isBanned;
  final int level, vipLevel;

  UserInfo({required this.id, required this.username, required this.nickname, required this.dawangId,
    this.phone, this.grade, this.major, this.hasTarget=false, this.targetSchool,
    this.direction, this.currentProgress, this.estimatedScore, this.studyStyle,
    this.avatar, this.school, this.undergradProvince, this.undergradSchool,
    this.undergradPrivate=false, this.isBanned=false, this.level=1, this.vipLevel=0});

  factory UserInfo.fromJson(Map d) => UserInfo(
    id: d['id']??'', username: d['username']??'', nickname: d['nickname']??'', dawangId: d['dawangId']??'',
    phone: d['phone'], grade: d['grade'], major: d['major'],
    hasTarget: d['hasTarget']??false, targetSchool: d['targetSchool'],
    direction: d['direction'], currentProgress: d['currentProgress'],
    estimatedScore: d['estimatedScore'], studyStyle: d['studyStyle'],
    avatar: d['avatar'], school: d['school'],
    undergradProvince: d['undergradProvince'], undergradSchool: d['undergradSchool'],
    undergradPrivate: d['undergradPrivate']??false, isBanned: d['isBanned']??false,
    level: d['level']??1, vipLevel: d['vipLevel']??0,
  );

  Map<String, dynamic> toJson() => {
    'id':id,'username':username,'nickname':nickname,'dawangId':dawangId,
    'phone':phone,'grade':grade,'major':major,'hasTarget':hasTarget,
    'targetSchool':targetSchool,'direction':direction,'currentProgress':currentProgress,
    'estimatedScore':estimatedScore,'studyStyle':studyStyle,'avatar':avatar,
    'school':school,'undergradProvince':undergradProvince,'undergradSchool':undergradSchool,
    'undergradPrivate':undergradPrivate,'isBanned':isBanned,'level':level,'vipLevel':vipLevel,
  };
}

class AuthResult {
  final UserInfo user; final String token;
  AuthResult({required this.user, required this.token});
  factory AuthResult.fromJson(Map d) => AuthResult(user: UserInfo.fromJson(d['user']??{}), token: d['token']??'');
}
