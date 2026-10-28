"""Run: python -m streamlit run app.py"""
from pathlib import Path
from uuid import uuid4
from io import BytesIO
import base64,hashlib,json
import streamlit as st
import streamlit.components.v1 as components
import engine
ROOT=Path(__file__).resolve().parent

def main():
 st.set_page_config(page_title='Nakshatra PDF Generator',page_icon='*',layout='wide')
 st.title('Nakshatra PDF Generator')
 st.caption('Edit 27 articles once. Preview 37 combinations. Download one PDF or a selected ZIP.')
 ss=st.session_state
 ss.setdefault('article',[]);ss.setdefault('revision','initial');ss.setdefault('source_token',str(uuid4()))
 ss.setdefault('selected_outputs',[o.key for o in engine.OUTPUTS]);ss.setdefault('results',{})
 auto=st.toggle('Auto preview refresh',value=False,key='auto_preview')
 with st.expander('Load master article'):
  upload=st.file_uploader('Master article (.docx or .txt)',type=['docx','txt'])
  def load(value):
   ss['article']=engine.parse_plain(value);ss['revision']=str(uuid4());ss['source_token']=str(uuid4());ss['force_refresh']=True
  a,b=st.columns(2)
  if a.button('Load uploaded article',disabled=upload is None):
   try:load(engine.support.docx_text(upload.getvalue())if upload.name.endswith('.docx')else upload.getvalue().decode('utf-8-sig'));st.rerun()
   except Exception as error:st.error(str(error))
  if b.button('Load supplied raw.docx',disabled=not(ROOT/'raw.docx').exists()):load(engine.support.docx_text((ROOT/'raw.docx').read_bytes()));st.rerun()
 cover=st.file_uploader('Front cover photo (optional)',type=['png','jpg','jpeg','webp'],help='Replaces the large cover picture. All other artwork remains fixed.')
 cover_data=cover.getvalue()if cover else None
 with st.sidebar:
  st.header('Preview and downloads')
  buttons=st.columns(2)
  if buttons[0].button('Select all'):ss['selected_outputs']=[o.key for o in engine.OUTPUTS]
  if buttons[1].button('Clear all'):ss['selected_outputs']=[]
  buttons=st.columns(3)
  for col,label,keys in [(buttons[0],'Singles',[o.key for o in engine.OUTPUTS[:27]]),(buttons[1],'Groups',[o.key for o in engine.OUTPUTS[27:36]]),(buttons[2],'Full',['all_27'])]:
   if col.button(label):ss['selected_outputs']=keys
  def tick_changed(key):
   current=set(ss['selected_outputs'])
   if ss['tick_'+key]:current.add(key)
   else:current.discard(key)
   ss['selected_outputs']=[o.key for o in engine.OUTPUTS if o.key in current]
  selected=st.multiselect('Tick outputs to download',[o.key for o in engine.OUTPUTS],format_func=lambda k:engine.BY_KEY[k].label,key='selected_outputs')
  with st.expander('Individual output tick boxes'):
   for label,outputs in [('27 single PDFs',engine.OUTPUTS[:27]),('9 grouped PDFs',engine.OUTPUTS[27:36]),('Complete collection',engine.OUTPUTS[36:])]:
    st.caption(label)
    for output in outputs:
     ss['tick_'+output.key]=output.key in selected
     st.checkbox(output.label,key='tick_'+output.key,on_change=tick_changed,args=(output.key,))
  st.caption(f'{len(selected)} / 37 selected. One selection downloads a PDF; multiple selections download a ZIP.')
  preview_key=st.selectbox('Preview output',[o.key for o in engine.OUTPUTS],index=36,format_func=lambda k:engine.BY_KEY[k].label,key='preview_output')
  st.caption(f'Preview limit: {engine.BY_KEY[preview_key].limit//1000} KB')
  font_size=st.number_input('Default text size (pt)',8.,60.,20.,.5)
  watermark=st.checkbox('Add watermark (groups and full only)',value=False,help='Adds the reference-style diagonal watermark to grouped and complete PDFs. Single-nakshatra PDFs stay unwatermarked.')
  default_align='justify'
  line_height=st.slider('Line spacing',1.05,1.8,1.25,.05)
  with st.expander('Front cover movement'):
   crop={'zoom':st.slider('Cover zoom',1.,3.,1.,.05),'pan_x':st.slider('Cover horizontal',-1.,1.,0.,.05),'pan_y':st.slider('Cover vertical',-1.,1.,0.,.05)}
  with st.expander('Clickable links'):
   enabled=st.checkbox('Enable PDF links',value=True)
   links={key:st.text_input(label,value=value,key='link_'+key)for key,label,value in [('banner','Banner link',engine.DEFAULT_LINKS['banner']),('app','Android app',engine.DEFAULT_LINKS['app']),('contact','Phone banner / contact',engine.DEFAULT_LINKS['contact']),('mail','Email',engine.DEFAULT_LINKS['mail'])]}
  st.caption('Lord images, phone banner and back cover are fixed. No replacement uploads are shown for them.')
 options={'default_align':default_align,'font_size':font_size,'line_height':line_height,'watermark':watermark,'cover_crop':crop,'links':links,'links_enabled':enabled}
 article=ss['article'];revision=ss['revision']
 try:
  found,_=engine.sections(article);missing=[engine.NAMES[i]for i in range(27)if i not in found or len(found[i])<2]
  st.caption(f'Master article: {27-len(missing)} / 27 sections ready')
  if missing:
   with st.expander('Missing sections / required heading order'):st.write(', '.join(missing));st.code('\n'.join(engine.NAMES))
 except Exception as error:st.error(str(error));missing=engine.NAMES
 artwork_version=tuple((p.name,p.stat().st_mtime_ns,p.stat().st_size)for p in sorted(list((engine.ASSET/'lords').glob('*.png'))+list(engine.ASSET.glob('*.jpg'))))
 signature=hashlib.sha256(repr((artwork_version,article,options,hashlib.sha256(cover_data).hexdigest()if cover_data else '')).encode()).hexdigest()
 if signature!=ss.get('master_signature'):
  ss['results']={};ss.pop('download_data',None);ss['master_signature']=signature
 force=ss.pop('force_refresh',False)
 fingerprint=signature+preview_key
 if (auto or force)and fingerprint!=ss.get('preview_fingerprint'):
  try:
   result=ss['results'].get(preview_key)
   if result is None:result=engine.generate(article,preview_key,options,cover_data);ss['results'][preview_key]=result
   ss['pages']=engine.preview(result);ss['error']=''
  except Exception as error:ss['pages']=[];ss['error']=str(error)
  ss['preview_fingerprint']=fingerprint
 fresh=ss.get('preview_fingerprint')==fingerprint
 if fresh:ss['preview_revision']=revision
 # Switching output refreshes only that preview, never every output.
 if ss.get('last_output')!=preview_key:
  ss['last_output']=preview_key;ss['force_refresh']=True
  if article:st.rerun()
 component=components.declare_component('nakshatra_editor',path=str(ROOT/'editor'))
 value=component(default_align=default_align,font=base64.b64encode(engine.support.BODY.read_bytes()).decode(),initial=article,initial_revision=revision,initial_token=ss['source_token'],preview=ss.get('pages',[]),preview_revision=ss.get('preview_revision','initial'),preview_error=ss.get('error',''),context=fingerprint,auto_preview=auto,preview_stale=not fresh,key='master_editor',default=None)
 if value and value.get('initial_token')==ss['source_token']:
  if repr(value.get('blocks',[]))!=repr(article)or value.get('revision',revision)!=revision:
   ss['article']=value.get('blocks',[]);ss['revision']=value.get('revision',revision);st.rerun()
  refresh=value.get('refresh_request')
  if refresh and refresh!=ss.get('handled_refresh'):ss['handled_refresh']=refresh;ss['force_refresh']=True;st.rerun()
  request=value.get('request')
  if request and request!=ss.get('handled_generate'):ss['handled_generate']=request;ss['prepare_download']=True
 generate=st.button('Prepare selected downloads',type='primary',disabled=not selected)
 if generate or ss.pop('prepare_download',False):
  try:
   if not selected:raise ValueError('Select at least one output in the sidebar.')
   found,_=engine.sections(article)
   required=sorted({i for key in selected for i in engine.BY_KEY[key].indices})
   missing_selected=[engine.NAMES[i]for i in required if i not in found or len(found[i])<2]
   if missing_selected:raise ValueError('Missing selected sections: '+', '.join(missing_selected))
   progress=st.progress(0,text='Preparing PDFs...');results={}
   for number,key in enumerate(selected):
    result=ss['results'].get(key)
    if result is None:result=engine.generate(article,key,options,cover_data);ss['results'][key]=result
    results[key]=result;progress.progress((number+1)/len(selected),text=f'{number+1}/{len(selected)}: {engine.BY_KEY[key].label}')
   ss['download_data']=next(iter(results.values())).data if len(results)==1 else engine.bundle(results)
   ss['download_name']=engine.BY_KEY[selected[0]].filename if len(results)==1 else 'nakshatra_selected.zip'
   ss['download_keys']=tuple(selected)
   ss['report']=[{'Output':engine.BY_KEY[k].label,'Pages':r.page_count,'KB':round(len(r.data)/1000,1),'Limit KB':engine.BY_KEY[k].limit//1000}for k,r in results.items()]
  except Exception as error:st.error(str(error))
 if ss.get('download_data') and ss.get('download_keys')==tuple(selected):
  payload=base64.b64encode(ss['download_data']).decode('ascii')
  filename=json.dumps(ss['download_name'])
  mime='application/pdf'if len(selected)==1 else 'application/zip'
  # A browser-owned Blob avoids a temporary Streamlit media URL being removed
  # during reruns or a large multi-file ZIP download.
  components.html(f'''<button id="download" style="padding:12px 20px;border:0;border-radius:7px;background:#d93243;color:white;cursor:pointer">DOWNLOAD SELECTED</button>
<script>
const encoded={json.dumps(payload)},bytes=Uint8Array.from(atob(encoded),c=>c.charCodeAt(0));
const url=URL.createObjectURL(new Blob([bytes],{{type:{json.dumps(mime)}}}));
document.getElementById('download').onclick=()=>{{const a=document.createElement('a');a.href=url;a.download={filename};document.body.appendChild(a);a.click();a.remove();}};
</script>''',height=60)
  st.dataframe(ss['report'],hide_index=True,use_container_width=True)
if __name__=='__main__':main()
