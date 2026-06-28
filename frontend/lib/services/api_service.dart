import 'dart:convert';
import 'package:http/http.dart' as http;
import '../config/constants.dart';

class ApiError implements Exception { final String message; ApiError(this.message); @override String toString() => message; }

class ApiService {
  static String? _token;
  static String? get token => _token;

  static dynamic _decode(http.Response r) {
    if (r.statusCode >= 400) {
      try { final d = jsonDecode(r.body); throw ApiError(d['detail']?.toString() ?? 'Error ${r.statusCode}'); }
      catch (e) { if (e is ApiError) rethrow; throw ApiError('Error ${r.statusCode}'); }
    }
    return jsonDecode(r.body);
  }

  static Future<dynamic> post(String path, Map body) async {
    final r = await http.post(Uri.parse('$kBaseUrl$path'), headers: _headers(), body: jsonEncode(body)).timeout(const Duration(seconds: 30));
    return _decode(r);
  }

  static Future<dynamic> get(String path, {Map<String,String>? params}) async {
    var url = '$kBaseUrl$path';
    if (params != null && params.isNotEmpty) url += '?${params.entries.map((e)=>'${e.key}=${Uri.encodeComponent(e.value)}').join('&')}';
    final r = await http.get(Uri.parse(url), headers: _headers()).timeout(const Duration(seconds: 15));
    return _decode(r);
  }

  static Future<void> del(String path) async {
    await http.delete(Uri.parse('$kBaseUrl$path'), headers: _headers()).timeout(const Duration(seconds: 10));
  }

  static Future<dynamic> put(String path, Map body) async {
    final r = await http.put(Uri.parse('$kBaseUrl$path'), headers: _headers(), body: jsonEncode(body)).timeout(const Duration(seconds: 15));
    return _decode(r);
  }

  static Map<String, String> _headers() => {
    'Content-Type': 'application/json; charset=utf-8',
    if (_token != null) 'Authorization': 'Bearer $_token',
  };

  // Auth
  static Future<Map> login(String u, String p) async { final d = await post('/auth/login', {'username':u,'password':p}); return d as Map; }
  static Future<Map> register(Map body) async { final d = await post('/auth/register', body); return d as Map; }
  static Future<Map> checkDawangId(String id) async { final d = await post('/auth/check-dawang-id', {'dawang_id':id}); return d as Map; }
  static Future<void> forgotPassword(String phone, String pw) async { await post('/auth/forgot-password', {'phone':phone,'new_password':pw}); }
  static Future<void> changePassword(String o, String n) async { await put('/auth/change-password', {'old_password':o,'new_password':n}); }
  static Future<void> changeDawangId(String n) async { await put('/auth/change-dawang-id', {'new_dawang_id':n}); }
  static Future<Map> getMe() async { final d = await get('/auth/me'); return d as Map; }
  static Future<Map> generateAiSummary() async { final d = await post('/auth/ai-summary', {}); return d as Map; }

  // Schools
  static Future<Map> getSchools({String? province, String? tag, String? search, int page=1}) async {
    final p = <String,String>{'page':page.toString(),'page_size':'30'};
    if(province!=null)p['province']=province; if(tag!=null)p['tag']=tag; if(search!=null)p['search']=search;
    final d = await get('/schools', params: p); return d as Map;
  }
  static Future<Map> getSchoolDetail(String id, {String? userMajor}) async {
    final p = <String,String>{}; if(userMajor!=null&&userMajor.isNotEmpty)p['user_major']=userMajor;
    final d = await get('/schools/$id', params: p.isNotEmpty?p:null); return d as Map;
  }
  static Future<List<String>> getProvinces() async { final d = await get('/schools/provinces'); return (d as List).cast<String>(); }
  static Future<List> getSubjectTree() async { final d = await get('/catalog/subjects'); return d as List; }
  static Future<Map> getUndergradSchools([String? province]) async {
    final d = await get('/catalog/undergrad-schools', params: province!=null?{'province':province}:null); return d as Map;
  }

  // Exams
  static Future<List> getExamPapers({String? subject, int? year}) async {
    final p = <String,String>{}; if(subject!=null)p['subject']=subject; if(year!=null)p['year']=year.toString();
    final d = await get('/exam-papers', params: p.isNotEmpty?p:null); return d as List;
  }
  static Future<Map> getExamDetail(String id) async { final d = await get('/exam-papers/$id'); return d as Map; }

  // Chat
  static Future<Map> chatSend(String msg) async { final d = await post('/chat/send', {'message':msg}); return d as Map; }

  // Posts
  static Future<Map> getPosts({int page=1}) async { final d = await get('/posts', params: {'page':page.toString()}); return d as Map; }
  static Future<Map> createPost(String c) async { final d = await post('/posts', {'content':c}); return d as Map; }
  static Future<Map> toggleLike(String pid) async { final d = await post('/posts/$pid/likes', {}); return d as Map; }
  static Future<List> getComments(String pid) async { final d = await get('/posts/$pid/comments'); return d as List; }
  static Future<Map> addComment(String pid, String c) async { final d = await post('/posts/$pid/comments', {'content':c}); return d as Map; }

  // Friends
  static Future<List> getFriends() async { final d = await get('/friends'); return d as List; }
  static Future<List> getFriendRequests() async { final d = await get('/friends/requests'); return d as List; }
  static Future<void> sendFriendRequest(String did) async { await post('/friends/request', {'dawang_id':did}); }
  static Future<void> acceptRequest(String id) async { await put('/friends/$id/accept', {}); }
  static Future<void> removeFriend(String id) async { await del('/friends/$id'); }
  static Future<Map> searchDawangId(String q) async { final d = await get('/friends/search', params: {'q':q}); return d as Map; }
  static Future<List> getMessages(String fid) async { final d = await get('/friends/messages/$fid'); return d as List; }

  // Coins & Sign-in
  static Future<Map> getCoinsStatus() async { final d = await get('/chat/coins/status'); return d as Map; }
  static Future<Map> dailySignIn() async { final d = await post('/auth/sign-in', {}); return d as Map; }
  static Future<Map> getSignInStatus() async { final d = await get('/auth/sign-in/status'); return d as Map; }

  // Redeem
  static Future<Map> redeemCode(String code) async { final d = await post('/redeem/use', {'code':code}); return d as Map; }
  static Future<Map> getRedeemHistory() async { final d = await get('/redeem/history'); return d as Map; }
  static Future<Map> getRedeemProducts() async { final d = await get('/redeem/products'); return d as Map; }
}
