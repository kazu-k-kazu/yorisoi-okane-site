#!/usr/bin/env python3
"""
MoneySpace 記事自動生成スクリプト
"""

import anthropic
import json
import re
import time
from datetime import datetime
from pathlib import Path

API_KEY      = "YOUR_ANTHROPIC_API_KEY"
BASE_DIR     = Path(__file__).parent
ARTICLES_DIR = BASE_DIR / "articles"
INDEX_FILE   = BASE_DIR / "articles_index.json"
ARTICLES_DIR.mkdir(exist_ok=True)

TOPICS = [
    {"category":"debt",       "cat_label":"借金・カードローン",   "keyword":"自己破産 メリット デメリット 手続き",    "title":"自己破産のメリット・デメリットと手続きの流れ"},
    {"category":"debt",       "cat_label":"借金・カードローン",   "keyword":"債務整理 種類 任意整理 個人再生",        "title":"債務整理3種類の違い：任意整理・個人再生・自己破産"},
    {"category":"debt",       "cat_label":"借金・カードローン",   "keyword":"過払い金 請求 時効 確認方法",            "title":"過払い金はいくら戻ってくる？請求の流れと時効"},
    {"category":"gambling",   "cat_label":"ギャンブル・課金",     "keyword":"ギャンブル依存症 治療 回復 方法",        "title":"ギャンブル依存症の回復方法と相談できる専門機関"},
    {"category":"gambling",   "cat_label":"ギャンブル・課金",     "keyword":"パチンコ 借金 解決 方法",                "title":"パチンコで作った借金を解決する方法"},
    {"category":"family",     "cat_label":"家族に内緒の出費",     "keyword":"夫婦 借金 隠す バレた 対処",            "title":"配偶者の隠し借金がバレた時の対処法"},
    {"category":"family",     "cat_label":"家族に内緒の出費",     "keyword":"夫婦 借金 連帯責任 範囲",               "title":"配偶者の借金は自分にも返済義務がある？法的な範囲"},
    {"category":"retirement",  "cat_label":"老後・退職後の不安",  "keyword":"老後 2000万円 貯金 50代 対策",          "title":"50代から始める老後2000万円問題への現実的な対策"},
    {"category":"retirement",  "cat_label":"老後・退職後の不安",  "keyword":"退職金 運用 失敗 しない 方法",          "title":"退職金の運用で失敗しないために知っておくこと"},
    {"category":"fraud",      "cat_label":"投資・詐欺被害",       "keyword":"投資詐欺 被害 取り戻す 方法 弁護士",    "title":"投資詐欺の被害を取り戻す方法と弁護士への相談"},
    {"category":"fraud",      "cat_label":"投資・詐欺被害",       "keyword":"SNS 投資詐欺 見分け方 手口",            "title":"SNS投資詐欺の手口と見分け方：被害に遭わないために"},
    {"category":"savings",    "cat_label":"貯金ゼロ・生活苦",     "keyword":"40代 貯金ゼロ 対策 立て直し",           "title":"40代で貯金ゼロ…今から立て直すための5つのステップ"},
    {"category":"savings",    "cat_label":"貯金ゼロ・生活苦",     "keyword":"毎月 赤字 原因 節約 家計 改善",         "title":"毎月赤字が続く原因と家計を黒字にする改善策"},
    {"category":"savings",    "cat_label":"貯金ゼロ・生活苦",     "keyword":"生活費 足りない シングルマザー 支援",   "title":"生活費が足りないシングルマザーが使える支援制度"},
    {"category":"debt",       "cat_label":"借金・カードローン",   "keyword":"リボ払い 怖い 仕組み 解決",             "title":"リボ払いが怖い理由と今すぐ解決する方法"},
]

def build_prompt(topic):
    return f"""あなたはお金・法律に関する専門的なウェブライターです。
以下の条件でSEO記事を作成してください。

【記事タイトル】
{topic['title']}

【メインキーワード】
{topic['keyword']}

【カテゴリ】
{topic['cat_label']}

【条件】
- 文字数: 1500〜2000文字
- 読者に寄り添った、わかりやすいトーン
- 専門用語には簡単な説明を付ける
- 見出しはH2（##）とH3（###）で構造化する
- 最後に「まとめ」セクションを入れる
- 法的アドバイスは避け「専門家にご相談ください」と誘導する
- 末尾に免責事項「本記事は法律・財務アドバイスではありません」を記載

【出力形式】
Markdown形式で出力してください（H1タイトルは不要）。
"""

def md_to_html(md_text):
    html = md_text
    html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
    html = re.sub(r'^[-・] (.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)
    html = re.sub(r'(<li>.*</li>\n?)+', lambda m: f'<ul>\n{m.group()}</ul>\n', html)
    paragraphs = []
    for para in html.split('\n\n'):
        para = para.strip()
        if not para: continue
        if para.startswith('<h') or para.startswith('<ul'):
            paragraphs.append(para)
        else:
            paragraphs.append(f'<p>{para}</p>')
    return '\n'.join(paragraphs)

def save_article_html(topic, content_md, slug):
    content_html = md_to_html(content_md)
    now_str = datetime.now().strftime('%Y年%m月%d日')
    cat_colors = {"debt":"#38B2AC","gambling":"#ED8936","family":"#9F7AEA","retirement":"#4299E1","fraud":"#F56565","savings":"#48BB78"}
    color = cat_colors.get(topic['category'], "#38B2AC")

    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{topic['title']} | MoneySpace</title>
  <meta name="description" content="{topic['keyword']}に関する解説記事。">
  <style>
    * {{ margin:0; padding:0; box-sizing:border-box; }}
    body {{ font-family:'Hiragino Sans','Yu Gothic',sans-serif; background:#F0FFF4; color:#2D3748; line-height:1.8; }}
    nav {{ background:#fff; border-bottom:1px solid #E2E8F0; padding:0 40px; height:64px; display:flex; align-items:center; justify-content:space-between; position:sticky; top:0; z-index:100; }}
    .logo {{ font-size:20px; font-weight:700; color:#2D3748; text-decoration:none; }}
    .logo span {{ color:#38B2AC; }}
    .back-link {{ color:#38B2AC; text-decoration:none; font-size:14px; }}
    .back-link:hover {{ text-decoration:underline; }}
    .container {{ max-width:780px; margin:48px auto; padding:0 24px; }}
    .cat-tag {{ display:inline-block; background:{color}1a; color:{color}; font-size:12px; font-weight:600; padding:4px 12px; border-radius:20px; margin-bottom:12px; }}
    h1 {{ font-size:30px; font-weight:700; color:#1A202C; line-height:1.4; margin-bottom:12px; }}
    .article-meta {{ font-size:13px; color:#718096; margin-bottom:32px; }}
    .article-body {{ background:#fff; border-radius:16px; padding:40px; box-shadow:0 2px 12px rgba(45,55,72,0.06); }}
    .article-body h2 {{ font-size:22px; font-weight:700; color:#2D3748; margin:36px 0 14px; padding-left:14px; border-left:4px solid {color}; }}
    .article-body h3 {{ font-size:17px; font-weight:700; color:#4A5568; margin:24px 0 10px; }}
    .article-body p {{ margin-bottom:16px; font-size:15px; }}
    .article-body ul {{ margin:12px 0 20px 24px; }}
    .article-body li {{ margin-bottom:8px; font-size:15px; }}
    .article-body strong {{ color:#2D3748; }}
    .disclaimer {{ background:#FFFBEB; border:1px solid #F6E05E; border-radius:8px; padding:16px 20px; margin-top:32px; font-size:13px; color:#744210; }}
    .cta-box {{ background:linear-gradient(135deg,#234E52,#2C7A7B); border-radius:12px; padding:24px; margin-top:32px; text-align:center; }}
    .cta-box p {{ color:#A0AEC0; font-size:13px; margin-bottom:12px; }}
    .cta-btn {{ background:#38B2AC; color:#fff; padding:12px 28px; border-radius:8px; text-decoration:none; font-weight:600; font-size:14px; display:inline-block; }}
    footer {{ text-align:center; padding:48px; color:#A0AEC0; font-size:13px; margin-top:48px; }}
  </style>
</head>
<body>
  <nav>
    <a href="../index.html" class="logo">Money<span>Space</span></a>
    <a href="../index.html" class="back-link">← トップに戻る</a>
  </nav>
  <div class="container">
    <span class="cat-tag">{topic['cat_label']}</span>
    <h1>{topic['title']}</h1>
    <div class="article-meta">公開日: {now_str} ｜ キーワード: {topic['keyword']}</div>
    <div class="article-body">
      {content_html}
      <div class="disclaimer">※ 本記事は法律・財務アドバイスではありません。具体的な対処は弁護士・FP等の専門家にご相談ください。</div>
      <div class="cta-box">
        <p>もっと詳しく相談したい方へ</p>
        <a href="../chat.html" class="cta-btn">AIに無料相談する</a>
      </div>
    </div>
  </div>
  <footer>© 2026 MoneySpace. All rights reserved.</footer>
</body>
</html>"""

    out_path = ARTICLES_DIR / f"{slug}.html"
    out_path.write_text(html, encoding='utf-8')
    return out_path

def update_index(entries):
    INDEX_FILE.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding='utf-8')

def main():
    client = anthropic.Anthropic(api_key=API_KEY)
    index = json.loads(INDEX_FILE.read_text(encoding='utf-8')) if INDEX_FILE.exists() else []
    existing_slugs = {e['slug'] for e in index}

    print('\n' + '='*50)
    print('  MoneySpace 記事自動生成')
    print('='*50)
    generated = skipped = 0

    for i, topic in enumerate(TOPICS, 1):
        slug = f"{topic['category']}-{i:03d}"
        if slug in existing_slugs:
            print(f'  [{i:02d}/{len(TOPICS)}] スキップ: {topic["title"][:35]}')
            skipped += 1
            continue

        print(f'  [{i:02d}/{len(TOPICS)}] 生成中: {topic["title"][:40]}')
        try:
            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=3000,
                messages=[{"role":"user","content":build_prompt(topic)}]
            )
            content_md = response.content[0].text
            out_path = save_article_html(topic, content_md, slug)
            index.append({"slug":slug,"title":topic['title'],"category":topic['category'],"cat_label":topic['cat_label'],"keyword":topic['keyword'],"file":f"articles/{slug}.html","created_at":datetime.now().isoformat()})
            update_index(index)
            existing_slugs.add(slug)
            print(f'         → 保存: {out_path.name}')
            generated += 1
            time.sleep(1)
        except Exception as e:
            print(f'         → エラー: {e}')

    print(f'\n  完了: {generated}件生成 / {skipped}件スキップ\n')

if __name__ == '__main__':
    main()
