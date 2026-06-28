part of xinan_dawang;

// ======================== API ========================
class Api {
  static String? _token;
  static Map<String, String> get _headers => {
    'Content-Type': 'application/json; charset=utf-8',
    if (_token != null) 'Authorization': 'Bearer $_token',
  };

  static dynamic _decode(http.Response r) {
    if (r.statusCode >= 400) {
      try {
        final d = jsonDecode(r.body);
        throw ApiError(d['detail']?.toString() ?? 'Error ${r.statusCode}');
      } catch (e) {
        if (e is ApiError) rethrow;
        throw ApiError('Error ${r.statusCode}');
      }
    }
    return jsonDecode(r.body);
  }

  static Future<dynamic> _post(String path, Map body) async {
    final r = await http.post(Uri.parse('$kBaseUrl$path'), headers: _headers, body: jsonEncode(body)).timeout(const Duration(seconds: 30));
    return _decode(r);
  }

  static Future<dynamic> _get(String path, {Map<String,String>? params}) async {
    var url = '$kBaseUrl$path';
    if (params != null && params.isNotEmpty) url += '?${params.entries.map((e)=>'${e.key}=${Uri.encodeComponent(e.value)}').join('&')}';
    final r = await http.get(Uri.parse(url), headers: _headers).timeout(const Duration(seconds: 15));
    return _decode(r);
  }

  static Future<void> _del(String path) async {
    await http.delete(Uri.parse('$kBaseUrl$path'), headers: _headers).timeout(const Duration(seconds: 10));
  }

  static Future<dynamic> _put(String path, Map body) async {
    final r = await http.put(Uri.parse('$kBaseUrl$path'), headers: _headers, body: jsonEncode(body)).timeout(const Duration(seconds: 15));
    return _decode(r);
  }

  // Public generic accessors for notifications etc.
  static Future<dynamic> get(String path, {Map<String,String>? params}) => _get(path, params: params);
  static Future<dynamic> post(String path, Map body) => _post(path, body);
  static Future<void> del(String path) => _del(path);
  static Future<dynamic> put(String path, Map body) => _put(path, body);

  // Auth
  static Future<Map> checkDawangId(String id) async { final d = await _post('/auth/check-dawang-id', {'dawang_id': id}); return d as Map; }
  static Future<Map> register(Map body) async { final d = await _post('/auth/register', body); return d as Map; }
  static Future<Map> login(String u, String p) async { final d = await _post('/auth/login', {'username': u, 'password': p}); return d as Map; }
  static Future<Map> forgotPassword(String phone, String pw) async { final d = await _post('/auth/forgot-password', {'phone': phone, 'new_password': pw}); return d as Map; }
  static Future<void> changePassword(String o, String n) async { await _put('/auth/change-password', {'old_password': o, 'new_password': n}); }
  static Future<void> changeDawangId(String n) async { await _put('/auth/change-dawang-id', {'new_dawang_id': n}); }
  static Future<Map> getMe() async { final d = await _get('/auth/me'); return d as Map; }
  static Future<Map> getAiSummary() async { final d = await _get('/auth/ai-summary'); return d as Map; }
  static Future<Map> generateAiSummary() async { final d = await _post('/auth/ai-summary', {}); return d as Map; }

  // Schools
  static Future<Map> getSchools({String? province, String? tag, String? search, int page=1}) async {
    final p = <String,String>{'page': page.toString(), 'page_size': '30'};
    if (province != null) p['province'] = province;
    if (tag != null) p['tag'] = tag;
    if (search != null) p['search'] = search;
    final d = await _get('/schools', params: p); return d as Map;
  }
  static Future<Map> getSchoolDetail(String id, {String? userMajor}) async {
    final p = <String,String>{};
    if (userMajor != null && userMajor.isNotEmpty) p['user_major'] = userMajor;
    final d = await _get('/schools/$id', params: p.isNotEmpty ? p : null); return d as Map;
  }
  static Future<List<String>> getProvinces() async { final d = await _get('/schools/provinces'); return (d as List).cast<String>(); }
  static Future<List> getUnifiedSchools(String exam) async { final d = await _get('/schools/unified/$exam'); return d as List; }

  // Catalog
  static Future<List> getSubjectTree() async { final d = await _get('/catalog/subjects'); return d as List; }
  static Future<Map> getUndergradSchools([String? province]) async {
    final d = await _get('/catalog/undergrad-schools', params: province != null ? {'province': province} : null); return d as Map;
  }

  // Exam papers
  static Future<List> getExamPapers({String? subject, int? year}) async {
    final p = <String,String>{};
    if (subject != null) p['subject'] = subject;
    if (year != null) p['year'] = year.toString();
    final d = await _get('/exam-papers', params: p.isNotEmpty ? p : null); return d as List;
  }
  static Future<Map> getExamDetail(String id) async { final d = await _get('/exam-papers/$id'); return d as Map; }

  // Chat
  static Future<Map> chatSend(String msg, {bool deepThink=false}) async { final d = await _post('/chat/send', {'message': msg, 'deep_think': deepThink}); return d as Map; }

  // Posts
  static Future<Map> getPosts({int page=1}) async { final d = await _get('/posts', params: {'page': page.toString()}); return d as Map; }
  static Future<Map> createPost(String c) async { final d = await _post('/posts', {'content': c}); return d as Map; }
  static Future<Map> toggleLike(String pid) async { final d = await _post('/posts/$pid/likes', {}); return d as Map; }
  static Future<List> getComments(String pid) async { final d = await _get('/posts/$pid/comments'); return d as List; }
  static Future<Map> addComment(String pid, String c, {String? replyTo}) async { final d = await _post('/posts/$pid/comments', {'content': c, if(replyTo!=null) 'reply_to': replyTo}); return d as Map; }

  // Phase 1: coins, sign-in, VIP, redeem
  static Future<Map> getCoinsStatus() async { final d = await _get('/chat/coins/status'); return d as Map; }
  static Future<Map> dailySignIn() async { final d = await _post('/auth/sign-in', {}); return d as Map; }
  static Future<Map> getSignInStatus() async { final d = await _get('/auth/sign-in/status'); return d as Map; }
  static Future<Map> redeemCode(String code) async { final d = await _post('/redeem/use', {'code': code}); return d as Map; }
  static Future<List> getRedeemHistory() async { final d = await _get('/redeem/history'); return d as List; }
  static Future<Map> getRedeemProducts() async { final d = await _get('/redeem/products'); return d as Map; }
  static Future<Map> confirmAdmitted() async { final d = await _post('/auth/confirm-admitted', {}); return d as Map; }

  // Phase 2: pomodoro and focus
  static Future<Map> startPomodoro(String subject, int minutes, {String? subjectId}) async { final d = await _post('/pomodoro/start', {'subject': subject, 'subject_id': subjectId, 'duration_minutes': minutes}); return d as Map; }
  static Future<Map> completePomodoro(String recordId) async { final d = await _post('/pomodoro/$recordId/complete', {}); return d as Map; }
  static Future<Map> abandonPomodoro(String recordId) async { final d = await _post('/pomodoro/$recordId/abandon', {}); return d as Map; }
  static Future<Map> getPomodoroToday() async { final d = await _get('/pomodoro/stats/today'); return d as Map; }
  static Future<Map> getPomodoroWeekly() async { final d = await _get('/pomodoro/stats/weekly'); return d as Map; }
  static Future<Map> getPomodoroStreak() async { final d = await _get('/pomodoro/streak'); return d as Map; }
  static Future<Map> getStudyRoomOnline() async { final d = await _get('/pomodoro/study-room/online'); return d as Map; }

  // Phase 3: questions, errors, flashcards, countdown, compare
  static Future<Map> getDailyQuestion({String? subject}) async { final d = await _get('/questions/daily', params: subject == null ? null : {'subject': subject}); return d as Map; }
  static Future<Map> answerQuestion(String id, String answer) async { final d = await _post('/questions/$id/answer', {'answer': answer}); return d as Map; }
  static Future<Map> getQuestionHistory({int page=1}) async { final d = await _get('/questions/history', params: {'page': '$page'}); return d as Map; }
  static Future<Map> getErrorNotes({String? status}) async { final d = await _get('/error-notes', params: status == null ? null : {'status': status}); return d as Map; }
  static Future<Map> getErrorStats() async { final d = await _get('/error-notes/stats'); return d as Map; }
  static Future<Map> getErrorReviewQueue() async { final d = await _get('/error-notes/review-queue'); return d as Map; }
  static Future<Map> reviewErrorNote(String id, String answer) async { final d = await _post('/error-notes/$id/review', {'answer': answer}); return d as Map; }
  static Future<Map> masterErrorNote(String id) async { final d = await _post('/error-notes/$id/master', {}); return d as Map; }
  static Future<Map> getFlashcardDecks() async { final d = await _get('/flashcards/decks'); return d as Map; }
  static Future<Map> getFlashcardStudy(String deckId) async { final d = await _get('/flashcards/decks/$deckId/study'); return d as Map; }
  static Future<Map> reviewFlashcard(String cardId, int rating) async { final d = await _post('/flashcards/cards/$cardId/review', {'rating': rating}); return d as Map; }
  static Future<Map> createFlashcard(Map body) async { final d = await _post('/flashcards/cards', body); return d as Map; }
  static Future<Map> compareSchools(List<String> ids) async { final d = await _get('/schools/compare', params: {'ids': ids.join(',')}); return d as Map; }
  static Future<Map> getCompareAiTip(List<String> ids) async { final d = await _get('/schools/compare/ai-tip', params: {'ids': ids.join(',')}); return d as Map; }
  static Future<Map> getExamDate() async { final d = await _get('/config/exam-date'); return d as Map; }
  static Future<Map> getDailyMotto() async { final d = await _get('/config/motto'); return d as Map; }
  static Future<Map> debugSelfUpdate(Map body) async { final d = await _post('/auth/debug-self', body); return d as Map; }

  // Phase 4: achievements, leaderboard, diary, match, fortune
  static Future<Map> getAchievements() async { final d = await _get('/achievements'); return d as Map; }
  static Future<Map> getRecentAchievements() async { final d = await _get('/achievements/recent'); return d as Map; }
  static Future<Map> getLeaderboard(String type) async { final d = await _get('/leaderboard/$type'); return d as Map; }
  static Future<Map> getDiaryList({int page=1}) async { final d = await _get('/diary', params: {'page': '$page'}); return d as Map; }
  static Future<Map> getDiaryByDate(String date) async { final d = await _get('/diary/$date'); return d as Map; }
  static Future<Map> saveDiary(Map body) async { final d = await _post('/diary', body); return d as Map; }
  static Future<void> deleteDiary(String id) async { await _del('/diary/$id'); }
  static Future<Map> getMatchSettings() async { final d = await _get('/match/settings'); return d as Map; }
  static Future<Map> updateMatchSettings(Map body) async { final d = await _put('/match/settings', body); return d as Map; }
  static Future<Map> getMatchRecommendations() async { final d = await _get('/match/recommendations'); return d as Map; }
  static Future<Map> getTodayFortune() async { final d = await _get('/fortune/today'); return d as Map; }
  static Future<Map> blessFortune() async { final d = await _post('/fortune/bless', {}); return d as Map; }
  static Future<Map> getFortuneStats() async { final d = await _get('/fortune/stats'); return d as Map; }
  static Future<Map> shareFortune() async { final d = await _post('/fortune/share', {}); return d as Map; }

  // Phase 5: exams, interview, transfer, study plan
  static Future<Map> getMockExams({String? subject}) async { final d = await _get('/exams', params: subject == null ? null : {'subject': subject}); return d as Map; }
  static Future<Map> startMockExam(String examId) async { final d = await _get('/exams/$examId/start'); return d as Map; }
  static Future<Map> answerMockExam(String attemptId, String questionId, String answer) async { final d = await _put('/exams/$attemptId/answer', {'question_id': questionId, 'answer': answer}); return d as Map; }
  static Future<Map> markMockExam(String attemptId, String questionId) async { final d = await _put('/exams/$attemptId/mark', {'question_id': questionId}); return d as Map; }
  static Future<Map> submitMockExam(String attemptId) async { final d = await _post('/exams/$attemptId/submit', {}); return d as Map; }
  static Future<Map> getMockExamResult(String attemptId) async { final d = await _get('/exams/$attemptId/result'); return d as Map; }
  static Future<Map> getMockExamHistory() async { final d = await _get('/exams/history'); return d as Map; }
  static Future<Map> getMockExamStats() async { final d = await _get('/exams/stats'); return d as Map; }
  static Future<Map> startInterview(Map body) async { final d = await _post('/interview/start', body); return d as Map; }
  static Future<Map> answerInterview(String sessionId, Map body) async { final d = await _post('/interview/$sessionId/answer', body); return d as Map; }
  static Future<Map> skipInterview(String sessionId) async { final d = await _post('/interview/$sessionId/skip', {}); return d as Map; }
  static Future<Map> getInterviewReport(String sessionId) async { final d = await _get('/interview/$sessionId/report'); return d as Map; }
  static Future<Map> getInterviewHistory() async { final d = await _get('/interview/history'); return d as Map; }
  static Future<Map> getTransferInfos({String? keyword}) async { final d = await _get('/transfer/infos', params: keyword == null || keyword.isEmpty ? null : {'keyword': keyword}); return d as Map; }
  static Future<Map> getTransferDetail(String id) async { final d = await _get('/transfer/infos/$id'); return d as Map; }
  static Future<Map> getTransferAnalysis(String id) async { final d = await _get('/transfer/infos/$id/ai-analysis'); return d as Map; }
  static Future<Map> getTransferAlerts() async { final d = await _get('/transfer/alerts'); return d as Map; }
  static Future<Map> createTransferAlert(Map body) async { final d = await _post('/transfer/alerts', body); return d as Map; }
  static Future<void> deleteTransferAlert(String id) async { await _del('/transfer/alerts/$id'); }
  static Future<Map> getTransferMatches() async { final d = await _get('/transfer/matches'); return d as Map; }
  static Future<Map> generateStudyPlan(Map body) async { final d = await _post('/study-plan/generate', body); return d as Map; }
  static Future<Map> getCurrentStudyPlan() async { final d = await _get('/study-plan/current'); return d as Map; }
  static Future<Map> getStudyPlanHistory() async { final d = await _get('/study-plan/history'); return d as Map; }
  static Future<Map> updateStudyTask(String id, bool done) async { final d = await _put('/study-plan/tasks/$id', {'completed': done}); return d as Map; }
  static Future<Map> getWeeklyStudyReport() async { final d = await _get('/study-plan/weekly-report/latest'); return d as Map; }

  // Friends
  static Future<List> getFriends() async { final d = await _get('/friends'); return d as List; }
  static Future<List> getFriendRequests() async { final d = await _get('/friends/requests'); return d as List; }
  static Future<void> sendFriendRequest(String did) async { await _post('/friends/request', {'dawang_id': did}); }
  static Future<void> acceptRequest(String id) async { await _put('/friends/$id/accept', {}); }
  static Future<void> removeFriend(String id) async { await _del('/friends/$id'); }
  static Future<Map> searchDawangId(String q) async { final d = await _get('/friends/search', params: {'q': q}); return d as Map; }
  static Future<List> getMessages(String fid) async { final d = await _get('/friends/messages/$fid'); return d as List; }
}

class ApiError implements Exception { final String message; ApiError(this.message); @override String toString() => message; }



