import {api,h} from '/base.js';

export const Cover = {grassland:'草甸',wetland:'湿地',shrub:'灌丛'};
export const Taxon = {lark:'百灵',wagtail:'鹡鸰',crane:'鹤类',duck:'鸭类',other:'其他'};
export const Axis = {route:'样线',cover:'地表',week:'ISO 周'};
export const Status = {booked:'待出发',walking:'巡护中',returned:'待复核',valid:'计入工时',excluded:'已剔除'};
export const ref = id => `P-${String(id).padStart(3,'0')}`;
export const patio = (id, action = '') => `/api/patrols/${id}${action ? '/' + action : ''}`;
export const localClock = value => value ? new Date(value).toLocaleString('zh-CN', {
  timeZone:'Asia/Shanghai', hour12:false, month:'2-digit', day:'2-digit', hour:'2-digit', minute:'2-digit',
}) : '待登记';

export const recordDesk = {
  patrolId:null,
  snapshotId:null,
  async fetch(page) {
    if (page === 'pivot') {
      const snapshots = await api('/api/effort');
      const selected = snapshots.find(item => item.id === this.snapshotId) ?? snapshots[0];
      const snapshot = selected ? await api(`/api/effort/${selected.id}`) : null;
      return {snapshots,snapshot};
    }
    const [routes,patrols] = await Promise.all([api('/api/transects'),api('/api/patrols')]);
    const active = patrols.find(item => item.id === this.patrolId) ??
      patrols.find(item => item.status === (page === 'review' ? 'returned' : 'booked')) ?? patrols[0];
    const birds = active && page !== 'routes' ? (await api(patio(active.id))).birds : [];
    return {routes,patrols,active,birds};
  },
};

export function selectField(name,label,options,value) {
  return `<label>${h(label)}<select name="${h(name)}">${Object.entries(options).map(([key,title]) =>
    `<option value="${h(key)}" ${key === String(value) ? 'selected' : ''}>${h(title)}</option>`).join('')}</select></label>`;
}
export const statusMark = value => `<span class="walk-status" data-status="${h(value)}">${Status[value]}</span>`;
export const related = row => `${ref(row.id)} · ${row.route_label} · ${row.crew}`;
export const timeField = (name,title,defaultValue) =>
  `<label>${h(title)}（北京时间）<input type="datetime-local" name="${h(name)}" value="${h(defaultValue)}" required></label>`;
export function pivotCell(cell) {
  if (!cell.effort_seconds) return '<span class="no-effort" aria-label="无有效巡护">—</span>';
  return `<div class="effort-cell ${cell.count > 0 ? '' : 'rate-zero'}">
    <strong>${cell.observations_per_hour.toFixed(2)}</strong><span>${cell.count} 只 / ${(cell.effort_seconds/3600).toFixed(2)} 小时</span>
    ${cell.zero_walks ? `<span>含 ${cell.zero_walks} 次有效零</span>` : ''}</div>`;
}
