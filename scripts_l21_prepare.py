from pathlib import Path
import re,json
R=Path(__file__).parent
S=R/'sources_extracted'; O=R/'content'; O.mkdir(exist_ok=True)
p=json.loads((S/'book_L21.json').read_text(encoding='utf-8'))
lines=[]
for page in p:
 for l in page.splitlines():
  l=re.sub(r'\s+',' ',l).strip()
  if not l or re.fullmatch(r'[ivx]+|\d+',l) or l.startswith('iPAS AI應用規劃師'): continue
  lines.append(l)
t='\n'.join(lines)
sims=[]
for m in re.finditer(r'模擬題\s+(SIM-L\d+-\d+)\s*｜[^\n]*\n',t):
 end=re.search(r'\n(?:模擬題\s+SIM-|\d+\.\d+\s*章末複習)',t[m.end():])
 b=t[m.end():m.end()+end.start()] if end else t[m.end():]
 sims.append({'id':m.group(1),'body':b,'question':b.split('答案與逐項解析')[0].strip(),'answer':re.search(r'答案：([ABCD])',b).group(1)})
(O/'L21_original_sims.json').write_text(json.dumps(sims,ensure_ascii=False,indent=2),encoding='utf-8')
(O/'L21_original_questions.txt').write_text('\n\n'.join(x['id']+'\n'+x['question']+'\n答案:'+x['answer'] for x in sims),encoding='utf-8')
(O/'L21_book_clean.txt').write_text(t,encoding='utf-8')
guides=json.loads((S/'guide_L21.json').read_text(encoding='utf-8'))
g=[]
for i,page in enumerate(guides):
 ls=[re.sub(r'\s+',' ',s).strip() for s in page.splitlines() if s.strip()]
 g.append(f'=== PDF {i+1} ===\n'+'\n'.join(ls))
(O/'L21_guide_clean.txt').write_text('\n\n'.join(g),encoding='utf-8')
print('sims',len(sims),'book pages',len(p),'guide pages',len(guides),'guide chars',sum(map(len,g)))
