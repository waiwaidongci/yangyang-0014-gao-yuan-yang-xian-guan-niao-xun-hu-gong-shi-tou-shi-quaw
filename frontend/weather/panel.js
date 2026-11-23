import {api,h} from '/base.js';
import {statusMark} from '/patrol.js';
import {conditionsRow} from './checkpoints.js';

export async function weatherPanel(role,selected){
  if(!selected)return '<p>先在样线册建立巡护班。</p>';
  const {walk,conditions,assessment}=await api('/api/patrols/'+selected+'/weather');
  const rows=Object.fromEntries(conditions.map(row=>[row.checkpoint,row]));
  return `<div class="condition-layout"><section class="field-panel">
    <div class="log-title"><h2>${h(walk.crew)} · ${h(walk.walked_on)}</h2>${statusMark(walk.status)}</div>
    <div class="weather-columns">${['outbound','return'].map(point=>conditionsRow(point,walk,rows[point],role,assessment)).join('')}</div>
    </section><aside class="field-panel"><h2>可比性核签</h2>
      ${assessment ? `<p class="condition-result" data-usable="${assessment.usable}">
       ${assessment.usable?'符合本线条件':'需剔除'} · ${h(assessment.reason)}<br>${h(assessment.verified_by)}</p>` :
       '<p>登记起点与终点后，可由值班员核签。</p>'}
      ${role==='reviewer' && walk.status==='returned' && !assessment ?
        `<form data-station-path="/api/patrols/${walk.id}/weather/sign"><button>签天气条件</button></form>` : ''}
      <p class="field-note">任一端能见度低于 100 m、风力达到 6 级或强降水，均按不可比处理。</p>
      <a class="field-link" href="#review">回到巡护复核</a></aside></div>`;
}
