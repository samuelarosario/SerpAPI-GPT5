import { useEffect, useMemo, useState, useRef, memo, forwardRef, useImperativeHandle } from 'react';
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

// Format price as "$ 12,345" (thousands separated, no decimals). Falls back to raw if unparseable.
function formatUSD(val: any): string {
  const toNum = (v: any): number | null => {
    if (typeof v === 'number' && isFinite(v)) return v;
    if (typeof v === 'string') {
      const m = v.replace(/[^0-9.]/g, '');
      const n = parseFloat(m);
      return isNaN(n) ? null : n;
    }
    return null;
  };
  const n = toNum(val);
  if (n == null) return String(val ?? 'N/A');
  const body = new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 }).format(n);
  return `\$ ${body}`;
}

function stopsCount(f: any){
  const segs = Array.isArray(f?.flights)? f.flights : [];
  return Math.max(0, segs.length - 1);
}
function totalDurationMinutes(f: any){
  const td = Number(f?.total_duration);
  if(!isNaN(td)) return td;
  const segs = Array.isArray(f?.flights)? f.flights : [];
  const sum = segs.reduce((acc:number, s:any)=> acc + (Number(s?.duration)||0), 0);
  return sum || 0;
}
function sortFlightsByStops(list: any[]){
  return [...(list||[])].sort((a,b)=>{
    const sa = stopsCount(a), sb = stopsCount(b);
    if (sa !== sb) return sa - sb; // fewer stops first
    const da = totalDurationMinutes(a), db = totalDurationMinutes(b);
    return da - db; // shorter total duration next
  });
}

const tomorrow = () => { const d = new Date(); d.setDate(d.getDate()+1); return ymd(d); };

type AirlineMetaMap = Record<string, { code: string; name: string }>;
type AirportMetaMap = Record<string, { code: string; name?: string; country?: string; country_code?: string; city?: string }>;

const ItineraryCard = memo(function ItineraryCard({ f, tclass, airlineMeta, airportMeta }: { f: any; tclass: string; airlineMeta: AirlineMetaMap; airportMeta: AirportMetaMap; }){
  const s = summarizeFlight(f);
  const segs: any[] = Array.isArray(f?.flights) ? f.flights : [];
  const layovers: any[] = Array.isArray(f?.layovers) ? f.layovers : [];
  const travelClassMap: Record<string,string> = { '1':'Economy', '2':'Premium Economy', '3':'Business', '4':'First' };
  const cls = travelClassMap[tclass] ?? 'Economy';
  const priceText = formatUSD(f?.price ?? s.price);
  const [showData, setShowData] = useState(false);
  const detailsRef = useRef<HTMLDetailsElement | null>(null);

  const rowStyle: React.CSSProperties = { display:'grid', gridTemplateColumns:'16px 1fr', gap:12, alignItems:'start' };
  const dot: React.CSSProperties = { width:8, height:8, borderRadius:999, background:'#9aa0a6', marginTop:6 };
  const pipe: React.CSSProperties = { borderLeft:'2px dotted #d1d5db', marginLeft:3, paddingLeft:0, height:'100%' };
  const small: React.CSSProperties = { fontSize:12, color:'#5f6368' };
  const strong: React.CSSProperties = { fontWeight:600 };

  return (
    <details ref={detailsRef} style={{border:'1px solid #e5e7eb', borderRadius:12, padding:12, marginBottom:12, background:'#0f172a0a'}}>
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
        <div style={{display:'flex', alignItems:'center', gap:10}}>
          <button type="button" onClick={(e)=>{ e.preventDefault(); e.stopPropagation(); setShowData(v=>{ const nv=!v; if(nv && detailsRef.current){ detailsRef.current.open = true; } return nv; }); }}
            style={{fontSize:11, padding:'2px 8px', border:'1px solid #d1d5db', borderRadius:999, background:'#fff', color:'#475569', cursor:'pointer'}}>
            {showData? 'Hide data' : 'Data info'}
          </button>
          <div style={{fontSize:16, fontWeight:700}}>{priceText}</div>
        </div>
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
                const alCode = String(seg?.airline_code || '').toUpperCase();
                const derivedCode = (() => { const s=String(seg?.flight_number||'').toUpperCase(); const m=s.match(/^([A-Z0-9]{2,3})\s*#?\s*\d/); return m? m[1] : ''; })();
                const codeFromAirlineField = (() => { const a = String(seg?.airline||'').toUpperCase().trim(); return /^[A-Z0-9]{2,3}$/.test(a) ? a : ''; })();
                const prefCode = (alCode || derivedCode || codeFromAirlineField);
                const metaName = prefCode ? airlineMeta[prefCode]?.name : undefined;
                let airlineName = (seg?.airline_name || seg?.airline || '').toString();
                if ((!airlineName || /^[A-Z0-9]{2,3}$/.test(airlineName)) && metaName) {
                  airlineName = String(metaName);
                } else if (!airlineName && prefCode) {
                  airlineName = prefCode; // final fallback to code
                }
                const fnum = seg?.flight_number || '';
                const aircraft = seg?.aircraft || '';
                const depT = fmtHM(seg?.departure_time);
                const arrT = fmtHM(seg?.arrival_time);
                const dur = fmtDuration(Number(seg?.duration));
                const lay = layovers[i]; // layover after this segment
                const layDurMin = Number(lay?.duration) || 0;
                const isShortLayover = layDurMin > 0 && layDurMin < 120; // < 2 hours
                const layCode = String(lay?.id || arrCode || '').toUpperCase();
                const layMeta = layCode ? airportMeta[layCode] : undefined;
                const layLabel = layMeta?.country ? `${layMeta.country} (${layCode})` : (lay?.name || lay?.id || (arrName + ' (' + arrCode + ')'));
                const noticeStyle: React.CSSProperties = isShortLayover
                  ? { background:'#FEE2E2', border:'1px solid #FCA5A5', color:'#991B1B', borderRadius:8, padding:'8px 10px', display:'flex', justifyContent:'space-between', alignItems:'center' }
                  : { background:'#FEF3C7', border:'1px solid #FDE68A', color:'#92400E', borderRadius:8, padding:'8px 10px', display:'flex', justifyContent:'space-between', alignItems:'center' };
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
                          {[airlineName, cls, aircraft].filter(Boolean).join(' • ')}{fnum? ` • ${airlineName ? '' : 'Flight '}${String(fnum).replace(/^#\s*/, '')}`:''}
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
                            <div style={noticeStyle}>
                              <div style={{fontSize:13}}>
                                <span style={{fontWeight:700}}>{fmtDuration(Number(lay?.duration))} layover</span>
                                {` • ${layLabel}`}
                              </div>
                              {isShortLayover ? (
                                <div style={{display:'flex', alignItems:'center', gap:6, color:'#991B1B', fontWeight:700}} title="Short layover">
                                  <span aria-hidden>⚠️</span>
                                  <span>Short layover — you could miss the next flight</span>
                                </div>
                              ) : (lay?.overnight && (
                                <div style={{display:'flex', alignItems:'center', gap:6, color:'#B91C1C', fontWeight:700}} title="Overnight layover">
                                  <span aria-hidden>⚠️</span>
                                  <span>Overnight</span>
                                </div>
                              ))}
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

          {/* Data info section */}
          {showData && (
            <div style={{marginTop:12, border:'1px dashed #cbd5e1', background:'#f8fafc', borderRadius:8, padding:10}}>
              <div style={{fontSize:12, color:'#0f172a', marginBottom:6}}>
                <strong>Used fields (per segment):</strong> departure_airport.id, departure_airport.name, arrival_airport.id, arrival_airport.name, departure_time, arrival_time, airline_name, flight_number, aircraft, duration
              </div>
              <div style={{fontSize:12, color:'#0f172a', marginBottom:6}}>
                <strong>Used fields (flight-level):</strong> price, total_duration, flights[], layovers[]
              </div>
              <div style={{display:'flex', flexDirection:'column', gap:8}}>
                {segs.map((seg:any, i:number) => {
                  const topKeys = Object.keys(seg || {}).sort();
                  const depKeys = seg?.departure_airport && typeof seg.departure_airport === 'object' ? Object.keys(seg.departure_airport).sort() : [];
                  const arrKeys = seg?.arrival_airport && typeof seg.arrival_airport === 'object' ? Object.keys(seg.arrival_airport).sort() : [];
                  return (
                    <div key={'k'+i} style={{fontSize:12, background:'#fff', border:'1px solid #e5e7eb', borderRadius:6, padding:8}}>
                      <div style={{fontWeight:600, marginBottom:4}}>Segment {i+1}: {seg?.departure_airport?.id || '?'} → {seg?.arrival_airport?.id || '?'}</div>
                      <div><span style={{color:'#475569'}}>Top-level keys:</span> {topKeys.join(', ') || '—'}</div>
                      <div><span style={{color:'#475569'}}>departure_airport keys:</span> {depKeys.join(', ') || '—'}</div>
                      <div><span style={{color:'#475569'}}>arrival_airport keys:</span> {arrKeys.join(', ') || '—'}</div>
                    </div>
                  );
                })}
                {layovers.length > 0 && (
                  <div style={{fontSize:12, background:'#fff', border:'1px solid #e5e7eb', borderRadius:6, padding:8}}>
                    <div style={{fontWeight:600, marginBottom:4}}>Layovers</div>
                    {layovers.map((lv:any, i:number) => (
                      <div key={'l'+i} style={{marginBottom:4}}>
                        <span style={{color:'#475569'}}>Layover {i+1} keys:</span> {Object.keys(lv||{}).sort().join(', ') || '—'}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </details>
  );
});

// Module-level helper: authFetch reads token from localStorage (no App closure needed)
async function authFetch(path: string, opts?: { allowNoAuth?: boolean }) {
  const tok = localStorage.getItem('access_token');
  const headers: Record<string,string> = {};
  if (tok) headers.Authorization = `Bearer ${tok}`;
  else if (!opts?.allowNoAuth) throw new Error('Not authenticated');
  const r = await fetch(path, { headers });
  return r;
}

// Shared type for airport input ref
type AirportInputRef = { getValue: () => string; setValue: (v: string) => void; focus: () => void };

// Native datalist-based airport input (module-scoped to avoid remounts)
const AirportSuggestInput = forwardRef<AirportInputRef, {
  placeholder: string;
  style?: React.CSSProperties;
  airportsReady: boolean;
  airportList: Array<{code:string; city?:string; country?:string}>;
}>(function AirportSuggestInput({ placeholder, style, airportsReady, airportList }, ref){
  const [value, setValue] = useState('');
  const [items, setItems] = useState<Array<{code:string; city?:string; country?:string}>>([]);
  const timerRef = useRef<number | null>(null);
  const listIdRef = useRef<string>(`ap-list-${Math.random().toString(36).slice(2)}`);
  const listId = listIdRef.current;
  const inputRef = useRef<HTMLInputElement | null>(null);

  useImperativeHandle(ref, () => ({
    getValue: () => value,
    setValue: (v: string) => setValue(v ?? ''),
    focus: () => { inputRef.current?.focus(); }
  }), [value]);

  useEffect(() => {
    if(timerRef.current){ window.clearTimeout(timerRef.current); timerRef.current = null; }
    const q = (value||'').trim();
    if(!q || q.length < 2){ setItems([]); return; }
    timerRef.current = window.setTimeout(async () => {
      const qq = q.toLowerCase();
      if(airportsReady && airportList.length){
        const res = airportList.filter(a => {
          const code = (a.code||'').toLowerCase();
          const city = (a.city||'').toLowerCase();
          const country = (a.country||'').toLowerCase();
          return code.includes(qq) || city.includes(qq) || country.includes(qq);
        }).slice(0, 10);
        setItems(res);
        return;
      }
      // Fallback to server suggest if list not ready
      try{
        const r = await authFetch(`/api/airports/suggest?q=${encodeURIComponent(q)}&limit=10`, { allowNoAuth: true });
        const j = await r.json();
        if(Array.isArray(j)) setItems(j); else setItems([]);
      }catch{
        try{ const r2 = await fetch(`/api/airports/suggest?q=${encodeURIComponent(q)}&limit=10`); const j2 = await r2.json(); setItems(Array.isArray(j2)? j2 : []); }catch{ setItems([]); }
      }
    }, 150) as unknown as number;
  }, [value, airportsReady, airportList]);

  const onInput = (e: React.ChangeEvent<HTMLInputElement>) => { setValue(e.target.value); };
  const onOptionSelect = (e: React.ChangeEvent<HTMLInputElement>) => { setValue(e.target.value); };

  return (
    <div style={{ position:'relative', ...style }}>
      <input ref={inputRef} list={listId} placeholder={placeholder} value={value} onChange={onInput} onInput={onOptionSelect} style={{ width:'100%' }} />
      <datalist id={listId}>
        {items.map((it, i) => {
          const label = `${(it.code||'').toUpperCase()}${it.city?` (${it.city})`:''}${it.country?`, ${it.country}`:''}`;
          return <option key={it.code+String(i)} value={(it.code||'').toUpperCase()} label={label} />;
        })}
      </datalist>
    </div>
  );
});

export default function App() {
  const token = useAuthToken();
  const [authed, setAuthed] = useState<boolean | null>(null);
  // Criteria values captured on search submit (avoid re-render on each keystroke)
  const [criteriaOrigin, setCriteriaOrigin] = useState('');
  const [date, setDate] = useState(tomorrow());
  const [ret, setRet] = useState('');
  const [trip, setTrip] = useState<'round'|'oneway'>('round');
  const [tclass, setTclass] = useState('1');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [outbound, setOutbound] = useState<any[]>([]);
  const [inbound, setInbound] = useState<any[]>([]);
  const [meta, setMeta] = useState<{ out?: { source?: string; cacheAgeHours?: number; searchId?: string; total: number; best: number; other: number }; in?: { source?: string; cacheAgeHours?: number; searchId?: string; total: number; best: number; other: number } }>({});
  const [airportMeta, setAirportMeta] = useState<Record<string, { code: string; country?: string; city?: string }>>({});
  const [airlineMeta, setAirlineMeta] = useState<Record<string, { code: string; name: string }>>({});
  // Preload airports once per session
  const [airportList, setAirportList] = useState<Array<{code:string; city?:string; country?:string}>>([]);
  const [airportsReady, setAirportsReady] = useState(false);
  const minRet = useMemo(() => date ? addDays(date, 1) : '', [date]);
  // Outbound must be at least +1 day from today
  const minOut = useMemo(() => tomorrow(), []);

  // Session-level airport cache (preloaded on first mount)
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const resp = await authFetch('/api/airports/all', { allowNoAuth: true });
        const data = await resp.json();
        if(!cancelled && Array.isArray(data)) { setAirportList(data); setAirportsReady(true); }
      } catch {
        try {
          const r2 = await fetch('/api/airports/all');
          const d2 = await r2.json();
          if(!cancelled && Array.isArray(d2)) { setAirportList(d2); setAirportsReady(true); }
        } catch { if(!cancelled) setAirportsReady(false); }
      }
    })();
    return () => { cancelled = true; };
  }, []);

  // Native datalist-based airport input (like V2)
  const originRef = useRef<AirportInputRef | null>(null);
  const destRef = useRef<AirportInputRef | null>(null);

  useEffect(() => { if(trip === 'oneway') setRet(''); }, [trip]);
  // Auto-correct outbound date if user tries to set earlier than allowed
  useEffect(() => { if(date && minOut && date < minOut) setDate(minOut); }, [date, minOut]);
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
  
  async function handleLogout(){
    try{
      const t = localStorage.getItem('access_token');
      if(t){ await fetch('/auth/logout', { method:'POST', headers:{ Authorization: `Bearer ${t}` } }); }
    }catch{}
    try{ localStorage.removeItem('access_token'); localStorage.removeItem('refresh_token'); }catch{}
    setAuthed(false);
  }

  

  async function authFetch(path: string, opts?: { allowNoAuth?: boolean }) {
    const tok = localStorage.getItem('access_token');
    const headers: Record<string,string> = {};
    if (tok) headers.Authorization = `Bearer ${tok}`;
    else if (!opts?.allowNoAuth) throw new Error('Not authenticated');
    const r = await fetch(path, { headers });
    return r;
  }

  // Enrich airport metadata for IATA codes via backend batch endpoint
  async function fetchAirportMetaForCodes(codes: string[]) {
    const list = Array.from(new Set((codes||[]).map(c => String(c||'').trim().toUpperCase()).filter(Boolean)));
    const missing = list.filter(c => !airportMeta[c]);
    if(missing.length === 0) return;
    try{
  let rr = await authFetch(`/api/airports/by_codes?codes=${encodeURIComponent(missing.join(','))}`, { allowNoAuth: true });
      const jj = await rr.json();
      if(Array.isArray(jj)){
        const map: Record<string, any> = {};
        for(const row of jj){ if(row && row.code){ map[String(row.code).toUpperCase()] = row; } }
        setAirportMeta(prev => ({ ...prev, ...map }));
      }
    }catch{
      // Fallback unauthenticated fetch (endpoint is public)
      try {
        const rr2 = await fetch(`/api/airports/by_codes?codes=${encodeURIComponent(missing.join(','))}`);
        const jj2 = await rr2.json();
        if(Array.isArray(jj2)){
          const map: Record<string, any> = {};
          for(const row of jj2){ if(row && row.code){ map[String(row.code).toUpperCase()] = row; } }
          setAirportMeta(prev => ({ ...prev, ...map }));
        }
      } catch {}
    }
  }

  // Enrich airline names by airline codes via backend batch endpoint
  async function fetchAirlineMetaForCodes(codes: string[]) {
    const list = Array.from(new Set((codes||[]).map(c => String(c||'').trim().toUpperCase()).filter(Boolean)));
    const missing = list.filter(c => !airlineMeta[c]);
    if(missing.length === 0) return;
    try{
  let rr = await authFetch(`/api/airlines/by_codes?codes=${encodeURIComponent(missing.join(','))}`, { allowNoAuth: true });
      const jj = await rr.json();
      if(Array.isArray(jj)){
        const map: Record<string, any> = {};
        for(const row of jj){ if(row && row.code){ map[String(row.code).toUpperCase()] = { code: String(row.code).toUpperCase(), name: row.name || row.code }; } }
        setAirlineMeta(prev => ({ ...prev, ...map }));
      }
    }catch{
      // Fallback unauthenticated fetch (endpoint is public)
      try {
        const rr2 = await fetch(`/api/airlines/by_codes?codes=${encodeURIComponent(missing.join(','))}`);
        const jj2 = await rr2.json();
        if(Array.isArray(jj2)){
          const map: Record<string, any> = {};
          for(const row of jj2){ if(row && row.code){ map[String(row.code).toUpperCase()] = { code: String(row.code).toUpperCase(), name: row.name || row.code }; } }
          setAirlineMeta(prev => ({ ...prev, ...map }));
        }
      } catch {}
    }
  }

  // keep values when switching dates or trip type

  async function search() {
    setError(null);
    const O = (originRef.current?.getValue() || '').trim().toUpperCase();
    const D = (destRef.current?.getValue() || '').trim().toUpperCase();
    if(!O || !D || !date) { setError('All fields are required.'); return; }
    if(!isIata(O) || !isIata(D)) { setError('Use 3-letter IATA codes for origin/destination (select from suggestions).'); return; }
    const df = daysFromToday(date); if(df==null || df < 1){ setError('Outbound must be at least 1 day from today.'); return; }
    if(trip !== 'oneway'){
      if(!ret){ setError('Return date is required for 2-way.'); return; }
      const od=ymdToDate(date), rd=ymdToDate(ret); if(!rd || (od && rd <= od)){ setError('Return date must be after outbound.'); return; }
    }
    setBusy(true);
    try {
  setCriteriaOrigin(O);
  const q1 = `/api/flight_search?origin=${encodeURIComponent(O)}&destination=${encodeURIComponent(D)}&date=${encodeURIComponent(date)}&travel_class=${encodeURIComponent(tclass)}&one_way=1`;
      const r1 = await authFetch(q1); const j1 = await r1.json();
      if(!j1?.success){ setError(j1?.error||'Search failed'); setBusy(false); return; }
  const outBest = Array.isArray(j1?.data?.best_flights)? j1.data.best_flights : [];
  const outOther = Array.isArray(j1?.data?.other_flights)? j1.data.other_flights : [];
  const out = [
        ...outBest,
        ...outOther
      ];
  setOutbound(sortFlightsByStops(out));
      setMeta(m => ({
        ...m,
        out: {
          source: j1?.source,
          cacheAgeHours: typeof j1?.cache_age_hours === 'number' ? j1.cache_age_hours : undefined,
          searchId: typeof j1?.search_id === 'string' ? j1.search_id : undefined,
          total: (outBest?.length||0) + (outOther?.length||0),
          best: outBest?.length||0,
          other: outOther?.length||0
        }
      }));
      const collectAirportCodes = (list:any[]) => {
        const set = new Set<string>();
        for(const f of list||[]){
          const segs = Array.isArray(f?.flights)? f.flights : [];
          const lays = Array.isArray(f?.layovers)? f.layovers : [];
          segs.forEach((seg:any) => { const ac = seg?.arrival_airport?.id; if(ac) set.add(String(ac).toUpperCase()); });
          lays.forEach((lv:any) => { const lc = lv?.id; if(lc) set.add(String(lc).toUpperCase()); });
        }
        return Array.from(set);
      };
  const collectAirlineCodes = (list:any[]) => {
        const set = new Set<string>();
        const deriveFromFlight = (fn:any):string => {
          const s = String(fn||'').toUpperCase();
          const m = s.match(/^([A-Z0-9]{2,3})\s*#?\s*\d/);
          return m? m[1] : '';
        };
        for(const f of list||[]){
          const segs = Array.isArray(f?.flights)? f.flights : [];
          segs.forEach((seg:any) => {
            const code = String(seg?.airline_code || deriveFromFlight(seg?.flight_number) || '').toUpperCase().trim();
            if(code) set.add(code);
    const a = String(seg?.airline||'').toUpperCase().trim();
    if(/^[A-Z0-9]{2,3}$/.test(a)) set.add(a);
          });
        }
        return Array.from(set);
      };
      let codesToFetch = collectAirportCodes(out);
      let airlineCodes = collectAirlineCodes(out);
      if(trip !== 'oneway' && ret){
        const q2 = `/api/flight_search?origin=${encodeURIComponent(D)}&destination=${encodeURIComponent(O)}&date=${encodeURIComponent(ret)}&travel_class=${encodeURIComponent(tclass)}&one_way=1`;
        const r2 = await authFetch(q2); const j2 = await r2.json();
        if(!j2?.success){ setError(j2?.error||'Inbound failed'); setBusy(false); return; }
  const inBest = Array.isArray(j2?.data?.best_flights)? j2.data.best_flights : [];
  const inOther = Array.isArray(j2?.data?.other_flights)? j2.data.other_flights : [];
  const inn = [
          ...inBest,
          ...inOther
        ];
  setInbound(sortFlightsByStops(inn));
        setMeta(m => ({
          ...m,
          in: {
            source: j2?.source,
            cacheAgeHours: typeof j2?.cache_age_hours === 'number' ? j2.cache_age_hours : undefined,
            searchId: typeof j2?.search_id === 'string' ? j2.search_id : undefined,
            total: (inBest?.length||0) + (inOther?.length||0),
            best: inBest?.length||0,
            other: inOther?.length||0
          }
        }));
        codesToFetch = Array.from(new Set([...codesToFetch, ...collectAirportCodes(inn)]));
        airlineCodes = Array.from(new Set([...airlineCodes, ...collectAirlineCodes(inn)]));
      } else {
        setInbound([]);
        setMeta(m => ({ ...m, in: undefined }));
      }
      await fetchAirportMetaForCodes(codesToFetch);
      await fetchAirlineMetaForCodes(airlineCodes);
    } finally { setBusy(false); }
  }

  if(!authed){
    return <Login onLogin={()=> setAuthed(true)} />;
  }
  return (
    <div style={{fontFamily:'Inter, system-ui, sans-serif', padding:16}}>
      <div style={{display:'flex', alignItems:'center', justifyContent:'space-between'}}>
        <h2>Flight Search</h2>
        {authed && (
          <button onClick={handleLogout} style={{fontSize:12, padding:'4px 10px', border:'1px solid #d1d5db', borderRadius:6, background:'#fff', color:'#475569', cursor:'pointer'}}>
            Logout
          </button>
        )}
      </div>
      <div style={{display:'flex', gap:12, rowGap:8, flexWrap:'wrap', alignItems:'flex-end'}}>
        <AirportSuggestInput ref={originRef} placeholder="Origin (code, name, city, country)" style={{ width: 260, flex: '0 0 260px' }} airportsReady={airportsReady} airportList={airportList} />
        <AirportSuggestInput ref={destRef} placeholder="Destination (code, name, city, country)" style={{ width: 280, flex: '0 0 280px' }} airportsReady={airportsReady} airportList={airportList} />
        <input type="date" value={date} onChange={e=>setDate(e.target.value)} min={minOut} style={{ minWidth: 160, flex: '0 0 auto' }} />
        <input type="date" value={ret} onChange={e=>setRet(e.target.value)} min={minRet} disabled={trip==='oneway'} style={{ minWidth: 160, flex: '0 0 auto' }} />
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
      {/* Meta info panel */}
      {(meta.out || meta.in) && (
        <div style={{marginTop:12, border:'1px solid #e5e7eb', background:'#f8fafc', borderRadius:8, padding:10, color:'#334155'}}>
          <div style={{fontSize:13, marginBottom:6}}>
              <strong>Criteria:</strong> {criteriaOrigin||'—'} on {date||'—'}{trip!=='oneway' && ret? ` • return ${ret}`:''} • class {({ '1':'Economy','2':'Premium Economy','3':'Business','4':'First' } as any)[tclass] || 'Economy'}
          </div>
          {meta.out && (
            <div style={{fontSize:12, marginBottom:4}}>
              <strong>Outbound:</strong> {meta.out.total} results (best {meta.out.best}, other {meta.out.other}) — Source: {meta.out.source || 'unknown'}{typeof meta.out.cacheAgeHours==='number'? ` (age ${meta.out.cacheAgeHours.toFixed(1)}h)` : ''}{meta.out.searchId? ` • id ${meta.out.searchId}`:''}
            </div>
          )}
          {meta.in && (
            <div style={{fontSize:12}}>
              <strong>Inbound:</strong> {meta.in.total} results (best {meta.in.best}, other {meta.in.other}) — Source: {meta.in.source || 'unknown'}{typeof meta.in.cacheAgeHours==='number'? ` (age ${meta.in.cacheAgeHours.toFixed(1)}h)` : ''}{meta.in.searchId? ` • id ${meta.in.searchId}`:''}
            </div>
          )}
        </div>
      )}
      <div style={{display:'flex', gap:24, marginTop:16}}>
        <div style={{flex:1}}>
          <h3 style={{margin:'8px 0', display:'flex', alignItems:'center', gap:8}}>
            <span>Outbound {outbound.length? `(${outbound.length})`: ''}</span>
            {meta.out?.source && (
              <span style={{fontSize:11, padding:'2px 6px', border:'1px solid #ddd', borderRadius:999, color:'#475569', background:'#fff'}} title={typeof meta.out.cacheAgeHours==='number'? `Cache age: ${meta.out.cacheAgeHours.toFixed(1)}h` : (meta.out.searchId? `Search ID: ${meta.out.searchId}` : '')}>
                {meta.out.source.toUpperCase()}
              </span>
            )}
          </h3>
          {outbound.length===0 ? <div style={{color:'#5f6368'}}>No results.</div> : outbound.slice(0,20).map((f,i)=> (
            <ItineraryCard key={i} f={f} tclass={tclass} airlineMeta={airlineMeta} airportMeta={airportMeta} />
          ))}
        </div>
        <div style={{flex:1}}>
          <h3 style={{margin:'8px 0', display:'flex', alignItems:'center', gap:8}}>
            <span>Inbound {inbound.length? `(${inbound.length})`: ''}</span>
            {meta.in?.source && (
              <span style={{fontSize:11, padding:'2px 6px', border:'1px solid #ddd', borderRadius:999, color:'#475569', background:'#fff'}} title={typeof meta.in.cacheAgeHours==='number'? `Cache age: ${meta.in.cacheAgeHours.toFixed(1)}h` : (meta.in.searchId? `Search ID: ${meta.in.searchId}` : '')}>
                {meta.in.source.toUpperCase()}
              </span>
            )}
          </h3>
          {inbound.length===0 ? <div style={{color:'#5f6368'}}>No results.</div> : inbound.slice(0,20).map((f,i)=> (
            <ItineraryCard key={i} f={f} tclass={tclass} airlineMeta={airlineMeta} airportMeta={airportMeta} />
          ))}
        </div>
      </div>
    </div>
  );
}
