import {api} from '/base.js';
import {related,selectField} from '/patrol.js';
import {taskCard} from './tallies.js';

export async function comparisonPanel(role){
  const [{tasks,posts,threshold},patrols]=await Promise.all([api('/api/agreement'),api('/api/patrols')]);
  const candidates=Object.fromEntries(patrols.filter(row=>row.completed_route && ['returned','valid'].includes(row.status)
    && !tasks.some(task=>task.source_walk===row.id)).map(row=>[row.id,related(row)]));
  return `<div class="agreement-grid"><section class="field-panel"><h2>双人复点记录</h2>
    ${tasks.map(task=>taskCard(task,posts.filter(post=>post.comparison_id===task.id),role)).join('') || '<p>尚未启动双人复点。</p>'}</section>
    <aside class="field-panel"><h2>独立观察配对</h2>
    ${role==='reviewer' && Object.keys(candidates).length ? `<form data-station-path="/api/agreement/{source}/create">
      ${selectField('source','原巡护班',candidates)}
      <label>观察者甲代号<input name="observer_one" pattern="[A-Z0-9]{2,10}" required></label>
      <label>观察者乙代号<input name="observer_two" pattern="[A-Z0-9]{2,10}" required></label>
      <button>启动配对</button></form>` : ''}
    <p class="field-note">两份报数在得出结论前分开保存。按各鸟种最小计数和除以最大计数和，低于 ${threshold*100}% 时可安排同样线补走。</p>
    </aside></div>`;
}
