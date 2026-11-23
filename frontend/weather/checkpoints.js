import {h} from '/base.js';
import {localClock,selectField,timeField} from '/patrol.js';

export const Rain = {none:'无降水',light:'轻微',heavy:'强降水'};
export const Checkpoint = {outbound:'起点',return:'终点'};
export function conditionsRow(point,walk,row,role,signed){
  const allowed = role==='operator' && ['walking','returned'].includes(walk.status) && !signed;
  return `<section class="condition-check"><h2>${Checkpoint[point]}条件</h2>
    ${row ? `<dl><dt>时刻</dt><dd>${h(localClock(row.measured_at))}</dd>
      <dt>能见度</dt><dd>${row.visibility_m} m</dd><dt>风力</dt><dd>${row.wind_rank} 级</dd>
      <dt>降水</dt><dd>${Rain[row.precipitation]}</dd></dl>` : '<p>暂无该点条件记录。</p>'}
    ${allowed ? `<form data-station-path="/api/patrols/${walk.id}/weather/${point}" data-station-method="PUT" data-number="visibility_m wind_rank" data-local="measured_at">
      ${timeField('measured_at','测量时刻',walk.walked_on+(point==='outbound'?'T08:00':'T09:00'))}
      <label>能见度 m<input name="visibility_m" type="number" min="1" max="20000" value="${row?.visibility_m ?? 500}" required></label>
      <label>风力等级<input name="wind_rank" type="number" min="0" max="12" value="${row?.wind_rank ?? 1}" required></label>
      ${selectField('precipitation','降水',Rain,row?.precipitation)}<button>保存${Checkpoint[point]}条件</button>
      </form>` : ''}</section>`;
}
