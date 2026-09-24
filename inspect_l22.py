import json,re
from pathlib import Path
p=Path('sources_extracted')
book='\n'.join(json.loads((p/'book_L22.json').read_text(encoding='utf-8')))
book=re.sub(r'^iPAS.*$', '',book,flags=re.M)
book=re.sub(r'^\s*\d+\s*$', '',book,flags=re.M)
chapters=re.split(r'第\s+(\d+)章\s*\n',book)
out=Path('content');out.mkdir(exist_ok=True)
for i in range(1,len(chapters),2):
 n=int(chapters[i]);s=chapters[i+1]
 if n>13:continue
 (out/f'L22_original_{n}.txt').write_text(s,encoding='utf-8')
 m=re.search(rf'{n}\\.1\\s+核心',s);core=s[m.start():] if m else s
 core=re.sub(rf'{n}\.\d+\s*正式公告試題索引.*?(?={n}\.\d+\s*自編模擬題)', '',core,flags=re.S)
 core=re.sub(rf'{n}\.\d+\s*自編模擬題.*?(?={n}\.\d+\s*章末複習)', '',core,flags=re.S)
 core=core.split('來源與稽核紀錄')[0]
 core='\n'.join(l.strip() for l in core.splitlines() if l.strip())
 (out/f'L22_core_{n}.txt').write_text(core,encoding='utf-8')
 sims=[]
 for m in re.finditer(r'模擬題\s+SIM-([^\n]+)\n(.*?)(?=\n\s*模擬題\s+SIM-|\n\s*'+str(n)+r'\.\d+\s*章末複習|\Z)',s,re.S):
  sims.append({'heading':m[1].strip(),'text':m[2].strip()})
 (out/f'L22_sims_{n}.json').write_text(json.dumps(sims,ensure_ascii=False,indent=2),encoding='utf-8')
guide=json.loads((p/'guide_L22.json').read_text(encoding='utf-8'))
compact=[]
for i,s in enumerate(guide):
 lines=[re.sub(r' {2,}',' ',l.strip()) for l in s.splitlines() if l.strip()]
 compact.append(f'PDF {i+1}\n'+'\n'.join(lines))
(out/'L22_guide_compact.txt').write_text('\n\n'.join(compact),encoding='utf-8')
print('Chapters and guide prepared')

