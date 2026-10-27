"""One canonical 27-section article; 37 deterministic output combinations."""
from pathlib import Path
from io import BytesIO
from zipfile import ZipFile,ZIP_DEFLATED
from dataclasses import dataclass
import json,re,hashlib
import fitz
from PIL import Image,ImageDraw
import render_support as support
text=support.text
ROOT=Path(__file__).resolve().parent
ASSET=ROOT/'asset'
NAMES=json.loads((ASSET/'names.json').read_text(encoding='utf-8'))
PAGE=fitz.Rect(0,0,612,792)
CONTENT=fitz.Rect(72,72,540,690)
DEFAULT_LINKS=support.DEFAULT_LINKS.copy()
ALIASES={ '\u0bae\u0bbf\u0bb0\u0bc1\u0b95\u0b9a\u0bc0\u0bb0\u0bbf\u0bb7\u0bae\u0bcd':4,'\u0bb9\u0bb8\u0bcd\u0ba4\u0bae\u0bcd':12,'\u0b85\u0b9a\u0bc1\u0bb5\u0bbf\u0ba9\u0bbf':0 }

def star_index(value):
 value=text.normalize_article_text(value).strip()
 value=re.sub(r'^\s*(?:\d+[.)]\s*|#{1,6}\s*)','',value).strip('* _:\u200b')
 return NAMES.index(value) if value in NAMES else ALIASES.get(value)

def parse_plain(value):
 value=__import__('html').unescape(value)
 result=[]
 for line in value.splitlines():
  line=line.strip()
  if not line:continue
  line=re.sub(r'^#{1,6}\s*','',line)
  runs=[]
  for i,part in enumerate(re.split(r'\*\*(.*?)\*\*',line)):
   if part:runs.append({'text':part,'bold':i%2==1})
  plain=''.join(r['text']for r in runs)
  kind='heading' if star_index(plain) is not None else 'subheading' if plain.endswith(':')and len(plain)<100 else 'body'
  result.append({'type':kind,'runs':runs,'text':plain,'align':'justify'})
 return result

def sections(raw):
 blocks=text.clean_blocks(raw) if raw else []
 found={};current=None;prefix=[]
 for block in blocks:
  index=star_index(block['text'])
  if index is not None:
   if index in found:raise ValueError('Duplicate nakshatra heading: '+NAMES[index])
   current=index;found[index]=[dict(block,text=NAMES[index],runs=[{'text':NAMES[index],'bold':False}])]
  elif current is None:prefix.append(block)
  else:found[current].append(block)
 return found,prefix

@dataclass(frozen=True)
class Output:
 key:str
 label:str
 indices:tuple
 limit:int
 @property
 def filename(self):return self.key+'_'+('_'.join(NAMES[i]for i in self.indices) if len(self.indices)<4 else 'all_27')+'.pdf'
OUTPUTS=[Output(f'single_{i+1:02}',f'{i+1:02}. {name}',(i,),200_000)for i,name in enumerate(NAMES)]
OUTPUTS += [Output(f'group_{i//3+1:02}',f'Group {i//3+1}: '+', '.join(NAMES[i:i+3]),tuple(range(i,i+3)),400_000)for i in range(0,27,3)]
OUTPUTS += [Output('all_27','All 27 nakshatras',tuple(range(27)),1_500_000)]
BY_KEY={o.key:o for o in OUTPUTS}

@dataclass
class Result:
 data:bytes
 placements:list
 labels:list
 @property
 def page_count(self):return len(self.labels)

def frame(doc,labels,label):
 page=doc.new_page(width=612,height=792);labels.append(label)
 for inset,width in ((24,1.2),(27,.5),(30,1.2)):page.draw_rect(fitz.Rect(inset,inset,612-inset,792-inset),color=(.22,.22,.22),width=width)
 return page

def picture(page,path,rect,quality=78):
 with Image.open(path)as im:
  rgba=im.convert('RGBA');im=Image.new('RGB',rgba.size,'white');mask=rgba.getchannel('A');
  if Path(path).parent.name=='lords':
   mask=Image.new('L',rgba.size);ImageDraw.Draw(mask).ellipse((0,0,rgba.width-1,rgba.height-1),fill=255)
  im.paste(rgba,mask=mask);im.thumbnail((900,1100));out=BytesIO();im.save(out,format='JPEG',quality=quality,optimize=True)
 page.insert_image(rect,stream=out.getvalue(),keep_proportion=True)

def uri(page,rect,key,options):support.link(page,fitz.Rect(rect),options.get('links',DEFAULT_LINKS).get(key,''),options)

def compact(doc,limit):
 support.repair_unicode_maps(doc);doc.subset_fonts()
 original=doc.tobytes(garbage=4,deflate=True,use_objstms=1)
 if len(original)<=limit:return original
 for side,quality in [(850,74),(700,62),(580,50),(460,38),(360,25)]:
  with fitz.open(stream=original,filetype='pdf')as candidate:
   protected={im['xref'] for page in candidate for im in page.get_image_info(xrefs=True) if abs(im['bbox'][1]-640)<2 and abs(im['bbox'][3]-745)<8}
   for xref in {im[0]for page in candidate for im in page.get_images()}-protected:
    data=candidate.extract_image(xref)
    with Image.open(BytesIO(data['image']))as image:
     image=image.convert('RGB');image.thumbnail((side,side));out=BytesIO();image.save(out,format='JPEG',quality=quality,optimize=True)
    candidate[0].replace_image(xref,stream=out.getvalue())
   data=candidate.tobytes(garbage=4,deflate=True,use_objstms=1)
   if len(data)<=limit:return data
 raise ValueError(f'PDF exceeds its {limit//1000} KB limit. Reduce photo detail or article length.')

def generate(raw,key='all_27',options=None,cover_photo=None):
 options=options or {};output=BY_KEY[key];found,prefix=sections(raw)
 missing=[NAMES[i]for i in output.indices if i not in found or len(found[i])<2]
 if missing:raise ValueError('Missing heading or article: '+', '.join(missing))
 for value in options.get('links',DEFAULT_LINKS).values():support.valid_link(value)
 text.ensure_bold_font(support.BODY)
 placements=[];labels=[]
 with fitz.open()as doc:
  page=frame(doc,labels,'Front cover')
  if cover_photo:
   crop=options.get('cover_crop',{})
   page.insert_image(fitz.Rect(31,31,581,761),stream=support.prepare(cover_photo,550,730,crop.get('zoom',1),crop.get('pan_x',0),crop.get('pan_y',0),fit='cover'))
  else:picture(page,ASSET/'cover.jpg',fitz.Rect(31,31,581,761))
  uri(page,(31,31,581,761),'banner',options)
  for star in output.indices:
   page=frame(doc,labels,NAMES[star]);y=72
   picture(page,ASSET/'lords'/f'{star+1:02}.png',fitz.Rect(234,y,378,y+143));y+=155
   for j,block in enumerate(found[star]):
    block=dict(block)
    if j==0:role='subtitle';block['align']='center'
    else:role='subheading'if block['type']in('heading','subheading')or(block['text'].endswith(':')and len(block['text'])<100)else 'body'
    if j>0 and not block.get('align_explicit'):block['align']=options.get('default_align','justify')
    if j>0:block['font_size']=block.get('font_size')or options.get('font_size',20)
    story,size,leading,align,color=support.story_for(block,options,role)
    _,bounds=story.place(fitz.Rect(72,0,540,100000));height=bounds[3];story.reset()
    if role=='subheading'and y+height+leading>690:page=frame(doc,labels,NAMES[star]+' continued');y=72
    while True:
     more,filled=story.place(fitz.Rect(72,y,540,690))
     if filled[3]<=y+.01:
      if y<=72.01:raise ValueError('Text cannot fit; reduce size or split a long word.')
      page=frame(doc,labels,NAMES[star]+' continued');y=72;continue
     support.draw_block(page,story,options)
     placements.append({'page':len(doc)-1,'source_index':block['source_index'],'type':block['type'],'rect':[72,y,540,min(filled[3],690)],'font_size':size,'line_height':leading,'align':align,'color':color})
     y=filled[3]
     if not more:break
     page=frame(doc,labels,NAMES[star]+' continued');y=72
    y+=10
  # The contact banner is always the final content element before the back.
  if y>625:page=frame(doc,labels,'Contact');y=72
  phone_rect=fitz.Rect(45,640,570,745)
  picture(page,ASSET/'phone.jpg',phone_rect);uri(page,phone_rect,'contact',options)
  page=frame(doc,labels,'Back cover');picture(page,ASSET/'back.jpg',fitz.Rect(30,31,582,765))
  for rect,keyname in [((126,643,277,736),'app'),((420,636,579,695),'contact'),((423,698,579,734),'mail')]:uri(page,rect,keyname,options)
  doc.set_metadata({'title':output.label,'creator':'Nakshatra PDF Generator'})
  return Result(compact(doc,output.limit),placements,labels)

def preview(result,scale=1):
 with fitz.open(stream=result.data,filetype='pdf')as doc:
  return [{'image':__import__('base64').b64encode(p.get_pixmap(matrix=fitz.Matrix(scale,scale)).tobytes('png')).decode(),'label':result.labels[i],'placements':[m for m in result.placements if m['page']==i]}for i,p in enumerate(doc)]

def bundle(results):
 out=BytesIO()
 with ZipFile(out,'w',ZIP_DEFLATED)as archive:
  for key,result in results.items():archive.writestr(BY_KEY[key].filename,result.data)
 return out.getvalue()
