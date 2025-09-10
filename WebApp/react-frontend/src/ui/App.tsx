import React, { useEffect, useMemo, useState } from 'react';
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
          {outbound.length===0 ? <div style={{color:'#5f6368'}}>No results.</div> : outbound.slice(0,20).map((f,i)=> {
            const s = summarizeFlight(f);
            return (
            <div key={i} style={{border:'1px solid #e5e7eb', borderRadius:8, padding:12, marginBottom:10}}>
              <div style={{display:'flex', justifyContent:'space-between'}}>
                <div>{s.route}</div>
                <div>{s.price}</div>
              </div>
              <div style={{fontSize:12, color:'#5f6368'}}>{s.stops} stops • {s.duration}</div>
            </div>
            );
          })}
        </div>
        <div style={{flex:1}}>
          <h3 style={{margin:'8px 0'}}>Inbound {inbound.length? `(${inbound.length})`: ''}</h3>
          {inbound.length===0 ? <div style={{color:'#5f6368'}}>No results.</div> : inbound.slice(0,20).map((f,i)=>{
            const s = summarizeFlight(f);
            return (
            <div key={i} style={{border:'1px solid #e5e7eb', borderRadius:8, padding:12, marginBottom:10}}>
              <div style={{display:'flex', justifyContent:'space-between'}}>
                <div>{s.route}</div>
                <div>{s.price}</div>
              </div>
              <div style={{fontSize:12, color:'#5f6368'}}>{s.stops} stops • {s.duration}</div>
            </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
