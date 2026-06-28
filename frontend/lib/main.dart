library xinan_dawang;

import 'dart:convert';
import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

import 'config/colors.dart';
import 'config/constants.dart';
import 'widgets/loaders/skeleton_list.dart';
import 'widgets/empty/empty_state.dart';

part 'services/api.dart';
part 'app_shell.dart';
part 'screens/auth/auth_gate.dart';
part 'screens/auth/login_screen.dart';
part 'screens/auth/forgot_password.dart';
part 'screens/auth/register_flow.dart';
part 'screens/tabs/main_shell.dart';
part 'widgets/app/bottom_nav.dart';
part 'widgets/shared_widgets.dart';
part 'screens/tabs/school_tab.dart';
part 'screens/detail/school_detail.dart';
part 'screens/tabs/course_tab.dart';
part 'screens/tabs/chat_tab.dart';
part 'screens/tabs/circle_tab.dart';
part 'screens/tabs/friends_tab.dart';
part 'screens/tabs/profile_tab.dart';
part 'screens/detail/account_security.dart';
part 'screens/detail/sign_in_page.dart';
part 'screens/detail/redeem_page.dart';
part 'screens/detail/vip_page.dart';
part 'screens/detail/level_page.dart';
part 'screens/detail/phase23_pages.dart';
part 'screens/detail/phase45_pages.dart';
part 'screens/detail/notifications_page.dart';
part 'screens/detail/help_page.dart';
part 'screens/detail/feedback_page.dart';
part 'screens/detail/user_profile_page.dart';

void main() => runApp(const ProviderScope(child: XinanApp()));


