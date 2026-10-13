#!/usr/bin/env python3
"""本文から iPhone 向けのリーダー HTML を生成する。

本文（works/<作品名>/chapters/NN_題名.txt）を読み、単一ファイルの HTML を
works/<作品名>/reader/ に書き出す。外部リソースを一切参照しないので、
iCloud Drive に置いて Safari で開けばそのまま読める。

使い方:
    python3 tools/build_reader.py 豊穣譜
    python3 tools/build_reader.py 豊穣譜 --title "別の題名"
"""

import argparse
import html
import pathlib
import re
import sys

# 作品ごとの場面転換の区切り（CLAUDE.md の規約と一致させる）
SEPARATORS = {"＊", "◇", "——"}

CSS = """
:root{
  --bg:#13110f; --paper:#1b1816; --ink:#ddd3c6; --dim:#8a7f73;
  --rule:#2e2a26; --accent:#c9a87c; --sel:#3a3128;
  --fs:17px; --lh:2.0; --measure:34em;
}
html[data-theme="light"]{
  --bg:#efe9e0; --paper:#fbf7f1; --ink:#2b2520; --dim:#7a6e62;
  --rule:#ddd4c7; --accent:#8a6a3c; --sel:#e6dccb;
}
*{box-sizing:border-box}
html,body{margin:0;padding:0}
body{
  background:var(--bg); color:var(--ink);
  font-family:"Hiragino Mincho ProN","Yu Mincho",YuMincho,"Noto Serif JP",serif;
  font-size:var(--fs); line-height:var(--lh);
  -webkit-text-size-adjust:100%;
  text-rendering:optimizeLegibility;
}
::selection{background:var(--sel)}

/* 上部バー */
#bar{
  position:sticky; top:0; z-index:10;
  display:flex; align-items:center; gap:.5rem;
  padding:calc(env(safe-area-inset-top,0px) + .55rem) .9rem .55rem;
  background:color-mix(in srgb, var(--bg) 88%, transparent);
  backdrop-filter:saturate(1.4) blur(12px);
  border-bottom:1px solid var(--rule);
  font-family:-apple-system,BlinkMacSystemFont,"Hiragino Sans",sans-serif;
  font-size:13px; line-height:1.2;
}
#bar .grow{flex:1 1 auto; min-width:0; color:var(--dim);
  overflow:hidden; text-overflow:ellipsis; white-space:nowrap}
#bar button{
  flex:0 0 auto; appearance:none; border:1px solid var(--rule);
  background:var(--paper); color:var(--ink);
  border-radius:8px; padding:.4rem .6rem; font:inherit; cursor:pointer;
  min-height:32px;
}
#bar button:active{background:var(--sel)}

/* 進捗 */
#prog{position:fixed; left:0; top:0; height:2px; background:var(--accent);
  width:0; z-index:20; transition:width .15s linear}

/* パネル */
#panel{
  display:none; position:sticky; top:0; z-index:9;
  padding:.9rem; border-bottom:1px solid var(--rule); background:var(--paper);
  font-family:-apple-system,BlinkMacSystemFont,"Hiragino Sans",sans-serif;
  font-size:13px;
}
#panel.open{display:block}
#panel .row{display:flex; align-items:center; gap:.6rem; margin:.35rem 0; flex-wrap:wrap}
#panel .row > span:first-child{flex:0 0 5.5em; color:var(--dim)}
#panel input[type=range]{flex:1 1 8rem; min-width:7rem; accent-color:var(--accent)}
#toc{margin:.6rem 0 0; padding:0; list-style:none; border-top:1px solid var(--rule)}
#toc li{border-bottom:1px solid var(--rule)}
#toc a{display:block; padding:.65rem .2rem; color:var(--ink); text-decoration:none}
#toc a:active{background:var(--sel)}
#toc .n{color:var(--accent); margin-right:.6em; font-variant-numeric:tabular-nums}

/* 本文 */
main{padding:0 1.15rem calc(env(safe-area-inset-bottom,0px) + 5rem)}
article{max-width:var(--measure); margin:0 auto}
h1.work{
  font-size:1.55em; line-height:1.45; margin:2.2rem 0 .3rem; letter-spacing:.04em;
}
.sub{color:var(--dim); font-size:.82em; letter-spacing:.08em; margin:0 0 2.4rem;
  font-family:-apple-system,BlinkMacSystemFont,"Hiragino Sans",sans-serif}
h2.ch{
  font-size:1.18em; line-height:1.5; margin:4rem 0 1.8rem;
  padding-top:1.6rem; border-top:1px solid var(--rule); letter-spacing:.05em;
}
h2.ch:first-of-type{border-top:0}
h2.ch .n{display:block; color:var(--accent); font-size:.62em; letter-spacing:.2em;
  margin-bottom:.5rem;
  font-family:-apple-system,BlinkMacSystemFont,"Hiragino Sans",sans-serif}
p{margin:0 0 1.35em; text-align:justify;
  word-break:normal; overflow-wrap:break-word; line-break:strict}
p.sep{text-align:center; color:var(--dim); margin:2.3em 0; letter-spacing:.5em}
.end{margin:4.5rem 0 1rem; padding-top:1.5rem; border-top:1px solid var(--rule);
  color:var(--dim); font-size:.82em; text-align:center;
  font-family:-apple-system,BlinkMacSystemFont,"Hiragino Sans",sans-serif}
"""

JS = """
(function(){
  var K='READER_KEY';
  var root=document.documentElement, body=document.body;
  var st={};
  try{ st=JSON.parse(localStorage.getItem(K)||'{}'); }catch(e){ st={}; }

  function save(){ try{ localStorage.setItem(K,JSON.stringify(st)); }catch(e){} }

  // 設定の復元
  if(st.theme) root.setAttribute('data-theme',st.theme);
  var fs=st.fs||17, lh=st.lh||20;
  function applyType(){
    body.style.setProperty('--fs',fs+'px');
    body.style.setProperty('--lh',(lh/10).toFixed(1));
    document.getElementById('fsv').textContent=fs+'px';
    document.getElementById('lhv').textContent=(lh/10).toFixed(1);
  }
  var rFs=document.getElementById('fs'), rLh=document.getElementById('lh');
  rFs.value=fs; rLh.value=lh; applyType();
  rFs.addEventListener('input',function(){fs=+rFs.value; applyType(); st.fs=fs; save();});
  rLh.addEventListener('input',function(){lh=+rLh.value; applyType(); st.lh=lh; save();});

  document.getElementById('theme').addEventListener('click',function(){
    var cur=root.getAttribute('data-theme')==='light'?null:'light';
    if(cur){root.setAttribute('data-theme','light');} else {root.removeAttribute('data-theme');}
    st.theme=cur; save();
  });
  var panel=document.getElementById('panel');
  document.getElementById('menu').addEventListener('click',function(){
    panel.classList.toggle('open');
  });
  Array.prototype.forEach.call(document.querySelectorAll('#toc a'),function(a){
    a.addEventListener('click',function(){ panel.classList.remove('open'); });
  });

  // 進捗と読書位置
  var prog=document.getElementById('prog'), label=document.getElementById('where');
  var heads=[].slice.call(document.querySelectorAll('h2.ch'));
  var raf=null;
  function onScroll(){
    if(raf) return;
    raf=requestAnimationFrame(function(){
      raf=null;
      var h=document.documentElement.scrollHeight-window.innerHeight;
      var y=window.scrollY||0;
      var r=h>0?Math.min(1,Math.max(0,y/h)):0;
      prog.style.width=(r*100).toFixed(2)+'%';
      var cur=heads[0];
      for(var i=0;i<heads.length;i++){
        if(heads[i].getBoundingClientRect().top<=90) cur=heads[i];
      }
      if(cur) label.textContent=cur.dataset.label+'　'+Math.round(r*100)+'%';
      st.y=y; save();
    });
  }
  window.addEventListener('scroll',onScroll,{passive:true});

  if(st.y>0){
    // レイアウト確定後に復元する
    window.requestAnimationFrame(function(){
      window.requestAnimationFrame(function(){ window.scrollTo(0,st.y); onScroll(); });
    });
  } else { onScroll(); }
})();
"""


def paragraphs(text: str) -> str:
    out = []
    for block in text.split("\n"):
        line = block.strip()
        if not line:
            continue
        if line in SEPARATORS:
            out.append('<p class="sep">%s</p>' % html.escape(line))
        else:
            out.append("<p>%s</p>" % html.escape(line))
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("work", help="作品名（works/ 以下のディレクトリ名）")
    ap.add_argument("--title", help="表示する題名。既定は作品名")
    args = ap.parse_args()

    root = pathlib.Path("works") / args.work
    chapter_dir = root / "chapters"
    if not chapter_dir.is_dir():
        print("本文のディレクトリがない: %s" % chapter_dir, file=sys.stderr)
        return 1

    paths = sorted(chapter_dir.glob("*.txt"))
    if not paths:
        print("本文が見つからない: %s" % chapter_dir, file=sys.stderr)
        return 1

    title = args.title or args.work
    chapters, toc, total = [], [], 0
    for path in paths:
        m = re.match(r"(\d+)_(.+)", path.stem)
        num, name = (m.group(1), m.group(2)) if m else ("", path.stem)
        body = path.read_text(encoding="utf-8")
        total += len(body)
        label = ("第%d話" % int(num)) if num else name
        anchor = "ch%s" % (num or len(chapters) + 1)
        toc.append(
            '<li><a href="#%s"><span class="n">%s</span>%s</a></li>'
            % (anchor, html.escape(label), html.escape(name))
        )
        chapters.append(
            '<h2 class="ch" id="%s" data-label="%s"><span class="n">%s</span>%s</h2>\n%s'
            % (
                anchor,
                html.escape(label),
                html.escape(label),
                html.escape(name),
                paragraphs(body),
            )
        )

    key = "gts-reader:%s" % args.work
    page = """<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="{title}">
<meta name="color-scheme" content="dark light">
<title>{title}</title>
<style>{css}</style>
</head>
<body>
<div id="prog"></div>
<div id="bar">
  <button id="menu" aria-label="目次と設定">目次</button>
  <span class="grow" id="where">&nbsp;</span>
  <button id="theme" aria-label="明暗を切り替え">明暗</button>
</div>
<div id="panel">
  <div class="row"><span>文字の大きさ</span><input id="fs" type="range" min="14" max="24" step="1"><span id="fsv"></span></div>
  <div class="row"><span>行の間隔</span><input id="lh" type="range" min="16" max="26" step="1"><span id="lhv"></span></div>
  <ul id="toc">{toc}</ul>
</div>
<main><article>
<h1 class="work">{title}</h1>
<p class="sub">全{n}話／{total}字</p>
{chapters}
<p class="end">{total}字　｜　{n}話</p>
</article></main>
<script>{js}</script>
</body>
</html>
""".format(
        title=html.escape(title),
        css=CSS,
        js=JS.replace("READER_KEY", key),
        toc="\n".join(toc),
        chapters="\n".join(chapters),
        n=len(paths),
        total="{:,}".format(total),
    )

    out_dir = root / "reader"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / ("%s_リーダー.html" % title)
    out.write_text(page, encoding="utf-8")
    print("書き出し: %s （%d話／%d字／%.1f KB）"
          % (out, len(paths), total, out.stat().st_size / 1024))
    return 0


if __name__ == "__main__":
    sys.exit(main())
