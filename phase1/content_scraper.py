"""
SereneX Phase 1 — 博主内容爬虫框架
支持：B站 / 微博 / 任意网页
"""

import urllib.request
import urllib.error
import gzip
import json
import re
import time
import html
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Post:
    """标准化的帖子/动态"""
    platform: str          # "bilibili" | "weibo" | "web"
    author: str
    content: str
    timestamp: float       # Unix时间戳
    date_str: str          # 可读时间
    url: str = ""
    likes: int = 0
    reposts: int = 0
    comments: int = 0
    raw_data: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.date_str:
            try:
                self.date_str = datetime.fromtimestamp(self.timestamp).strftime("%Y-%m-%d %H:%M")
            except:
                self.date_str = str(self.timestamp)


class ContentScraper:
    """
    内容爬虫基类
    所有平台爬虫继承此类
    """

    # 默认请求头（模拟浏览器）
    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate",
        "Referer": "",
    }

    # 请求间隔（秒），防止被封
    RATE_LIMIT = 1.5

    def __init__(self):
        self._last_request = 0.0
        self._opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor()
        )

    def _rate_limit(self):
        """两次请求之间的间隔"""
        elapsed = time.time() - self._last_request
        if elapsed < self.RATE_LIMIT:
            time.sleep(self.RATE_LIMIT - elapsed)
        self._last_request = time.time()

    def _fetch(self, url: str, headers: Dict = None,
                timeout: int = 15) -> Optional[str]:
        """
        发起 GET 请求，返回页面内容
        自动处理 gzip 压缩、编码、跳转
        """
        self._rate_limit()
        h = dict(self.DEFAULT_HEADERS)
        if headers:
            h.update(headers)
        if "Referer" not in h:
            h["Referer"] = "/".join(url.split("/")[:3])

        req = urllib.request.Request(url, headers=h, method="GET")
        try:
            with self._opener.open(req, timeout=timeout) as resp:
                # 自动解压
                if resp.info().get("Content-Encoding") == "gzip":
                    return gzip.decompress(resp.read()).decode("utf-8", errors="replace")
                return resp.read().decode("utf-8", errors="replace")
        except Exception as e:
            print(f"  ⚠️ 请求失败 [{url[:60]}]: {e}")
            return None

    def _json_get(self, url: str, headers: Dict = None) -> Optional[dict]:
        """GET + 自动 JSON 解析"""
        text = self._fetch(url, headers)
        if not text:
            return None
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None

    def _clean_html(self, text: str) -> str:
        """去掉 HTML 标签，保留纯文本"""
        text = re.sub(r"<[^>]+>", "", text)
        text = html.unescape(text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def scrape(self, user_id: str, limit: int = 20) -> List[Post]:
        """子类实现具体爬取逻辑"""
        raise NotImplementedError


# ── 工厂函数 ───────────────────────────────────────────────
def create_scraper(platform: str) -> ContentScraper:
    if platform == "bilibili":
        return BilibiliScraper()
    elif platform == "weibo":
        return WeiboScraper()
    elif platform == "web":
        return WebPageScraper()
    else:
        raise ValueError(f"不支持的平台: {platform}")


# ── B站爬虫 ────────────────────────────────────────────────
class BilibiliScraper(ContentScraper):
    """
    爬取B站用户视频/动态
    公开接口，无需登录

    user_id: B站用户数字ID（如 672328094）
    可从用户主页 URL 提取：https://space.bilibili.com/672328094
    """

    RATE_LIMIT = 2.0  # B站限制更严

    def scrape(self, user_id: str, limit: int = 30) -> List[Post]:
        posts = []
        # 方式1：用户动态（公开接口）
        posts += self._scrape_dynamic(user_id, limit)
        # 方式2：用户视频列表
        posts += self._scrape_videos(user_id, limit)
        return sorted(posts, key=lambda p: p.timestamp, reverse=True)[:limit]

    def _scrape_dynamic(self, uid: str, limit: int) -> List[Post]:
        """通过用户动态接口获取"""
        url = f"https://api.bilibili.com/x/polymer/web-dynamic/v1/feed/space?host_mid={uid}&dm_img_list=[]&dm_img_str=V2ViR0wgMS4wIChPcGVuR0wgRVMgMi4wIENPVCkgQXBwbGVtZW50IEtIVE1MUCwxLjAgR2Vvcmdldik=&dm_cover_img_str=QU5HTEUgKE5WSURJQSBHZUZvcmNlIEdUWCA0MCk=&features=itemImg2_aspect&update_cache_time=1000&dm_img_list=[]&dm_img_str=V2ViR0wgMS4wIChPcGVuR0wgRVMgMi4wIENPVCkgQXBwbGVtZW50IEtIVE1MUCwxLjAgR2Vvcmdldik="
        data = self._json_get(url)
        if not data or data.get("code") != 0:
            return []

        posts = []
        items = data.get("data", {}).get("items", [])
        for item in items[:limit]:
            modules = item.get("modules", {})
            dynamic = modules.get("module_dynamic", {})
            content = dynamic.get("content", "")
            author = dynamic.get("author", {}).get("name", "B站用户")
            timestamp = int(dynamic.get("pub_ts", 0))

            # 取正文，清理HTML
            text = self._clean_html(content)
            if len(text) < 5:
                continue

            posts.append(Post(
                platform="bilibili",
                author=author,
                content=text,
                timestamp=timestamp,
                date_str=datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M") if timestamp else "",
                url=f"https://www.bilibili.com/opus/{item.get('opus_id', '')}",
                raw_data=item,
            ))
        return posts

    def _scrape_videos(self, uid: str, limit: int) -> List[Post]:
        """获取用户视频列表"""
        url = f"https://api.bilibili.com/x/space/wbi/pubinfo?mid={uid}&platform=pc&jsonp=jsonp&pn=1&ps=25"
        data = self._json_get(url)
        if not data or data.get("code") != 0:
            return []

        posts = []
        for v in data.get("data", {}).get("tlist", {}).values():
            # 视频列表项
            posts.append(Post(
                platform="bilibili",
                author=v.get("name", "B站用户"),
                content=f"[视频标题] {v.get('title','无标题')} [描述] {v.get('description','')}",
                timestamp=int(v.get("created", 0)),
                date_str=datetime.fromtimestamp(int(v.get("created", 0))).strftime("%Y-%m-%d") if v.get("created") else "",
                url=f"https://www.bilibili.com/video/{v.get('bvid','')}",
                likes=v.get("like", 0),
                raw_data=v,
            ))
        return posts

    @staticmethod
    def uid_from_url(url: str) -> Optional[str]:
        """从B站主页URL提取UID"""
        m = re.search(r"space\.bilibili\.com/(\d+)", url)
        return m.group(1) if m else None


# ── 微博爬虫 ────────────────────────────────────────────────
class WeiboScraper(ContentScraper):
    """
    爬取微博用户发布内容
    使用移动端接口，部分公开
    """

    RATE_LIMIT = 3.0

    def scrape(self, user_id: str, limit: int = 30) -> List[Post]:
        """
        user_id: 微博用户数字ID（如 1195230310）
        可从用户主页 URL 提取：https://weibo.com/u/1195230310
        或移动端：https://m.weibo.cn/u/1195230310
        """
        # 方法1：移动端API（无需登录）
        posts = self._scrape_mobile(user_id, limit)
        if posts:
            return posts[:limit]
        # 方法2：PC端（可能需要登录）
        return self._scrape_pc(user_id, limit)

    def _scrape_mobile(self, uid: str, limit: int) -> List[Post]:
        """使用移动端API"""
        # containerid 需要先获取，这里用简化的用户timeline接口
        url = f"https://m.weibo.cn/api/container/getIndex?type=uid&value={uid}&containerid=107603{uid}"
        headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                          "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
            "Referer": f"https://m.weibo.cn/u/{uid}",
            "Accept": "application/json, text/plain",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "MWeibo-Pwa": "1",
            "X-Requested-With": "XMLHttpRequest",
        }
        data = self._json_get(url, headers)
        if not data or data.get("ok") != 1:
            return []

        posts = []
        for card in data.get("data", {}).get("cards", []):
            mblog = card.get("mblog", {})
            if not mblog:
                continue

            # 提取文字内容
            text = self._clean_html(mblog.get("text", ""))
            if len(text) < 5:
                continue

            # 时间戳
            created_at = mblog.get("created_timestamp", 0) or mblog.get("created_at", 0)
            try:
                ts = int(created_at)
            except:
                ts = 0

            # 转发/评论/点赞
            reposts = int(mblog.get("reposts_count", 0))
            comments = int(mblog.get("comments_count", 0))
            likes = int(mblog.get("attitudes_count", 0))

            posts.append(Post(
                platform="weibo",
                author=mblog.get("user", {}).get("screen_name", "微博用户"),
                content=text,
                timestamp=ts,
                date_str=datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M") if ts else "",
                url=f"https://weibo.com/{mblog.get('user',{}).get('id','')}/{mblog.get('bid','')}",
                likes=likes,
                reposts=reposts,
                comments=comments,
                raw_data=mblog,
            ))
        return posts

    def _scrape_pc(self, uid: str, limit: int) -> List[Post]:
        """PC端微博（正则解析HTML）"""
        url = f"https://weibo.com/u/{uid}"
        html_content = self._fetch(url)
        if not html_content:
            return []

        posts = []
        # 提取微博内容（PC端 HTML 中的 JSON 数据）
        pattern = re.compile(r'\$render_data\s*=\s*\[(.*?)\]\[0\]', re.DOTALL)
        match = pattern.search(html_content)
        if not match:
            return []

        try:
            json_str = match.group(1).replace("&quot;", '"')
            json_str = html.unescape(json_str)
            data = json.loads(json_str)
            user_info = data.get("status", {}).get("user", {})
            statuses = data.get("status", {}).get("statuses", [])
            for s in statuses[:limit]:
                text = self._clean_html(s.get("text", ""))
                if len(text) < 5:
                    continue
                ts = int(s.get("created_at", {}).get("timestamp", 0)) if isinstance(s.get("created_at"), dict) else 0
                posts.append(Post(
                    platform="weibo",
                    author=user_info.get("name", "微博用户"),
                    content=text,
                    timestamp=ts,
                    date_str=datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M") if ts else "",
                    url=f"https://weibo.com/{s.get('id','')}",
                    likes=s.get("attitudes_count", 0),
                    reposts=s.get("reposts_count", 0),
                    comments=s.get("comments_count", 0),
                    raw_data=s,
                ))
        except Exception:
            pass
        return posts

    @staticmethod
    def uid_from_url(url: str) -> Optional[str]:
        """从微博URL提取UID"""
        # https://weibo.com/u/6723462181
        m = re.search(r"weibo\.com/u/(\d+)", url)
        if m:
            return m.group(1)
        # https://weibo.com/xxxx (个人域名)
        m = re.search(r"weibo\.com/([a-zA-Z][a-zA-Z0-9_-]{2,})(?:\?|/|$)", url)
        if m and not m.group(1).isdigit():
            return None  # 个人域名，需要额外查询
        return m.group(1) if m else None


# ── 通用网页爬虫 ────────────────────────────────────────────
class WebPageScraper(ContentScraper):
    """
    爬取任意网页正文
    自动提取 <article>、<main>、正文段落
    """

    def scrape(self, url: str, limit: int = 20) -> List[Post]:
        content = self._fetch(url)
        if not content:
            return []

        # 提取 <title>
        title_match = re.search(r"<title[^>]*>([^<]+)</title>", content)
        title = title_match.group(1).strip() if title_match else "网页内容"

        # 提取正文段落
        text = self._extract_article_text(content)

        if len(text) < 50:
            return []

        return [Post(
            platform="web",
            author=title,
            content=text[:3000],  # 截断避免过长
            timestamp=0,
            date_str="",
            url=url,
            raw_data={},
        )]

    def _extract_article_text(self, html_content: str) -> str:
        """提取网页正文"""
        # 去掉 <script> <style> <nav> <footer> 等无关标签
        html_content = re.sub(r"<script[^>]*>.*?</script>", " ", html_content, flags=re.DOTALL)
        html_content = re.sub(r"<style[^>]*>.*?</style>", " ", html_content, flags=re.DOTALL)
        html_content = re.sub(r"<nav[^>]*>.*?</nav>", " ", html_content, flags=re.DOTALL)
        html_content = re.sub(r"<footer[^>]*>.*?</footer>", " ", html_content, flags=re.DOTALL)

        # 提取 <article> 或 <main>
        article_match = re.search(r"<article[^>]*>(.*?)</article>", html_content, re.DOTALL)
        main_match = re.search(r"<main[^>]*>(.*?)</main>", html_content, re.DOTALL)
        body_match = re.search(r"<body[^>]*>(.*?)</body>", html_content, re.DOTALL)

        best = article_match or main_match or body_match
        text_source = best.group(1) if best else html_content

        # 提取所有段落
        paragraphs = re.findall(r"<p[^>]*>(.*?)</p>", text_source, re.DOTALL)
        sentences = []
        for p in paragraphs:
            text = self._clean_html(p)
            if len(text) > 10:
                sentences.append(text)

        return "。".join(sentences) if sentences else self._clean_html(text_source)


if __name__ == "__main__":
    print("ContentScraper OK — 支持 bilibili / weibo / 任意URL")
