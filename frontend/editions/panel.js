import {api,h} from '/base.js';
import {selectField} from '/patrol.js';
import {editionBox,readers} from './archive.js';

export async function editionPanel(role){
  const [{editions,inbox},snapshots]=await Promise.all([api('/api/editions'),api('/api/effort')]);
  const saved=Object.fromEntries(snapshots.filter(row=>row.status==='frozen').map(row=>[row.id,row.label]));
  const previous={0:'首次发布',...Object.fromEntries(editions.map(row=>[row.id,row.series+' V'+row.volume]))};
  return `<div class="edition-grid"><section class="field-panel"><h2>巡护汇总发布簿</h2>
    ${editions.map(row=>editionBox(row,inbox.filter(mail=>mail.edition_id===row.id),role)).join('') || '<p>暂无签发版。</p>'}
    </section><aside class="field-panel"><h2>签发一期</h2>
    ${role==='reviewer' && Object.keys(saved).length ? `<form data-station-path="/api/editions" data-number="snapshot_id supersedes" data-audiences>
      <label>站内系列号<input name="series" pattern="[a-z][a-z0-9-]{1,39}" placeholder="例如 birds-weekly" required></label>
      ${selectField('snapshot_id','冻结透视',saved)}${selectField('supersedes','更正来源',previous,0)}
      <label>更正依据<input name="reason" maxlength="300"></label>
      <fieldset><legend>站内收件岗位</legend>${Object.entries(readers).map(([code,label])=>`<label class="check-row">
        <input type="checkbox" name="audiences" value="${code}" ${code==='station'?'checked':''}>${h(label)}</label>`).join('')}</fieldset>
      <button>签发统计版</button></form>` : ''}
    <p class="field-note">只签发范围内所有班次已处理的快照。更正版保留原统计口径及原收件范围。</p>
    </aside></div>`;
}
