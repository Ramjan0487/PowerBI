/* dashboard.js — live KPIs, Chart.js charts, activity feed */
(function(){
  let typeChart, riskChart, trendChart;

  function fmtMoney(v){
    if(v>=1e6) return '$'+(v/1e6).toFixed(1)+'M';
    if(v>=1e3) return '$'+(v/1e3).toFixed(0)+'K';
    return '$'+Math.round(v);
  }

  function initCharts(){
    const typeCtx  = document.getElementById('typeChart');
    const riskCtx  = document.getElementById('riskChart');
    const trendCtx = document.getElementById('trendChart');
    const dark = window.matchMedia('(prefers-color-scheme:dark)').matches;
    const tickColor = dark?'#94a3b8':'#64748b';
    const gridColor = dark?'rgba(255,255,255,.06)':'rgba(0,0,0,.06)';

    if(typeCtx) typeChart = new Chart(typeCtx,{
      type:'doughnut',
      data:{labels:[],datasets:[{data:[],backgroundColor:['#3b7dd8','#0f6e56','#854f0b','#7c3aed','#a32d2d','#0e4d7b'],borderWidth:0}]},
      options:{responsive:true,maintainAspectRatio:true,plugins:{legend:{position:'right',labels:{color:tickColor,font:{size:11},boxWidth:10}}}}
    });
    if(riskCtx) riskChart = new Chart(riskCtx,{
      type:'doughnut',
      data:{labels:['Low','Medium','High','Critical'],datasets:[{data:[0,0,0,0],backgroundColor:['#16a34a','#d97706','#f97316','#dc2626'],borderWidth:0}]},
      options:{responsive:true,maintainAspectRatio:true,plugins:{legend:{position:'right',labels:{color:tickColor,font:{size:11},boxWidth:10}}}}
    });
    if(trendCtx) trendChart = new Chart(trendCtx,{
      type:'bar',
      data:{labels:[],datasets:[{label:'Contracts',data:[],backgroundColor:'rgba(59,125,216,.7)',borderRadius:4}]},
      options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},
        scales:{x:{ticks:{color:tickColor,font:{size:11}},grid:{color:gridColor}},
                y:{ticks:{color:tickColor,font:{size:11}},grid:{color:gridColor},beginAtZero:true}}}
    });
  }

  async function refreshKPIs(){
    try{
      const res  = await fetch('/dashboard/api/kpis',{credentials:'same-origin'});
      const data = await res.json();

      setText('kpiTotal',  data.total);
      setText('kpiActive', data.active);
      setText('kpiExp30',  data.expiring_30d);
      setText('kpiExp90',  data.expiring_90d);
      setText('kpiValue',  fmtMoney(data.total_value||0));
      setText('kpiSms',    (data.sms_sent_today||0)+(data.email_sent_today||0));

      if(typeChart && data.by_type){
        typeChart.data.labels = Object.keys(data.by_type);
        typeChart.data.datasets[0].data = Object.values(data.by_type);
        typeChart.update('none');
      }
      if(riskChart && data.risk_dist){
        const r = data.risk_dist||{};
        riskChart.data.datasets[0].data = [r.LOW||0,r.MEDIUM||0,r.HIGH||0,r.CRITICAL||0];
        riskChart.update('none');
      }
      if(trendChart && data.monthly_trend){
        trendChart.data.labels = data.monthly_trend.map(m=>m.month);
        trendChart.data.datasets[0].data = data.monthly_trend.map(m=>m.count);
        trendChart.update('none');
      }
    } catch(e){ console.warn('KPI fetch failed',e); }
  }

  async function refreshExpiring(){
    const tbody = document.getElementById('expiringTbody');
    if(!tbody) return;
    try{
      const res  = await fetch('/api/v1/contracts/expiring?days=30',{credentials:'same-origin'});
      const data = await res.json();
      if(!data.length){ tbody.innerHTML='<tr><td colspan="6" class="loading-row" style="color:var(--success)">No contracts expiring in the next 30 days</td></tr>'; return; }
      tbody.innerHTML = data.map(c=>{
        const days = c.days_left;
        const cls  = days<=7?'days-urgent':days<=30?'days-warn':'days-ok';
        const risk = c.risk_level||'—';
        const riskCls = `risk-badge risk-${risk}`;
        return `<tr>
          <td><div style="font-size:13px;font-weight:500">${c.title}</div><div style="font-size:11px;color:var(--text-muted);font-family:monospace">${c.ref}</div></td>
          <td style="font-size:12px">${c.counterparty||'—'}</td>
          <td style="font-size:12px">${c.end_date}</td>
          <td><span class="days-badge ${cls}">${days}d</span></td>
          <td><span class="${riskCls}">${risk}</span></td>
          <td><a href="/contracts/${c.ref}" class="btn btn-ghost btn-sm">View</a></td>
        </tr>`;
      }).join('');
    } catch(e){ tbody.innerHTML='<tr><td colspan="6" class="loading-row">Failed to load</td></tr>'; }
  }

  async function refreshActivity(){
    const feed = document.getElementById('activityFeed');
    if(!feed) return;
    try{
      const res  = await fetch('/dashboard/api/activity',{credentials:'same-origin'});
      const data = await res.json();
      feed.innerHTML = data.slice(0,20).map(l=>`
        <div class="act-item">
          <span class="act-action">${l.action}</span>
          <span class="act-detail"> — ${l.detail||''}</span>
          <div class="act-time">${l.time} · ${l.ip||''}</div>
        </div>`).join('');
    } catch(e){ if(feed) feed.textContent='Feed unavailable'; }
  }

  function setText(id,val){ const el=document.getElementById(id); if(el) el.textContent=val; }

  // Init
  initCharts();
  refreshKPIs();
  refreshExpiring();
  refreshActivity();
  setInterval(refreshKPIs, 15000);
  setInterval(refreshActivity, 30000);
})();
