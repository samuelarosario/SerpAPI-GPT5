import { useEffect, useMemo, useState } from 'react';
import Login from './Login';

function useAuthToken() {
  const [token, setToken] = useState<string | null>(null);
  useEffect(() => { setToken(localStorage.getItem('access_token')); }, []);
  return token;
}

function ymd(d: Date) { return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`; }
function addDays(y: string, n: number) { const d = new Date(y + 'T00:00:00'); d.setDate(d.getDate()+n); return ymd(d); }
function isIata(s: string){ return /^[A-Z]{3}$/.test((s||'').trim().toUpperCase()); }
function ymdToDate(y?: string){ if(!y) return null; const d=new Date(y+"T00:00:00"); return isNaN(d.getTime())? null : d; }
function daysFromToday(y?: string){ const d=ymdToDate(y); if(!d) return null; const now=new Date(); const td=new Date(now.getFullYear(), now.getMonth(), now.getDate()); const dd=new Date(d.getFullYear(), d.getMonth(), d.getDate()); return Math.round((dd.getTime()-td.getTime())/86400000); }
function fmtDuration(mins?: number){ if(mins==null||isNaN(mins)) return ''; const h=Math.floor(mins/60), m=mins%60; return `${h} hr ${m} min`; }
function fmtHM(ts?: string){
  if(!ts) return '';
  // Accepts 'YYYY-MM-DD HH:MM[:SS]' or ISO-like; fallback to raw
  try{
    if(/^[0-9]{4}-[0-9]{2}-[0-9]{2}[ T][0-9]{2}:[0-9]{2}/.test(ts)){
      const s = ts.replace(' ', 'T');
      const d = new Date(s);
      if(!isNaN(d.getTime())) return d.toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'});
    }
    const d = new Date(ts);
    if(!isNaN(d.getTime())) return d.toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'});
  }catch{}
  // Fallback: try to extract HH:MM
  const m = ts.match(/([0-9]{1,2}:[0-9]{2}(?: *[AP]M)?)/i);
  return m? m[1] : ts;
}
function summarizeFlight(f: any){
  const segs = Array.isArray(f?.flights)? f.flights : [];
  const a = segs.length? (segs[0]?.departure_airport?.id||'') : '';
  const b = segs.length? (segs[segs.length-1]?.arrival_airport?.id||'') : '';
  const route = (a && b)? `${a} → ${b}` : 'Flight';
  const price = f?.price || 'N/A';
  const duration = fmtDuration(Number(f?.total_duration));
  const stops = Math.max(0, segs.length - 1);
  return { route, price, duration, stops };
}

const tomorrow = () => { const d = new Date(); d.setDate(d.getDate()+1); return ymd(d); };

export default function App() {
  const token = useAuthToken();
  const [authed, setAuthed] = useState<boolean | null>(null);
  const [origin, setOrigin] = useState('');
  const [dest, setDest] = useState('');
  const [date, setDate] = useState(tomorrow());
  const [ret, setRet] = useState('');
  const [trip, setTrip] = useState<'round'|'oneway'>('round');
  const [tclass, setTclass] = useState('1');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [outbound, setOutbound] = useState<any[]>([]);
  const [inbound, setInbound] = useState<any[]>([]);
  const minRet = useMemo(() => date ? addDays(date, 1) : '', [date]);

  useEffect(() => { if(trip === 'oneway') setRet(''); }, [trip]);
  useEffect(() => { if(ret && date && ret <= date) setRet(''); }, [date, ret]);
  useEffect(() => {
    (async () => {
      if(!token){ setAuthed(false); return; }
      try{
        const r = await fetch('/auth/me', { headers: { Authorization: `Bearer ${token}` } });
        setAuthed(r.ok);
      } catch { setAuthed(false); }
    })();
  }, [token]);
  function ItineraryCard({ f }: { f: any }) {
    const s = summarizeFlight(f);
    const segs: any[] = Array.isArray(f?.flights) ? f.flights : [];
    const layovers: any[] = Array.isArray(f?.layovers) ? f.layovers : [];
    const travelClassMap: Record<string,string> = { '1':'Economy', '2':'Premium Economy', '3':'Business', '4':'First' };
    const cls = travelClassMap[tclass] ?? 'Economy';

    const rowStyle: React.CSSProperties = { display:'grid', gridTemplateColumns:'16px 1fr', gap:12, alignItems:'start' };
    const dot: React.CSSProperties = { width:8, height:8, borderRadius:999, background:'#9aa0a6', marginTop:6 };
    const pipe: React.CSSProperties = { borderLeft:'2px dotted #d1d5db', marginLeft:3, paddingLeft:0, height:'100%' };
    const small: React.CSSProperties = { fontSize:12, color:'#5f6368' };
    const strong: React.CSSProperties = { fontWeight:600 };

    return (
      <details style={{border:'1px solid #e5e7eb', borderRadius:12, padding:12, marginBottom:12, background:'#0f172a0a'}}>
        <summary style={{display:'flex', justifyContent:'space-between', alignItems:'center', cursor:'pointer', listStyle:'none'}}>
          <div style={{display:'flex', gap:8, alignItems:'center', flexWrap:'wrap'}}>
            <span style={{fontWeight:600}}>{s.route}</span>
            <span style={{...small}}>• {s.stops} stops • {s.duration}</span>
            {f?.eco_note && (
              <span style={{display:'inline-block', background:'#DCFCE7', color:'#166534', border:'1px solid #86EFAC', borderRadius:6, padding:'2px 8px', fontSize:12}}>
                {String(f.eco_note)}
              </span>
            )}
          </div>
          <div style={{fontSize:16, fontWeight:700}}>{s.price}</div>
        </summary>
        <div style={{marginTop:12, display:'grid', gridTemplateColumns:'auto 1fr', gap:0}}>
          <div style={{gridColumn:'1 / span 1'}}></div>
          <div style={{gridColumn:'2 / span 1'}}></div>
          <div style={{gridColumn:'1 / span 1', ...pipe}}></div>
          <div style={{gridColumn:'2 / span 1'}}>
            {/* Segments timeline */}
            {segs.length === 0 ? (
              <div style={{...small}}>No segment details available.</div>
            ) : (
              <div style={{display:'flex', flexDirection:'column', gap:10}}>
                {segs.map((seg:any, i:number) => {
                  const depCode = seg?.departure_airport?.id || '';
                  const arrCode = seg?.arrival_airport?.id || '';
                  const depName = seg?.departure_airport?.name || depCode;
                  const arrName = seg?.arrival_airport?.name || arrCode;
                  const airline = seg?.airline || '';
                  const fnum = seg?.flight_number || '';
                  const aircraft = seg?.aircraft || '';
                  const depT = fmtHM(seg?.departure_time);
                  const arrT = fmtHM(seg?.arrival_time);
                  const dur = fmtDuration(Number(seg?.duration));
                  const lay = layovers[i]; // layover after this segment (i -> between i and i+1)
                  return (
                    <div key={i}>
                      <div style={rowStyle}>
                        <div style={{display:'flex', flexDirection:'column', alignItems:'center'}}>
                          <div style={dot}></div>
                        </div>
                        <div>
                          <div style={{display:'flex', justifyContent:'space-between', gap:8}}>
                            <div>
                              <div style={strong}>{depT} • {depName} ({depCode})</div>
                              <div style={small}>Travel time: {dur}</div>
                            </div>
                            <div style={{textAlign:'right'}}>
                              <div style={strong}>{arrT} • {arrName} ({arrCode})</div>
                            </div>
                          </div>
                          <div style={{...small, marginTop:4}}>
                            {[airline, cls, aircraft].filter(Boolean).join(' • ')}{fnum? ` • ${airline ? '' : 'Flight '}#${fnum}`:''}
                          </div>
                        </div>
                      </div>
                      {lay && (
                        <div style={{margin:'10px 0 0 0'}}>
                          <div style={rowStyle}>
                            <div style={{display:'flex', flexDirection:'column', alignItems:'center'}}>
                              <div style={{width:8, height:8}}></div>
                            </div>
                            <div>
                              <div style={{background:'#FEF3C7', border:'1px solid #FDE68A', color:'#92400E', borderRadius:8, padding:'8px 10px', display:'flex', justifyContent:'space-between', alignItems:'center'}}>
                                <div style={{fontSize:13}}>
                                  <span style={{fontWeight:700}}>{fmtDuration(Number(lay?.duration))} layover</span>
                                  {` • ${lay?.name || lay?.id || (arrName + ' (' + arrCode + ')')}`}
                                </div>
                                {lay?.overnight && (
                                  <div style={{display:'flex', alignItems:'center', gap:6, color:'#B91C1C', fontWeight:700}} title="Overnight layover">
                                    <span aria-hidden>⚠️</span>
                                    <span>Overnight</span>
                                  </div>
                                )}
                              </div>
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </details>
    );
  }

  

  async function authFetch(path: string) {
  const tok = localStorage.getItem('access_token');
  if(!tok) throw new Error('Not authenticated');
  const r = await fetch(path, { headers: { Authorization: `Bearer ${tok}` } });
    return r;
  }

  async function search() {
    setError(null);
    if(!origin || !dest || !date) { setError('All fields are required.'); return; }
    if(!isIata(origin) || !isIata(dest)) { setError('Use 3-letter IATA codes for origin/destination.'); return; }
    const df = daysFromToday(date); if(df==null || df < 1){ setError('Outbound must be at least 1 day from today.'); return; }
    if(trip !== 'oneway'){
      if(!ret){ setError('Return date is required for 2-way.'); return; }
      const od=ymdToDate(date), rd=ymdToDate(ret); if(!rd || (od && rd <= od)){ setError('Return date must be after outbound.'); return; }
    }
    setBusy(true);
    try {
      const q1 = `/api/flight_search?origin=${encodeURIComponent(origin)}&destination=${encodeURIComponent(dest)}&date=${encodeURIComponent(date)}&travel_class=${encodeURIComponent(tclass)}&one_way=1`;
      const r1 = await authFetch(q1); const j1 = await r1.json();
      if(!j1?.success){ setError(j1?.error||'Search failed'); setBusy(false); return; }
      const out = [
        ...(Array.isArray(j1?.data?.best_flights)? j1.data.best_flights : []),
        ...(Array.isArray(j1?.data?.other_flights)? j1.data.other_flights : [])
      ];
      setOutbound(out);
      if(trip !== 'oneway' && ret){
        const q2 = `/api/flight_search?origin=${encodeURIComponent(dest)}&destination=${encodeURIComponent(origin)}&date=${encodeURIComponent(ret)}&travel_class=${encodeURIComponent(tclass)}&one_way=1`;
        const r2 = await authFetch(q2); const j2 = await r2.json();
        if(!j2?.success){ setError(j2?.error||'Inbound failed'); setBusy(false); return; }
        const inn = [
          ...(Array.isArray(j2?.data?.best_flights)? j2.data.best_flights : []),
          ...(Array.isArray(j2?.data?.other_flights)? j2.data.other_flights : [])
        ];
        setInbound(inn);
      } else {
        setInbound([]);
      }
    } finally { setBusy(false); }
  }

  if(!authed){
    return <Login onLogin={()=> setAuthed(true)} />;
  }
  return (
    <div style={{fontFamily:'Inter, system-ui, sans-serif', padding:16}}>
      <h2>SerpFlights (React) <span style={{fontSize:12, padding:'2px 6px', border:'1px solid #ddd', borderRadius:4, marginLeft:8}}>V2</span></h2>
      <div style={{display:'flex', gap:8, flexWrap:'wrap', alignItems:'center'}}>
        <input placeholder="Origin (IATA)" value={origin} onChange={e=>setOrigin(e.target.value.toUpperCase())} maxLength={3} style={{width:140}} />
        <input placeholder="Destination (IATA)" value={dest} onChange={e=>setDest(e.target.value.toUpperCase())} maxLength={3} style={{width:160}} />
        <input type="date" value={date} onChange={e=>setDate(e.target.value)} />
        <input type="date" value={ret} onChange={e=>setRet(e.target.value)} min={minRet} disabled={trip==='oneway'} />
        <select value={trip} onChange={e=>setTrip(e.target.value as any)}>
          <option value="round">2-way</option>
          <option value="oneway">1-way</option>
        </select>
        <select value={tclass} onChange={e=>setTclass(e.target.value)}>
          <option value="1">Economy</option>
          <option value="2">Premium</option>
          <option value="3">Business</option>
          <option value="4">First</option>
        </select>
        <button onClick={search} disabled={busy}>{busy?'Searching…':'Search'}</button>
      </div>
      {error && <div style={{color:'#b91c1c', marginTop:8}}>{error}</div>}
      <div style={{display:'flex', gap:24, marginTop:16}}>
        <div style={{flex:1}}>
          <h3 style={{margin:'8px 0'}}>Outbound {outbound.length? `(${outbound.length})`: ''}</h3>
          {outbound.length===0 ? <div style={{color:'#5f6368'}}>No results.</div> : outbound.slice(0,20).map((f,i)=> (
            <ItineraryCard key={i} f={f} />
          ))}
        </div>
        <div style={{flex:1}}>
          <h3 style={{margin:'8px 0'}}>Inbound {inbound.length? `(${inbound.length})`: ''}</h3>
          {inbound.length===0 ? <div style={{color:'#5f6368'}}>No results.</div> : inbound.slice(0,20).map((f,i)=> (
            <ItineraryCard key={i} f={f} />
          ))}
        </div>
      </div>
    </div>
  );
}
