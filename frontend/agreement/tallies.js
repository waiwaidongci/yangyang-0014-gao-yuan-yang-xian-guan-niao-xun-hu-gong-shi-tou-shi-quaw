import {h} from '/base.js';
import {Taxon,ref,selectField} from '/patrol.js';

const stages={collecting:'盲报收集中',aligned:'双人一致',repeat_required:'须补走',repeat_booked:'补走已安排'};
export function taskCard(task,posts,role){
  const remaining=[task.observer_one,task.observer_two].filter(code=>!posts.some(row=>row.observer===code));
  const path='/api/agreement/'+task.id;
  return `<article class="agreement-ticket"><div class="log-title"><h2>原巡护 ${ref(task.source_walk)}</h2><strong>${stages[task.decision]}</strong></div>
    <div class="observer-sheet">${[task.observer_one,task.observer_two].map(code=>{
      const post=posts.find(row=>row.observer===code);
      return `<div><strong>${h(code)}</strong><p>${post?'已提交':'待独立提交'}</p>
      ${post?.tallies ? `<p>${Object.entries(Taxon).map(([key,label])=>label+' '+post.tallies[key]).join(' · ')}</p>` : ''}</div>`;
    }).join('')}</div>
    ${task.agreement !== null ? `<p class="agreement-score">一致率 <strong>${(task.agreement*100).toFixed(1)}%</strong></p>` : ''}
    ${task.repeat_walk ? `<p>补走班号 ${ref(task.repeat_walk)}。可在野外记录中选择该班开始巡护。</p>` : ''}
    ${role==='operator' && remaining.length && task.decision==='collecting' ? `<form data-station-path="${path}/observations/{observer}"
      data-number="${Object.keys(Taxon).join(' ')}">
      ${selectField('observer','提交人员',Object.fromEntries(remaining.map(code=>[code,code])))}
      <div class="bird-tally-fields">${Object.entries(Taxon).map(([key,label])=>`<label>${label}<input name="${key}" type="number" min="0" max="5000" value="0" required></label>`).join('')}</div>
      <button>保存独立计数</button></form>` : ''}
    ${role==='reviewer' && task.decision==='collecting' ? `<form data-station-path="${path}/assess">
      <button>计算一致率</button></form>` : ''}
    ${role==='reviewer' && task.decision==='repeat_required' ? `<form data-station-path="${path}/repeat">
      <label>补走日期<input name="walked_on" type="date" required></label><label>小组<input name="crew" minlength="2" maxlength="60" required></label>
      <button>安排原样线补走</button></form>` : ''}</article>`;
}
