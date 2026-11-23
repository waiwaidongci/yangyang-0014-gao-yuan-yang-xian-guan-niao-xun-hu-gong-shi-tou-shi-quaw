import {api,h} from '/base.js';
import {recordDesk,related,selectField} from '/patrol.js';
import {weatherPanel} from '/weather/panel.js';
import {comparisonPanel} from '/agreement/panel.js';
import {editionPanel} from '/editions/panel.js';

const maps={
  weather:['天气条件','核签起点和终点的能见度、风力与降水。',weatherPanel],
  agreement:['双人复点','记录独立观察的一致率，有偏差时补走原路线。',comparisonPanel],
  editions:['统计发布','从冻结透视签发站内统计，登记回执和更正。',editionPanel],
};
export const extraFieldPages=Object.fromEntries(Object.entries(maps).map(([key,[label]])=>[key,label]));

export async function renderField(page,outlet,user,flash=''){
  const [name,copy,load]=maps[page];
  const visits=page==='weather'?await api('/api/patrols'):[];
  const selected=visits.find(row=>row.id===recordDesk.patrolId)??visits[0];
  const panel=await load(user.role,selected?.id);
  if(!outlet.isConnected)return;
  outlet.innerHTML=`<div class="fieldbook"><header class="field-head"><div><h1>${name}</h1><p>${copy}</p></div>
  ${selected?selectField('pick_walk','巡护班',Object.fromEntries(visits.map(row=>[row.id,related(row)])),selected.id):''}</header>
  <p class="field-message" role="status">${h(flash)}</p>${panel}</div>`;
  const banner=outlet.querySelector('.field-message');
  const fail=error=>{banner.textContent=error.message;banner.dataset.type='error';};
  outlet.querySelector('[name=pick_walk]')?.addEventListener('change',event=>{
    recordDesk.patrolId=Number(event.target.value);
    renderField(page,outlet,user).catch(fail);
  });
  for(const form of outlet.querySelectorAll('form[data-station-path]')) form.onsubmit=async event=>{
    event.preventDefault();
    const formValues=new FormData(form);
    const data=Object.fromEntries(formValues);
    const path=form.dataset.stationPath.replace(/\{(\w+)\}/g,(_,key)=>{
      const value=data[key];delete data[key];return encodeURIComponent(value);
    });
    for(const key of (form.dataset.number??'').split(' ').filter(Boolean))data[key]=Number(data[key]);
    if(form.dataset.local)data[form.dataset.local]+=':00+08:00';
    if(form.hasAttribute('data-audiences')){
      data.audiences=formValues.getAll('audiences');
      data.supersedes||=null;
      data.reason||=null;
    }
    const button=event.submitter;
    if(button)button.disabled=true;
    try{
      await api(path,form.dataset.stationMethod??'POST',data);
      if(outlet.contains(form))await renderField(page,outlet,user,'已更新业务记录');
    }catch(error){fail(error);}
    finally{if(button)button.disabled=false;}
  };
  for(const button of outlet.querySelectorAll('[data-csv]'))button.onclick=async()=>{
    try{
      const content=await api(button.dataset.csv);
      const url=URL.createObjectURL(new Blob(['\ufeff',content],{type:'text/csv'}));
      Object.assign(document.createElement('a'),{href:url,download:button.dataset.name}).click();
      setTimeout(()=>URL.revokeObjectURL(url),1000);
    }catch(error){fail(error);}
  };
}
