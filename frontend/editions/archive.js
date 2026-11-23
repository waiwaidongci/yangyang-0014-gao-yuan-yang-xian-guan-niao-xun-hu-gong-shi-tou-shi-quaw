import {h} from '/base.js';
import {Axis,Taxon} from '/patrol.js';

export const readers={station:'站务',field_team:'巡护小组',education:'科普组'};
export function editionBox(row,mail,role) {
  return `<article class="edition-record"><div class="edition-caption">
    <span>V${row.volume}</span><div><h2>${h(row.label)}</h2><p>${h(row.series)} · ${h(row.date_from)} 至 ${h(row.date_to)}
      · ${Axis[row.row_axis]} / ${Axis[row.col_axis]} · ${Taxon[row.taxon] ?? '全部'}</p></div></div>
      ${row.reason ? `<p>更正说明：${h(row.reason)}</p>` : ''}
      <ul>${mail.map(item=>`<li><span>${readers[item.audience]}</span>
        ${item.received_at ? '<span>已登记收件</span>' : role==='operator' ?
        `<form data-station-path="/api/editions/${row.id}/inbox/${item.audience}/receive"><button>登记收到</button></form>` :
        '<span>待收到</span>'}</li>`).join('')}</ul>
      <button type="button" class="quiet" data-csv="/api/editions/${row.id}/matrix" data-name="${h(row.series)}-v${row.volume}.csv">下载冻结矩阵</button>
      </article>`;
}
