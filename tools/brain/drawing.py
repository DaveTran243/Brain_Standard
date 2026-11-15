"""brain kg draw: one HTML page that shows the platform map and the knowledge graph together (docs/platform-map.md).

The page is self-contained (data inline, d3 from cdnjs) so it opens from the disk in any browser. `fragment=True`
leaves out the document wrapper for hosts that add their own (a claude.ai artifact).
"""
from __future__ import annotations

import json
from pathlib import Path

from . import drive, notes
from .config import Brain

D3 = "https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js"


def html(data: dict, fragment: bool = False) -> str:
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    body = PAGE.replace("__D3__", D3).replace("__DATA__", payload)
    if fragment:
        return body
    return ("<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1, viewport-fit=cover\">\n"
            "</head>\n<body>\n" + body + "\n</body>\n</html>\n")


def write(brain: Brain, path: Path, with_files: bool = False, with_knowledge: bool = True, fragment: bool = False) -> int:
    data = drive.draw_data(brain, with_files=with_files, with_knowledge=with_knowledge)
    data["stats"] = drive.stats(brain)
    data["kg_facts"] = sum(1 for _ in _kg_lines(brain))
    notes.write(Path(path), html(data, fragment=fragment))
    return len(data["nodes"])


def _kg_lines(brain: Brain):
    f = brain.path("kg_triples")
    if f.is_file():
        yield from (x for x in notes.read(f).splitlines() if x.strip())


PAGE = r"""<title>Platform Map</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
/* Layout: a sidebar of controls and details beside one full-height canvas; on phones the sidebar stacks above. */
:root{
  --bg:#eef1f4; --panel:#ffffff; --ink:#18202b; --muted:#5b6675; --line:#d4dae2;
  --folder:#6c7a8c; --dataset:#c27a12; --repo:#11807a; --jd:#6a4fc4; --concept:#c2416b; --file:#8b97a6;
  --edge:rgba(40,52,68,.16); --edge-kg:rgba(194,65,107,.30); --focus:#1f6fd1;
  --sans:"IBM Plex Sans",system-ui,-apple-system,"Segoe UI",sans-serif;
  --mono:"IBM Plex Mono",ui-monospace,Consolas,monospace;
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    --bg:#0f141b; --panel:#161d26; --ink:#e3e9f0; --muted:#97a3b2; --line:#2a3542;
    --folder:#8e9cb0; --dataset:#e2a14a; --repo:#3fc1b8; --jd:#a18cf0; --concept:#ef7aa0; --file:#6d7988;
    --edge:rgba(200,214,230,.13); --edge-kg:rgba(239,122,160,.30); --focus:#6aa8f2; color-scheme:dark;
  }
}
:root[data-theme="dark"]{
  --bg:#0f141b; --panel:#161d26; --ink:#e3e9f0; --muted:#97a3b2; --line:#2a3542;
  --folder:#8e9cb0; --dataset:#e2a14a; --repo:#3fc1b8; --jd:#a18cf0; --concept:#ef7aa0; --file:#6d7988;
  --edge:rgba(200,214,230,.13); --edge-kg:rgba(239,122,160,.30); --focus:#6aa8f2; color-scheme:dark;
}
*{box-sizing:border-box}
html,body{height:100%}
body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--sans);font-size:14px;line-height:1.45}
.app{height:100%;display:grid;grid-template-columns:320px minmax(0,1fr);gap:0}
aside{background:var(--panel);border-right:1px solid var(--line);overflow:auto;display:flex;flex-direction:column;gap:16px;
  padding-block:18px;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:16px}
h1{font-size:1.25rem;margin:0;font-weight:600;letter-spacing:-.01em;text-wrap:balance}
.sub{color:var(--muted);font-size:.85rem;margin:2px 0 0}
.sub code{font-family:var(--mono);font-size:.8rem}
.stats{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px}
.stat{border:1px solid var(--line);border-radius:8px;padding:8px}
.stat b{display:block;font-size:1.05rem;font-variant-numeric:tabular-nums}
.stat span{font-size:.72rem;color:var(--muted);text-transform:uppercase;letter-spacing:.05em}
label.h{font-size:.72rem;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);display:block;margin-bottom:6px}
input[type=search]{width:100%;font:inherit;color:var(--ink);background:var(--bg);border:1px solid var(--line);border-radius:8px;padding:8px 10px}
input[type=search]:focus-visible,button:focus-visible,input[type=checkbox]:focus-visible,input[type=range]:focus-visible{outline:2px solid var(--focus);outline-offset:2px}
.layers{display:flex;flex-direction:column;gap:6px}
.layer{display:flex;align-items:center;gap:8px;cursor:pointer}
.dot{width:11px;height:11px;border-radius:50%;flex:none}
.layer small{margin-left:auto;color:var(--muted);font-variant-numeric:tabular-nums}
.row{display:flex;align-items:center;gap:10px}
input[type=range]{flex:1;accent-color:var(--focus)}
.results{display:flex;flex-direction:column;gap:2px;max-height:180px;overflow:auto}
.results button{all:unset;cursor:pointer;padding:5px 6px;border-radius:6px;font-family:var(--mono);font-size:.78rem;overflow-wrap:anywhere}
.results button:hover,.results button:focus-visible{background:var(--bg)}
.detail{border:1px solid var(--line);border-radius:10px;padding:12px;display:flex;flex-direction:column;gap:6px;min-width:0}
.detail .path{font-family:var(--mono);font-size:.8rem;overflow-wrap:anywhere}
.detail dl{display:grid;grid-template-columns:auto minmax(0,1fr);gap:4px 10px;margin:0;font-size:.85rem}
.detail dt{color:var(--muted)} .detail dd{margin:0;overflow-wrap:anywhere;font-variant-numeric:tabular-nums}
.empty{color:var(--muted);font-size:.85rem}
.note{color:var(--muted);font-size:.78rem;margin-top:auto}
main{position:relative;min-width:0;min-height:0}
canvas{display:block;width:100%;height:100%;cursor:grab}
canvas.drag{cursor:grabbing}
.tip{position:absolute;pointer-events:none;background:var(--panel);border:1px solid var(--line);border-radius:6px;padding:4px 8px;
  font-family:var(--mono);font-size:.75rem;max-width:420px;overflow-wrap:anywhere;box-shadow:0 4px 14px rgba(0,0,0,.12)}
@media (max-width:760px){
  .app{grid-template-columns:1fr;grid-template-rows:auto minmax(420px,70vh);height:auto}
  aside{border-right:0;border-bottom:1px solid var(--line);padding-right:max(16px,env(safe-area-inset-right,0px))}
  main{height:70vh}
}
@media (prefers-reduced-motion:reduce){canvas{scroll-behavior:auto}}
</style>

<div class="app">
<aside>
  <div>
    <h1>Platform map</h1>
    <p class="sub">The brain platform: folders, datasets, repositories, Johnny Decimal numbers and the knowledge graph's concepts. Root <code id="root"></code>, scanned <span id="built"></span>.</p>
  </div>
  <div class="stats" id="stats"></div>
  <div>
    <label class="h" for="q">Find a location</label>
    <input type="search" id="q" placeholder="e.g. invoices, run logs, a repository" autocomplete="off">
    <div class="results" id="results"></div>
  </div>
  <div>
    <span class="h">Layers</span>
    <div class="layers" id="layers"></div>
  </div>
  <div>
    <label class="h" for="depth">Folder depth: <span id="depthv"></span></label>
    <div class="row"><input type="range" id="depth" min="1" max="14" step="1"></div>
    <label class="layer" style="margin-top:8px"><input type="checkbox" id="arch"> Show 90-Archive</label>
  </div>
  <div class="detail" id="detail"><span class="empty">Click a node to see its path, file count and JD number.</span></div>
  <p class="note">Made by <code>brain kg draw</code> from <code>_kg/drive.jsonl</code> and <code>_kg/triples.jsonl</code>. Only file names, sizes and dates are read, never contents.</p>
</aside>
<main id="stage"><canvas id="cv" aria-label="Graph of the folders and concepts on the platform root"></canvas><div class="tip" id="tip" hidden></div></main>
</div>

<script src="__D3__"></script>
<script>
const DATA = __DATA__;
(function(){
  const $ = s => document.querySelector(s);
  const KINDS = [
    ["folder","Folder","--folder"],["dataset","Dataset (many files)","--dataset"],["repo","Git repository","--repo"],
    ["jd","Johnny Decimal number","--jd"],["concept","Knowledge graph concept","--concept"],["file","File","--file"]];
  const fmtN = n => (n||0).toLocaleString();
  const fmtB = b => { if(!b) return "0 B"; const u=["B","KB","MB","GB","TB"]; let i=0; while(b>=1024&&i<4){b/=1024;i++} return b.toFixed(b<10&&i?1:0)+" "+u[i]; };
  $("#root").textContent = DATA.root || "";
  $("#built").textContent = (DATA.built||"").replace("T"," ").slice(0,16);
  const st = DATA.stats||{};
  const jdCount = DATA.nodes.filter(n=>n.kind==="jd").length;
  [["folders",st.folders],["files",st.files],["size",null,fmtB(st.bytes)],["datasets",st.datasets],["repos",st.repositories],["KG facts",DATA.kg_facts]]
    .forEach(([l,v,txt])=>{const d=document.createElement("div");d.className="stat";d.innerHTML=`<b>${txt||fmtN(v)}</b><span>${l}</span>`;$("#stats").appendChild(d)});

  const byId = new Map(DATA.nodes.map(n=>[n.id,n]));
  const rootKey = DATA.root;
  DATA.nodes.forEach(n=>{ n.depth = n.path ? n.path.replace(/\/$/,"").split("/").length-1 : 0; n.archive = !!(n.path && /\/(90-Archive|backups)(\/|$)/.test(n.path)); });
  const counts = {}; DATA.nodes.forEach(n=>counts[n.kind]=(counts[n.kind]||0)+1);
  const on = {folder:true,dataset:true,repo:true,jd:true,concept:true,file:true};
  KINDS.forEach(([k,label,tok])=>{
    if(!counts[k]) return;
    const id="layer-"+k, el=document.createElement("label"); el.className="layer";
    el.innerHTML=`<input type="checkbox" id="${id}" checked><span class="dot" style="background:var(${tok})"></span>${label}<small>${fmtN(counts[k])}</small>`;
    el.querySelector("input").addEventListener("change",e=>{on[k]=e.target.checked;rebuild()});
    $("#layers").appendChild(el);
  });
  let maxDepth = 5, showArch = false;
  try{ const s=JSON.parse(localStorage.getItem("platform-map")||"{}"); if(s.depth) maxDepth=s.depth; if(s.arch) showArch=true; }catch(e){}
  $("#depth").value = maxDepth; $("#depthv").textContent = maxDepth; $("#arch").checked = showArch;
  const save = ()=>{ try{localStorage.setItem("platform-map",JSON.stringify({depth:maxDepth,arch:showArch}))}catch(e){} };
  $("#depth").addEventListener("input",e=>{maxDepth=+e.target.value;$("#depthv").textContent=maxDepth;save();rebuild()});
  $("#arch").addEventListener("change",e=>{showArch=e.target.checked;save();rebuild()});

  const cv = $("#cv"), ctx = cv.getContext("2d"), stage=$("#stage"), tip=$("#tip");
  let W=0,H=0,dpr=1, transform=d3.zoomIdentity, colors={}, nodes=[], links=[], sim=null, selected=null, hover=null;
  function readColors(){ const cs=getComputedStyle(document.documentElement); KINDS.forEach(([k,,t])=>colors[k]=cs.getPropertyValue(t).trim());
    ["--edge","--edge-kg","--ink","--muted","--focus","--panel"].forEach(t=>colors[t]=cs.getPropertyValue(t).trim()); }
  function size(){ const r=stage.getBoundingClientRect(); dpr=window.devicePixelRatio||1; W=r.width; H=r.height; cv.width=W*dpr; cv.height=H*dpr; draw(); }
  function visible(n){
    if(!on[n.kind]) return false;
    if(n.archive && !showArch) return false;
    if((n.kind==="folder"||n.kind==="dataset"||n.kind==="repo"||n.kind==="file") && n.depth>maxDepth) return false;
    return true;
  }
  function radius(n){
    if(n.kind==="concept") return 3.5;
    if(n.kind==="jd") return 5;
    if(n.kind==="file") return 2.5;
    const f = n.files||0; return Math.max(3, Math.min(16, 2.5+Math.sqrt(f)*.6)) + (n.id===rootKey?6:0);
  }
  function rebuild(){
    const keep = new Set(DATA.nodes.filter(visible).map(n=>n.id));
    nodes = DATA.nodes.filter(n=>keep.has(n.id));
    links = DATA.links.filter(l=>keep.has(l.source.id||l.source) && keep.has(l.target.id||l.target))
      .map(l=>({source:l.source.id||l.source,target:l.target.id||l.target,kind:l.kind,p:l.p}));
    const deg={}; links.forEach(l=>{deg[l.source]=(deg[l.source]||0)+1;deg[l.target]=(deg[l.target]||0)+1});
    nodes = nodes.filter(n=>n.kind!=="concept" || deg[n.id]);
    const ids=new Set(nodes.map(n=>n.id)); links=links.filter(l=>ids.has(l.source)&&ids.has(l.target));
    if(sim) sim.stop();
    sim = d3.forceSimulation(nodes)
      .force("link", d3.forceLink(links).id(d=>d.id).distance(l=>l.kind==="contains"?26:l.kind==="jd"?18:22).strength(l=>l.kind==="knows"?.25:.9))
      .force("charge", d3.forceManyBody().strength(n=>n.kind==="concept"?-18:-40).distanceMax(320))
      .force("collide", d3.forceCollide(n=>radius(n)+1.5))
      .force("x", d3.forceX(0).strength(.03)).force("y", d3.forceY(0).strength(.03))
      .alphaDecay(matchMedia("(prefers-reduced-motion: reduce)").matches?0.2:0.03)
      .on("tick", draw);
  }
  function draw(){
    if(!W) return;
    ctx.setTransform(dpr,0,0,dpr,0,0); ctx.clearRect(0,0,W,H);
    ctx.save(); ctx.translate(W/2+transform.x, H/2+transform.y); ctx.scale(transform.k, transform.k);
    ctx.lineWidth = 1/transform.k;
    for(const l of links){ if(l.source.x==null) continue;
      ctx.strokeStyle = l.kind==="knows"||l.kind==="stored" ? colors["--edge-kg"] : colors["--edge"];
      ctx.beginPath(); ctx.moveTo(l.source.x,l.source.y); ctx.lineTo(l.target.x,l.target.y); ctx.stroke(); }
    const hot = new Set(); if(selected){ hot.add(selected.id); links.forEach(l=>{ if(l.source.id===selected.id) hot.add(l.target.id); if(l.target.id===selected.id) hot.add(l.source.id); }); }
    for(const n of nodes){ if(n.x==null) continue;
      ctx.globalAlpha = selected && !hot.has(n.id) ? .25 : (n.archive?.55:1);
      ctx.fillStyle = colors[n.kind]; ctx.beginPath(); ctx.arc(n.x,n.y,radius(n),0,7); ctx.fill();
      if(n===selected||n===hover){ ctx.globalAlpha=1; ctx.strokeStyle=colors["--focus"]; ctx.lineWidth=2/transform.k; ctx.stroke(); ctx.lineWidth=1/transform.k; } }
    ctx.globalAlpha=1; ctx.fillStyle=colors["--ink"]; ctx.font=`${11/transform.k}px "IBM Plex Sans",sans-serif`;
    for(const n of nodes){ if(n.x==null) continue;
      const big = n.kind!=="concept" && n.kind!=="file" && (n.depth<=2 || radius(n)>9 || n.kind==="repo" || n.kind==="dataset");
      if(big || hot.has(n.id) || transform.k>2.4){ ctx.fillText(n.label, n.x+radius(n)+2, n.y+3.5/transform.k); } }
    ctx.restore();
  }
  function at(px,py){ const x=(px-W/2-transform.x)/transform.k, y=(py-H/2-transform.y)/transform.k; let best=null,bd=1e9;
    for(const n of nodes){ const d=(n.x-x)**2+(n.y-y)**2, r=radius(n)+4/transform.k; if(d<r*r&&d<bd){bd=d;best=n} } return best; }
  const zoom = d3.zoom().scaleExtent([.15,8]).on("zoom",e=>{transform=e.transform;draw()});
  d3.select(cv).call(zoom).on("dblclick.zoom",null);
  d3.select(cv).call(d3.drag().container(cv).subject(e=>{const n=at(e.x,e.y); if(n){n.x0=n.x;n.y0=n.y} return n;})
    .on("start",e=>{cv.classList.add("drag"); if(!e.active) sim.alphaTarget(.2).restart(); e.subject.fx=e.subject.x; e.subject.fy=e.subject.y;})
    .on("drag",e=>{e.subject.fx=(e.x-W/2-transform.x)/transform.k; e.subject.fy=(e.y-H/2-transform.y)/transform.k;})
    .on("end",e=>{cv.classList.remove("drag"); if(!e.active) sim.alphaTarget(0); e.subject.fx=null; e.subject.fy=null;}));
  cv.addEventListener("mousemove",e=>{const r=cv.getBoundingClientRect(); const n=at(e.clientX-r.left,e.clientY-r.top);
    if(n!==hover){hover=n;draw()} if(n){tip.hidden=false; tip.textContent=n.path||n.label; tip.style.left=(e.clientX-r.left+12)+"px"; tip.style.top=(e.clientY-r.top+12)+"px"} else tip.hidden=true;});
  cv.addEventListener("mouseleave",()=>{tip.hidden=true;hover=null;draw()});
  cv.addEventListener("click",e=>{const r=cv.getBoundingClientRect(); select(at(e.clientX-r.left,e.clientY-r.top), false);});
  function select(n, center){
    selected=n; draw(); const box=$("#detail");
    if(!n){ box.innerHTML='<span class="empty">Click a node to see its path, file count and JD number.</span>'; return; }
    const jd = DATA.links.filter(l=>(l.target.id||l.target)===n.id && l.kind==="jd").map(l=>byId.get(l.source.id||l.source).label);
    const kgs = DATA.links.filter(l=>(l.target.id||l.target)===n.id && l.kind==="stored").map(l=>byId.get(l.source.id||l.source).label);
    const rel = n.kind==="concept" ? DATA.links.filter(l=>l.kind==="knows" && ((l.source.id||l.source)===n.id || (l.target.id||l.target)===n.id)).slice(0,8)
      .map(l=>{const s=byId.get(l.source.id||l.source), t=byId.get(l.target.id||l.target); return `${s.label} → ${l.p} → ${t.label}`}) : [];
    const kindName = (KINDS.find(k=>k[0]===n.kind)||[])[1]||n.kind;
    const rows = [["Kind",kindName]];
    if(n.files!=null && n.kind!=="file") rows.push(["Files",fmtN(n.files)]);
    if(n.bytes!=null) rows.push(["Size",fmtB(n.bytes)]);
    if(n.exts && Object.keys(n.exts).length) rows.push(["Extensions",Object.entries(n.exts).map(([e,c])=>`${e} ${fmtN(c)}`).join(", ")]);
    if(n.git) rows.push(["Repository",n.git]);
    if(jd.length) rows.push(["JD number",jd.join(", ")]);
    if(kgs.length) rows.push(["Notes in the KG",kgs.slice(0,6).join("; ")]);
    if(rel.length) rows.push(["Relations",rel.join("\n")]);
    const esc=s=>String(s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
    box.innerHTML = `<div class="path">${esc(n.path||n.label)}</div><dl>${rows.map(([a,b])=>`<dt>${esc(a)}</dt><dd style="white-space:pre-line">${esc(b)}</dd>`).join("")}</dl>`;
    if(center && n.x!=null){ d3.select(cv).transition().duration(500).call(zoom.transform, d3.zoomIdentity.translate(-n.x*2,-n.y*2).scale(2)); }
  }
  const fold = s=>String(s||"").replace(/đ/g,"d").replace(/Đ/g,"D").normalize("NFKD").replace(/[̀-ͯ]/g,"").toLowerCase();
  $("#q").addEventListener("input",e=>{
    const words = fold(e.target.value).split(/[^a-z0-9]+/).filter(w=>w.length>1); const out=$("#results"); out.innerHTML="";
    if(!words.length) return;
    const hits = DATA.nodes.map(n=>{const hay=fold((n.path||"")+" "+n.label); const s=words.filter(w=>hay.includes(w)).length + (words.every(w=>fold(n.label).includes(w))?2:0); return [s,n]})
      .filter(([s])=>s>=words.length).sort((a,b)=>b[0]-a[0]||(a[1].depth||0)-(b[1].depth||0)).slice(0,12);
    hits.forEach(([,n])=>{const b=document.createElement("button"); b.type="button"; b.textContent=n.path||n.label;
      b.addEventListener("click",()=>{ if(!visible(n)){ on[n.kind]=true; showArch = showArch||n.archive; if(n.depth>maxDepth){maxDepth=Math.min(14,n.depth);$("#depth").value=maxDepth;$("#depthv").textContent=maxDepth} $("#arch").checked=showArch; const cb=document.getElementById("layer-"+n.kind); if(cb) cb.checked=true; rebuild(); setTimeout(()=>select(n,true),700);} else select(n,true); });
      out.appendChild(b)});
  });
  readColors();
  matchMedia("(prefers-color-scheme: dark)").addEventListener("change",()=>{readColors();draw()});
  new MutationObserver(()=>{readColors();draw()}).observe(document.documentElement,{attributes:true,attributeFilter:["data-theme"]});
  new ResizeObserver(size).observe(stage);
  rebuild(); size();
})();
</script>"""
