from pathlib import Path
import json, hashlib, csv, sys
sys.stdout.reconfigure(encoding='utf-8')
from pypdf import PdfReader

root=Path(__file__).parent
src=Path(r'C:\Users\liangtinglin\Downloads')
out=root/'sources_extracted'; out.mkdir(exist_ok=True)
mapping={}
for n in (1,2,3):
    roman=('I','II','III')[n-1]
    mapping[f'book_L2{n}']=next(src.glob(f'iPAS_中級教科書_第{roman}冊_L2{n}_v0.2.0.pdf'))
    mapping[f'guide_L2{n}']=next(src.glob(f'AI應用規劃師(中級)-學習指引-科目{n}*.pdf'))
    zh=('一','二','三')[n-1]
    mapping[f'exam_114_2_L2{n}']=next(src.glob(f'114年第二梯次中級AI應用規劃師第{zh}科*.pdf'))
    mapping[f'exam_115_1_L2{n}']=next(p for p in src.glob(f'115年第一次中級AI應用規劃師_第{zh}科*.pdf') if '(1)' not in p.name)
mapping['scope_11506']=next(src.glob('AI應用規劃師能力鑑定_評鑑內容範圍參考_11506*.pdf'))
mapping['errata_1150410']=next(src.glob('AI應用規劃師(中級)_學習指引勘誤表_1150410*.pdf'))
manifest=[]
for key,path in mapping.items():
    reader=PdfReader(path)
    cache=out/f'{key}.json'
    pages=json.loads(cache.read_text(encoding='utf-8')) if cache.exists() else [p.extract_text(extraction_mode='layout') if '/Contents' in p else '' for p in reader.pages]
    (out/f'{key}.json').write_text(json.dumps(pages,ensure_ascii=False,indent=2),encoding='utf-8')
    (out/f'{key}.txt').write_text('\n\n'.join(f'===== PDF PAGE {i+1} =====\n{t}' for i,t in enumerate(pages)),encoding='utf-8')
    entry={'id':key,'filename':path.name,'path':str(path),'pages':len(pages),'chars':sum(map(len,pages)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    manifest.append(entry); print(json.dumps(entry,ensure_ascii=False))
for name in ['考過但本冊未教.csv','學習指引涵蓋缺口清單.csv','書有指引無_待試題驗證.csv','待判定主題_試題判定.csv','學習指引頁碼對照.csv','iPAS_中級教科書_對話.txt','iPAS 中級考綱教科書 v0.3 修訂規格.md']:
    path=src/name
    content=path.read_text(encoding='utf-8-sig')
    (out/name).write_text(content,encoding='utf-8-sig' if name.endswith('.csv') else 'utf-8')
    entry={'id':name,'filename':name,'path':str(path),'chars':len(content),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    manifest.append(entry); print(json.dumps(entry,ensure_ascii=False))
(out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
