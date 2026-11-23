import {api,h,mount,waitJob} from '/base.js';
import {Cover,Taxon,Axis,Status,ref,patio,localClock,recordDesk,selectField,statusMark,related,timeField,pivotCell} from '/patrol.js';

import {extraFieldPages,renderField} from '/field_extensions.js';

const pages = {routes:'样线登记',log:'野外记录',review:'巡护复核',pivot:'工时透视',...extraFieldPages};
const hints = {
  routes:'在计划日期和小组下登记巡护班，核对样线最低工时。',
  log:'按实际当地时间标记出发、逐种观察和返回。',
  review:'区分完整巡护、确认零观测和提前原路折返。',
  pivot:'把已复核的计数和有效工时按维度汇总，再生成带口径的快照。',
};

function routes(view,role) {
  return `<div class="field-columns routes-columns">
    <section class="field-panel route-map"><h2>样线册</h2><ol>${view.routes.map(route =>
    `<li data-cover="${h(route.cover)}"><span class="trail-code">${h(route.code)}</span>
      <div><strong>${h(route.label)}</strong><span>${Cover[route.cover]} · ${route.km} km</span></div>
      <span>至少 ${route.min_minutes} 分钟</span></li>`).join('')}</ol></section>
    <section class="field-panel"><h2>安排巡护班</h2>
    ${role === 'operator' ? `<form data-action="book">
      ${selectField('route_code','样线',Object.fromEntries(view.routes.map(row => [row.code,row.label])),'WX')}
      <label>高原当地日期<input type="date" name="walked_on" value="2026-11-23" required></label>
      <label>小组<input name="crew" placeholder="例如 晚霞组" minlength="2" maxlength="60" required></label>
      <button>登记巡护班</button></form>` : '<p>录入员可为样线安排巡护班。</p>'}
    <h2>最近巡护班</h2><ul class="roster">
    ${view.patrols.slice(0,7).map(row => `<li><button type="button" data-open="${row.id}">${h(related(row))}</button>${statusMark(row.status)}</li>`).join('')}</ul>
    </section></div>`;
}

function log(view,role) {
  const row = view.active;
  if (!row) return '<p>暂无巡护班。请先在样线登记创建计划。</p>';
  const canWrite = role === 'operator';
  return `<div class="field-columns">
    <section class="field-panel"><div class="log-title"><h2>${h(row.route_label)} · ${h(row.crew)}</h2>${statusMark(row.status)}</div>
      <ol class="stamp-line">
        <li><span>出发</span><strong>${h(localClock(row.started_at))}</strong></li>
        <li><span>累计观测</span><strong>${row.observed_count} 只</strong></li>
        <li><span>返回</span><strong>${h(localClock(row.ended_at))}</strong></li>
      </ol>
      <h3>逐种观察</h3>
      ${view.birds.length ? `<table><thead><tr><th>时刻</th><th>鸟种分类</th><th>个体数</th></tr></thead>
       <tbody>${view.birds.map(item => `<tr><td>${h(localClock(item.observed_at))}</td><td>${Taxon[item.taxon]}</td><td>${item.tally}</td></tr>`).join('')}</tbody></table>` :
       `<p class="field-note">${row.zero_declared ? '返回时明确确认未观测到鸟。' : '暂未登记观测。完成路线时如未见鸟，返回栏需确认零观测。'}</p>`}
      ${canWrite && row.status === 'walking' ? `<form data-action="birds" class="bird-form">
        ${timeField('observed_at','观察时间',row.walked_on+'T08:15')}
        ${selectField('taxon','鸟种分类',Taxon,'duck')}<label>个体数<input name="tally" type="number" min="1" max="500" required></label>
        <button>追加观察</button></form>` : ''}
    </section><aside class="field-panel log-forms">
      <h2>${row.status === 'booked' ? '记录出发' : '返回登记'}</h2>
      ${canWrite && row.status === 'booked' ?
        `<form data-action="start">${timeField('started_at','实际开始',row.walked_on+'T08:00')}<button>标记出发</button></form>` :
        canWrite && row.status === 'walking' ? `<form data-action="return">${timeField('ended_at','实际返回',row.walked_on+'T09:00')}
        <label class="check-row"><input name="completed_route" type="checkbox" checked>走完全程并到终点</label>
        <label class="check-row"><input name="zero_declared" type="checkbox">确认未观测到任何鸟</label>
        <label>折返原因<input name="early_reason" maxlength="300" placeholder="未到终点时必填"></label>
        <button>提交巡护记录</button></form>` :
        `<p>${row.review_note ? h(row.review_note) : '由值班复核员检查完整度和工时。'}</p>`}
      <p class="field-note">该班线路最低工时 ${row.min_minutes} 分钟，长度与地表见样线册。</p>
      ${row.status === 'returned' ? '<a class="field-link" href="#review">查看待复核班</a>' : ''}
    </aside></div>`;
}

function review(view,role) {
  const rows = view.patrols.filter(row => ['returned','valid','excluded'].includes(row.status));
  const row = view.active;
  if (!row) return '<p>暂无巡护班可复核。</p>';
  const minutes = row.ended_at ? (new Date(row.ended_at) - new Date(row.started_at))/60000 : null;
  return `<div class="field-columns review-columns">
    <section class="field-panel"><h2>返回及已核查</h2><ul class="roster review-roster">${rows.map(entry =>
      `<li><button data-select="${entry.id}" type="button">${h(related(entry))}<small>${h(entry.walked_on)} · ${entry.observed_count} 只</small></button>
      ${statusMark(entry.status)}</li>`).join('')}</ul></section>
    <section class="field-panel"><div class="log-title"><h2>${h(related(row))}</h2>${statusMark(row.status)}</div>
      <dl class="review-slip"><dt>到达终点</dt><dd>${row.completed_route === null ? '未登记' : row.completed_route ? '是' : '未到，提前折返'}</dd>
      <dt>实际 / 样线最低工时</dt><dd>${minutes === null ? '未登记' : minutes.toFixed(0)+' 分钟'} / ${row.min_minutes} 分钟</dd>
      <dt>记录只数</dt><dd>${row.observed_count} 只${row.zero_declared ? '（已明确声明零观测）' : ''}</dd>
      <dt>折返原因</dt><dd>${h(row.early_reason ?? '无')}</dd><dt>复核结论</dt><dd>${h(row.review_note ?? '待定')}</dd></dl>
      ${role === 'reviewer' && row.status === 'returned' ? '<form data-action="review"><button>复核并确认统计资格</button></form>' : ''}
      <p class="field-note">提前折返或未达最低工时的记录保留在日志，观测与工时均不进入透视。</p>
    </section></div>`;
}

function pivot(view,role) {
  const item = view.snapshot;
  const result = item?.result;
  const keyLabel = (key,axis) => axis === 'cover' ? Cover[key] : key;
  return `<div class="field-columns pivot-columns">
    <section class="field-panel matrix-panel"><h2>${h(item?.label ?? '冻结透视')}</h2>
      ${item ? `<p class="field-note">${h(item.date_from)} 至 ${h(item.date_to)} · ${item.taxon ? Taxon[item.taxon] : '全部鸟种'} · ${result ? '已冻结' : '后台计算中'}</p>` : ''}
      ${result?.rows.length ? `<div class="matrix-scroll"><table class="matrix">
        <caption>只/小时 · 行 ${Axis[item.row_axis]} × 列 ${Axis[item.col_axis]}</caption>
        <thead><tr><th>${Axis[item.row_axis]}</th>${result.columns.map(col => `<th scope="col">${h(keyLabel(col.key,item.col_axis))}</th>`).join('')}<th>汇总</th></tr></thead>
        <tbody>${result.rows.map(row => `<tr><th scope="row">${h(keyLabel(row.key,item.row_axis))}</th>${row.cells.map(cell =>
          `<td>${pivotCell(cell)}</td>`).join('')}<td>${pivotCell(row.total)}</td></tr>`).join('')}</tbody>
        <tfoot><tr><th scope="row">总计</th>${result.columns.map(col => `<td>${pivotCell(col.total)}</td>`).join('')}<td>${pivotCell(result.grand_total)}</td></tr></tfoot>
        </table></div>` : '<p>当前范围暂无已复核的有效巡护。</p>'}
      ${result ? `<details class="trace-note"><summary>复核范围：纳入 ${result.included_walks.length} 班 · 剔除 ${result.excluded_walks.length} 班 · 未复核 ${result.unreviewed_walks.length} 班</summary>
        <p>纳入：${result.included_walks.map(ref).join('、') || '无'}</p>
        <ul>${result.excluded_walks.map(row => `<li>${ref(row.id)} · ${h(row.reason)}</li>`).join('')}</ul></details>` : ''}
    </section><aside class="field-panel snapshot-form"><h2>统计口径</h2>
      ${view.snapshots.length ? selectField('snapshot','已存透视',Object.fromEntries(view.snapshots.map(row => [row.id,row.label])),item?.id) : ''}
      ${role === 'operator' ? `<form data-action="snapshot"><label>快照标题<input name="label" placeholder="例如 十一月巡护周报" maxlength="100" minlength="2" required></label>
      <label>起始日<input name="date_from" type="date" value="2026-11-16" required></label>
      <label>结束日<input name="date_to" type="date" value="2026-11-23" required></label>
      <div class="axis-fields">${selectField('row_axis','行',Axis,'route')}${selectField('col_axis','列',Axis,'week')}</div>
      ${selectField('taxon','计数范围',{'':'全部鸟种',...Taxon},'')}
      <button>生成透视快照</button></form>` : ''}
      <p class="field-note">限定鸟种仅改变计数，仍以同组全部有效工时为分母。有效零保留在分母。</p>
    </aside></div>`;
}

const views = {routes,log,review,pivot};
async function render(page,outlet,user,flash = '') {
  if(Object.hasOwn(extraFieldPages,page))return renderField(page,outlet,user,flash);
  const view = await recordDesk.fetch(page);
  if (!outlet.isConnected) return;
  outlet.innerHTML = `<div class="fieldbook"><header class="field-head"><div><h1>${pages[page]}</h1>
    <p>${hints[page]}</p></div>
    ${['log','review'].includes(page) && view.patrols.length ? selectField('active','巡护班',
      Object.fromEntries(view.patrols.map(row => [row.id,related(row)])),view.active?.id) : ''}</header>
    <p role="status" class="field-message">${h(flash)}</p>${views[page](view,user.role)}</div>`;
  const status = outlet.querySelector('.field-message');
  const choose = async (key,id) => {
    recordDesk[key] = Number(id);
    try { await render(page,outlet,user); }
    catch (error) { status.textContent = error.message; status.dataset.type = 'error'; }
  };
  outlet.querySelector('[name=active]')?.addEventListener('change', event => choose('patrolId',event.target.value));
  outlet.querySelector('[name=snapshot]')?.addEventListener('change', event => choose('snapshotId',event.target.value));
  for (const button of outlet.querySelectorAll('[data-select]')) button.onclick = () => choose('patrolId',button.dataset.select);
  for (const button of outlet.querySelectorAll('[data-open]')) button.onclick = () => {
    recordDesk.patrolId = Number(button.dataset.open);
    location.hash = '#log';
  };
  for (const form of outlet.querySelectorAll('form[data-action]')) form.onsubmit = async event => {
    event.preventDefault();
    const button = event.submitter;
    if (button) button.disabled = true;
    const fields = Object.fromEntries(new FormData(form));
    const action = form.dataset.action;
    status.textContent = '正在处理…';
    status.dataset.type = 'success';
    try {
      if (action === 'book') {
        recordDesk.patrolId = (await api('/api/patrols','POST',fields)).id;
        location.hash = '#log';
        return;
      }
      if (action === 'snapshot') {
        fields.taxon ||= null;
        const queued = await api('/api/effort','POST',fields);
        recordDesk.snapshotId = queued.id;
        await waitJob(queued.job_id);
      } else {
        for (const field of ['started_at','ended_at','observed_at']) if (fields[field]) fields[field] += ':00+08:00';
        if (action === 'birds') fields.tally = Number(fields.tally);
        if (action === 'return') {
          fields.completed_route = form.elements.completed_route.checked;
          fields.zero_declared = form.elements.zero_declared.checked;
          fields.early_reason ||= null;
        }
        await api(patio(view.active.id,action),'POST',fields);
      }
      if (outlet.contains(form)) await render(page,outlet,user,'已更新巡护记录');
    } catch (error) {
      status.textContent = error.message;
      status.dataset.type = 'error';
    } finally {
      if (button) button.disabled = false;
    }
  };
}
mount({title:'高原样线',kicker:'岭北湿地巡护站',pages,render});
