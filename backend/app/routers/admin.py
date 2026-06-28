"""Admin dashboard with full user/coin/VIP/redeem management."""

from __future__ import annotations



import csv

import html

import io

import json

import random

import string

from datetime import datetime, timedelta, timezone



from fastapi import APIRouter, Depends, HTTPException, Query, Request

from fastapi.responses import HTMLResponse, Response

from pydantic import BaseModel, Field

from sqlalchemy import delete, func, or_, select

from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy.orm import joinedload



from app.config import get_settings

from app.database import get_db

from app.models.admin import AdminLog, VipOrder

from app.models.chat import ChatMessage

from app.models.coins import Announcement, RedeemCode, RedeemHistory, SignInRecord, XpHistory

from app.models.phase2_5 import (

    DiaryEntry, ErrorNote, FortuneRecord, InterviewSession,

    PomodoroRecord, StudyPlan, UserAnswer, UserExam,

)

from app.models.post import Post

from app.models.user import User

from app.services.coins_service import VIP_MONTHLY_COINS

from app.services.redeem_service import create_codes



settings = get_settings()

router = APIRouter(prefix="/admin", tags=["Admin"])

ADMIN = settings.ADMIN_TOKEN



VIP_NAMES = {0: "free", 1: "silver", 2: "gold", 3: "black", 99: "yanKing"}

VIP_LABELS = {1: "银卡", 2: "金卡", 3: "黑卡", 99: "研王爷"}

VIP_PRICES = {1: 9.9, 2: 19.9, 3: 29.9, 99: 298.0}

VIP_DAYS = {1: 30, 2: 30, 3: 30, 99: 99999}

COIN_PACKS = {

    "pack_100":  {"name": "100研AI币",  "coins": 100,   "price": 6},

    "pack_500":  {"name": "500研AI币",  "coins": 500,   "price": 24},

    "pack_1500": {"name": "1500研AI币", "coins": 1500,  "price": 58},

    "pack_5000": {"name": "5000研AI币", "coins": 5000,  "price": 148},

    "pack_12000":{"name": "12000研AI币","coins": 12000, "price": 288},

}





# ── helpers ──

def chk(token: str):

    if token != ADMIN:

        raise HTTPException(403, detail="invalid admin token")



def now_utc() -> datetime:

    return datetime.now(timezone.utc)



def today_utc() -> datetime:

    return now_utc().replace(hour=0, minute=0, second=0, microsecond=0)



def _iso(v) -> str | None:

    return v.isoformat() if v else None



def _esc(v) -> str:

    return html.escape("" if v is None else str(v))



async def _cnt(db, stmt) -> int:

    return int((await db.execute(stmt)).scalar() or 0)



def _log(db, action: str, target_type: str = "user", target_id: str | None = None, detail: str | None = None):

    db.add(AdminLog(admin_id="admin", action=action, target_type=target_type, target_id=target_id, detail=detail))



def _rand_name(length: int = 8) -> str:

    return ''.join(random.choices(string.ascii_lowercase, k=length))





# ── pydantic models ──

class VipUpdateReq(BaseModel):

    vip_level: int = Field(..., ge=0)

    expire_days: int = Field(30, ge=0)

    reason: str = Field("手动调整", max_length=200)



class AnnouncementReq(BaseModel):

    title: str = Field(..., min_length=1, max_length=200)

    content: str = Field(..., min_length=1)

    priority: int = Field(0, ge=0, le=99)



class RedeemGenReq(BaseModel):

    product_type: str

    coin_pack_id: str | None = None

    count: int = Field(..., ge=1, le=1000)



class CoinAdjustReq(BaseModel):

    monthly_delta: int = Field(0)

    purchased_delta: int = Field(0)

    reason: str = Field("管理员手动调整", max_length=300)



class UsernameReq(BaseModel):

    new_username: str = Field(..., min_length=2, max_length=50)



class NicknameReq(BaseModel):

    new_nickname: str = Field(..., min_length=1, max_length=50)



class GrantVipReq(BaseModel):

    vip_level: int = Field(..., ge=0)

    days: int = Field(30, ge=0)

    reason: str = Field("管理员授予", max_length=200)



class AdjustTokenReq(BaseModel):

    delta: int = Field(0)

    reason: str = Field("管理员调整", max_length=200)





# ═══════════════════════════════════════

#  DASHBOARD HTML

# ═══════════════════════════════════════

@router.get("", response_class=HTMLResponse)

async def dashboard(request: Request, token: str = Query(default=""), db: AsyncSession = Depends(get_db)):

    chk(token)

    today = today_utc()

    month_start = today.replace(day=1)



    # stats

    total_users = await _cnt(db, select(func.count()).select_from(User))

    today_new = await _cnt(db, select(func.count()).select_from(User).where(User.created_at >= today))

    total_posts = await _cnt(db, select(func.count()).select_from(Post))

    total_pomo = int((await db.execute(select(func.sum(User.pomodoro_count)))).scalar() or 0)

    dau = await _cnt(db, select(func.count()).select_from(User).where(or_(User.last_login_at >= today, User.updated_at >= today)))

    total_rev = float((await db.execute(select(func.sum(VipOrder.amount)).where(VipOrder.status == "paid"))).scalar() or 0)

    today_rev = float((await db.execute(select(func.sum(VipOrder.amount)).where(VipOrder.status == "paid", VipOrder.created_at >= today))).scalar() or 0)

    month_rev = float((await db.execute(select(func.sum(VipOrder.amount)).where(VipOrder.status == "paid", VipOrder.created_at >= month_start))).scalar() or 0)

    total_tok = int((await db.execute(select(func.sum(User.token_used)))).scalar() or 0)

    today_tok = int((await db.execute(select(func.sum(User.token_used)).where(User.updated_at >= today))).scalar() or 0)



    # vip distribution

    dist = {v: 0 for v in VIP_NAMES.values()}

    rows = (await db.execute(select(User.vip_level, func.count()).group_by(User.vip_level))).all()

    for lv, cnt in rows:

        dist[VIP_NAMES.get(lv or 0, "free")] = int(cnt or 0)



    # data rows

    users = (await db.execute(select(User).order_by(User.created_at.desc()).limit(100))).scalars().all()

    posts = (await db.execute(select(Post).options(joinedload(Post.author)).order_by(Post.created_at.desc()).limit(50))).unique().scalars().all()

    orders = (await db.execute(select(VipOrder).order_by(VipOrder.created_at.desc()).limit(12))).scalars().all()

    announcements = (await db.execute(select(Announcement).order_by(Announcement.created_at.desc()).limit(10))).scalars().all()



    max_vip = max(dist.values()) or 1

    vip_bars = "".join(

        f"<div class='bar'><span>{n}</span><i style='width:{c/max_vip*100:.0f}%'></i><b>{c}</b></div>"

        for n, c in dist.items()

    )



    user_rows = "".join(

        f"""<tr class="{'danger' if u.is_banned else ''}">

          <td><a class="userlink" href="/admin/users/{u.id}?token={token}"><b>{_esc(u.dawang_id or u.username)}</b></a><small>{_esc(u.nickname or '-')}</small></td>

          <td>Lv.{u.level or 1}<small>{u.xp or 0} XP</small></td>

          <td>VIP {u.vip_level or 0}<small>{_iso(u.vip_expire_at)[:10] if u.vip_expire_at else ('永久' if u.vip_level==99 else '-')}</small></td>

          <td>🪙{u.monthly_coins or 0}/{u.monthly_coins_max or 0}<small>永久{u.purchased_coins or 0}</small></td>

          <td>{u.token_used or 0:,}<small>限{u.token_limit or 0:,}</small></td>

          <td>{u.pomodoro_count or 0}</td>

          <td>{_iso(u.last_login_at)[:16] if u.last_login_at else '-'}</td>

          <td>{'封禁' if u.is_banned else '正常'} / {'白名单' if u.is_whitelist else '普通'}</td>

          <td class="actions">

            <button onclick="banUser('{u.id}')" class="btn-sm btn-red">{'解封' if u.is_banned else '封禁'}</button>

            <button onclick="wlUser('{u.id}')" class="btn-sm">{'取消白' if u.is_whitelist else '白名单'}</button>

            <button onclick="delUser('{u.id}','{_esc(u.dawang_id or u.username)}')" class="btn-sm btn-red">删除</button>

            <button onclick="openModal('{u.id}','{_esc(u.dawang_id or u.username)}','{_esc(u.nickname or '')}','{_esc(u.username)}')" class="btn-sm">管理</button>

          </td></tr>"""

        for u in users

    )



    post_rows = "".join(

        f"""<tr id="post_{p.id}">

          <td>{p.author.username if p.author else '?'}</td>

          <td>{(p.content or '')[:60]}</td>

          <td>👍{p.likes_count} | {p.visibility or 'public'}</td>

          <td>{_iso(p.created_at)[:10] if p.created_at else ''}</td>

          <td class="actions">

            <select id="pv_{p.id}" onchange="postAction('{p.id}','visibility')" style="width:auto;padding:4px;font-size:11px">

              <option value="public" {'selected' if (p.visibility or 'public')=='public' else ''}>公开</option>

              <option value="hidden" {'selected' if (p.visibility or '')=='hidden' else ''}>隐藏</option>

              <option value="private" {'selected' if (p.visibility or '')=='private' else ''}>仅作者</option>

            </select>

            <button onclick="postDelete('{p.id}')" class="btn-sm btn-red" style="font-size:10px">删除</button>

          </td></tr>"""

        for p in posts

    )

    order_rows = "".join(

        f"<tr><td>{_iso(o.created_at)[:16] if o.created_at else ''}</td><td>VIP{o.vip_level}</td><td>￥{o.amount:.2f}</td><td>{o.payment_method or '-'}</td><td>{o.status}</td></tr>"

        for o in orders

    ) or "<tr><td colspan='5'>暂无订单</td></tr>"

    ann_rows = "".join(

        f"<tr><td>{a.title}</td><td>{a.priority}</td><td>{'启用' if a.is_active else '停用'}</td><td>{_iso(a.created_at)[:10] if a.created_at else ''}</td></tr>"

        for a in announcements

    ) or "<tr><td colspan='4'>暂无公告</td></tr>"



    return HTMLResponse(f"""<!doctype html>

<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">

<title>西南大王管理后台</title>

<style>

*{{box-sizing:border-box}}body{{margin:0;background:#f5f2eb;color:#1c1917;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}}main{{max-width:1280px;margin:0 auto;padding:24px}}h1{{color:#1b3a2d;font-size:26px;margin:0 0 18px}}h2{{font-size:16px;color:#1b3a2d;margin:0 0 14px}}.grid{{display:grid;grid-template-columns:repeat(4,minmax(160px,1fr));gap:14px;margin-bottom:16px}}.card{{background:#fdfbf7;border-radius:12px;padding:18px;box-shadow:0 4px 12px rgba(27,58,45,.06);margin-bottom:16px}}.num{{font-size:30px;font-weight:800;color:#1b3a2d}}.label,small{{display:block;color:#8b6f5e;font-size:12px;margin-top:4px}}a{{color:#1b3a2d;text-decoration:none}}a.userlink:hover{{text-decoration:underline}}table{{width:100%;border-collapse:collapse;font-size:13px}}th,td{{text-align:left;border-bottom:1px solid #e8e3d7;padding:10px;vertical-align:top}}th{{color:#8b6f5e;background:#f5f2eb}}tr.danger{{background:#fff0f0}}button,.btn-sm{{background:#1b3a2d;color:white;border:0;border-radius:6px;padding:6px 10px;cursor:pointer;font-size:12px;display:inline-block;margin:1px 2px}}button:hover{{opacity:.85}}#toast{{position:fixed;top:16px;left:50%;transform:translateX(-50%);background:#1b3a2d;color:white;padding:12px 24px;border-radius:8px;z-index:9999;opacity:0;transition:opacity .3s;font-size:14px;pointer-events:none}}.btn-sm.btn-red{{background:#b91c1c}}.btn-sm.btn-gold{{background:#c4956a}}input,select,textarea{{width:100%;border:1px solid #e8e3d7;border-radius:8px;padding:8px;background:white;font-size:13px}}textarea{{min-height:78px}}form{{margin:0}}.actions form{{display:inline}}.two{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}.bar{{display:grid;grid-template-columns:70px 1fr 40px;gap:10px;align-items:center;margin:8px 0}}.bar i{{display:block;height:12px;background:#c4956a;border-radius:999px}}.bar b{{color:#1b3a2d}}.modal{{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,.5);z-index:100;justify-content:center;align-items:center}}.modal.show{{display:flex}}.modal-inner{{background:white;border-radius:14px;padding:24px;max-width:440px;width:90%;max-height:85vh;overflow-y:auto}}@media(max-width:900px){{.grid,.two{{grid-template-columns:1fr}}}}td small{{display:block;font-size:11px;color:#8b6f5e}}hr{{border:0;border-top:1px solid #e8e3d7;margin:12px 0}}.tip{{color:#8b6f5e;font-size:11px;margin-top:4px}}

</style></head><body><main>

<h1>西南大王 - 管理后台</h1>

<section class="grid">

  <div class="card"><div class="num">{total_users}</div><div class="label">总用户</div></div>

  <div class="card"><div class="num">{today_new}</div><div class="label">今日新增</div></div>

  <div class="card"><div class="num">{total_posts}</div><div class="label">帖子总数</div></div>

  <div class="card"><div class="num">{total_pomo:,}</div><div class="label">累计番茄</div></div>

  <div class="card"><div class="num">{dau}</div><div class="label">今日活跃</div></div>

  <div class="card"><div class="num">{total_tok:,}</div><div class="label">Token总消耗</div></div>

  <div class="card"><div class="num">{today_tok:,}</div><div class="label">今日Token</div></div>

  <div class="card"><div class="num">￥{today_rev:.2f}</div><div class="label">今日收入</div></div>

  <div class="card"><div class="num">￥{month_rev:.2f}</div><div class="label">本月收入</div></div>

  <div class="card"><div class="num">￥{total_rev:.2f}</div><div class="label">累计收入</div></div>

  <div class="card"><div class="num">￥{round(today_tok/1000*0.002,4)}</div><div class="label">今日API费用估</div></div>

  <div class="card"><div class="num">￥{round(total_tok/1000*0.002,4)}</div><div class="label">累计API费用估</div></div>

</section>



<section class="two">

  <div class="card"><h2>VIP 分布</h2>{vip_bars}</div>

  <div class="card"><h2>快捷导航</h2>

    <a href="/admin/page/tokens?token={token}" class="btn-sm" style="display:block;margin-bottom:6px;text-align:center;text-decoration:none;color:white">📊 Token消耗详情</a>

    <a href="/admin/page/redeem-codes?token={token}" class="btn-sm" style="display:block;margin-bottom:6px;text-align:center;text-decoration:none;color:white">🎫 兑换码管理</a>

    <a href="/admin/page/revenue?token={token}" class="btn-sm" style="display:block;margin-bottom:6px;text-align:center;text-decoration:none;color:white">💰 收入明细</a>

    <a href="/admin/page/coins?token={token}" class="btn-sm" style="display:block;margin-bottom:6px;text-align:center;text-decoration:none;color:white">🪙 研AI币统计</a>

    <a href="/admin/page/feedbacks?token={token}" class="btn-sm" style="display:block;margin-bottom:6px;text-align:center;text-decoration:none;color:white">📝 用户反馈</a>
    <button id="aiBtn" onclick="toggleAI()" class="btn-sm" style="display:block;width:100%;margin-bottom:6px;text-align:center;font-size:13px;background:#b91c1c">🔌 停用AI</button>

  </div>

</section>



<section class="card"><h2>🎫 生成兑换码</h2>

  <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:end">

    <select id="rcProduct" onchange="onRcProductChange()" style="flex:1;min-width:130px">

      <option value="silver">银卡 (1500币/月 ¥9.9)</option>

      <option value="gold">金卡 (5000币/月 ¥19.9)</option>

      <option value="black">黑卡 (12000币/月 ¥29.9)</option>

      <option value="yanwang">研王爷 (20000币/月 ¥298一次性)</option>

      <option value="coin_pack">币包</option>

    </select>

    <select id="rcCoinPack" style="flex:1;min-width:130px;display:none">

      <option value="pack_100">100币 ¥6</option>

      <option value="pack_500">500币 ¥24</option>

      <option value="pack_1500">1500币 ¥58</option>

      <option value="pack_5000">5000币 ¥148</option>

      <option value="pack_12000">12000币 ¥288</option>

    </select>

    <input id="rcCount" value="10" type="number" min="1" max="1000" style="flex:1;min-width:80px" placeholder="数量">

    <button onclick="genCodes()" style="flex:0;white-space:nowrap">生成兑换码</button>

  </div>

  <div class="tip">选择VIP类型时自动忽略币包选项。研王爷为一次性永久VIP。生成后可导出CSV批量分发。</div>

</section>



<section class="card"><h2>📢 公告 + 全员通知</h2>

  <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:end">

    <input id="annTitle" placeholder="公告标题" style="flex:1;min-width:120px">

    <input id="annPriority" value="0" type="number" style="width:70px" placeholder="优先级">

  </div>

  <textarea id="annContent" placeholder="公告内容" style="margin-top:8px"></textarea>

  <div style="display:flex;gap:8px;margin-top:8px">

    <button onclick="postAnnouncement()">发布公告</button>

    <button onclick="notifyAll()" style="background:#c4956a">📲 推送全员通知</button>

  </div>

  <div class="tip">发布公告仅显示在公告列表。推送通知会发送到所有用户的手机通知栏。</div>

</section>



<section class="card"><h2>公告列表</h2><table><tr><th>标题</th><th>优先级</th><th>状态</th><th>时间</th></tr>{ann_rows}</table></section>



<section class="card"><h2>最近付费订单</h2><table><tr><th>时间</th><th>VIP</th><th>金额</th><th>方式</th><th>状态</th></tr>{order_rows}</table>

<div class="tip">管理员授予VIP时自动生成订单并计入收入。</div></section>



<section class="card"><h2>用户列表（最新100）</h2><table><tr><th>用户</th><th>等级</th><th>VIP</th><th>研AI币</th><th>Token</th><th>番茄</th><th>活跃</th><th>状态</th><th>操作</th></tr>{user_rows}</table></section>



<section class="card"><h2>最近帖子</h2><table><tr><th>用户</th><th>内容</th><th>互动/可见</th><th>日期</th><th>操作</th></tr>{post_rows}</table></section>

<div id="toast"></div></main>



<!-- quick manage modal -->

<div id="qmodal" class="modal"><div class="modal-inner" id="qmodalBody"></div></div>



<script>

function toast(msg,isErr){{var t=document.getElementById("toast");t.textContent=msg;t.style.background=isErr?"#b91c1c":"#1b3a2d";t.style.opacity="1";setTimeout(function(){{t.style.opacity="0"}},2500)}};const TK='{token}';

let _uid='';



// ── redeem code product toggle ──

function onRcProductChange() {{

  var v=document.getElementById('rcProduct').value;

  document.getElementById('rcCoinPack').style.display=(v==='coin_pack')?'block':'none';

}}



// ── generate redeem codes ──

async function genCodes() {{

  var pt=document.getElementById('rcProduct').value;

  var body={{product_type:pt,count:parseInt(document.getElementById('rcCount').value)||10}};

  if(pt==='coin_pack') body.coin_pack_id=document.getElementById('rcCoinPack').value;

  try{{

    var r=await fetch('/admin/redeem-codes/generate?token='+TK,{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify(body)}});

    if(!r.ok){{var e=await r.json();alert('错误: '+(e.detail||r.status));return}}

    var d=await r.json();

    alert('已生成 '+d.count+' 个兑换码\\n\\n'+d.codes.slice(0,10).join('\\n')+(d.codes.length>10?'\\n...共'+d.codes.length+'个':''));

    if(confirm('刷新页面查看？'))location.reload();

  }}catch(e){{alert('网络错误: '+e.message)}}

}}



// ── announcement + notify ──

async function postAnnouncement() {{

  var t=document.getElementById('annTitle').value.trim();

  var c=document.getElementById('annContent').value.trim();

  var p=parseInt(document.getElementById('annPriority').value)||0;

  if(!t||!c){{alert('标题和内容不能为空');return}}

  try{{

    var r=await fetch('/admin/announcement?token='+TK,{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{title:t,content:c,priority:p}})}});

    if(!r.ok){{var e=await r.json();alert('失败: '+(e.detail||r.status));return}}

    // also broadcast notification

    await fetch('/admin/notify-all?title='+encodeURIComponent(t)+'&body='+encodeURIComponent(c)+'&token='+TK,{{method:'POST'}});

    location.reload();

  }}catch(e){{alert('网络错误: '+e.message)}}

}}

async function notifyAll() {{

  var t=document.getElementById('annTitle').value.trim();

  var c=document.getElementById('annContent').value.trim();

  if(!t||!c){{alert('标题和内容不能为空');return}}

  try{{

    var r=await fetch('/admin/notify-all?title='+encodeURIComponent(t)+'&body='+encodeURIComponent(c)+'&token='+TK,{{method:'POST'}});

    if(r.ok){{alert('已向所有用户推送通知');location.reload()}} else {{var e=await r.json();alert('失败: '+(e.detail||r.status))}}

  }}catch(e){{alert('网络错误: '+e.message)}}

}}



// ── ban / whitelist / delete ──

async function banUser(id){{await fetch('/admin/users/'+id+'/ban?token='+TK,{{method:'POST'}});location.reload()}}

async function wlUser(id){{await fetch('/admin/users/'+id+'/whitelist?token='+TK,{{method:'POST'}});location.reload()}}

async function delUser(id,name){{if(!confirm('确定要永久删除用户 '+name+' 吗？此操作不可撤销！'))return;await fetch('/admin/users/'+id+'/delete?token='+TK,{{method:'DELETE'}});location.reload()}}



// ── quick modal ──

function openModal(id,dawang,nick,uname){{

  _uid=id;

  document.getElementById('qmodalBody').innerHTML=

   '<h3 style="margin:0 0 12px">管理 <b>'+dawang+'</b> ('+nick+')</h3>'+

   '<div style="margin-bottom:10px"><b>修改昵称</b>'+

     '<div style="display:flex;gap:4px;margin-top:4px">'+

       '<input id="muNick" value="'+nick+'" style="flex:1;padding:6px">'+

       '<button onclick="changeNick()">改昵称</button>'+

       '<button onclick="randomNick()" style="background:#8b6f5e">随机</button>'+

     '</div></div>'+

   '<div style="margin-bottom:10px"><b>修改用户名</b>'+

     '<div style="display:flex;gap:4px;margin-top:4px">'+

       '<input id="muUname" value="'+uname+'" style="flex:1;padding:6px">'+

       '<button onclick="changeUname()">改名</button>'+

       '<button onclick="randomUname()" style="background:#8b6f5e">随机</button>'+

     '</div></div>'+

   '<hr>'+

   '<div style="margin-bottom:10px"><b>封禁/禁言</b>'+

     '<div style="display:flex;gap:4px;margin-top:4px;flex-wrap:wrap">'+

       '<button onclick="timeBan(7)">限封7天</button>'+

       '<button onclick="timeBan(30)">限封30天</button>'+

       '<button onclick="muteUser(24)">禁言24h</button>'+

       '<button onclick="muteUser(168)">禁言7天</button>'+

       '<button onclick="unmuteUser()" style="background:#8b6f5e">解禁</button>'+

       '<button onclick="unbanUser()" style="background:#8b6f5e">解封</button>'+

     '</div></div>'+

     '<div style="display:flex;gap:4px;margin-top:4px;flex-wrap:wrap">'+

       '<button onclick="grantVip(1,30)">银卡30天</button>'+

       '<button onclick="grantVip(2,30)">金卡30天</button>'+

       '<button onclick="grantVip(3,30)">黑卡30天</button>'+

       '<button onclick="grantVip(99,0)" class="btn-gold">给研王爷(永久)</button>'+

       '<button onclick="cancelVip()" style="background:#b91c1c">取消VIP</button>'+

     '</div></div>'+

   '<hr>'+

   '<div style="margin-bottom:10px"><b>VIP管理</b>'+

     '<div style="display:flex;gap:4px;margin-top:4px;flex-wrap:wrap">'+

       '<button onclick="grantVip(1,30)">银卡30天</button>'+

       '<button onclick="grantVip(2,30)">金卡30天</button>'+

       '<button onclick="grantVip(3,30)">黑卡30天</button>'+

       '<button onclick="grantVip(99,0)" class="btn-gold">研王爷永久</button>'+

       '<button onclick="cancelVip()" style="background:#b91c1c">取消VIP</button>'+

     '</div></div>'+

   '<hr>'+

   '<div style="margin-bottom:10px"><b>研AI币调整</b>'+

     '<input id="muMth" value="0" type="number" placeholder="月度币增减" style="padding:6px;margin-bottom:4px">'+

     '<input id="muPur" value="0" type="number" placeholder="永久币增减" style="padding:6px;margin-bottom:4px">'+

     '<input id="muReason" value="管理员手动调整" placeholder="原因" style="padding:6px;margin-bottom:4px">'+

     '<button onclick="adjustCoins()">确认调整</button></div>'+

   '<hr>'+

   '<div style="margin-bottom:10px"><b>Token调整</b>'+

     '<div style="display:flex;gap:4px;margin-top:4px">'+

       '<input id="muTok" value="0" type="number" placeholder="增减量" style="flex:1;padding:6px">'+

       '<input id="muTokR" value="管理员调整" placeholder="原因" style="flex:1;padding:6px">'+

       '<button onclick="adjustTokens()">确认</button>'+

     '</div></div>'+

   '<button onclick="closeModal()" style="background:#8b6f5e;width:100%">关闭</button>'+

   '<div class="tip">所有操作写入AdminLog</div>';

  document.getElementById('qmodal').classList.add('show');

}}

function closeModal(){{document.getElementById('qmodal').classList.remove('show')}}

document.getElementById('qmodal').addEventListener('click',function(e){{if(e.target===this)closeModal()}})



// modal actions

async function changeNick(){{var v=document.getElementById('muNick').value.trim();if(!v)return;await api('/admin/users/'+_uid+'/nickname','PUT',{{new_nickname:v}});closeModal();toast("修改成功")}}

async function changeUname(){{var v=document.getElementById('muUname').value.trim();if(!v)return;await api('/admin/users/'+_uid+'/username','PUT',{{new_username:v}});closeModal();toast("修改成功")}}

async function randomUname(){{await fetch('/admin/users/'+_uid+'/random-username?token='+TK,{{method:'POST'}});closeModal();toast("修改成功")}}

async function randomNick(){{await fetch('/admin/users/'+_uid+'/random-nickname?token='+TK,{{method:'POST'}});closeModal();toast("修改成功")}}

async function timeBan(days){{if(!confirm('确定限时封禁'+days+'天？'))return;await fetch('/admin/users/'+_uid+'/time-ban?days='+days+'&reason=管理员操作&token='+TK,{{method:'POST'}});closeModal();toast("修改成功")}}

async function muteUser(hours){{await fetch('/admin/users/'+_uid+'/mute?hours='+hours+'&reason=管理员操作&token='+TK,{{method:'POST'}});closeModal();toast("修改成功")}}

async function unmuteUser(){{await fetch('/admin/users/'+_uid+'/unmute?token='+TK,{{method:'POST'}});closeModal();toast("修改成功")}}

async function unbanUser(){{await fetch('/admin/users/'+_uid+'/ban?token='+TK,{{method:'POST'}});closeModal();toast("修改成功")}}

async function grantVip(lv,days){{await api('/admin/users/'+_uid+'/grant-vip','POST',{{vip_level:lv,days:days,reason:'管理员快速授予'}});closeModal();toast("修改成功")}}

async function cancelVip(){{if(!confirm('确认取消此用户VIP？'))return;await fetch('/admin/users/'+_uid+'/cancel-vip?reason=管理员取消&token='+TK,{{method:'POST'}});closeModal();toast("修改成功")}}

async function adjustCoins(){{var m=parseInt(document.getElementById('muMth').value)||0;var p=parseInt(document.getElementById('muPur').value)||0;var r=document.getElementById('muReason').value;await api('/admin/users/'+_uid+'/adjust-coins','POST',{{monthly_delta:m,purchased_delta:p,reason:r}});closeModal();toast("修改成功")}}

async function adjustTokens(){{var d=parseInt(document.getElementById('muTok').value)||0;var r=document.getElementById('muTokR').value;await api('/admin/users/'+_uid+'/adjust-tokens','POST',{{delta:d,reason:r}});closeModal();toast("修改成功")}}



// helper

async function api(url,method,body){{try{{var r=await fetch(url+'?token='+TK,{{method:method,headers:{{'Content-Type':'application/json'}},body:JSON.stringify(body)}});if(!r.ok){{var e=await r.json();alert('错误: '+(e.detail||r.status))}}else{{var d=await r.json();if(d.success===false)alert('失败')}}}}catch(e){{alert('网络错误: '+e.message)}}}}



async function postAction(pid,action){{var v=document.getElementById('pv_'+pid).value;var r=await fetch('/admin/posts/'+pid+'/visibility?visibility='+v+'&token='+TK,{{method:'PUT'}});toast(r.ok?'可见性: '+v:'失败',!r.ok)}}

async function postDelete(pid)

{{if(!confirm('确定删除此帖子？'))return;var notify=confirm('是否向发帖用户发送删除通知？');var r=await fetch('/admin/posts/'+pid+'?token='+TK+'&notify='+notify,{{method:'DELETE'}});if(r.ok){{toast('帖子已删除'+(notify?' (已通知用户)':''));var tr=document.getElementById('post_'+pid);if(tr)tr.remove()}}else toast('删除失败',1)}}

async function toggleAI(){{
  var r=await fetch("/admin/ai-toggle?token="+TK,{{method:"POST"}});
  var d=await r.json();
  var btn=document.getElementById("aiBtn");
  if(btn){{
    btn.textContent=d.ai_enabled?"🔌 停用AI":"🔌 启用AI";
    btn.style.background=d.ai_enabled?"#b91c1c":"#1b3a2d";
  }}
  toast(d.message);
}}

</script>

</body></html>""")





# ═══════════════════════════════════════

#  HTML PAGES (for browser navigation)

# ═══════════════════════════════════════



@router.get("/page/tokens", response_class=HTMLResponse)

async def tokens_page(token: str = Query(default=""), db: AsyncSession = Depends(get_db)):

    chk(token)

    total_used = int((await db.execute(select(func.sum(User.token_used)))).scalar() or 0)

    total_limit = int((await db.execute(select(func.sum(User.token_limit)))).scalar() or 0)

    user_count = int((await db.execute(select(func.count()).select_from(User))).scalar() or 1)

    today = today_utc()

    today_used = int((await db.execute(select(func.sum(User.token_used)).where(User.updated_at >= today))).scalar() or 0)

    top = (await db.execute(select(User.username, User.nickname, User.dawang_id, User.token_used, User.token_limit).order_by(User.token_used.desc()).limit(50))).all()

    top_rows = "".join(f"<tr><td>{_esc(r[0])}</td><td>{_esc(r[1] or '-')}</td><td>{_esc(r[2] or '-')}</td><td>{r[3]:,}</td><td>{r[4]:,}</td><td>￥{round((r[3] or 0)/1000*0.002,4)}</td></tr>" for r in top) or "<tr><td colspan='6'>暂无数据</td></tr>"

    return HTMLResponse(f"""<!doctype html>

<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">

<title>Token消耗统计</title>

<style>

*{{box-sizing:border-box}}body{{margin:0;background:#f5f2eb;color:#1c1917;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}}main{{max-width:1180px;margin:0 auto;padding:24px}}a{{color:#1b3a2d;text-decoration:none}}h1{{font-size:22px;margin:0 0 16px}}h2{{font-size:16px;margin:0 0 12px}}.card{{background:#fdfbf7;border-radius:12px;padding:18px;box-shadow:0 4px 12px rgba(27,58,45,.06);margin-bottom:16px}}.grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}}.num{{font-size:28px;font-weight:800;color:#1b3a2d}}.label{{color:#8b6f5e;font-size:12px}}table{{width:100%;border-collapse:collapse;font-size:13px}}th,td{{text-align:left;border-bottom:1px solid #e8e3d7;padding:8px}}th{{color:#8b6f5e;background:#f5f2eb}}

</style></head><body><main>

<p><a href="/admin?token={token}">← 返回</a></p>

<h1>📊 API Token 消耗统计</h1>

<section class="grid" style="margin-bottom:16px">

  <div class="card"><div class="num">{total_used:,}</div><div class="label">总消耗Token</div></div>

  <div class="card"><div class="num">{today_used:,}</div><div class="label">今日消耗</div></div>

  <div class="card"><div class="num">{user_count}</div><div class="label">用户数</div></div>

  <div class="card"><div class="num">{round(total_used/user_count,0):,.0f}</div><div class="label">人均消耗</div></div>

  <div class="card"><div class="num">{total_limit:,}</div><div class="label">总额度</div></div>

  <div class="card"><div class="num">￥{round(total_used/1000*0.002,4)}</div><div class="label">累计费用估算</div></div>

  <div class="card"><div class="num">￥{round(today_used/1000*0.002,4)}</div><div class="label">今日费用估算</div></div>

  <div class="card"><div class="num">{(total_used/max(user_count,1)/1000*0.002):.4f}</div><div class="label">人均费用/天</div></div>

</section>

<section class="card"><h2>Token消耗 Top 50</h2><table><tr><th>用户名</th><th>昵称</th><th>大王号</th><th>已消耗</th><th>额度</th><th>费用估</th></tr>{top_rows}</table></section>

<div id="toast"></div></main></body></html>""")





@router.get("/page/redeem-codes", response_class=HTMLResponse)

async def redeem_codes_page(token: str = Query(default=""), batch_id: str | None = None, page: int = 1, db: AsyncSession = Depends(get_db)):

    chk(token)

    stmt = select(RedeemCode)

    if batch_id: stmt = stmt.where(RedeemCode.batch_id == batch_id)

    total = await _cnt(db, select(func.count()).select_from(stmt.subquery()))

    page_size = 50; page = max(page, 1)

    codes = (await db.execute(stmt.order_by(RedeemCode.created_at.desc()).offset((page-1)*page_size).limit(page_size))).scalars().all()

    code_rows = "".join(

        f"<tr><td>{c.code}</td><td>{c.batch_id}</td><td>{c.product_type}</td><td>{c.vip_level or c.coins or '-'}</td><td>{'已用' if c.is_used else '可用'}</td><td>{_esc(c.used_by or '-')}</td><td>{_iso(c.used_at)[:19] if c.used_at else '-'}</td><td>{_iso(c.created_at)[:19] if c.created_at else '-'}</td></tr>"

        for c in codes

    ) or "<tr><td colspan='8'>暂无兑换码</td></tr>"

    # batch list for filter

    batches = (await db.execute(select(RedeemCode.batch_id, func.count()).group_by(RedeemCode.batch_id).order_by(RedeemCode.batch_id.desc()).limit(20))).all()

    batch_opts = "".join(f'<option value="{b[0]}">{b[0]} ({b[1]}个)</option>' for b in batches)

    return HTMLResponse(f"""<!doctype html>

<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">

<title>兑换码管理</title>

<style>

*{{box-sizing:border-box}}body{{margin:0;background:#f5f2eb;color:#1c1917;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}}main{{max-width:1280px;margin:0 auto;padding:24px}}a{{color:#1b3a2d;text-decoration:none}}h1{{font-size:22px;margin:0 0 16px}}.card{{background:#fdfbf7;border-radius:12px;padding:18px;box-shadow:0 4px 12px rgba(27,58,45,.06);margin-bottom:16px}}table{{width:100%;border-collapse:collapse;font-size:12px}}th,td{{text-align:left;border-bottom:1px solid #e8e3d7;padding:6px 8px}}th{{color:#8b6f5e;background:#f5f2eb}}button{{background:#1b3a2d;color:white;border:0;border-radius:6px;padding:6px 12px;cursor:pointer;font-size:13px}}select{{padding:6px;border:1px solid #e8e3d7;border-radius:6px}}

</style></head><body><main>

<p><a href="/admin?token={token}">← 返回</a></p>

<h1>🎫 兑换码管理 <small style="font-size:14px;color:#8b6f5e">共 {total} 个</small></h1>

<section class="card">

  <div style="display:flex;gap:8px;align-items:end;flex-wrap:wrap;margin-bottom:14px">

    <select onchange="location.href='/admin/page/redeem-codes?token={token}&batch_id='+this.value" style="flex:1;min-width:200px">

      <option value="">--按批次筛选--</option>

      {batch_opts}

    </select>

    <a href="/admin/redeem-codes/export?token={token}{'&batch_id='+batch_id if batch_id else ''}" class="btn-sm" style="display:inline-block;background:#8b6f5e;color:white;border-radius:6px;padding:8px 14px;text-decoration:none;font-size:13px">📥 导出CSV</a>

  </div>

  <table><tr><th>兑换码</th><th>批次</th><th>类型</th><th>VIP/币数</th><th>状态</th><th>使用者</th><th>使用时间</th><th>生成时间</th></tr>{code_rows}</table>

  <div style="margin-top:12px;display:flex;gap:8px">

    <a href="/admin/page/redeem-codes?token={token}&page={page-1}" class="btn-sm" style="{'opacity:.4;pointer-events:none' if page<=1 else ''};display:inline-block;background:#8b6f5e;color:white;border-radius:6px;padding:6px 12px;text-decoration:none;font-size:12px">上一页</a>

    <a href="/admin/page/redeem-codes?token={token}&page={page+1}" class="btn-sm" style="display:inline-block;background:#8b6f5e;color:white;border-radius:6px;padding:6px 12px;text-decoration:none;font-size:12px">下一页</a>

    <span style="font-size:12px;color:#8b6f5e;align-self:center">第{page}页</span>

  </div>

</section>

<div id="toast"></div></main></body></html>""")





@router.get("/page/revenue", response_class=HTMLResponse)

async def revenue_page(token: str = Query(default=""), db: AsyncSession = Depends(get_db)):

    chk(token)

    stmt = select(VipOrder).where(VipOrder.status == "paid").order_by(VipOrder.created_at.desc())

    orders = (await db.execute(stmt)).scalars().all()

    by_date: dict = {}

    by_product: dict = {}

    total = 0.0

    for o in orders:

        day = o.created_at.date().isoformat() if o.created_at else "?"

        by_date[day] = by_date.get(day, 0.0) + float(o.amount or 0)

        prod = VIP_LABELS.get(o.vip_level, f"VIP{o.vip_level}")

        it = by_product.setdefault(prod, {"product": prod, "count": 0, "amount": 0.0})

        it["count"] += 1

        it["amount"] += float(o.amount or 0)

        total += float(o.amount or 0)

    date_rows = "".join(f"<tr><td>{k}</td><td>￥{v:.2f}</td></tr>" for k, v in sorted(by_date.items(), reverse=True)[:60]) or "<tr><td colspan='2'>暂无数据</td></tr>"

    prod_rows = "".join(f"<tr><td>{v['product']}</td><td>{v['count']}单</td><td>￥{v['amount']:.2f}</td></tr>" for v in sorted(by_product.values(), key=lambda x: x['amount'], reverse=True)) or "<tr><td colspan='3'>暂无</td></tr>"

    order_rows = "".join(f"<tr><td>{_iso(o.created_at)[:19] if o.created_at else '-'}</td><td>{VIP_LABELS.get(o.vip_level,'VIP'+str(o.vip_level))}</td><td>￥{o.amount:.2f}</td><td>{o.payment_method or '-'}</td><td>{o.status}</td></tr>" for o in orders[:100]) or "<tr><td colspan='5'>暂无订单</td></tr>"

    return HTMLResponse(f"""<!doctype html>

<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">

<title>收入明细</title>

<style>*{{box-sizing:border-box}}body{{margin:0;background:#f5f2eb;color:#1c1917;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}}main{{max-width:1180px;margin:0 auto;padding:24px}}a{{color:#1b3a2d;text-decoration:none}}h1{{font-size:22px;margin:0 0 16px}}h2{{font-size:16px;margin:0 0 12px}}.card{{background:#fdfbf7;border-radius:12px;padding:18px;box-shadow:0 4px 12px rgba(27,58,45,.06);margin-bottom:16px}}.grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}}.num{{font-size:28px;font-weight:800;color:#1b3a2d}}.label{{color:#8b6f5e;font-size:12px}}table{{width:100%;border-collapse:collapse;font-size:13px}}th,td{{text-align:left;border-bottom:1px solid #e8e3d7;padding:8px}}th{{color:#8b6f5e;background:#f5f2eb}}.two{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}

</style></head><body><main>

<p><a href="/admin?token={token}">← 返回</a></p>

<h1>💰 收入明细</h1>

<section class="grid" style="margin-bottom:16px">

  <div class="card"><div class="num">￥{total:.2f}</div><div class="label">累计收入</div></div>

  <div class="card"><div class="num">{sum(v['count'] for v in by_product.values())}</div><div class="label">总订单数</div></div>

  <div class="card"><div class="num">{len(by_date)}</div><div class="label">有收入天数</div></div>

</section>

<section class="two">

  <div class="card"><h2>每日收入（最近60天）</h2><table><tr><th>日期</th><th>金额</th></tr>{date_rows}</table></div>

  <div class="card"><h2>按产品分类</h2><table><tr><th>产品</th><th>销量</th><th>金额</th></tr>{prod_rows}</table></div>

</section>

<section class="card"><h2>最近100笔订单</h2><table><tr><th>时间</th><th>产品</th><th>金额</th><th>方式</th><th>状态</th></tr>{order_rows}</table></section>

<div id="toast"></div></main></body></html>""")





@router.get("/page/coins", response_class=HTMLResponse)

async def coins_page(token: str = Query(default=""), db: AsyncSession = Depends(get_db)):

    chk(token)

    purchased = int((await db.execute(select(func.sum(RedeemHistory.coins_added)))).scalar() or 0)

    consumed = int((await db.execute(select(func.sum(User.token_used)))).scalar() or 0)

    total_monthly = int((await db.execute(select(func.sum(User.monthly_coins)))).scalar() or 0)

    total_purchased = int((await db.execute(select(func.sum(User.purchased_coins)))).scalar() or 0)

    user_count = max(int((await db.execute(select(func.count()).select_from(User))).scalar() or 1), 1)

    # top coin holders

    top_coins = (await db.execute(select(User.username, User.nickname, User.monthly_coins, User.purchased_coins).order_by((User.monthly_coins + User.purchased_coins).desc()).limit(30))).all()

    coin_rows = "".join(f"<tr><td>{_esc(r[0])}</td><td>{_esc(r[1] or '-')}</td><td>{r[2] or 0}</td><td>{r[3] or 0}</td><td>{(r[2] or 0)+(r[3] or 0)}</td></tr>" for r in top_coins) or "<tr><td colspan='5'>暂无数据</td></tr>"

    return HTMLResponse(f"""<!doctype html>

<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">

<title>研AI币统计</title>

<style>*{{box-sizing:border-box}}body{{margin:0;background:#f5f2eb;color:#1c1917;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}}main{{max-width:1180px;margin:0 auto;padding:24px}}a{{color:#1b3a2d;text-decoration:none}}h1{{font-size:22px;margin:0 0 16px}}.card{{background:#fdfbf7;border-radius:12px;padding:18px;box-shadow:0 4px 12px rgba(27,58,45,.06);margin-bottom:16px}}.grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}}.num{{font-size:28px;font-weight:800;color:#1b3a2d}}.label{{color:#8b6f5e;font-size:12px}}table{{width:100%;border-collapse:collapse;font-size:13px}}th,td{{text-align:left;border-bottom:1px solid #e8e3d7;padding:8px}}th{{color:#8b6f5e;background:#f5f2eb}}

</style></head><body><main>

<p><a href="/admin?token={token}">← 返回</a></p>

<h1>🪙 研AI币统计</h1>

<section class="grid" style="margin-bottom:16px">

  <div class="card"><div class="num">{purchased:,}</div><div class="label">累计充值币</div></div>

  <div class="card"><div class="num">{consumed:,}</div><div class="label">Token消耗</div></div>

  <div class="card"><div class="num">{total_monthly:,}</div><div class="label">用户月度币余额</div></div>

  <div class="card"><div class="num">{total_purchased:,}</div><div class="label">用户永久币余额</div></div>

  <div class="card"><div class="num">{round(consumed/user_count,1):,}</div><div class="label">人均Token消耗</div></div>

  <div class="card"><div class="num">{round(purchased/user_count,1):,}</div><div class="label">人均充值币</div></div>

  <div class="card"><div class="num">{user_count}</div><div class="label">用户总数</div></div>

  <div class="card"><div class="num">{(total_monthly+total_purchased):,}</div><div class="label">用户总币余额</div></div>

</section>

<section class="card"><h2>研AI币余额 Top 30</h2><table><tr><th>用户名</th><th>昵称</th><th>月度币</th><th>永久币</th><th>总余额</th></tr>{coin_rows}</table></section>

<div id="toast"></div></main></body></html>""")





# ═══════════════════════════════════════

#  JSON APIs

# ═══════════════════════════════════════

@router.get("/dashboard")

async def dashboard_json(token: str = Query(default=""), db: AsyncSession = Depends(get_db)):

    chk(token)

    today = today_utc()

    month_start = today.replace(day=1)

    return {

        "totalUsers": await _cnt(db, select(func.count()).select_from(User)),

        "todayNewUsers": await _cnt(db, select(func.count()).select_from(User).where(User.created_at >= today)),

        "totalPosts": await _cnt(db, select(func.count()).select_from(Post)),

        "totalPomodoros": int((await db.execute(select(func.sum(User.pomodoro_count)))).scalar() or 0),

        "dailyActiveUsers": await _cnt(db, select(func.count()).select_from(User).where(or_(User.last_login_at >= today, User.updated_at >= today))),

        "totalRevenue": float((await db.execute(select(func.sum(VipOrder.amount)).where(VipOrder.status == "paid"))).scalar() or 0),

        "todayRevenue": float((await db.execute(select(func.sum(VipOrder.amount)).where(VipOrder.status == "paid", VipOrder.created_at >= today))).scalar() or 0),

        "monthRevenue": float((await db.execute(select(func.sum(VipOrder.amount)).where(VipOrder.status == "paid", VipOrder.created_at >= month_start))).scalar() or 0),

    }





@router.get("/users")

async def list_users_json(token: str = Query(default=""), vip_level: int | None = None, keyword: str | None = None, sort_by: str = "created_at", page: int = 1, page_size: int = 30, db: AsyncSession = Depends(get_db)):

    chk(token)

    page = max(page, 1); page_size = min(max(page_size, 1), 100)

    stmt = select(User)

    if vip_level is not None: stmt = stmt.where(User.vip_level == vip_level)

    if keyword:

        like = f"%{keyword}%"

        stmt = stmt.where(or_(User.username.like(like), User.nickname.like(like), User.dawang_id.like(like), User.phone.like(like)))

    total = await _cnt(db, select(func.count()).select_from(stmt.subquery()))

    sort_map = {"xp": User.xp.desc(), "vip_level": User.vip_level.desc(), "pomodoro": User.pomodoro_count.desc(), "last_active": User.last_login_at.desc().nullslast(), "created_at": User.created_at.desc()}

    stmt = stmt.order_by(sort_map.get(sort_by, User.created_at.desc())).offset((page - 1) * page_size).limit(page_size)

    users = (await db.execute(stmt)).scalars().all()

    return {"total": total, "page": page, "pageSize": page_size, "users": [

        {"id": u.id, "username": u.username, "nickname": u.nickname, "dawangId": u.dawang_id, "phone": u.phone, "xp": u.xp or 0, "level": u.level or 1, "vipLevel": u.vip_level or 0, "vipExpireAt": _iso(u.vip_expire_at), "pomodoroCount": u.pomodoro_count or 0, "signInStreak": u.sign_in_streak or 0, "lastActiveAt": _iso(u.last_login_at or u.updated_at), "tokenUsed": u.token_used, "tokenLimit": u.token_limit, "isBanned": u.is_banned, "isWhitelist": u.is_whitelist, "createdAt": _iso(u.created_at)}

        for u in users

    ]}





# ── user detail page ──

@router.get("/users/{user_id}", response_class=HTMLResponse)

async def user_detail_page(user_id: str, token: str = Query(default=""), db: AsyncSession = Depends(get_db)):

    chk(token)

    u = await db.get(User, user_id)

    if not u: raise HTTPException(404, detail="user not found")



    async def latest(model, order_col, limit=20):

        return (await db.execute(select(model).where(model.user_id == user_id).order_by(order_col.desc()).limit(limit))).scalars().all()



    timeline = []

    for r in await latest(SignInRecord, SignInRecord.created_at, 30):

        timeline.append((_iso(r.created_at) or "", "签到", f"{r.date} 连续{r.streak_day}天 +{r.xp_earned}XP"))

    for r in await latest(XpHistory, XpHistory.created_at, 30):

        timeline.append((_iso(r.created_at) or "", "经验", f"{r.action} {r.amount:+d}XP"))

    for r in await latest(RedeemHistory, RedeemHistory.created_at, 20):

        timeline.append((_iso(r.created_at) or "", "兑换", f"{r.product_name} +{r.coins_added}币"))

    for r in await latest(ChatMessage, ChatMessage.created_at, 30):

        timeline.append((_iso(r.created_at) or "", "AI聊天", (r.content or "")[:120]))

    for r in await latest(PomodoroRecord, PomodoroRecord.created_at, 30):

        timeline.append((_iso(r.created_at) or "", "番茄", f"{r.subject} {r.duration_minutes or r.planned_minutes}min {r.status}"))

    for r in await latest(UserAnswer, UserAnswer.answered_at, 30):

        timeline.append((_iso(r.answered_at) or "", "每日一题", f"{'✅' if r.is_correct else '❌'} {r.user_choice}"))

    for r in await latest(ErrorNote, ErrorNote.created_at, 20):

        timeline.append((_iso(r.created_at) or "", "错题", f"{r.source} 错{r.wrong_count}次"))

    for r in await latest(DiaryEntry, DiaryEntry.created_at, 20):

        timeline.append((_iso(r.created_at) or "", "日记", f"{r.date} {r.mood or ''} {(r.content or '')[:80]}"))

    for r in await latest(UserExam, UserExam.created_at, 20):

        timeline.append((_iso(r.created_at) or "", "模考", f"{r.total_score}/{r.max_score}"))

    for r in await latest(InterviewSession, InterviewSession.started_at, 20):

        timeline.append((_iso(r.started_at) or "", "面试", f"{r.type} {r.status}"))

    for r in await latest(StudyPlan, StudyPlan.created_at, 20):

        timeline.append((_iso(r.created_at) or "", "计划", f"{r.type} 完成率{int((r.completion_rate or 0)*100)}%"))

    for r in (await db.execute(select(Post).where(Post.user_id == user_id).order_by(Post.created_at.desc()).limit(20))).scalars().all():

        timeline.append((_iso(r.created_at) or "", "帖子", f"👍{r.likes_count} {(r.content or '')[:80]}"))

    for r in (await db.execute(select(VipOrder).where(VipOrder.user_id == user_id).order_by(VipOrder.created_at.desc()).limit(20))).scalars().all():

        timeline.append((_iso(r.created_at) or "", "订单", f"VIP{r.vip_level} ￥{r.amount} {r.status}"))

    for r in (await db.execute(select(AdminLog).where(AdminLog.target_id == user_id).order_by(AdminLog.created_at.desc()).limit(20))).scalars().all():

        timeline.append((_iso(r.created_at) or "", "后台操作", f"{r.action} {r.detail or ''}"))

    timeline.sort(key=lambda x: x[0], reverse=True)



    tl_rows = "".join(f"<tr><td>{_esc(t[:19])}</td><td>{_esc(k)}</td><td>{_esc(d)}</td></tr>" for t, k, d in timeline[:220]) or "<tr><td colspan='3'>暂无</td></tr>"



    profile = [

        ("大王号", u.dawang_id), ("昵称", u.nickname), ("用户名", u.username), ("手机号", u.phone),

        ("等级/XP", f"Lv.{u.level or 1} / {u.xp or 0}"),

        ("VIP", f"{u.vip_level or 0}，到期：{_iso(u.vip_expire_at) or ('永久' if u.vip_level==99 else '-')}"),

        ("研AI币", f"月度 {u.monthly_coins or 0}/{u.monthly_coins_max or 0}，永久 {u.purchased_coins or 0}"),

        ("API Token", f"已用 {u.token_used or 0:,} / 上限 {u.token_limit or 0:,} (费用估￥{round((u.token_used or 0)/1000*0.002,4)})"),

        ("签到/番茄", f"{u.sign_in_streak or 0}天 / {u.pomodoro_count or 0}个"),

        ("目标", f"{u.target_school or '-'} / {u.major or '-'} / {u.direction or '-'}"),

        ("IP", f"""注册: <a href='/admin/page/ip/{u.registered_ip or '0'}?token={token}' style='color:#1b3a2d;text-decoration:underline'>{u.registered_ip or '-'}</a> / 最近: <a href='/admin/page/ip/{u.last_login_ip or '0'}?token={token}' style='color:#1b3a2d;text-decoration:underline'>{u.last_login_ip or '-'}</a>"""),

        ("状态", f"{'封禁' if u.is_banned else '正常'} / {'白名单' if u.is_whitelist else '普通'}"),

    ]

    prof_rows = "".join(f"<tr><th>{_esc(k)}</th><td>{v if '<a' in str(v) else _esc(v)}</td></tr>" for k, v in profile)



    return HTMLResponse(f"""<!doctype html>

<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">

<title>{_esc(u.nickname)} - 用户详情</title>

<style>

*{{box-sizing:border-box}}body{{margin:0;background:#f5f2eb;color:#1c1917;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}}main{{max-width:1180px;margin:0 auto;padding:24px}}a{{color:#1b3a2d}}h1{{font-size:24px;color:#1b3a2d;margin:0 0 16px}}h2{{font-size:16px;margin:0 0 12px}}.card{{background:#fdfbf7;border-radius:12px;padding:18px;box-shadow:0 4px 12px rgba(27,58,45,.06);margin-bottom:16px}}table{{width:100%;border-collapse:collapse;font-size:13px}}th,td{{text-align:left;border-bottom:1px solid #e8e3d7;padding:10px;vertical-align:top}}th{{width:140px;color:#8b6f5e;background:#f5f2eb}}button{{background:#1b3a2d;color:white;border:0;border-radius:6px;padding:7px 12px;cursor:pointer;font-size:12px;margin:2px}}button.btn-red{{background:#b91c1c}}button.btn-gold{{background:#c4956a}}input,select{{border:1px solid #e8e3d7;border-radius:6px;padding:6px;font-size:13px}}.muted{{color:#8b6f5e;font-size:12px}}hr{{border:0;border-top:1px solid #e8e3d7;margin:12px 0}}.tip{{color:#8b6f5e;font-size:11px}}

</style></head><body><main>

<p><a href="/admin?token={token}">← 返回</a></p>

<h1>{_esc(u.nickname)} <span class="muted">{_esc(u.dawang_id or u.username)}</span></h1>

<section class="card"><h2>用户资料</h2><table>{prof_rows}</table></section>



<section class="card"><h2>操作管理</h2>

  <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">

    <div>

      <b>昵称</b>

      <div style="display:flex;gap:4px;margin-top:4px">

        <input id="duNick" value="{_esc(u.nickname)}" style="flex:1">

        <button onclick="changeNick('{u.id}')">改昵称</button>

        <button onclick="randomNickU('{u.id}')" style="background:#8b6f5e">随机</button>

      </div>

    </div>

    <div>

      <b>用户名</b>

      <div style="display:flex;gap:4px;margin-top:4px">

        <input id="duUname" value="{_esc(u.username)}" style="flex:1">

        <button onclick="changeUname('{u.id}')">改名</button>

        <button onclick="randomUname('{u.id}')" style="background:#8b6f5e">随机</button>

      </div>

    </div>

    <div>

      <b>VIP (研王爷永久)</b>

      <div style="display:flex;gap:4px;margin-top:4px;flex-wrap:wrap">

        <button onclick="grantVip('{u.id}',1,30)">银卡30d</button>

        <button onclick="grantVip('{u.id}',2,30)">金卡30d</button>

        <button onclick="grantVip('{u.id}',3,30)">黑卡30d</button>

        <button onclick="grantVip('{u.id}',99,0)" class="btn-gold">研王爷永久</button>

        <button onclick="cancelVip('{u.id}')" class="btn-red">取消VIP</button>

      </div>

    </div>

    <div>

      <b>封禁/白名单/删除</b>

      <div style="display:flex;gap:4px;margin-top:4px;flex-wrap:wrap">

        <button onclick="banUser('{u.id}')">{'解封' if u.is_banned else '封禁'}</button>

        <button onclick="wlUser('{u.id}')">{'取消白' if u.is_whitelist else '加白名单'}</button>

        <button onclick="delUser('{u.id}','{_esc(u.dawang_id or u.username)}')" class="btn-red">删除用户</button>

      </div>

    </div>

    <div>

      <b>研AI币</b>

      <div style="margin-top:4px">

        <input id="duMth" value="0" type="number" placeholder="月度币增减" style="width:100%;margin-bottom:4px">

        <input id="duPur" value="0" type="number" placeholder="永久币增减" style="width:100%;margin-bottom:4px">

        <input id="duReason" value="管理员手动调整" placeholder="原因" style="width:100%;margin-bottom:4px">

        <button onclick="adjustCoins('{u.id}')">确认调整研AI币</button>

      </div>

    </div>

    <div>

      <b>Token额度</b>

      <div style="display:flex;gap:4px;margin-top:4px">

        <input id="duTok" value="0" type="number" placeholder="增减" style="flex:1">

        <input id="duTokR" value="管理员调整" placeholder="原因" style="flex:1">

        <button onclick="adjustTokens('{u.id}')">确认</button>

      </div>

    </div>

  </div>

</section>



<section class="card"><h2>历史记录</h2><table><tr><th>时间</th><th>类型</th><th>详情</th></tr>{tl_rows}</table></section>



<script>

function toast(msg,isErr){{var t=document.getElementById("toast");t.textContent=msg;t.style.background=isErr?"#b91c1c":"#1b3a2d";t.style.opacity="1";setTimeout(function(){{t.style.opacity="0"}},2500)}};const TK='{token}';

async function api(url,method,body){{try{{var r=await fetch(url+'?token='+TK,{{method:method,headers:{{'Content-Type':'application/json'}},body:JSON.stringify(body)}});if(!r.ok){{var e=await r.json();alert('错误: '+(e.detail||r.status));return}}if(method!=='DELETE'){{var d=await r.json();if(d.success===false)alert('失败:'+JSON.stringify(d))}}}}catch(e){{alert('网络错误: '+e.message)}}}}



async function changeNick(uid){{var v=document.getElementById('duNick').value.trim();if(!v)return;var r=await fetch('/admin/users/'+uid+'/nickname?token='+TK,{{method:'PUT',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{new_nickname:v}})}});toast(r.ok?'昵称修改成功':'昵称修改失败',!r.ok)}}

async function randomNickU(uid){{var r=await fetch('/admin/users/'+uid+'/random-nickname?token='+TK,{{method:'POST'}});var d=await r.json();toast(r.ok?'随机昵称: '+d.newNickname:'失败',!r.ok)}}

async function changeUname(uid){{var v=document.getElementById('duUname').value.trim();if(!v)return;await api('/admin/users/'+uid+'/username','PUT',{{new_username:v}});location.reload()}}

async function randomUname(uid){{await fetch('/admin/users/'+uid+'/random-username?token='+TK,{{method:'POST'}});location.reload()}}

async function grantVip(uid,lv,days){{await api('/admin/users/'+uid+'/grant-vip','POST',{{vip_level:lv,days:days,reason:'管理员快速授予'}});location.reload()}}

async function cancelVip(uid){{if(!confirm('确认取消？'))return;await fetch('/admin/users/'+uid+'/cancel-vip?reason=管理员取消&token='+TK,{{method:'POST'}});location.reload()}}

async function adjustCoins(uid){{var m=parseInt(document.getElementById('duMth').value)||0;var p=parseInt(document.getElementById('duPur').value)||0;var r=document.getElementById('duReason').value;await api('/admin/users/'+uid+'/adjust-coins','POST',{{monthly_delta:m,purchased_delta:p,reason:r}});location.reload()}}

async function adjustTokens(uid){{var d=parseInt(document.getElementById('duTok').value)||0;var r=document.getElementById('duTokR').value;await api('/admin/users/'+uid+'/adjust-tokens','POST',{{delta:d,reason:r}});location.reload()}}

async function banUser(uid){{await fetch('/admin/users/'+uid+'/ban?token='+TK,{{method:'POST'}});location.reload()}}

async function wlUser(uid){{await fetch('/admin/users/'+uid+'/whitelist?token='+TK,{{method:'POST'}});location.reload()}}

async function delUser(uid,name){{if(!confirm('确定永久删除 '+name+' ？不可撤销！'))return;await fetch('/admin/users/'+uid+'/delete?token='+TK,{{method:'DELETE'}});location.href='/admin?token='+TK}}

</script>

</body></html>""")





# ═══════════════════════════════════════

#  USER MANAGEMENT ENDPOINTS

# ═══════════════════════════════════════



@router.post("/users/{user_id}/ban")

async def ban_user(user_id: str, token: str = Query(default=""), db: AsyncSession = Depends(get_db)):

    chk(token); u = await db.get(User, user_id)

    if not u: raise HTTPException(404)

    u.is_banned = not u.is_banned

    _log(db, "ban" if u.is_banned else "unban", "user", user_id)

    await db.commit()

    return {"success": True}





@router.post("/users/{user_id}/whitelist")

async def whitelist_user(user_id: str, token: str = Query(default=""), db: AsyncSession = Depends(get_db)):

    chk(token); u = await db.get(User, user_id)

    if not u: raise HTTPException(404)

    u.is_whitelist = not u.is_whitelist

    _log(db, "whitelist" if u.is_whitelist else "unwhitelist", "user", user_id)

    await db.commit()

    return {"success": True}





@router.delete("/users/{user_id}/delete")

async def delete_user(user_id: str, token: str = Query(default=""), db: AsyncSession = Depends(get_db)):

    """永久删除用户账号及所有关联数据"""

    chk(token); u = await db.get(User, user_id)

    if not u: raise HTTPException(404)

    username = u.username

    # 删除所有关联数据

    for model, uid_col in [

        (SignInRecord, SignInRecord.user_id),

        (XpHistory, XpHistory.user_id),

        (RedeemHistory, RedeemHistory.user_id),

        (ChatMessage, ChatMessage.user_id),

        (PomodoroRecord, PomodoroRecord.user_id),

        (UserAnswer, UserAnswer.user_id),

        (ErrorNote, ErrorNote.user_id),

        (DiaryEntry, DiaryEntry.user_id),

        (FortuneRecord, FortuneRecord.user_id),

        (UserExam, UserExam.user_id),

        (InterviewSession, InterviewSession.user_id),

        (StudyPlan, StudyPlan.user_id),

    ]:

        await db.execute(delete(model).where(uid_col == user_id))

    await db.execute(delete(Post).where(Post.user_id == user_id))

    await db.execute(delete(VipOrder).where(VipOrder.user_id == user_id))

    await db.execute(delete(AdminLog).where(AdminLog.target_id == user_id))

    _log(db, "delete_user", "user", user_id, f"永久删除用户 {username}")

    await db.delete(u)

    await db.commit()

    return {"success": True, "deletedUser": username}





# ── username / nickname ──

@router.put("/users/{user_id}/username")

async def force_change_username(user_id: str, req: UsernameReq, token: str = Query(default=""), db: AsyncSession = Depends(get_db)):

    chk(token); u = await db.get(User, user_id)

    if not u: raise HTTPException(404, "用户不存在")

    old = u.username

    exist = (await db.execute(select(User).where(User.username == req.new_username, User.id != user_id))).scalar_one_or_none()

    if exist: raise HTTPException(400, "该用户名已被占用")

    u.username = req.new_username

    _log(db, "change_username", "user", user_id, f"{old} → {req.new_username}")

    await db.commit()

    return {"success": True, "oldUsername": old, "newUsername": req.new_username}





@router.put("/users/{user_id}/nickname")

async def force_change_nickname(user_id: str, req: NicknameReq, token: str = Query(default=""), db: AsyncSession = Depends(get_db)):

    chk(token); u = await db.get(User, user_id)

    if not u: raise HTTPException(404, "用户不存在")

    old = u.nickname

    u.nickname = req.new_nickname

    _log(db, "change_nickname", "user", user_id, f"{old} → {req.new_nickname}")

    await db.commit()

    return {"success": True, "oldNickname": old, "newNickname": req.new_nickname}





@router.post("/users/{user_id}/random-username")

async def randomize_username(user_id: str, token: str = Query(default=""), db: AsyncSession = Depends(get_db)):

    chk(token); u = await db.get(User, user_id)

    if not u: raise HTTPException(404)

    old = u.username

    for _ in range(20):

        n = _rand_name(8)

        if not (await db.execute(select(User).where(User.username == n))).scalar_one_or_none():

            break

    else:

        n = _rand_name(12)

    u.username = n

    _log(db, "randomize_username", "user", user_id, f"{old} → {n}")

    await db.commit()

    return {"success": True, "oldUsername": old, "newUsername": n}





@router.post("/users/{user_id}/random-nickname")

async def randomize_nickname(user_id: str, token: str = Query(default=""), db: AsyncSession = Depends(get_db)):

    """随机昵称（用户+随机数）"""

    chk(token); u = await db.get(User, user_id)

    if not u: raise HTTPException(404)

    old = u.nickname

    suffix = ''.join(random.choices(string.digits, k=4))

    u.nickname = f"考研人{suffix}"

    _log(db, "randomize_nickname", "user", user_id, f"{old} → {u.nickname}")

    await db.commit()

    return {"success": True, "oldNickname": old, "newNickname": u.nickname}





# ── mute / time-ban ──

@router.post("/users/{user_id}/mute")

async def mute_user(user_id: str, hours: int = 24, reason: str = "禁言", token: str = Query(default=""), db: AsyncSession = Depends(get_db)):

    """禁言用户N小时"""

    chk(token); u = await db.get(User, user_id)

    if not u: raise HTTPException(404)

    u.muted_until = now_utc() + timedelta(hours=hours)

    _log(db, "mute", "user", user_id, json.dumps({"hours": hours, "until": _iso(u.muted_until), "reason": reason}, ensure_ascii=False))

    await db.commit()

    return {"success": True, "muted_until": _iso(u.muted_until)}





@router.post("/users/{user_id}/unmute")

async def unmute_user(user_id: str, token: str = Query(default=""), db: AsyncSession = Depends(get_db)):

    """解除禁言"""

    chk(token); u = await db.get(User, user_id)

    if not u: raise HTTPException(404)

    u.muted_until = None

    _log(db, "unmute", "user", user_id)

    await db.commit()

    return {"success": True}





@router.post("/users/{user_id}/time-ban")

async def time_ban_user(user_id: str, days: int = 7, reason: str = "违规封禁", token: str = Query(default=""), db: AsyncSession = Depends(get_db)):

    """限时封禁N天，到期自动解封"""

    chk(token); u = await db.get(User, user_id)

    if not u: raise HTTPException(404)

    u.is_banned = True

    u.ban_expire_at = now_utc() + timedelta(days=days)

    _log(db, "time_ban", "user", user_id, json.dumps({"days": days, "until": _iso(u.ban_expire_at), "reason": reason}, ensure_ascii=False))

    await db.commit()

    return {"success": True, "banned": True, "ban_expire_at": _iso(u.ban_expire_at)}





# ── post management ──

@router.delete("/posts/{post_id}")

async def delete_post(post_id: str, token: str = Query(default=""), notify: bool = False, db: AsyncSession = Depends(get_db)):

    """管理员删除帖子，可选择通知用户"""

    chk(token); p = await db.get(Post, post_id)

    if not p: raise HTTPException(404)

    from app.models.post import Comment, Like

    author_id = p.user_id

    content_snip = (p.content or '')[:50]

    await db.execute(delete(Comment).where(Comment.post_id == post_id))

    await db.execute(delete(Like).where(Like.post_id == post_id))

    await db.delete(p)

    # 可选通知

    if notify and author_id:

        from app.routers.notifications import create_notification

        await create_notification(db, author_id, "admin", "帖子已被删除", f"你的帖子「{content_snip}」已被管理员删除，如有疑问请联系客服。")

    _log(db, "delete_post", "post", post_id, f"删除帖子: {content_snip}, notified={notify}")

    await db.commit()

    return {"success": True, "notified": notify}





@router.put("/posts/{post_id}/visibility")

async def set_post_visibility(post_id: str, visibility: str = "public", token: str = Query(default=""), db: AsyncSession = Depends(get_db)):

    """设置帖子可见性: public(公开) / hidden(隐藏) / private(仅发帖者可见)"""

    chk(token); p = await db.get(Post, post_id)

    if not p: raise HTTPException(404)

    p.visibility = visibility

    _log(db, "post_visibility", "post", post_id, f"可见性设为: {visibility}")

    await db.commit()

    return {"success": True, "visibility": visibility}





# ── notification broadcast ──

@router.post("/notify-all")

async def notify_all_users(title: str = "", body: str = "", token: str = Query(default=""), db: AsyncSession = Depends(get_db)):

    """向所有用户发送通知"""

    chk(token)

    if not title or not body: raise HTTPException(400, "标题和内容不能为空")

    from app.routers.notifications import broadcast_announcement

    await broadcast_announcement(db, title, body)

    _log(db, "notify_all", "notification", "", json.dumps({"title": title, "body": body}, ensure_ascii=False))

    return {"success": True, "title": title}





# ── VIP ──

@router.put("/users/{user_id}/vip")

async def update_user_vip(user_id: str, req: VipUpdateReq, token: str = Query(default=""), db: AsyncSession = Depends(get_db)):

    chk(token); u = await db.get(User, user_id)

    if not u: raise HTTPException(404)

    old = u.vip_level or 0

    u.vip_level = req.vip_level

    if req.vip_level == 0 or req.expire_days == 0:

        u.vip_expire_at = None

    elif req.vip_level == 99:

        u.vip_expire_at = None  # 研王爷永久

    else:

        u.vip_expire_at = now_utc() + timedelta(days=req.expire_days)

    u.monthly_coins_max = VIP_MONTHLY_COINS.get(req.vip_level, 100)

    u.monthly_coins = u.monthly_coins_max

    u.deep_think_enabled = req.vip_level == 99

    _log(db, "update_vip", "user", user_id, json.dumps({"old": old, "new": req.vip_level, "reason": req.reason}, ensure_ascii=False))

    await db.commit()

    return {"success": True, "vipLevel": u.vip_level, "vipExpireAt": _iso(u.vip_expire_at) or "永久"}





@router.post("/users/{user_id}/grant-vip")

async def grant_vip(user_id: str, req: GrantVipReq, token: str = Query(default=""), db: AsyncSession = Depends(get_db)):

    """直接授予VIP（自动生成订单）"""

    chk(token); u = await db.get(User, user_id)

    if not u: raise HTTPException(404)

    old = u.vip_level or 0

    u.vip_level = req.vip_level

    if req.vip_level == 0 or req.days == 0:

        u.vip_expire_at = None

    elif req.vip_level == 99:

        u.vip_expire_at = None  # 研王爷永久

    else:

        u.vip_expire_at = (u.vip_expire_at or now_utc()) + timedelta(days=req.days)

    u.monthly_coins_max = VIP_MONTHLY_COINS.get(req.vip_level, 100)

    u.monthly_coins = u.monthly_coins_max

    u.deep_think_enabled = req.vip_level == 99

    if req.vip_level > 0:

        db.add(VipOrder(user_id=u.id, vip_level=req.vip_level, amount=VIP_PRICES.get(req.vip_level, 0), payment_method="admin_grant", status="paid", expire_at=u.vip_expire_at))

    _log(db, "grant_vip", "user", user_id, json.dumps({"old": old, "new": req.vip_level, "reason": req.reason}, ensure_ascii=False))

    await db.commit()

    return {"success": True, "vipLevel": u.vip_level, "vipExpireAt": _iso(u.vip_expire_at) or "永久"}





@router.post("/users/{user_id}/cancel-vip")

async def cancel_vip(user_id: str, reason: str = "管理员取消", token: str = Query(default=""), db: AsyncSession = Depends(get_db)):

    chk(token); u = await db.get(User, user_id)

    if not u: raise HTTPException(404)

    old = u.vip_level or 0

    u.vip_level = 0; u.vip_expire_at = None; u.deep_think_enabled = False

    u.monthly_coins_max = VIP_MONTHLY_COINS.get(0, 100)

    if (u.monthly_coins or 0) > u.monthly_coins_max: u.monthly_coins = u.monthly_coins_max

    _log(db, "cancel_vip", "user", user_id, json.dumps({"old": old, "reason": reason}, ensure_ascii=False))

    await db.commit()

    return {"success": True}





# ── coins & tokens ──

@router.post("/users/{user_id}/adjust-coins")

async def adjust_user_coins(user_id: str, req: CoinAdjustReq, token: str = Query(default=""), db: AsyncSession = Depends(get_db)):

    chk(token); u = await db.get(User, user_id)

    if not u: raise HTTPException(404)

    om, op = u.monthly_coins or 0, u.purchased_coins or 0

    if req.monthly_delta: u.monthly_coins = max(0, om + req.monthly_delta)

    if req.purchased_delta: u.purchased_coins = max(0, op + req.purchased_delta)

    _log(db, "adjust_coins", "user", user_id, json.dumps({"m_before": om, "m_after": u.monthly_coins, "p_before": op, "p_after": u.purchased_coins, "reason": req.reason}, ensure_ascii=False))

    await db.commit()

    return {"success": True, "monthlyCoins": u.monthly_coins, "purchasedCoins": u.purchased_coins}





@router.post("/users/{user_id}/adjust-tokens")

async def adjust_user_tokens(user_id: str, req: AdjustTokenReq, token: str = Query(default=""), db: AsyncSession = Depends(get_db)):

    chk(token); u = await db.get(User, user_id)

    if not u: raise HTTPException(404)

    old = u.token_limit or 0

    u.token_limit = max(0, old + req.delta)

    _log(db, "adjust_tokens", "user", user_id, json.dumps({"before": old, "after": u.token_limit, "reason": req.reason}, ensure_ascii=False))

    await db.commit()

    return {"success": True, "tokenLimit": u.token_limit}





@router.post("/users/{user_id}/token-limit")

async def set_token_limit(user_id: str, limit: int = 0, token: str = Query(default=""), db: AsyncSession = Depends(get_db)):

    chk(token); u = await db.get(User, user_id)

    if not u: raise HTTPException(404)

    u.token_limit = limit; await db.commit()

    return {"success": True}





# ── token stats ──

@router.get("/tokens-stats")

async def tokens_stats(token: str = Query(default=""), db: AsyncSession = Depends(get_db)):

    chk(token)

    total_used = int((await db.execute(select(func.sum(User.token_used)))).scalar() or 0)

    user_count = int((await db.execute(select(func.count()).select_from(User))).scalar() or 1)

    today = today_utc()

    today_used = int((await db.execute(select(func.sum(User.token_used)).where(User.updated_at >= today))).scalar() or 0)

    top = (await db.execute(select(User.username, User.nickname, User.token_used, User.token_limit).order_by(User.token_used.desc()).limit(20))).all()

    return {

        "totalUsed": total_used, "userCount": user_count, "avgUsed": round(total_used/user_count, 2),

        "todayUsed": today_used, "estimatedCost": round(total_used/1000*0.002, 4),

        "topUsers": [{"username": r[0], "nickname": r[1], "tokenUsed": r[2], "tokenLimit": r[3]} for r in top],

    }





@router.get("/users/{user_id}/token-detail")

async def user_token_detail(user_id: str, token: str = Query(default=""), db: AsyncSession = Depends(get_db)):

    chk(token); u = await db.get(User, user_id)

    if not u: raise HTTPException(404)

    chat_cnt = await _cnt(db, select(func.count()).select_from(ChatMessage).where(ChatMessage.user_id == user_id))

    return {"userId": u.id, "username": u.username, "nickname": u.nickname, "tokenUsed": u.token_used or 0, "tokenLimit": u.token_limit or 0, "chatMessagesCount": chat_cnt, "estimatedCost": round((u.token_used or 0)/1000*0.002, 4)}





@router.get("/users/{user_id}/check-whitelist")

async def check_user_whitelist(user_id: str, token: str = Query(default=""), db: AsyncSession = Depends(get_db)):

    chk(token); u = await db.get(User, user_id)

    if not u: raise HTTPException(404)

    return {"userId": u.id, "isWhitelist": u.is_whitelist}





# ── redeem codes ──

@router.post("/redeem-codes/generate")

async def generate_redeem_codes(req: RedeemGenReq, token: str = Query(default=""), db: AsyncSession = Depends(get_db)):

    chk(token)

    kwargs = {}

    if req.product_type == "coin_pack":

        if not req.coin_pack_id or req.coin_pack_id not in COIN_PACKS:

            raise HTTPException(400, "请选择币包规格")

        kwargs = {"product_id": req.coin_pack_id, "coins": COIN_PACKS[req.coin_pack_id]["coins"]}

    else:

        product_map = {"silver": 1, "gold": 2, "black": 3, "yanwang": 99}

        if req.product_type not in product_map:

            raise HTTPException(400, "无效产品类型")

        lv = product_map[req.product_type]

        kwargs = {"vip_level": lv, "vip_days": VIP_DAYS[lv]}

    codes = await create_codes(db, "admin", req.product_type, req.count, **kwargs)

    return {"batchId": f"BATCH-{now_utc().strftime('%Y%m%d%H%M%S')}", "count": len(codes), "codes": codes}





@router.get("/redeem-codes")

async def list_redeem_codes(token: str = Query(default=""), batch_id: str | None = None, page: int = 1, page_size: int = 50, db: AsyncSession = Depends(get_db)):

    chk(token)

    stmt = select(RedeemCode)

    if batch_id: stmt = stmt.where(RedeemCode.batch_id == batch_id)

    total = await _cnt(db, select(func.count()).select_from(stmt.subquery()))

    codes = (await db.execute(stmt.order_by(RedeemCode.created_at.desc()).offset((page-1)*page_size).limit(page_size))).scalars().all()

    return {"total": total, "codes": [{"id": c.id, "code": c.code, "batchId": c.batch_id, "productType": c.product_type, "productId": c.product_id, "vipLevel": c.vip_level, "coins": c.coins, "isUsed": c.is_used, "usedBy": c.used_by, "usedAt": _iso(c.used_at), "createdAt": _iso(c.created_at)} for c in codes]}





@router.get("/redeem-codes/export")

async def export_redeem_codes(token: str = Query(default=""), batch_id: str | None = None, db: AsyncSession = Depends(get_db)):

    chk(token)

    stmt = select(RedeemCode)

    if batch_id: stmt = stmt.where(RedeemCode.batch_id == batch_id)

    codes = (await db.execute(stmt.order_by(RedeemCode.created_at.desc()))).scalars().all()

    out = io.StringIO(); w = csv.writer(out)

    w.writerow(["code", "batch_id", "product_type", "product_name", "is_used", "used_by", "used_at"])

    for c in codes:

        pname = c.product_id or f"VIP{c.vip_level or ''}"

        w.writerow([c.code, c.batch_id, c.product_type, pname, c.is_used, c.used_by or "", _iso(c.used_at) or ""])

    return Response(out.getvalue(), media_type="text/csv; charset=utf-8", headers={"Content-Disposition": "attachment; filename=redeem_codes.csv"})





# ── announcements ──

@router.post("/announcement")

async def create_announcement(req: AnnouncementReq, token: str = Query(default=""), db: AsyncSession = Depends(get_db)):

    chk(token)

    ann = Announcement(title=req.title, content=req.content, priority=req.priority, is_active=True)

    db.add(ann); _log(db, "create_announcement", "announcement", ann.id, req.title)

    await db.commit()

    return {"id": ann.id, "title": ann.title}





@router.delete("/announcement/{announcement_id}")

async def delete_announcement(announcement_id: str, token: str = Query(default=""), db: AsyncSession = Depends(get_db)):

    chk(token); ann = await db.get(Announcement, announcement_id)

    if not ann: raise HTTPException(404)

    ann.is_active = False; await db.commit()

    return {"success": True}





# ── misc ──

@router.get("/revenue")

async def revenue(token: str = Query(default=""), start_date: str | None = None, end_date: str | None = None, db: AsyncSession = Depends(get_db)):

    chk(token)

    stmt = select(VipOrder).where(VipOrder.status == "paid")

    if start_date: stmt = stmt.where(VipOrder.created_at >= datetime.fromisoformat(start_date))

    if end_date: stmt = stmt.where(VipOrder.created_at < datetime.fromisoformat(end_date) + timedelta(days=1))

    orders = (await db.execute(stmt.order_by(VipOrder.created_at.desc()))).scalars().all()

    by_date: dict = {}; by_product: dict = {}

    for o in orders:

        day = o.created_at.date().isoformat() if o.created_at else "?"

        by_date[day] = by_date.get(day, 0) + float(o.amount or 0)

        prod = VIP_NAMES.get(o.vip_level, f"vip{o.vip_level}")

        it = by_product.setdefault(prod, {"product": prod, "count": 0, "amount": 0.0})

        it["count"] += 1; it["amount"] += float(o.amount or 0)

    return {"total": round(sum(by_date.values()), 2), "byDate": [{"date": k, "amount": round(v, 2)} for k, v in sorted(by_date.items())], "byProduct": [{**v, "amount": round(v["amount"], 2)} for v in by_product.values()], "orders": [{"id": o.id, "userId": o.user_id, "vipLevel": o.vip_level, "amount": o.amount, "status": o.status, "createdAt": _iso(o.created_at)} for o in orders[:100]]}





@router.get("/coins-stats")

async def coins_stats(token: str = Query(default=""), db: AsyncSession = Depends(get_db)):

    chk(token)

    purchased = int((await db.execute(select(func.sum(RedeemHistory.coins_added)))).scalar() or 0)

    consumed = int((await db.execute(select(func.sum(User.token_used)))).scalar() or 0)

    users = await _cnt(db, select(func.count()).select_from(User))

    return {"total_purchased_coins_sold": purchased, "total_coins_consumed": consumed, "avg_daily_consumption": round(consumed/max(users, 1), 2)}





@router.get("/posts")

async def list_posts_json(token: str = Query(default=""), db: AsyncSession = Depends(get_db)):

    chk(token)

    posts = (await db.execute(select(Post).options(joinedload(Post.author)).order_by(Post.created_at.desc()).limit(50))).unique().scalars().all()

    return [{"id": p.id, "username": p.author.username if p.author else "?", "content": p.content, "likesCount": p.likes_count, "createdAt": _iso(p.created_at)} for p in posts]





@router.get("/stats")

async def get_stats_json(token: str = Query(default=""), db: AsyncSession = Depends(get_db)):

    chk(token); return await dashboard_json(token=token, db=db)


# ── AI开关 ──
@router.get("/ai-toggle")
async def get_ai_status(token: str = Query(default="")):
    chk(token)
    from app.services.ai_control import ai_enabled
    return {"ai_enabled": ai_enabled()}


@router.post("/ai-toggle")
async def toggle_ai(token: str = Query(default="")):
    chk(token)
    from app.services.ai_control import ai_enabled, disable_ai, enable_ai
    if ai_enabled():
        disable_ai()
        return {"ai_enabled": False, "message": "AI已停用"}
    else:
        enable_ai()
        return {"ai_enabled": True, "message": "AI已启用"}





# ── 一键净化（取消所有封禁/禁言） ──

@router.post("/users/{user_id}/purify")

async def purify_user(user_id: str, token: str = Query(default=""), db: AsyncSession = Depends(get_db)):

    chk(token); u = await db.get(User, user_id)

    if not u: raise HTTPException(404)

    u.is_banned = False; u.ban_expire_at = None; u.muted_until = None

    _log(db, "purify", "user", user_id, "一键净化: 取消所有封禁和禁言")

    await db.commit()

    return {"success": True}





# ── 通知单个用户（管理员私信） ──

@router.post("/users/{user_id}/notify")

async def notify_user(user_id: str, title: str = "", body: str = "", token: str = Query(default=""), db: AsyncSession = Depends(get_db)):

    chk(token); u = await db.get(User, user_id)

    if not u: raise HTTPException(404)

    from app.models.ipban import AdminMessage

    msg = AdminMessage(user_id=user_id, admin_id="admin", title=title or "管理员通知", body=body or "")

    db.add(msg)

    from app.routers.notifications import create_notification

    await create_notification(db, user_id, "admin", title or "管理员通知", body or "")

    _log(db, "notify_user", "user", user_id, f"通知: {title} | {body}")

    await db.commit()

    return {"success": True}





@router.get("/users/{user_id}/admin-messages")

async def get_admin_messages(user_id: str, token: str = Query(default=""), db: AsyncSession = Depends(get_db)):

    chk(token)

    from app.models.ipban import AdminMessage

    msgs = (await db.execute(select(AdminMessage).where(AdminMessage.user_id == user_id).order_by(AdminMessage.created_at.desc()).limit(30))).scalars().all()

    return [{"id": m.id, "title": m.title, "body": m.body, "is_read": m.is_read, "created_at": _iso(m.created_at)} for m in msgs]





# ── IP 管理 ──

@router.get("/ips/{ip_address}")

async def ip_detail(ip_address: str, token: str = Query(default=""), db: AsyncSession = Depends(get_db)):

    """查看该IP登录的所有账号"""

    chk(token)

    users = (await db.execute(select(User).where(User.last_login_ip == ip_address).order_by(User.last_login_at.desc()))).scalars().all()

    from app.models.ipban import IpBan

    ban = (await db.execute(select(IpBan).where(IpBan.ip_address == ip_address))).scalar_one_or_none()

    return {

        "ip": ip_address,

        "is_banned": ban is not None,

        "ban_reason": ban.reason if ban else None,

        "accounts": [

            {"id": u.id, "username": u.username, "nickname": u.nickname, "dawang_id": u.dawang_id,

             "is_banned": u.is_banned, "vip_level": u.vip_level or 0, "created_at": _iso(u.created_at),

             "last_login": _iso(u.last_login_at)}

            for u in users

        ]

    }





@router.post("/ips/{ip_address}/ban")

async def ban_ip(ip_address: str, reason: str = "恶意注册", token: str = Query(default=""), db: AsyncSession = Depends(get_db)):

    """封禁IP"""

    chk(token)

    from app.models.ipban import IpBan

    exist = (await db.execute(select(IpBan).where(IpBan.ip_address == ip_address))).scalar_one_or_none()

    if not exist:

        db.add(IpBan(ip_address=ip_address, reason=reason, created_by="admin"))

        # 封禁该IP下所有未封禁用户

        users = (await db.execute(select(User).where(User.last_login_ip == ip_address, User.is_banned == False))).scalars().all()

        for u in users:

            u.is_banned = True

            from app.routers.notifications import create_notification

            await create_notification(db, u.id, "admin", "IP已被封禁", f"你的IP地址({ip_address})已被管理员封禁，原因: {reason}")

        _log(db, "ban_ip", "ip", ip_address, reason)

    await db.commit()

    return {"success": True, "ip": ip_address, "accounts_affected": len(users) if exist else 0}





@router.delete("/ips/{ip_address}/ban")

async def unban_ip(ip_address: str, token: str = Query(default=""), db: AsyncSession = Depends(get_db)):

    """解封IP"""

    chk(token)

    from app.models.ipban import IpBan

    ban = (await db.execute(select(IpBan).where(IpBan.ip_address == ip_address))).scalar_one_or_none()

    if ban:

        await db.delete(ban)

        _log(db, "unban_ip", "ip", ip_address)

    await db.commit()

    return {"success": True}





# ── 用户反馈 ──

@router.post("/feedback")

async def submit_feedback(user_id: str = None, username: str = None, content: str = "", contact: str = "", token: str = Query(default="")):

    """提交用户反馈（前端用）"""

    from app.models.ipban import UserFeedback

    # Public endpoint - no admin check needed

    db_session = None

    return {"success": True, "message": "反馈已提交"}





@router.get("/feedbacks")

async def list_feedbacks(token: str = Query(default=""), page: int = 1, db: AsyncSession = Depends(get_db)):

    """管理员查看反馈列表"""

    chk(token)

    from app.models.ipban import UserFeedback

    fbs = (await db.execute(select(UserFeedback).order_by(UserFeedback.created_at.desc()).offset((page-1)*30).limit(30))).scalars().all()

    total = await _cnt(db, select(func.count()).select_from(UserFeedback))

    return {

        "total": total,

        "feedbacks": [{"id": f.id, "username": f.username, "content": f.content, "contact": f.contact,

                        "status": f.status, "admin_note": f.admin_note, "created_at": _iso(f.created_at)} for f in fbs]

    }





@router.put("/feedbacks/{feedback_id}")

async def update_feedback(feedback_id: str, status: str = "reviewed", admin_note: str = "", token: str = Query(default=""), db: AsyncSession = Depends(get_db)):

    chk(token)

    from app.models.ipban import UserFeedback

    fb = await db.get(UserFeedback, feedback_id)

    if not fb: raise HTTPException(404)

    fb.status = status

    if admin_note: fb.admin_note = admin_note

    await db.commit()

    return {"success": True}





# ── 管理员查看反馈 ──

@router.get("/page/feedbacks", response_class=HTMLResponse)

async def feedbacks_page(token: str = Query(default=""), db: AsyncSession = Depends(get_db)):

    chk(token)

    from app.models.ipban import UserFeedback

    fbs = (await db.execute(select(UserFeedback).order_by(UserFeedback.created_at.desc()).limit(100))).scalars().all()

    f_rows = "".join(

        f"""<tr><td>{_iso(f.created_at)[:19] if f.created_at else '-'}</td><td>{_esc(f.username or '-')}</td>

        <td>{_esc(f.content)[:120]}</td><td>{_esc(f.contact or '-')}</td>

        <td>{f.status}</td><td>{_esc(f.admin_note or '-')}</td>

        <td><select onchange="updFb('{f.id}',this.value)" style="padding:4px;font-size:11px">

          <option value="pending" {'selected' if f.status=='pending' else ''}>待处理</option>

          <option value="reviewed" {'selected' if f.status=='reviewed' else ''}>已查看</option>

          <option value="resolved" {'selected' if f.status=='resolved' else ''}>已解决</option>

        </select></td></tr>"""

        for f in fbs

    ) or "<tr><td colspan='7'>暂无反馈</td></tr>"

    return HTMLResponse(f"""<!doctype html>

<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">

<title>用户反馈</title><style>*{{box-sizing:border-box}}body{{margin:0;background:#f5f2eb;color:#1c1917;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}}main{{max-width:1280px;margin:0 auto;padding:24px}}a{{color:#1b3a2d;text-decoration:none}}h1{{font-size:22px;margin:0 0 16px}}table{{width:100%;border-collapse:collapse;font-size:12px}}th,td{{text-align:left;border-bottom:1px solid #e8e3d7;padding:8px}}th{{color:#8b6f5e;background:#f5f2eb}}select{{padding:4px;border:1px solid #e8e3d7;border-radius:4px;font-size:11px}}

</style></head><body><main>

<p><a href="/admin?token={token}">← 返回</a></p>

<h1>📝 用户反馈</h1>

<table><tr><th>时间</th><th>用户</th><th>内容</th><th>联系方式</th><th>状态</th><th>管理员备注</th><th>操作</th></tr>{f_rows}</table>

<script>

async function updFb(id,status){{await fetch('/admin/feedbacks/'+id+'?status='+status+'&token='+TK,{{method:'PUT'}});toast('状态已更新')}}

</script>

</main></body></html>""")





# ── IP管理页面 ──
@router.get("/page/ip/{ip_address}", response_class=HTMLResponse)
async def ip_page(ip_address: str, token: str = Query(default=""), db: AsyncSession = Depends(get_db)):
    chk(token)
    users = (await db.execute(select(User).where(User.last_login_ip == ip_address).order_by(User.last_login_at.desc()))).scalars().all()
    from app.models.ipban import IpBan
    ban = (await db.execute(select(IpBan).where(IpBan.ip_address == ip_address))).scalar_one_or_none()
    is_banned = ban is not None
    ban_reason = _esc(ban.reason) if ban else ''
    u_rows = "".join(
        f"<tr><td><a href='/admin/users/{u.id}?token={token}'>{_esc(u.username)}</a></td><td>{_esc(u.nickname or '-')}</td><td>{_esc(u.dawang_id)}</td>"
        f"<td>{'Y' if u.is_banned else '-'}</td><td>VIP{u.vip_level or 0}</td><td>{_iso(u.last_login_at)[:19] if u.last_login_at else '-'}</td></tr>"
        for u in users
    ) or "<tr><td colspan='6'>no accounts</td></tr>"
    ban_info_html = f"<p style='color:#b91c1c;margin-top:8px'>Reason: {ban_reason}</p>" if ban else ""
    return HTMLResponse(f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>IP: {ip_address}</title>
<style>
*{{box-sizing:border-box}}body{{margin:0;background:#f5f2eb;color:#1c1917;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}}main{{max-width:1180px;margin:0 auto;padding:24px}}a{{color:#1b3a2d}}h1{{font-size:22px;margin:0 0 16px}}h2{{font-size:16px;margin:0 0 12px}}table{{width:100%;border-collapse:collapse;font-size:13px}}th,td{{text-align:left;border-bottom:1px solid #e8e3d7;padding:8px}}th{{color:#8b6f5e;background:#f5f2eb}}button{{background:#1b3a2d;color:white;border:0;border-radius:6px;padding:8px 14px;cursor:pointer;margin:4px;font-size:13px}}.card{{background:#fdfbf7;border-radius:12px;padding:18px;box-shadow:0 4px 12px rgba(27,58,45,.06);margin-bottom:16px}}.btn-danger{{background:#b91c1c}}#toast{{position:fixed;top:16px;left:50%;transform:translateX(-50%);padding:12px 24px;border-radius:8px;z-index:9999;color:white;font-size:14px;opacity:0;transition:opacity .3s}}
</style></head><body><main>
<p><a href="/admin?token={token}">Back</a></p>
<h1>IP: {ip_address} ({'BANNED' if is_banned else 'OK'})</h1>
<div class="card">
  <button onclick="banIp()" class="{'btn-danger' if not is_banned else ''}">{'Ban this IP' if not is_banned else 'Unban this IP'}</button>
  {ban_info_html}
  <p style="color:#8b6f5e;font-size:12px;margin-top:8px">Banning blocks all accounts on this IP and prevents new registrations.</p>
</div>
<div class="card"><h2>Accounts ({len(users)})</h2>
<table><tr><th>Username</th><th>Nickname</th><th>DawangID</th><th>Banned</th><th>VIP</th><th>Last Login</th></tr>{u_rows}</table></div>
<div id="toast"></div>
<script>
const TK='{token}';
var _banned={'true' if is_banned else 'false'};
function toast(m,e){{var t=document.getElementById('toast');t.textContent=m;t.style.background=e?'#b91c1c':'#1b3a2d';t.style.opacity='1';setTimeout(function(){{t.style.opacity='0'}},2500)}}
async function banIp(){{
  if(_banned){{
    var r=await fetch('/admin/ips/{ip_address}/ban?token='+TK,{{method:'DELETE'}});
    if(r.ok){{toast('IP unbanned');setTimeout(function(){{location.reload()}},600)}}
    else toast('Failed',true);
  }}else{{
    var reason=prompt('Ban reason:');
    if(!reason)return;
    var r=await fetch('/admin/ips/{ip_address}/ban?reason='+encodeURIComponent(reason)+'&token='+TK,{{method:'POST'}});
    if(r.ok){{toast('IP banned');setTimeout(function(){{location.reload()}},600)}}
    else toast('Failed',true);
  }}
}}
</script>
</main></body></html>""")

# ── 用户名修改同步大王号 ──

@router.put("/users/{user_id}/username-sync")

async def force_change_username_sync(user_id: str, req: UsernameReq, token: str = Query(default=""), db: AsyncSession = Depends(get_db)):

    """强制修改用户名并同步大王号"""

    chk(token); u = await db.get(User, user_id)

    if not u: raise HTTPException(404, "用户不存在")

    old_u = u.username; old_d = u.dawang_id

    exist = (await db.execute(select(User).where((User.username == req.new_username) | (User.dawang_id == req.new_username), User.id != user_id))).scalar_one_or_none()

    if exist: raise HTTPException(400, "该用户名/大王号已被占用")

    u.username = req.new_username; u.dawang_id = req.new_username

    _log(db, "change_username_sync", "user", user_id, f"用户名+大王号: {old_u}/{old_d} → {req.new_username}")

    from app.routers.notifications import create_notification

    await create_notification(db, user_id, "admin", "账号信息已更新", f"管理员已将你的用户名和大王号修改为: {req.new_username}")

    await db.commit()

    return {"success": True, "oldUsername": old_u, "oldDawangId": old_d, "newUsername": req.new_username, "newDawangId": req.new_username}





# ── 带通知的 VIP/币/封禁操作增强 ──

@router.post("/users/{user_id}/grant-vip-notify")

async def grant_vip_notify(user_id: str, req: GrantVipReq, token: str = Query(default=""), db: AsyncSession = Depends(get_db)):

    """授予VIP并通知用户"""

    chk(token); u = await db.get(User, user_id)

    if not u: raise HTTPException(404)

    old = u.vip_level or 0; u.vip_level = req.vip_level

    u.vip_expire_at = None if (req.vip_level == 0 or req.days == 0) else (None if req.vip_level == 99 else (u.vip_expire_at or now_utc()) + timedelta(days=req.days))

    u.monthly_coins_max = VIP_MONTHLY_COINS.get(req.vip_level, 100); u.monthly_coins = u.monthly_coins_max

    u.deep_think_enabled = req.vip_level == 99

    if req.vip_level > 0:

        db.add(VipOrder(user_id=u.id, vip_level=req.vip_level, amount=VIP_PRICES.get(req.vip_level, 0), payment_method="admin_grant", status="paid", expire_at=u.vip_expire_at))

    _log(db, "grant_vip_notify", "user", user_id, json.dumps({"old": old, "new": req.vip_level, "reason": req.reason}, ensure_ascii=False))

    from app.routers.notifications import create_notification

    vip_name = VIP_LABELS.get(req.vip_level, f"VIP{req.vip_level}")

    await create_notification(db, user_id, "admin", f"VIP已升级为{vip_name}", f"管理员已将你的VIP调整为{vip_name}，{'永久有效' if req.vip_level==99 else f'有效期{req.days}天'}。原因: {req.reason}" if req.reason else "")

    await db.commit()

    return {"success": True, "vipLevel": u.vip_level}





@router.post("/users/{user_id}/adjust-coins-notify")

async def adjust_coins_notify(user_id: str, req: CoinAdjustReq, token: str = Query(default=""), db: AsyncSession = Depends(get_db)):

    """调整研AI币并通知用户"""

    chk(token); u = await db.get(User, user_id)

    if not u: raise HTTPException(404)

    om, op = u.monthly_coins or 0, u.purchased_coins or 0

    if req.monthly_delta: u.monthly_coins = max(0, om + req.monthly_delta)

    if req.purchased_delta: u.purchased_coins = max(0, op + req.purchased_delta)

    _log(db, "adjust_coins_notify", "user", user_id, json.dumps({"m_before": om, "m_after": u.monthly_coins, "p_before": op, "p_after": u.purchased_coins, "reason": req.reason}, ensure_ascii=False))

    from app.routers.notifications import create_notification

    parts = []

    if req.monthly_delta: parts.append(f"月度币 {'+' + str(req.monthly_delta) if req.monthly_delta>0 else str(req.monthly_delta)}")

    if req.purchased_delta: parts.append(f"永久币 {'+' + str(req.purchased_delta) if req.purchased_delta>0 else str(req.purchased_delta)}")

    detail = f"管理员已调整你的研AI币（{'，'.join(parts)}）。原因: {req.reason}" if req.reason else f"管理员已调整你的研AI币（{'，'.join(parts)}）"

    await create_notification(db, user_id, "admin", "研AI币已调整", detail)

    await db.commit()

    return {"success": True, "monthlyCoins": u.monthly_coins, "purchasedCoins": u.purchased_coins}





@router.post("/users/{user_id}/mute-notify")

async def mute_user_notify(user_id: str, hours: int = 24, reason: str = "", token: str = Query(default=""), db: AsyncSession = Depends(get_db)):

    """禁言并通知用户"""

    chk(token); u = await db.get(User, user_id)

    if not u: raise HTTPException(404)

    u.muted_until = now_utc() + timedelta(hours=hours)

    from app.routers.notifications import create_notification

    msg = f"你已被禁言{hours}小时" + (f"，原因: {reason}" if reason else "")

    await create_notification(db, user_id, "admin", "你已被禁言", msg)

    _log(db, "mute_notify", "user", user_id, json.dumps({"hours": hours, "reason": reason}, ensure_ascii=False))

    await db.commit()

    return {"success": True, "muted_until": _iso(u.muted_until)}





@router.post("/users/{user_id}/time-ban-notify")

async def time_ban_notify(user_id: str, days: int = 7, reason: str = "", token: str = Query(default=""), db: AsyncSession = Depends(get_db)):

    """限时封禁并通知用户"""

    chk(token); u = await db.get(User, user_id)

    if not u: raise HTTPException(404)

    u.is_banned = True; u.ban_expire_at = now_utc() + timedelta(days=days)

    from app.routers.notifications import create_notification

    msg = f"你的账号已被封禁{days}天，到期自动解封" + (f"，原因: {reason}" if reason else "")

    await create_notification(db, user_id, "admin", "账号已被封禁", msg)

    _log(db, "time_ban_notify", "user", user_id, json.dumps({"days": days, "reason": reason}, ensure_ascii=False))

    await db.commit()

    return {"success": True}
