import re,json
from pathlib import Path
r=Path('sources_extracted')
s='\n'.join(json.loads((r/'book_L23.json').read_text(encoding='utf-8')))
s=re.sub(r'^iPAS.*$', '',s,flags=re.M)
s=re.sub(r'^\s*\d+\s*$', '',s,flags=re.M)
pat=re.compile(r'模擬題\s+SIM-(L\d{5})-(\d{3})[^\n]*\n')
ms=list(pat.finditer(s)); sims=[]
for i,m in enumerate(ms):
 e=ms[i+1].start() if i+1<len(ms) else s.find('12.6章末',m.end())
 chunk=s[m.end():e]
 chunk=re.split(r'\n\s*\d+\.\d+\s*章末複習',chunk)[0]
 sims.append({'id':f'SIM-{m[1]}-{m[2]}','text':chunk.strip()})
Path('content').mkdir(exist_ok=True)
Path('content/L23_original_sims.json').write_text(json.dumps(sims,ensure_ascii=False,indent=2),encoding='utf-8')
print('simulations',len(sims))
for ex in ['114_2','115_1']:
 t='\n'.join(json.loads((r/f'exam_{ex}_L23.json').read_text(encoding='utf-8')))
 q=list(re.finditer(r'^\s*([ABCDＡＢＣＤ])\s+(\d{1,2})\.\s*',t,re.M))
 rows=[]
 for j,m in enumerate(q):
  piece=t[m.end():q[j+1].start() if j+1<len(q) else len(t)]
  rows.append({'question':int(m[2]),'answer':m[1].translate(str.maketrans('ＡＢＣＤ','ABCD')),'text':piece})
 Path(f'content/L23_exam_{ex}_raw.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
 print(ex,len(rows))
 print('\n'.join(f'{v["question"]:02d} {v["answer"]}: '+re.sub(r'\s+',' ',v['text'])[:200] for v in rows))
