#!/usr/bin/env python3
"""更新 AC 的公开 Stars；仅使用 Python 标准库，不需要 Token。"""
import argparse, collections, datetime, json, os, shutil, subprocess, sys, tempfile, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
USER = 'Adrianchen916'

def read(path, default):
    return json.loads(path.read_text()) if path.exists() else default

def atomic(path, content):
    with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=ROOT, delete=False) as f:
        f.write(content); temp = f.name
    os.replace(temp, path)

def dump(obj):
    return json.dumps(obj, ensure_ascii=False, indent=2) + '\n'

def fetch():
    repos = []
    for page in range(1, 101):
        url = f'https://api.github.com/users/{USER}/starred?per_page=100&page={page}&sort=created&direction=desc'
        # macOS 系统 curl 使用系统证书；Python 独立安装的证书库可能未配置。
        # 两种方式均保留 HTTPS 证书验证，不需要安装 Python 第三方包。
        if shutil.which('curl'):
            response = subprocess.run(['curl','--fail','--silent','--show-error','--location',
                                       '--connect-timeout','15','--max-time','45',
                                       '-H','Accept: application/vnd.github+json',
                                       '-H','User-Agent: AC-Stars-Library',url],
                                      capture_output=True, text=True, timeout=50)
            if response.returncode:
                raise RuntimeError(response.stderr.strip() or 'GitHub 请求失败')
            batch = json.loads(response.stdout)
        else:
            req = urllib.request.Request(url, headers={'Accept':'application/vnd.github+json', 'User-Agent':'AC-Stars-Library'})
            with urllib.request.urlopen(req, timeout=45) as response:
                batch = json.load(response)
        if not isinstance(batch, list): raise ValueError('GitHub 未返回仓库列表')
        repos.extend(batch)
        if len(batch) < 100: return repos
    raise ValueError('分页超出上限，保留旧版数据')

def tags(r):
    hay = (r['full_name']+' '+(r.get('description') or '')).lower()
    words = {'Skill':['skill'], 'MCP':['mcp'], 'macOS':['macos','mac app','macbook'],
             'Windows':['windows'], '自托管':['self-host','selfhost','自托管','私有化'],
             'Obsidian':['obsidian'], 'Cloudflare':['cloudflare'], '公众号':['wechat','微信','公众号'],
             '小红书':['xiaohongshu','小红书','xhs'], 'Codex':['codex'], 'Claude':['claude']}
    return [tag for tag,keys in words.items() if any(k in hay for k in keys)]

def normalize(raw, config):
    repos=[]; seen=set()
    for i,r in enumerate(raw):
        name=r['full_name']
        if name in seen: raise ValueError(f'分页中出现重复仓库 {name}，请重试')
        seen.add(name)
        entry=config['repositories'].get(name,{})
        cat=entry.get('category','待确认用途')
        if cat not in config['categories']: raise ValueError(f'{name} 的分类不在 categories 中')
        public_description=r.get('description') or ''
        description=public_description or entry.get('summary','')
        repos.append({'name':name,'url':r['html_url'],'description':description,
                      'description_source':'GitHub 简介' if public_description else 'README 摘要' if description else '未提供',
                      'category':cat, 'tags':tags(r), 'language':r.get('language'),
                      'stars':r.get('stargazers_count',0),'archived':r.get('archived',False),
                      'pushed_at':r.get('pushed_at'),'topics':r.get('topics',[]),'rank':i+1,
                      'needs_review':not description or not entry or cat=='待确认用途'})
    return repos

def md(data,history):
    counts=collections.Counter(r['category'] for r in data['repositories'])
    text=[f'# AC 的 GitHub Stars 项目库', '',f'- 账户：[{USER}](https://github.com/{USER}?tab=stars)',
          f'- 最后同步：{data["synced_at"]}（北京时间）',f'- 当前项目：{len(data["repositories"])} 个',
          '- 来源：GitHub 公开 Stars API；分类根据仓库名称和简介判断，并非项目质量评级。',
          '- 每个项目只设一个主分类；跨领域用途用标签补充。分类可在 classifications.json 中调整。',
          '- 列表按最近加星顺序排列；代码更新时间与加星时间不同。无公开简介的项目按 README 补充摘要，仍不明确则标注待核实。',
          '- 每月 1 日 09:00（Asia/Shanghai）由 Codex 更新；实际运行取决于 Codex 调度与网络可用性。', '', '## 分类索引','', '| 分类 | 数量 |', '| --- | ---: |']
    text += [f'| {c} | {counts[c]} |' for c in data['categories'] if counts[c]]
    for c in data['categories']:
        entries=[r for r in data['repositories'] if r['category']==c]
        if not entries: continue
        text+=['',f'## {c}（{len(entries)}）','']
        for r in entries:
            desc=' '.join(r['description'].split()) or '仓库未提供简介；用途待核实。'
            detail=' · '.join(([r['language']] if r['language'] else [])+r['tags']+(['已归档'] if r['archived'] else []))
            text += [f'### [{r["name"]}]({r["url"]})','',desc,'',f'- Stars：{r["stars"]:,}'+(f' · {detail}' if detail else '')+(' · README 摘要' if r['description_source']=='README 摘要' else '')]
            if r['needs_review'] and r['description']: text+=['- 分类待进一步确认。']
    text+=['','## 同步记录','']
    for item in history[-12:][::-1]:
        text += [f'### {item["at"]}','', f'共 {item["total"]} 项；新增 {len(item["added"])} 项，移出当前列表 {len(item["removed"])} 项。']
        if item.get('initial'): text+=['首次建立快照；不把全部项目计为本周新增。']
        for label,key in [('新增','added'),('移出','removed')]:
            if item[key]: text += [f'- {label}：'+', '.join(f'[{n}](https://github.com/{n})' for n in item[key])]
    return '\n'.join(text)+'\n'

def html(data,history):
    template=(ROOT/'page-template.html').read_text()
    payload=dump({'data':data,'history':history}).replace('<','\\u003c').replace('&','\\u0026')
    return template.replace('__STARS_PAYLOAD__',payload)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,help='使用已下载的 GitHub 仓库列表 JSON（离线生成）')
    args=parser.parse_args()
    config=read(ROOT/'classifications.json',{'categories':['待确认用途'],'repositories':{}})
    # 全部分页成功后才写文件；网络失败不会清空上次的项目库。
    raw=json.loads(args.input.read_text()) if args.input else fetch()
    repos=normalize(raw,config)
    previous=read(ROOT/'stars.json',None)
    if previous and previous['repositories'] and not repos:
        raise ValueError('GitHub 返回空列表，拒绝覆盖非空快照；请核实账户状态')
    now=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).strftime('%Y-%m-%d %H:%M')
    oldnames={r['name'] for r in previous['repositories']} if previous else set()
    names={r['name'] for r in repos}
    added=sorted(names-oldnames) if previous else []
    removed=sorted(oldnames-names)
    history=read(ROOT/'updates.json',[])
    if not previous or added or removed:
        history.append({'at':now,'total':len(repos),'added':added,'removed':removed,'initial':previous is None})
    data={'account':USER,'source':f'https://api.github.com/users/{USER}/starred',
          'synced_at':now,'categories':config['categories'],'repositories':repos}
    # 先完成两个视图的生成，避免模板故障写入一半。
    markdown=md(data,history); page=html(data,history)
    for filename,content in [('stars.json',dump(data)),('updates.json',dump(history)),('stars.md',markdown),('index.html',page)]:
        atomic(ROOT/filename,content)
    print(dump({'total':len(repos),'added':added,'removed':removed,'initial':previous is None,
                'needs_review':[r['name'] for r in repos if r['needs_review']]}))

if __name__=='__main__':
    try: main()
    except Exception as e:
        print(f'同步失败：{e}。已有快照保留。',file=sys.stderr); sys.exit(1)
